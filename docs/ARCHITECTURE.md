# Architecture Documentation

## Architectural Principles
1. **Local-First & Zero Paid API**: All telemetry, datasets, configurations, and evaluation results persist locally in SQLite.
2. **Adapter Pattern**: Backends decouple execution from inference engines (Ollama, llama.cpp, OpenAI-compatible local servers, and Fake test adapter).
3. **Decoupled Orchestration**: Benchmark worker runs asynchronously in background tasks, persisting metrics incrementally per iteration.
4. **Resilience & Safe Cancellation**: Tests can be cancelled gracefully mid-execution without data corruption or hanging worker threads.

## Component Diagram

```
+--------------------------------------------------------------+
|                     React 19 Frontend Web UI                 |
|  - Dashboard / Overview   - Benchmark Lab    - Model Compare |
|  - Dataset Manager        - Results Detail   - System Monitor|
+------------------------------+-------------------------------+
                               | REST & SSE (Progress Stream)
+------------------------------v-------------------------------+
|                      FastAPI Web Service                     |
|  - API Routing            - Pydantic Validation              |
|  - Task Dispatcher        - Report Generator (HTML/JSON/CSV) |
+------------------------------+-------------------------------+
                               |
       +-----------------------+-----------------------+
       |                                               |
+------v--------------------+             +------------v-------------+
|    Benchmark Engine       |             |   SQLite Storage Engine  |
| - Warmup & Measured runs  |             | - backends, models       |
| - TTFT / TPS calculation  |             | - datasets & test cases  |
| - Concurrency controller  |             | - benchmark_runs & stats |
| - Quality Evaluator suite |             | - system_samples metrics |
+--------------+------------+             +--------------------------+
               |
  +------------+-------------+------------+
  |                          |            |
+-v---------------+  +-------v------+  +--v---------------------+
| Ollama Adapter  |  | llama.cpp    |  | Fake Adapter (Testing) |
| (11434 API)     |  | (8080 API)   |  | (Deterministic Mock)   |
+-----------------+  +--------------+  +------------------------+
```

## Database Schema Model
- `backends`: Configured inference runtimes (id, name, type, base_url, is_active, created_at)
- `models`: Discovered local models (id, backend_id, name, identifier, size_bytes, parameter_count, quantization, context_length, last_seen)
- `datasets`: Benchmark suites (id, name, description, category, is_builtin, created_at)
- `dataset_cases`: Individual prompts & criteria (id, dataset_id, case_id, prompt, expected_output, evaluation_type, criteria_json, max_tokens)
- `benchmark_runs`: Executed runs (id, name, status, config_json, total_requests, completed_requests, error_count, started_at, completed_at)
- `benchmark_iterations`: Per-prompt execution trace (id, run_id, case_id, model_id, prompt_tokens, output_tokens, ttft_ms, latency_ms, tokens_per_sec, response_text, is_warmup, status, error_message)
- `benchmark_metrics`: Statistical aggregates (id, run_id, model_id, mean_tps, median_tps, p90_tps, p95_tps, mean_ttft_ms, median_ttft_ms, error_rate)
- `evaluation_results`: Quality assessment (id, iteration_id, evaluator_name, score, passed, explanation)
- `system_samples`: Hardware telemetry (id, run_id, timestamp, cpu_percent, memory_used_mb, memory_percent, process_memory_mb, gpu_percent, gpu_memory_mb)
