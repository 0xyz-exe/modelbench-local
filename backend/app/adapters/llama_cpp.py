import time
import json
import httpx
from typing import Dict, Any, List, Optional
from backend.app.adapters.base import BaseModelAdapter, ModelInfo, InferenceResult

class LlamaCppAdapter(BaseModelAdapter):
    async def health_check(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/health")
                if res.status_code == 200:
                    return {"status": "online", "url": self.base_url}
        except Exception as e:
            return {"status": "offline", "error": str(e), "url": self.base_url}
        return {"status": "offline", "error": "Non-200 response", "url": self.base_url}

    async def list_models(self) -> List[ModelInfo]:
        models = []
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/v1/models")
                if res.status_code == 200:
                    data = res.json().get("data", [])
                    for item in data:
                        mid = item.get("id", "llama-model")
                        models.append(ModelInfo(
                            id=f"{self.backend_id}_{mid}",
                            name=mid,
                            identifier=mid,
                            backend_id=self.backend_id,
                            parameter_count="Unknown",
                            quantization="GGUF",
                            context_length=4096,
                        ))
        except Exception:
            pass
        return models

    async def execute_inference(
        self,
        model_identifier: str,
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.7,
        seed: Optional[int] = None,
        timeout: float = 60.0,
    ) -> InferenceResult:
        payload = {
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        if seed is not None:
            payload["seed"] = seed

        start_time = time.perf_counter()
        first_token_time: Optional[float] = None
        accumulated_text = []
        token_count = 0

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("POST", f"{self.base_url}/completion", json=payload) as response:
                    if response.status_code != 200:
                        err_text = await response.aread()
                        return InferenceResult(
                            text="",
                            prompt_tokens=0,
                            output_tokens=0,
                            ttft_ms=0.0,
                            latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                            tokens_per_sec=0.0,
                            status="failed",
                            error_message=f"HTTP {response.status_code}: {err_text.decode('utf-8', errors='ignore')}"
                        )

                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        raw_data = line[6:].strip()
                        if raw_data == "[DONE]":
                            break
                        chunk = json.loads(raw_data)
                        content = chunk.get("content", "")
                        if content:
                            if first_token_time is None:
                                first_token_time = time.perf_counter()
                            accumulated_text.append(content)
                            token_count += 1

            end_time = time.perf_counter()
            total_latency_ms = (end_time - start_time) * 1000.0
            ttft_ms = (first_token_time - start_time) * 1000.0 if first_token_time else total_latency_ms
            gen_sec = (end_time - first_token_time) if first_token_time and end_time > first_token_time else (total_latency_ms / 1000.0)
            tps = (token_count / gen_sec) if gen_sec > 0.001 else 0.0

            return InferenceResult(
                text="".join(accumulated_text),
                prompt_tokens=max(1, len(prompt.split())),
                output_tokens=token_count,
                ttft_ms=round(ttft_ms, 2),
                latency_ms=round(total_latency_ms, 2),
                tokens_per_sec=round(tps, 2),
                status="success"
            )
        except Exception as exc:
            return InferenceResult(
                text="",
                prompt_tokens=0,
                output_tokens=0,
                ttft_ms=0.0,
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                tokens_per_sec=0.0,
                status="failed",
                error_message=str(exc)
            )
