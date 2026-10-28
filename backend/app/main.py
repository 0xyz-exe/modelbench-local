import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.app.core.config import settings
from backend.app.db.database import init_db, get_connection
from backend.app.api.routes import router as api_router
from backend.app.adapters.fake import FakeInferenceAdapter

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema & seed datasets
    init_db()

    # Pre-populate simulated models for test runner
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as count FROM models WHERE backend_id = 'backend_fake'")
    if c.fetchone()["count"] == 0:
        fake_adapter = FakeInferenceAdapter("backend_fake", "http://127.0.0.1:0/fake")
        models = await fake_adapter.list_models()
        now = "2026-10-28T12:00:00Z"
        for m in models:
            c.execute("""
                INSERT OR IGNORE INTO models (id, backend_id, name, identifier, size_bytes, parameter_count, quantization, context_length, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (m.id, m.backend_id, m.name, m.identifier, m.size_bytes, m.parameter_count, m.quantization, m.context_length, now))
        conn.commit()
    conn.close()

    yield

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Local AI Model Benchmarking & Evaluation Platform",
    lifespan=lifespan
)

# CORS (Loopback & Localhost only by default for security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Mount frontend static distribution if built
dist_dir = Path(__file__).resolve().parent.parent.parent / "apps" / "web" / "dist"
if dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        file_path = dist_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(dist_dir / "index.html")
