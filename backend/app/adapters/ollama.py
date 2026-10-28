import time
import json
import httpx
from typing import Dict, Any, List, Optional
from backend.app.adapters.base import BaseModelAdapter, ModelInfo, InferenceResult

class OllamaAdapter(BaseModelAdapter):
    async def health_check(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/version")
                if res.status_code == 200:
                    data = res.json()
                    return {"status": "online", "version": data.get("version", "unknown"), "url": self.base_url}
        except Exception as e:
            return {"status": "offline", "error": str(e), "url": self.base_url}
        return {"status": "offline", "error": "Non-200 response", "url": self.base_url}

    async def list_models(self) -> List[ModelInfo]:
        models = []
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    items = res.json().get("models", [])
                    for item in items:
                        name = item.get("name", "Unknown")
                        details = item.get("details", {})
                        models.append(ModelInfo(
                            id=f"{self.backend_id}_{name}",
                            name=name,
                            identifier=name,
                            backend_id=self.backend_id,
                            size_bytes=item.get("size", 0),
                            parameter_count=details.get("parameter_size", "Unknown"),
                            quantization=details.get("quantization_level", "Unknown"),
                            context_length=details.get("context_length", 0) or 2048,
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
            "model": model_identifier,
            "prompt": prompt,
            "stream": True,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            }
        }
        if seed is not None:
            payload["options"]["seed"] = seed

        start_time = time.perf_counter()
        first_token_time: Optional[float] = None
        accumulated_text = []
        token_count = 0
        prompt_tokens = 0
        prefill_ms = 0.0

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("POST", f"{self.base_url}/api/generate", json=payload) as response:
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
                        if not line.strip():
                            continue
                        chunk = json.loads(line)
                        token = chunk.get("response", "")
                        if token:
                            if first_token_time is None:
                                first_token_time = time.perf_counter()
                            accumulated_text.append(token)
                            token_count += 1

                        if chunk.get("done", False):
                            prompt_tokens = chunk.get("prompt_eval_count", 0)
                            if chunk.get("prompt_eval_duration"):
                                prefill_ms = round(chunk["prompt_eval_duration"] / 1_000_000.0, 2)
                            if chunk.get("eval_count"):
                                token_count = chunk["eval_count"]

            end_time = time.perf_counter()
            total_latency_ms = (end_time - start_time) * 1000.0
            ttft_ms = (first_token_time - start_time) * 1000.0 if first_token_time else total_latency_ms

            # Throughput calculated over generation window (after TTFT)
            gen_duration_sec = (end_time - first_token_time) if first_token_time and end_time > first_token_time else (total_latency_ms / 1000.0)
            tps = (token_count / gen_duration_sec) if gen_duration_sec > 0.001 else 0.0

            return InferenceResult(
                text="".join(accumulated_text),
                prompt_tokens=prompt_tokens or max(1, len(prompt.split())),
                output_tokens=token_count,
                ttft_ms=round(ttft_ms, 2),
                latency_ms=round(total_latency_ms, 2),
                tokens_per_sec=round(tps, 2),
                prefill_duration_ms=prefill_ms,
                status="success"
            )
        except Exception as exc:
            total_latency_ms = (time.perf_counter() - start_time) * 1000.0
            return InferenceResult(
                text="",
                prompt_tokens=0,
                output_tokens=0,
                ttft_ms=0.0,
                latency_ms=round(total_latency_ms, 2),
                tokens_per_sec=0.0,
                status="failed",
                error_message=str(exc)
            )
