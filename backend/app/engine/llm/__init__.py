"""Bring-your-own-key LLM providers.

Each org stores its own credentials (encrypted). Contract text goes only to the
provider and region the client chose, under the client's own agreement with that
provider. RISKWISE never sends contracts to a shared or free-tier key.

Providers are plain HTTPS calls (no SDKs) with schema-enforced JSON output:
- gemini:        Gemini API generateContent with responseSchema
- openai:        Chat Completions with json_schema (strict)
- azure_openai:  same, on the client's Azure deployment and region
- anthropic:     Messages API with a forced tool call

AWS Bedrock (SigV4 signing) is planned; see docs/DECISIONS.md.
"""

import json
from dataclasses import dataclass
from typing import Any

import httpx

PROVIDERS = ("gemini", "openai", "azure_openai", "anthropic")


class LLMError(RuntimeError):
    def __init__(self, message: str, *, fatal: bool = False) -> None:
        super().__init__(message)
        self.fatal = fatal  # auth/config errors: stop calling for this run


@dataclass
class LLMConfig:
    provider: str
    model: str
    api_key: str
    endpoint: str | None = None
    api_version: str | None = None
    timeout: float = 60.0


def _to_gemini_schema(schema: Any) -> Any:
    """Gemini's responseSchema uses OpenAPI-style upper-case types and no additionalProperties."""
    if isinstance(schema, dict):
        out = {}
        for k, v in schema.items():
            if k == "additionalProperties":
                continue
            if k == "type" and isinstance(v, str):
                out[k] = v.upper()
            else:
                out[k] = _to_gemini_schema(v)
        return out
    if isinstance(schema, list):
        return [_to_gemini_schema(x) for x in schema]
    return schema


class LLMClient:
    def __init__(self, cfg: LLMConfig, transport: httpx.BaseTransport | None = None) -> None:
        if cfg.provider not in PROVIDERS:
            raise LLMError(f"Unsupported provider: {cfg.provider}", fatal=True)
        if not cfg.model:
            raise LLMError("No model configured", fatal=True)
        if cfg.provider == "azure_openai" and not cfg.endpoint:
            raise LLMError("Azure OpenAI needs an endpoint", fatal=True)
        self.cfg = cfg
        self._http = httpx.Client(timeout=cfg.timeout, transport=transport)

    def close(self) -> None:
        self._http.close()

    # -- public ---------------------------------------------------------------
    def structured(self, system: str, user: str, schema: dict, name: str = "result") -> dict:
        fn = getattr(self, f"_call_{self.cfg.provider}")
        try:
            return fn(system, user, schema, name)
        except httpx.TimeoutException as exc:
            raise LLMError("LLM request timed out") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM request failed: {type(exc).__name__}") from exc

    # -- helpers --------------------------------------------------------------
    def _post(self, url: str, headers: dict, body: dict) -> dict:
        r = self._http.post(url, headers=headers, json=body)
        if r.status_code in (401, 403):
            raise LLMError("LLM provider rejected the API key", fatal=True)
        if r.status_code == 404:
            raise LLMError("LLM model or deployment not found", fatal=True)
        if r.status_code == 429:
            raise LLMError("LLM provider rate limit or quota reached")
        if r.status_code >= 400:
            raise LLMError(f"LLM provider error HTTP {r.status_code}")
        return r.json()

    @staticmethod
    def _parse(text: str | None) -> dict:
        if not text:
            raise LLMError("LLM returned an empty response")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMError("LLM returned invalid JSON") from exc
        if not isinstance(data, dict):
            raise LLMError("LLM returned JSON that is not an object")
        return data

    # -- providers ------------------------------------------------------------
    def _call_gemini(self, system: str, user: str, schema: dict, name: str) -> dict:
        base = (self.cfg.endpoint or "https://generativelanguage.googleapis.com").rstrip("/")
        url = f"{base}/v1beta/models/{self.cfg.model}:generateContent"
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "responseSchema": _to_gemini_schema(schema),
            },
        }
        data = self._post(url, {"x-goog-api-key": self.cfg.api_key}, body)
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Gemini returned no content (possibly blocked)") from exc
        return self._parse(text)

    def _openai_body(self, system: str, user: str, schema: dict, name: str) -> dict:
        return {
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": name, "strict": True, "schema": schema},
            },
        }

    def _openai_text(self, data: dict) -> str | None:
        try:
            msg = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("OpenAI returned no choices") from exc
        if msg.get("refusal"):
            raise LLMError("Model refused the request")
        return msg.get("content")

    def _call_openai(self, system: str, user: str, schema: dict, name: str) -> dict:
        base = (self.cfg.endpoint or "https://api.openai.com/v1").rstrip("/")
        body = {"model": self.cfg.model, **self._openai_body(system, user, schema, name)}
        data = self._post(f"{base}/chat/completions", {"Authorization": f"Bearer {self.cfg.api_key}"}, body)
        return self._parse(self._openai_text(data))

    def _call_azure_openai(self, system: str, user: str, schema: dict, name: str) -> dict:
        base = (self.cfg.endpoint or "").rstrip("/")
        version = self.cfg.api_version or "2024-10-21"
        url = f"{base}/openai/deployments/{self.cfg.model}/chat/completions?api-version={version}"
        data = self._post(url, {"api-key": self.cfg.api_key}, self._openai_body(system, user, schema, name))
        return self._parse(self._openai_text(data))

    def _call_anthropic(self, system: str, user: str, schema: dict, name: str) -> dict:
        base = (self.cfg.endpoint or "https://api.anthropic.com").rstrip("/")
        body = {
            "model": self.cfg.model,
            "max_tokens": 4096,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "tools": [{"name": name, "description": "Report the analysis result.", "input_schema": schema}],
            "tool_choice": {"type": "tool", "name": name},
        }
        headers = {"x-api-key": self.cfg.api_key, "anthropic-version": "2023-06-01"}
        data = self._post(f"{base}/v1/messages", headers, body)
        for block in data.get("content", []):
            if block.get("type") == "tool_use" and isinstance(block.get("input"), dict):
                return block["input"]
        raise LLMError("Anthropic returned no tool result")
