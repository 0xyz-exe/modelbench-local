import json
import uuid
import datetime
import asyncio
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.db.database import get_connection
from backend.app.monitoring.system import get_system_info, get_current_metrics
from backend.app.benchmark.engine import engine
from backend.app.adapters.ollama import OllamaAdapter
from backend.app.adapters.llama_cpp import LlamaCppAdapter
from backend.app.adapters.fake import FakeInferenceAdapter
from backend.app.services.export_service import (
    generate_json_report, generate_csv_report, generate_markdown_report, generate_html_report
)

router = APIRouter(prefix="/api")

# Schemas
class BackendCreate(BaseModel):
    name: str
    type: str  # ollama, llama_cpp, fake, openai_compatible
    base_url: str

class BenchmarkCreate(BaseModel):
    name: str = "Standard Model Benchmark"
    model_ids: List[str]
    dataset_ids: List[str]
    warmup_iterations: int = Field(default=1, ge=0, le=5)
    measured_iterations: int = Field(default=2, ge=1, le=20)
    concurrency: int = Field(default=1, ge=1, le=8)
    max_tokens: int = Field(default=128, ge=16, le=2048)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    seed: Optional[int] = 42
    timeout_seconds: float = Field(default=45.0, ge=5.0, le=300.0)

class DatasetCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    category: str

class TestCaseCreate(BaseModel):
    case_id: str
    category: str
    prompt: str
    expected_output: Optional[str] = None
    evaluation_type: str = "none"
    criteria_json: Optional[str] = None
    language: str = "en"
    max_tokens: int = 256

# Health & System
@router.get("/health")
def get_health():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "mode": "local-first"
    }

@router.get("/system/info")
def system_info():
    return get_system_info()

@router.get("/system/metrics")
def system_metrics():
    return get_current_metrics()

# Backends
@router.get("/backends")
def list_backends():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM backends ORDER BY created_at ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.post("/backends")
def create_backend(payload: BackendCreate):
    conn = get_connection()
    backend_id = f"backend_{uuid.uuid4().hex[:8]}"
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO backends VALUES (?, ?, ?, ?, ?, ?)",
        (backend_id, payload.name, payload.type, payload.base_url, 1, now)
    )
    conn.commit()
    conn.close()
    return {"id": backend_id, "message": "Backend created"}

@router.get("/backends/{backend_id}/health")
async def check_backend_health(backend_id: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM backends WHERE id = ?", (backend_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Backend not found")

    b_type = row["type"]
    b_url = row["base_url"]
    adapter = engine.get_adapter(b_type, backend_id, b_url)
    return await adapter.health_check()

# Models
@router.get("/models")
def list_models():
    conn = get_connection()
    rows = conn.execute("""
        SELECT m.*, b.name as backend_name, b.type as backend_type
        FROM models m
        JOIN backends b ON m.backend_id = b.id
        ORDER BY m.name ASC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.post("/models/refresh")
async def refresh_models():
    conn = get_connection()
    backends = conn.execute("SELECT * FROM backends WHERE is_active = 1").fetchall()
    discovered_count = 0
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    for b in backends:
        adapter = engine.get_adapter(b["type"], b["id"], b["base_url"])
        try:
            models = await adapter.list_models()
            for m in models:
                conn.execute("""
                    INSERT INTO models (id, backend_id, name, identifier, size_bytes, parameter_count, quantization, context_length, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        size_bytes=excluded.size_bytes,
                        parameter_count=excluded.parameter_count,
                        quantization=excluded.quantization,
                        context_length=excluded.context_length,
                        last_seen=excluded.last_seen
                """, (
                    m.id, m.backend_id, m.name, m.identifier, m.size_bytes,
                    m.parameter_count, m.quantization, m.context_length, now
                ))
                discovered_count += 1
        except Exception:
            pass

    conn.commit()
    conn.close()
    return {"status": "refreshed", "discovered_count": discovered_count}

# Datasets
@router.get("/datasets")
def list_datasets():
    conn = get_connection()
    datasets = conn.execute("""
        SELECT d.*, COUNT(c.id) as case_count
        FROM datasets d
        LEFT JOIN dataset_cases c ON d.id = c.dataset_id
        GROUP BY d.id
        ORDER BY d.is_builtin DESC, d.name ASC
    """).fetchall()
    conn.close()
    return [dict(d) for d in datasets]

@router.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: str):
    conn = get_connection()
    dataset = conn.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
    if not dataset:
        conn.close()
        raise HTTPException(status_code=404, detail="Dataset not found")
    cases = conn.execute("SELECT * FROM dataset_cases WHERE dataset_id = ?", (dataset_id,)).fetchall()
    conn.close()
    return {
        "dataset": dict(dataset),
        "cases": [dict(c) for c in cases]
    }

@router.post("/datasets")
def create_dataset(payload: DatasetCreate):
    conn = get_connection()
    ds_id = f"ds_{uuid.uuid4().hex[:8]}"
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO datasets VALUES (?, ?, ?, ?, ?, ?)",
        (ds_id, payload.name, payload.description, payload.category, 0, now)
    )
    conn.commit()
    conn.close()
    return {"id": ds_id, "message": "Custom dataset created"}

@router.post("/datasets/{dataset_id}/cases")
def add_case_to_dataset(dataset_id: str, payload: TestCaseCreate):
    conn = get_connection()
    cid = f"case_{uuid.uuid4().hex[:8]}"
    conn.execute("""
        INSERT INTO dataset_cases (id, dataset_id, case_id, category, prompt, expected_output, evaluation_type, criteria_json, language, max_tokens, is_enabled)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (
        cid, dataset_id, payload.case_id, payload.category, payload.prompt,
        payload.expected_output, payload.evaluation_type, payload.criteria_json,
        payload.language, payload.max_tokens
    ))
    conn.commit()
    conn.close()
    return {"id": cid, "message": "Test case created"}

# Benchmarks
@router.get("/benchmarks")
def list_benchmarks():
    conn = get_connection()
    runs = conn.execute("SELECT * FROM benchmark_runs ORDER BY started_at DESC LIMIT 50").fetchall()
    result = []
    for r in runs:
        item = dict(r)
        # Fetch best tps if completed
        m = conn.execute("SELECT MAX(mean_tps) as best_tps, AVG(average_quality_score) as avg_q FROM benchmark_metrics WHERE run_id = ?", (r["id"],)).fetchone()
        item["best_tps"] = round(m["best_tps"] or 0.0, 1) if m else 0.0
        item["avg_quality"] = round(m["avg_q"] or 0.0, 2) if m else 0.0
        result.append(item)
    conn.close()
    return result

@router.post("/benchmarks")
async def create_benchmark(payload: BenchmarkCreate):
    run_id = f"run_{uuid.uuid4().hex[:10]}"
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn = get_connection()
    conn.execute("""
        INSERT INTO benchmark_runs (id, name, status, config_json, total_requests, completed_requests, error_count, started_at)
        VALUES (?, ?, 'pending', ?, 0, 0, 0, ?)
    """, (run_id, payload.name, payload.model_dump_json(), now))
    conn.commit()
    conn.close()

    # Trigger background execution
    await engine.start_run(run_id)
    return {"run_id": run_id, "status": "started"}

@router.get("/benchmarks/{run_id}")
def get_benchmark(run_id: str):
    conn = get_connection()
    run = conn.execute("SELECT * FROM benchmark_runs WHERE id = ?", (run_id,)).fetchone()
    if not run:
        conn.close()
        raise HTTPException(status_code=404, detail="Benchmark not found")

    metrics = conn.execute("""
        SELECT bm.*, m.name as model_name, m.identifier as model_identifier, m.quantization, m.parameter_count
        FROM benchmark_metrics bm
        JOIN models m ON bm.model_id = m.id
        WHERE bm.run_id = ?
    """, (run_id,)).fetchall()

    iterations = conn.execute("""
        SELECT bi.*, dc.prompt, dc.category, m.name as model_name
        FROM benchmark_iterations bi
        LEFT JOIN dataset_cases dc ON bi.case_id = dc.id
        LEFT JOIN models m ON bi.model_id = m.id
        WHERE bi.run_id = ? AND bi.is_warmup = 0
        ORDER BY bi.created_at ASC
    """, (run_id,)).fetchall()

    samples = conn.execute("SELECT * FROM system_samples WHERE run_id = ? ORDER BY timestamp ASC", (run_id,)).fetchall()
    conn.close()

    return {
        "run": dict(run),
        "config": json.loads(run["config_json"]) if run["config_json"] else {},
        "metrics": [dict(m) for m in metrics],
        "iterations": [dict(it) for it in iterations],
        "samples": [dict(s) for s in samples]
    }

@router.post("/benchmarks/{run_id}/cancel")
async def cancel_benchmark_run(run_id: str):
    success = await engine.cancel_run(run_id)
    return {"run_id": run_id, "cancelled": success}

@router.get("/benchmarks/{run_id}/stream")
async def stream_benchmark_progress(run_id: str):
    q = engine.register_listener(run_id)

    async def event_generator():
        try:
            while True:
                event = await q.get()
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") in ("completed", "cancelled", "failed"):
                    break
        finally:
            engine.unregister_listener(run_id, q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Model Comparison
@router.get("/comparisons")
def compare_models(model_ids: Optional[str] = Query(None)):
    conn = get_connection()
    if model_ids:
        ids = [i.strip() for i in model_ids.split(",") if i.strip()]
        placeholders = ",".join(["?"] * len(ids))
        query = f"""
            SELECT bm.*, m.name as model_name, m.identifier, m.quantization, m.parameter_count, br.name as run_name, br.completed_at
            FROM benchmark_metrics bm
            JOIN models m ON bm.model_id = m.id
            JOIN benchmark_runs br ON bm.run_id = br.id
            WHERE bm.model_id IN ({placeholders})
            ORDER BY bm.mean_tps DESC
        """
        rows = conn.execute(query, ids).fetchall()
    else:
        rows = conn.execute("""
            SELECT bm.*, m.name as model_name, m.identifier, m.quantization, m.parameter_count, br.name as run_name, br.completed_at
            FROM benchmark_metrics bm
            JOIN models m ON bm.model_id = m.id
            JOIN benchmark_runs br ON bm.run_id = br.id
            ORDER BY bm.mean_tps DESC LIMIT 20
        """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Reports Export
@router.get("/reports/{run_id}/export")
def export_report(run_id: str, format: str = Query("json")):
    fmt = format.lower()
    if fmt == "csv":
        csv_data = generate_csv_report(run_id)
        return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=modelbench_{run_id}.csv"})
    elif fmt == "markdown" or fmt == "md":
        md_data = generate_markdown_report(run_id)
        return Response(content=md_data, media_type="text/markdown", headers={"Content-Disposition": f"attachment; filename=modelbench_{run_id}.md"})
    elif fmt == "html":
        html_data = generate_html_report(run_id)
        return Response(content=html_data, media_type="text/html", headers={"Content-Disposition": f"attachment; filename=modelbench_{run_id}.html"})
    else:
        return generate_json_report(run_id)
