from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class ModelInfo(BaseModel):
    id: str
    name: str
    identifier: str
    backend_id: str
    size_bytes: int = 0
    parameter_count: str = "Unknown"
    quantization: str = "Unknown"
    context_length: int = 0

class InferenceResult(BaseModel):
    text: str
    prompt_tokens: int
    output_tokens: int
    ttft_ms: float
    latency_ms: float
    tokens_per_sec: float
    prefill_duration_ms: float = 0.0
    status: str = "success"
    error_message: Optional[str] = None

class BaseModelAdapter(ABC):
    def __init__(self, backend_id: str, base_url: str):
        self.backend_id = backend_id
        self.base_url = base_url.rstrip("/")

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check if backend service is reachable and responsive."""
        pass

    @abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        """Discover available models from the backend."""
        pass

    @abstractmethod
    async def execute_inference(
        self,
        model_identifier: str,
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.7,
        seed: Optional[int] = None,
        timeout: float = 30.0,
    ) -> InferenceResult:
        """Run inference with streaming measurements to capture TTFT and output throughput."""
        pass
