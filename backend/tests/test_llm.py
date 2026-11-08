import json

import httpx
import pytest

from app.engine.llm import LLMClient, LLMConfig, LLMError

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["ok"],
    "properties": {"ok": {"type": "boolean"}},
}


def client_with(provider: str, handler, **kw) -> LLMClient:
    cfg = LLMConfig(provider=provider, model=kw.pop("model", "m"), api_key="sk-test-123456", **kw)
    return LLMClient(cfg, transport=httpx.MockTransport(handler))


def test_gemini_request_and_parse():
    seen = {}

    def handler(req: httpx.Request):
        seen["url"] = str(req.url)
        seen["key"] = req.headers["x-goog-api-key"]
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}}]})

    out = client_with("gemini", handler, model="gemini-test").structured("sys", "user", SCHEMA)
    assert out == {"ok": True}
    assert seen["url"].endswith("/v1beta/models/gemini-test:generateContent")
    assert seen["key"] == "sk-test-123456"
    gen = seen["body"]["generationConfig"]
    assert gen["responseMimeType"] == "application/json"
    assert gen["responseSchema"]["type"] == "OBJECT" and "additionalProperties" not in gen["responseSchema"]


def test_openai_uses_strict_json_schema():
    seen = {}

    def handler(req):
        seen["auth"] = req.headers["authorization"]
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"ok": true}'}}]})

    assert client_with("openai", handler).structured("s", "u", SCHEMA) == {"ok": True}
    assert seen["auth"] == "Bearer sk-test-123456"
    assert seen["body"]["response_format"]["json_schema"]["strict"] is True


def test_azure_openai_url_and_header():
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        seen["key"] = req.headers["api-key"]
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"ok": false}'}}]})

    c = client_with("azure_openai", handler, model="my-deploy", endpoint="https://x.openai.azure.com/")
    assert c.structured("s", "u", SCHEMA) == {"ok": False}
    assert (
        seen["url"] == "https://x.openai.azure.com/openai/deployments/my-deploy/chat/completions?api-version=2024-10-21"
    )
    assert seen["key"] == "sk-test-123456"


def test_anthropic_forced_tool():
    seen = {}

    def handler(req):
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={"content": [{"type": "tool_use", "name": "result", "input": {"ok": True}}]})

    assert client_with("anthropic", handler).structured("s", "u", SCHEMA) == {"ok": True}
    assert seen["body"]["tool_choice"] == {"type": "tool", "name": "result"}


@pytest.mark.parametrize("status,fatal", [(401, True), (404, True), (429, False), (500, False)])
def test_errors_are_classified(status, fatal):
    c = client_with("openai", lambda req: httpx.Response(status, json={}))
    with pytest.raises(LLMError) as e:
        c.structured("s", "u", SCHEMA)
    assert e.value.fatal is fatal


def test_bad_json_and_config_errors():
    c = client_with("openai", lambda req: httpx.Response(200, json={"choices": [{"message": {"content": "nope"}}]}))
    with pytest.raises(LLMError):
        c.structured("s", "u", SCHEMA)
    with pytest.raises(LLMError):
        LLMClient(LLMConfig("azure_openai", "d", "k"))  # no endpoint
    with pytest.raises(LLMError):
        LLMClient(LLMConfig("bedrock", "m", "k"))
