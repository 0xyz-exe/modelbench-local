# Testing Strategy

## Philosophy
Reliable testing is non-negotiable for benchmarking infrastructure. Tests must verify timing calculations, statistical aggregations, streaming token parser stability, and quality scoring without requiring gigabytes of LLM weights or internet connectivity.

## Test Levels
1. **Unit Tests (`tests/test_metrics.py`)**:
   - Validation of Percentiles (Median, P90, P95, Mean, StdDev)
   - Edge case calculations (zero tokens, single iteration, empty sample handling)
   - TTFT and throughput formulas

2. **Quality Evaluator Tests (`tests/test_evaluators.py`)**:
   - Exact match & Normalized match edge cases
   - Structured JSON validation (syntax check, schema conformity, missing required keys)
   - Rubric keyword checking with explanation generation

3. **Adapter & Engine Tests (`tests/test_engine.py`)**:
   - Fake adapter streaming & complete generation
   - Concurrency bounds enforcement
   - Cancellation token behavior
   - Incremental SQLite persistence

4. **API Integration Tests (`tests/test_api.py`)**:
   - Health check and system info endpoints
   - Backend discovery and registration
   - Benchmark configuration validation and execution dispatch
   - Report export generation (JSON, CSV, Markdown, HTML)

5. **End-to-End Visual Verification**:
   - Playwright headless capture of operational pages: Dashboard, Benchmark Lab, Comparison View, Datasets, and System Telemetry
