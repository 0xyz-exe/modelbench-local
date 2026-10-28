import pytest
from backend.app.adapters.fake import FakeInferenceAdapter

@pytest.mark.asyncio
async def test_fake_adapter_health():
    adapter = FakeInferenceAdapter("backend_fake", "http://127.0.0.1:0/fake")
    health = await adapter.health_check()
    assert health["status"] == "online"
    assert health["testing_only"] is True

@pytest.mark.asyncio
async def test_fake_adapter_models():
    adapter = FakeInferenceAdapter("backend_fake", "http://127.0.0.1:0/fake")
    models = await adapter.list_models()
    assert len(models) >= 3
    assert any("simulated-7b" in m.identifier for m in models)

@pytest.mark.asyncio
async def test_fake_adapter_inference():
    adapter = FakeInferenceAdapter("backend_fake", "http://127.0.0.1:0/fake")
    res = await adapter.execute_inference(
        model_identifier="simulated-7b-q4",
        prompt="What is the capital city of France?"
    )
    assert res.status == "success"
    assert "Paris" in res.text
    assert res.output_tokens > 0
    assert res.ttft_ms > 0
    assert res.tokens_per_sec > 0
