import httpx
import pytest
from openai import AsyncOpenAI

from codetrace.models import OpenAICompatibleModel
from codetrace.repository import TOOLS


async def test_sdk_tool_calls_and_usage_without_network():
    import json

    def handle(request):
        body = json.loads(request.content)
        assert body["model"] == "test-model"
        assert body["tools"] == TOOLS
        assert body["messages"][0]["content"] == "q"
        return httpx.Response(200, json={
            "id": "test-response", "object": "chat.completion", "created": 0,
            "model": "test-model", "choices": [{"index": 0, "finish_reason": "tool_calls",
                "message": {"role": "assistant", "content": None, "tool_calls": [
                    {"id": "call_1", "type": "function", "function": {"name": "list_files", "arguments": "{}"}}
                ]}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        })

    adapter = object.__new__(OpenAICompatibleModel)
    adapter.model = "test-model"
    adapter.client = AsyncOpenAI(api_key="test-only", base_url="https://test.invalid/v1",
                                 http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle)))
    try:
        result = await adapter.respond([{"role": "user", "content": "q"}], TOOLS)
        assert result["message"]["tool_calls"][0]["function"]["name"] == "list_files"
        assert result["usage"]["total_tokens"] == 15
    finally:
        await adapter.close()
    assert adapter.client.is_closed()


def test_missing_model_settings_fail_before_request(monkeypatch):
    for name in ("CODETRACE_API_KEY", "CODETRACE_MODEL", "CODETRACE_BASE_URL"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError, match="CODETRACE_API_KEY"):
        OpenAICompatibleModel()
