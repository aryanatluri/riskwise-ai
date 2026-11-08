"""Org settings: analysis mode, the org's own LLM key (BYOK), and integrations.

Secrets are write-only: the API stores them encrypted and only ever returns whether
one is set (plus the last 4 characters of the LLM key).
"""

import secrets
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field, HttpUrl

from app.api.deps import OrgContext, admin, get_org_context
from app.engine.llm import PROVIDERS, LLMClient, LLMConfig, LLMError
from app.models import OrgSettings
from app.security.crypto import SecretsNotConfigured, decrypt, encrypt, last4
from app.services import audit

router = APIRouter(prefix="/api/v1/org/settings", tags=["settings"])


def _out(s: OrgSettings) -> dict:
    return {
        "analysis_mode": s.analysis_mode,
        "llm": {
            "provider": s.llm_provider,
            "model": s.llm_model,
            "endpoint": s.llm_endpoint,
            "api_version": s.llm_api_version,
            "api_key_set": bool(s.llm_api_key_enc),
            "api_key_last4": s.llm_api_key_last4,
        },
        "jira": {
            "base_url": s.jira_base_url,
            "email": s.jira_email,
            "project_key": s.jira_project_key,
            "token_set": bool(s.jira_token_enc),
        },
        "slack_webhook_set": bool(s.slack_webhook_enc),
        "jira_webhook_secret_set": bool(s.webhook_secret_enc),
        "escalation_email": s.escalation_email,
        "sla_escalation_days": s.sla_escalation_days,
    }


@router.get("")
def get_settings_(ctx: OrgContext = Depends(get_org_context)) -> dict:
    return _out(ctx.db.get(OrgSettings, ctx.org_id))


class LLMUpdate(BaseModel):
    provider: Literal[PROVIDERS] | None = None  # type: ignore[valid-type]
    model: str | None = Field(default=None, max_length=128)
    endpoint: HttpUrl | None = None
    api_version: str | None = Field(default=None, max_length=32)
    api_key: str | None = Field(default=None, min_length=8, max_length=4096)


class JiraUpdate(BaseModel):
    base_url: HttpUrl | None = None
    email: EmailStr | None = None
    project_key: str | None = Field(default=None, max_length=32)
    token: str | None = Field(default=None, min_length=8, max_length=4096)


class SettingsUpdate(BaseModel):
    analysis_mode: Literal["rules_only", "hybrid"] | None = None
    llm: LLMUpdate | None = None
    jira: JiraUpdate | None = None
    slack_webhook: HttpUrl | None = None
    escalation_email: EmailStr | None = None
    sla_escalation_days: int | None = Field(default=None, ge=1, le=60)


@router.put("")
def update(body: SettingsUpdate, ctx: OrgContext = Depends(admin)) -> dict:
    s = ctx.db.get(OrgSettings, ctx.org_id)
    changed: list[str] = []
    try:
        if body.llm:
            for f in ("provider", "model", "api_version"):
                v = getattr(body.llm, f)
                if v is not None:
                    setattr(s, f"llm_{f}", v)
                    changed.append(f"llm.{f}")
            if body.llm.endpoint is not None:
                s.llm_endpoint = str(body.llm.endpoint)
                changed.append("llm.endpoint")
            if body.llm.api_key:
                s.llm_api_key_enc = encrypt(body.llm.api_key)
                s.llm_api_key_last4 = last4(body.llm.api_key)
                changed.append("llm.api_key")
        if body.jira:
            if body.jira.base_url is not None:
                s.jira_base_url = str(body.jira.base_url)
            if body.jira.email is not None:
                s.jira_email = body.jira.email
            if body.jira.project_key is not None:
                s.jira_project_key = body.jira.project_key
            if body.jira.token:
                s.jira_token_enc = encrypt(body.jira.token)
            changed.append("jira")
        if body.slack_webhook is not None:
            s.slack_webhook_enc = encrypt(str(body.slack_webhook))
            changed.append("slack_webhook")
    except SecretsNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    if body.escalation_email is not None:
        s.escalation_email = body.escalation_email
        changed.append("escalation_email")
    if body.sla_escalation_days is not None:
        s.sla_escalation_days = body.sla_escalation_days
        changed.append("sla_escalation_days")
    if body.analysis_mode is not None:
        if body.analysis_mode == "hybrid" and not (s.llm_provider and s.llm_model and s.llm_api_key_enc):
            raise HTTPException(422, "Set an LLM provider, model and API key before switching to hybrid mode")
        s.analysis_mode = body.analysis_mode
        changed.append("analysis_mode")
    audit.record(
        ctx.db,
        ctx.org_id,
        "settings.updated",
        actor=ctx.user,
        target_type="org",
        target_id=ctx.org_id,
        details={"changed": changed},
    )
    return _out(s)


@router.post("/jira-webhook-secret")
def rotate_webhook_secret(ctx: OrgContext = Depends(admin)) -> dict:
    """Generate a new HMAC secret for Jira webhooks. Shown once; paste it into Jira."""
    s = ctx.db.get(OrgSettings, ctx.org_id)
    secret = secrets.token_urlsafe(32)
    try:
        s.webhook_secret_enc = encrypt(secret)
    except SecretsNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    audit.record(ctx.db, ctx.org_id, "settings.webhook_secret_rotated", actor=ctx.user)
    return {"secret": secret, "webhook_url": f"/api/v1/webhooks/jira/{ctx.org_id}"}


@router.post("/llm/test")
def test_llm(ctx: OrgContext = Depends(admin)) -> dict:
    """Make one tiny structured call to confirm the org's key, model and region work."""
    s = ctx.db.get(OrgSettings, ctx.org_id)
    try:
        key = decrypt(s.llm_api_key_enc)
        if not (s.llm_provider and s.llm_model and key):
            raise HTTPException(422, "LLM provider, model and API key must all be set")
        client = LLMClient(LLMConfig(s.llm_provider, s.llm_model, key, s.llm_endpoint, s.llm_api_version, 30))
        try:
            out = client.structured(
                "Reply with ok=true.",
                "Health check.",
                {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["ok"],
                    "properties": {"ok": {"type": "boolean"}},
                },
                name="health",
            )
        finally:
            client.close()
    except (LLMError, SecretsNotConfigured) as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": bool(out.get("ok"))}
