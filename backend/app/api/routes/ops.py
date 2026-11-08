"""Audit log, inbound Jira webhooks, and scheduled jobs."""

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import select

from app.api.deps import OrgContext, admin
from app.config import get_settings
from app.db import set_tenant, system_session
from app.jobs.sla import sla_sweep
from app.models import AuditLog, Finding, FindingStatus, OrgSettings
from app.security.crypto import decrypt
from app.services import audit

router = APIRouter(prefix="/api/v1")


@router.get("/audit", tags=["audit"])
def audit_log(
    limit: int = Query(200, ge=1, le=1000), before_id: int | None = None, ctx: OrgContext = Depends(admin)
) -> list[dict]:
    q = select(AuditLog).where(AuditLog.org_id == ctx.org_id)
    if before_id:
        q = q.where(AuditLog.id < before_id)
    rows = ctx.db.scalars(q.order_by(AuditLog.id.desc()).limit(limit))
    return [
        {
            "id": a.id,
            "at": a.created_at.isoformat(),
            "actor": a.actor_label,
            "action": a.action,
            "target_type": a.target_type,
            "target_id": a.target_id,
            "details": a.details,
        }
        for a in rows
    ]


DONE_STATUSES = {"done", "closed", "resolved"}


@router.post("/webhooks/jira/{org_id}", tags=["webhooks"])
async def jira_webhook(
    org_id: uuid.UUID, request: Request, x_hub_signature: str | None = Header(None, alias="X-Hub-Signature")
) -> dict:
    """Jira calls this when an issue changes. Signed with the org's own HMAC secret
    (Jira sends 'X-Hub-Signature: sha256=<hex>')."""
    body = await request.body()
    with system_session() as db:
        set_tenant(db, org_id)
        s = db.get(OrgSettings, org_id)
        secret = decrypt(s.webhook_secret_enc) if s else None
        if not secret or not x_hub_signature:
            raise HTTPException(401, "Unsigned or unknown")
        expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, x_hub_signature):
            raise HTTPException(401, "Bad signature")
        try:
            payload = json.loads(body or b"{}")
        except json.JSONDecodeError as exc:
            raise HTTPException(400, "Invalid JSON") from exc
        issue = payload.get("issue") or {}
        key = issue.get("key")
        status_name = (((issue.get("fields") or {}).get("status") or {}).get("name") or "").lower()
        if not key:
            return {"ok": True, "ignored": "no issue"}
        f = db.scalar(select(Finding).where(Finding.org_id == org_id, Finding.jira_key == key))
        if f is None:
            return {"ok": True, "ignored": "unknown issue"}
        if status_name in DONE_STATUSES and f.status != FindingStatus.resolved.value:
            f.status = FindingStatus.resolved.value
            f.resolved_at = datetime.now(UTC)
            actor = ((payload.get("user") or {}).get("displayName")) or "Jira"
            audit.record(
                db,
                org_id,
                "finding.resolved",
                actor_label=f"jira:{actor}",
                target_type="finding",
                target_id=f.id,
                details={"jira_key": key, "jira_status": status_name},
            )
            return {"ok": True, "resolved": str(f.id)}
        return {"ok": True}


@router.post("/jobs/sla-sweep", tags=["jobs"])
def run_sla_sweep(x_job_token: str | None = Header(None, alias="X-Job-Token")) -> dict:
    token = get_settings().job_token
    if not token or not x_job_token or not hmac.compare_digest(token, x_job_token):
        raise HTTPException(401, "Bad job token")
    with system_session() as db:
        return sla_sweep(db)
