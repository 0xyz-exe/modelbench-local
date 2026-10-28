# ModelBench Local - Project Plan

## Executive Overview
ModelBench Local is an open-source, local-first benchmarking and evaluation platform for Large Language Models (LLMs). It measures actual generation throughput, TTFT (Time to First Token), latency, quality compliance, and hardware resource consumption without sending proprietary data to external cloud services.

## Milestones & Phased Execution

### Phase 1: Environment & Foundation
- Initial repository audit and directory setup
- Virtual environment with FastAPI, Pydantic, pytest, psutil
- SQLite schema design and seed initialization
- Core configuration and security controls (loopback binding, CORS, safe endpoints)

### Phase 2: Runtime & Model Discovery
- Extensible `BaseModelAdapter` abstraction
- `OllamaAdapter` implementation (local HTTP API integration)
- `LlamaCppAdapter` implementation (local server endpoints)
- `OpenAICompatibleAdapter` implementation (v1 chat/completions)
- `FakeInferenceAdapter` for deterministic local CI/CD testing with explicit `testing_only` attribution

### Phase 3: Benchmark Engine & Metrics
- Async benchmark execution loop with concurrency bounds
- Warmup and measured iterations
- High-precision telemetry: TTFT, Time per token, Tokens/sec, Latency, Prompt eval prefill duration
- Statistical aggregation: Mean, Median, Min, Max, StdDev, P90, P95, Error rate
- System telemetry: CPU utilization, System RAM, Process RSS memory, GPU detection

### Phase 4: Quality Evaluation Engine
- Deterministic Exact Match
- Normalized Match (case/whitespace folding)
- Structured Output Validation (JSON syntax, schema compliance, missing keys)
- Rubric/Keyword Rule Evaluator (with explainability payload)

### Phase 5: Datasets & Comparison Lab
- 8 Curated local benchmark categories (General Knowledge, Reasoning, Instruction, Summarization, Coding, Structured Output, Indonesian, English)
- Custom dataset creation, JSON/JSONL import & export
- Multi-model comparison matrix, scatter plots, latency distribution charts
- Presets: Quick Test, Performance Test, Quality Test, Stress Test, Hardware Efficiency Test

### Phase 6: Report Export & Developer Experience
- Multiformat reporting: JSON, CSV, Markdown, Standalone HTML
- Unit and integration tests in pytest
- Single-page React frontend dashboard with dark mode developer UI
- Comprehensive documentation, screenshots, and GitHub Actions CI
