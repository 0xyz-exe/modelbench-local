import asyncio
import time
from typing import Dict, Any, List, Optional
from backend.app.adapters.base import BaseModelAdapter, ModelInfo, InferenceResult

class FakeInferenceAdapter(BaseModelAdapter):
    """
    Simulated Inference Adapter (TESTING ONLY).
    Provides realistic, reproducible latency and streaming token simulation
    for CI/CD pipeline, local test suites, and UI smoke testing.
    """

    async def health_check(self) -> Dict[str, Any]:
        return {
            "status": "online",
            "testing_only": True,
            "url": self.base_url,
            "version": "1.0.0-mock",
            "message": "Deterministic test runner active"
        }

    async def list_models(self) -> List[ModelInfo]:
        return [
            ModelInfo(
                id=f"{self.backend_id}_simulated-7b-q4",
                name="Simulated Llama-3-8B-Q4 (Test Only)",
                identifier="simulated-7b-q4",
                backend_id=self.backend_id,
                size_bytes=4_800_000_000,
                parameter_count="8.0B",
                quantization="Q4_K_M",
                context_length=8192,
            ),
            ModelInfo(
                id=f"{self.backend_id}_simulated-3b-q8",
                name="Simulated Phi-3-Mini-3.8B-Q8 (Test Only)",
                identifier="simulated-3b-q8",
                backend_id=self.backend_id,
                size_bytes=4_100_000_000,
                parameter_count="3.8B",
                quantization="Q8_0",
                context_length=4096,
            ),
            ModelInfo(
                id=f"{self.backend_id}_simulated-1b-fp16",
                name="Simulated TinyLlama-1.1B-FP16 (Test Only)",
                identifier="simulated-1b-fp16",
                backend_id=self.backend_id,
                size_bytes=2_200_000_000,
                parameter_count="1.1B",
                quantization="FP16",
                context_length=2048,
            )
        ]

    async def execute_inference(
        self,
        model_identifier: str,
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.7,
        seed: Optional[int] = None,
        timeout: float = 30.0,
    ) -> InferenceResult:
        start_time = time.perf_counter()

        # Simulated TTFT (approx 40-70ms)
        await asyncio.sleep(0.045)
        first_token_time = time.perf_counter()

        # Deterministic response generation matching test prompts
        lower_p = prompt.lower()
        if "capital city of france" in lower_p:
            answer = "Paris"
        elif "atomic number 6" in lower_p:
            answer = "Carbon"
        elif "calculate 15% of 240" in lower_p:
            answer = "The result of 15% of 240 is 36."
        elif "prime numbers between 20 and 40" in lower_p:
            answer = "23, 29, 31"
        elif "is_even" in lower_p:
            answer = "def is_even(n):\n    return n % 2 == 0"
        elif "keys: name (string), age (number)" in lower_p:
            answer = '{"name": "Alice", "age": 28, "skills": ["Python", "FastAPI"]}'
        elif "ibu kota baru" in lower_p:
            answer = "Nusantara"
        elif "superlative form of the adjective 'good'" in lower_p:
            answer = "best"
        elif "roses are flowers" in lower_p:
            answer = "Not necessarily. While all roses are flowers, only some flowers fade quickly, so roses may not be among them."
        elif "summarize in under 15 words" in lower_p:
            answer = "Machine learning enables systems to learn data patterns without explicit programming."
        else:
            answer = f"ModelBench simulated response for: {prompt[:30]}... Executed deterministically."

        tokens = answer.split()
        num_tokens = max(1, len(tokens))

        # Simulated generation speed: ~25ms per 5 tokens
        delay = (num_tokens * 0.005)
        await asyncio.sleep(delay)

        end_time = time.perf_counter()
        total_latency_ms = (end_time - start_time) * 1000.0
        ttft_ms = (first_token_time - start_time) * 1000.0

        gen_sec = (end_time - first_token_time)
        tps = (num_tokens / gen_sec) if gen_sec > 0.0001 else 35.0

        return InferenceResult(
            text=answer,
            prompt_tokens=max(1, len(prompt.split())),
            output_tokens=num_tokens,
            ttft_ms=round(ttft_ms, 2),
            latency_ms=round(total_latency_ms, 2),
            tokens_per_sec=round(tps, 2),
            prefill_duration_ms=round(ttft_ms * 0.8, 2),
            status="success"
        )
