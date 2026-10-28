import os
import platform
import psutil
import datetime
import subprocess
import shutil
from typing import Dict, Any, Optional

def get_system_info() -> Dict[str, Any]:
    ram = psutil.virtual_memory()
    info = {
        "os": platform.system(),
        "os_release": platform.release(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor() or "Generic Processor",
        "cpu_count_physical": psutil.cpu_count(logical=False) or psutil.cpu_count(logical=True),
        "cpu_count_logical": psutil.cpu_count(logical=True),
        "total_ram_bytes": ram.total,
        "total_ram_gb": round(ram.total / (1024 ** 3), 2),
        "python_version": platform.python_version(),
        "gpu_available": False,
        "gpu_name": None,
    }

    # Optional GPU Detection
    gpu_data = probe_nvidia_gpu()
    if gpu_data:
        info["gpu_available"] = True
        info["gpu_name"] = gpu_data.get("name")
        info["gpu_total_memory_mb"] = gpu_data.get("total_memory_mb")

    return info

def probe_nvidia_gpu() -> Optional[Dict[str, Any]]:
    if not shutil.which("nvidia-smi"):
        return None
    try:
        cmd = ["nvidia-smi", "--query-gpu=name,memory.total,utilization.gpu,memory.used", "--format=csv,noheader,nounits"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=1.5)
        if res.returncode == 0 and res.stdout.strip():
            parts = [p.strip() for p in res.stdout.strip().split(",")]
            if len(parts) >= 4:
                return {
                    "name": parts[0],
                    "total_memory_mb": float(parts[1]),
                    "utilization_gpu_percent": float(parts[2]),
                    "memory_used_mb": float(parts[3]),
                }
    except Exception:
        pass
    return None

def get_current_metrics() -> Dict[str, Any]:
    ram = psutil.virtual_memory()
    proc = psutil.Process(os.getpid())
    proc_ram_mb = proc.memory_info().rss / (1024 * 1024)

    metrics = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cpu_percent": round(psutil.cpu_percent(interval=None), 1),
        "memory_used_mb": round(ram.used / (1024 * 1024), 1),
        "memory_percent": round(ram.percent, 1),
        "memory_available_mb": round(ram.available / (1024 * 1024), 1),
        "process_memory_mb": round(proc_ram_mb, 1),
        "gpu_percent": 0.0,
        "gpu_memory_mb": 0.0,
        "gpu_available": False,
    }

    gpu_data = probe_nvidia_gpu()
    if gpu_data:
        metrics["gpu_available"] = True
        metrics["gpu_percent"] = gpu_data.get("utilization_gpu_percent", 0.0)
        metrics["gpu_memory_mb"] = gpu_data.get("memory_used_mb", 0.0)

    return metrics
