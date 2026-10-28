# Changelog

All notable changes to ModelBench Local will be documented in this file.

## [1.0.0] - 2026-10-28
### Added
- Initial release of ModelBench Local.
- Native Ollama, llama.cpp, and OpenAI-compatible runtime adapters.
- Built-in FakeInferenceAdapter for zero-dependency local testing.
- High-precision telemetry: TTFT, Generation Throughput (TPS), Latency, Prefill time, and Percentiles (P50, P90, P95).
- Hardware resource tracking: CPU, System RAM, Process RSS, and GPU stats.
- 8 Curated local benchmark datasets across multiple categories and languages.
- Quality Evaluation Suite: Exact match, Normalized match, Structured JSON validation, and Rubric keywords.
- Multi-model comparison matrix, scatter plots, and exportable reports (JSON, CSV, Markdown, standalone HTML).
- React 19 dark-first responsive web UI with real-time SSE progress streaming.
