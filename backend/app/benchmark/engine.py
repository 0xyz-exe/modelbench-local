import asyncio
import datetime
import json
import uuid
from typing import Dict, Any, List, Optional
from backend.app.core.config import settings
from backend.app.db.database import get_connection
from backend.app.monitoring.system import get_current_metrics
from backend.app.adapters.base import BaseModelAdapter
from backend.app.adapters.ollama import OllamaAdapter
from backend.app.adapters.llama_cpp import LlamaCppAdapter
from backend.app.adapters.fake import FakeInferenceAdapter
from backend.app.evaluators.manager import evaluate_output
from backend.app.benchmark.metrics import aggregate_iteration_metrics

class BenchmarkEngine:
    def __init__(self):
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.cancel_flags: Dict[str, bool] = {}
        self.listeners: Dict[str, List[asyncio.Queue]] = {}

    def get_adapter(self, backend_type: str, backend_id: str, base_url: str) -> BaseModelAdapter:
        if backend_type == "ollama":
            return OllamaAdapter(backend_id=backend_id, base_url=base_url)
        elif backend_type == "llama_cpp":
            return LlamaCppAdapter(backend_id=backend_id, base_url=base_url)
        elif backend_type == "fake":
            return FakeInferenceAdapter(backend_id=backend_id, base_url=base_url)
        else:
            # Fallback to Ollama or Fake
            return FakeInferenceAdapter(backend_id=backend_id, base_url=base_url)

    def register_listener(self, run_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        if run_id not in self.listeners:
            self.listeners[run_id] = []
        self.listeners[run_id].append(q)
        return q

    def unregister_listener(self, run_id: str, q: asyncio.Queue):
        if run_id in self.listeners and q in self.listeners[run_id]:
            self.listeners[run_id].remove(q)

    async def broadcast_event(self, run_id: str, event_data: Dict[str, Any]):
        if run_id in self.listeners:
            for q in list(self.listeners[run_id]):
                try:
                    await q.put(event_data)
                except Exception:
                    pass

    async def cancel_run(self, run_id: str) -> bool:
        if run_id in self.active_tasks:
            self.cancel_flags[run_id] = True
            task = self.active_tasks[run_id]
            task.cancel()
            conn = get_connection()
            conn.execute(
                "UPDATE benchmark_runs SET status = 'cancelled', completed_at = ? WHERE id = ?",
                (datetime.datetime.now(datetime.timezone.utc).isoformat(), run_id)
            )
            conn.commit()
            conn.close()
            await self.broadcast_event(run_id, {"type": "cancelled", "run_id": run_id})
            return True
        return False

    async def start_run(self, run_id: str):
        task = asyncio.create_task(self._execute_run(run_id))
        self.active_tasks[run_id] = task
        self.cancel_flags[run_id] = False

    async def _execute_run(self, run_id: str):
        conn = get_connection()
        run = conn.execute("SELECT * FROM benchmark_runs WHERE id = ?", (run_id,)).fetchone()
        if not run:
            conn.close()
            return

        config = json.loads(run["config_json"])
        conn.execute("UPDATE benchmark_runs SET status = 'running' WHERE id = ?", (run_id,))
        conn.commit()

        model_ids = config.get("model_ids", [])
        dataset_ids = config.get("dataset_ids", [])
        warmup_count = config.get("warmup_iterations", 1)
        measured_count = config.get("measured_iterations", 1)
        concurrency = max(1, config.get("concurrency", 1))
        temperature = config.get("temperature", 0.7)
        max_tokens = config.get("max_tokens", 256)
        seed = config.get("seed", 42)
        timeout = float(config.get("timeout_seconds", 45.0))

        # Fetch model details & backend info
        models_data = []
        for mid in model_ids:
            row = conn.execute("""
                SELECT m.id, m.name, m.identifier, m.backend_id, b.type as backend_type, b.base_url
                FROM models m JOIN backends b ON m.backend_id = b.id
                WHERE m.id = ?
            """, (mid,)).fetchone()
            if row:
                models_data.append(dict(row))

        # Fetch dataset test cases
        cases_data = []
        for did in dataset_ids:
            rows = conn.execute("SELECT * FROM dataset_cases WHERE dataset_id = ? AND is_enabled = 1", (did,)).fetchall()
            for r in rows:
                cases_data.append(dict(r))

        conn.close()

        if not models_data or not cases_data:
            conn = get_connection()
            conn.execute(
                "UPDATE benchmark_runs SET status = 'failed', completed_at = ? WHERE id = ?",
                (datetime.datetime.now(datetime.timezone.utc).isoformat(), run_id)
            )
            conn.commit()
            conn.close()
            await self.broadcast_event(run_id, {"type": "failed", "error": "No valid models or test cases found."})
            return

        # Prepare execution plan
        total_requests = len(models_data) * len(cases_data) * (warmup_count + measured_count)
        conn = get_connection()
        conn.execute("UPDATE benchmark_runs SET total_requests = ? WHERE id = ?", (total_requests, run_id))
        conn.commit()
        conn.close()

        completed_requests = 0
        error_count = 0
        sem = asyncio.Semaphore(concurrency)

        # Baseline system sample
        base_sample = get_current_metrics()
        conn = get_connection()
        conn.execute("""
            INSERT INTO system_samples (id, run_id, timestamp, cpu_percent, memory_used_mb, memory_percent, process_memory_mb, gpu_percent, gpu_memory_mb)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()), run_id, base_sample["timestamp"], base_sample["cpu_percent"],
            base_sample["memory_used_mb"], base_sample["memory_percent"], base_sample["process_memory_mb"],
            base_sample["gpu_percent"], base_sample["gpu_memory_mb"]
        ))
        conn.commit()
        conn.close()

        async def run_single_iteration(model_info: Dict[str, Any], case: Dict[str, Any], is_warmup: bool):
            nonlocal completed_requests, error_count

            if self.cancel_flags.get(run_id):
                return

            async with sem:
                adapter = self.get_adapter(
                    model_info["backend_type"],
                    model_info["backend_id"],
                    model_info["base_url"]
                )

                # Inference execution
                res = await adapter.execute_inference(
                    model_identifier=model_info["identifier"],
                    prompt=case["prompt"],
                    max_tokens=case.get("max_tokens") or max_tokens,
                    temperature=temperature,
                    seed=seed,
                    timeout=timeout
                )

                iteration_id = str(uuid.uuid4())
                status = res.status
                if status != "success":
                    error_count += 1

                # Quality evaluation
                eval_res = None
                if status == "success" and not is_warmup:
                    eval_res = evaluate_output(
                        eval_type=case.get("evaluation_type", "none"),
                        actual_output=res.text,
                        expected_output=case.get("expected_output"),
                        criteria_json=case.get("criteria_json")
                    )

                # Incremental persistence
                conn_it = get_connection()
                now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
                conn_it.execute("""
                    INSERT INTO benchmark_iterations (
                        id, run_id, case_id, model_id, prompt_tokens, output_tokens,
                        ttft_ms, latency_ms, tokens_per_sec, response_text, is_warmup, status, error_message, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    iteration_id, run_id, case["id"], model_info["id"], res.prompt_tokens,
                    res.output_tokens, res.ttft_ms, res.latency_ms, res.tokens_per_sec,
                    res.text, 1 if is_warmup else 0, status, res.error_message, now_str
                ))

                if eval_res:
                    conn_it.execute("""
                        INSERT INTO evaluation_results (id, iteration_id, run_id, evaluator_name, score, passed, explanation)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(uuid.uuid4()), iteration_id, run_id, eval_res.evaluator_name,
                        eval_res.score, 1 if eval_res.passed else 0, eval_res.explanation
                    ))

                completed_requests += 1
                conn_it.execute(
                    "UPDATE benchmark_runs SET completed_requests = ?, error_count = ? WHERE id = ?",
                    (completed_requests, error_count, run_id)
                )
                conn_it.commit()
                conn_it.close()

                # Stream progress
                await self.broadcast_event(run_id, {
                    "type": "progress",
                    "run_id": run_id,
                    "completed": completed_requests,
                    "total": total_requests,
                    "model_id": model_info["id"],
                    "case_id": case["id"],
                    "is_warmup": is_warmup,
                    "status": status,
                    "tps": res.tokens_per_sec,
                    "ttft_ms": res.ttft_ms,
                    "latency_ms": res.latency_ms,
                })

        try:
            # 1. Warmup Loop
            if warmup_count > 0:
                for model_item in models_data:
                    for case_item in cases_data:
                        for _ in range(warmup_count):
                            if self.cancel_flags.get(run_id):
                                break
                            await run_single_iteration(model_item, case_item, is_warmup=True)

            # 2. Measured Loop
            for model_item in models_data:
                for case_item in cases_data:
                    for _ in range(measured_count):
                        if self.cancel_flags.get(run_id):
                            break
                        await run_single_iteration(model_item, case_item, is_warmup=False)

            # Telemetry sample post-inference
            end_sample = get_current_metrics()
            conn = get_connection()
            conn.execute("""
                INSERT INTO system_samples (id, run_id, timestamp, cpu_percent, memory_used_mb, memory_percent, process_memory_mb, gpu_percent, gpu_memory_mb)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()), run_id, end_sample["timestamp"], end_sample["cpu_percent"],
                end_sample["memory_used_mb"], end_sample["memory_percent"], end_sample["process_memory_mb"],
                end_sample["gpu_percent"], end_sample["gpu_memory_mb"]
            ))

            # Compute and persist aggregates for each model
            for model_item in models_data:
                mid = model_item["id"]
                iters = conn.execute("""
                    SELECT * FROM benchmark_iterations
                    WHERE run_id = ? AND model_id = ? AND is_warmup = 0
                """, (run_id, mid)).fetchall()

                eval_rows = conn.execute("""
                    SELECT score FROM evaluation_results
                    WHERE run_id = ? AND iteration_id IN (
                        SELECT id FROM benchmark_iterations WHERE run_id = ? AND model_id = ? AND is_warmup = 0
                    )
                """, (run_id, run_id, mid)).fetchall()
                quality_scores = [float(r["score"]) for r in eval_rows]

                metrics = aggregate_iteration_metrics([dict(it) for it in iters], quality_scores)

                conn.execute("""
                    INSERT INTO benchmark_metrics (
                        id, run_id, model_id, successful_iterations, failed_iterations,
                        mean_tps, median_tps, min_tps, max_tps, p90_tps, p95_tps, std_dev_tps,
                        mean_ttft_ms, median_ttft_ms, p90_ttft_ms, p95_ttft_ms,
                        mean_latency_ms, median_latency_ms, p90_latency_ms, error_rate,
                        mean_cpu_percent, peak_memory_mb, average_quality_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()), run_id, mid, metrics["successful_iterations"], metrics["failed_iterations"],
                    metrics["tps"]["mean"], metrics["tps"]["median"], metrics["tps"]["min"], metrics["tps"]["max"],
                    metrics["tps"]["p90"], metrics["tps"]["p95"], metrics["tps"]["std_dev"],
                    metrics["ttft"]["mean"], metrics["ttft"]["median"], metrics["ttft"]["p90"], metrics["ttft"]["p95"],
                    metrics["latency"]["mean"], metrics["latency"]["median"], metrics["latency"]["p90"],
                    metrics["error_rate"], end_sample["cpu_percent"], end_sample["memory_used_mb"],
                    metrics["average_quality_score"]
                ))

            # Mark run as completed
            final_status = "cancelled" if self.cancel_flags.get(run_id) else "completed"
            conn.execute(
                "UPDATE benchmark_runs SET status = ?, completed_at = ? WHERE id = ?",
                (final_status, datetime.datetime.now(datetime.timezone.utc).isoformat(), run_id)
            )
            conn.commit()
            conn.close()

            await self.broadcast_event(run_id, {"type": final_status, "run_id": run_id})

        except asyncio.CancelledError:
            conn = get_connection()
            conn.execute(
                "UPDATE benchmark_runs SET status = 'cancelled', completed_at = ? WHERE id = ?",
                (datetime.datetime.now(datetime.timezone.utc).isoformat(), run_id)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            conn = get_connection()
            conn.execute(
                "UPDATE benchmark_runs SET status = 'failed', completed_at = ? WHERE id = ?",
                (datetime.datetime.now(datetime.timezone.utc).isoformat(), run_id)
            )
            conn.commit()
            conn.close()
            await self.broadcast_event(run_id, {"type": "failed", "error": str(e)})
        finally:
            self.active_tasks.pop(run_id, None)
            self.cancel_flags.pop(run_id, None)

engine = BenchmarkEngine()
