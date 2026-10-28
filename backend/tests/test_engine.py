import pytest
import asyncio
from backend.app.db.database import init_db, get_connection
from backend.app.benchmark.engine import engine
from backend.app.services.export_service import generate_json_report, generate_markdown_report, generate_html_report

@pytest.mark.asyncio
async def test_full_benchmark_run_lifecycle():
    init_db()

    conn = get_connection()
    # Ensure fake model is available
    m = conn.execute("SELECT id FROM models WHERE backend_id = 'backend_fake' LIMIT 1").fetchone()
    if not m:
        conn.execute("""
            INSERT INTO models (id, backend_id, name, identifier, size_bytes, parameter_count, quantization, context_length, last_seen)
            VALUES ('backend_fake_test_model', 'backend_fake', 'Test Model', 'simulated-7b-q4', 1000, '7B', 'Q4', 2048, '2026-10-28T00:00:00Z')
        """)
        conn.commit()
        model_id = 'backend_fake_test_model'
    else:
        model_id = m["id"]

    ds = conn.execute("SELECT id FROM datasets LIMIT 1").fetchone()
    dataset_id = ds["id"]
    conn.close()

    run_id = "test_run_auto_1"
    config = {
        "model_ids": [model_id],
        "dataset_ids": [dataset_id],
        "warmup_iterations": 0,
        "measured_iterations": 1,
        "concurrency": 1,
        "max_tokens": 32,
        "temperature": 0.5,
        "seed": 42,
        "timeout_seconds": 10.0
    }

    import json
    conn = get_connection()
    conn.execute("DELETE FROM benchmark_runs WHERE id = ?", (run_id,))
    conn.execute("""
        INSERT INTO benchmark_runs (id, name, status, config_json, total_requests, completed_requests, error_count, started_at)
        VALUES (?, 'Test Benchmark Run', 'pending', ?, 0, 0, 0, '2026-10-28T12:00:00Z')
    """, (run_id, json.dumps(config)))
    conn.commit()
    conn.close()

    # Execute run
    await engine._execute_run(run_id)

    # Verify run completed
    conn = get_connection()
    run = conn.execute("SELECT * FROM benchmark_runs WHERE id = ?", (run_id,)).fetchone()
    assert run["status"] == "completed"
    assert run["completed_requests"] > 0

    metrics = conn.execute("SELECT * FROM benchmark_metrics WHERE run_id = ?", (run_id,)).fetchall()
    assert len(metrics) > 0
    assert metrics[0]["mean_tps"] > 0
    assert metrics[0]["successful_iterations"] > 0
    conn.close()

    # Test report export
    json_rep = generate_json_report(run_id)
    assert json_rep["run"]["id"] == run_id
    assert len(json_rep["metrics"]) > 0

    md_rep = generate_markdown_report(run_id)
    assert "# ModelBench Local Report" in md_rep

    html_rep = generate_html_report(run_id)
    assert "<!DOCTYPE html>" in html_rep
    assert "ModelBench Local Report" in html_rep
