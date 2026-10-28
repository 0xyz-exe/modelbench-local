# Tech Stack Baseline

## Backend
- **Runtime**: Python 3.11+ / 3.12+ (tested on Python 3.14 on Windows)
- **Web Framework**: FastAPI 0.115+
- **Data Validation & Serializer**: Pydantic v2
- **Database**: SQLite3 with WAL mode enabled for concurrent reads/writes
- **HTTP Client**: HTTPX (async client with streaming SSE capabilities)
- **System Telemetry**: psutil (CPU, Virtual Memory, Process RSS, platform info)
- **Testing**: pytest & pytest-asyncio

## Frontend
- **Framework**: React 19 / TypeScript 5.7+
- **Bundler**: Vite 6
- **Styling**: Tailwind CSS v4 / Modern dark-first utility design
- **Icons**: Lucide React
- **Visualizations**: Interactive SVG charts & telemetry dashboards
- **State Management**: Clean hooks & service layer with polling & SSE integration

## Supported Local AI Runtimes
- **Ollama**: Native `/api/tags` and `/api/generate` with live streaming tokens
- **llama.cpp**: `/v1/models` and `/completion` endpoints
- **OpenAI-Compatible Local Endpoints**: v1 format (vLLM, LocalAI, LM Studio)
- **Fake Test Adapter**: Deterministic, zero-resource local test runner
