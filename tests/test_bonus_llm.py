"""Verify the optional paid boundary without making any network calls."""
import json

import httpx
import pytest

from bonus import llm


@pytest.fixture(autouse=True)
def api_config(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")


def test_combines_message_text_and_disables_response_storage():
    def respond(request):
        payload = json.loads(request.content)
        assert payload["store"] is False
        assert payload["input"] == "isolated user context"
        assert payload["model"] == "test-model"
        return httpx.Response(200, json={
            "status": "completed", "model": "test-model", "usage": {"total_tokens": 12},
            "output": [
                {"type": "reasoning"},
                {"type": "message", "content": [{"type": "output_text", "text": "First"}]},
                {"type": "message", "content": [{"type": "output_text", "text": "Second"}]},
            ],
        })
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = llm.answer("isolated user context", client=client)
    assert result["text"] == "First\nSecond"
    assert result["usage"]["total_tokens"] == 12


def test_http_failure_does_not_expose_server_error_or_key():
    def respond(request):
        return httpx.Response(429, json={"error": {"message": "test-secret"}})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(RuntimeError, match="HTTP 429") as error:
            llm.answer("context", client=client)
    assert "test-secret" not in str(error.value)


def test_incomplete_answer_is_rejected():
    def respond(request):
        return httpx.Response(200, json={"status": "incomplete", "output": []})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(RuntimeError, match="incomplete"):
            llm.answer("context", client=client)
