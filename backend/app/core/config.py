import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseModel):
    app_name: str = "ModelBench Local"
    app_version: str = "1.0.0"
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8000"))
    db_path: Path = Path(os.getenv("DATABASE_PATH", str(DATA_DIR / "modelbench.db")))
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    llama_cpp_base_url: str = os.getenv("LLAMA_CPP_BASE_URL", "http://127.0.0.1:8080")
    enable_fake_adapter: bool = True
    enable_hardware_monitor: bool = True
    monitor_interval_seconds: float = 1.0

settings = Settings()
