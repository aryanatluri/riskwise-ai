import csv
import io
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select

from app.api.deps import OrgContext, get_org_context, reviewer
from app.integrations.jira import JiraError, create_issue
from app.integrations.notify import slack_post
from app.models import Clause, Contract, Finding, FindingStatus, OrgSettings
from app.security.crypto import SecretsNotConfigured, decrypt
from app.services import audit

router = APIRouter(prefix="/api/v1/findings", tags=["findings"])


def _out(f: Finding, clause: Clause | None = None, contract: Contract | None = None) -> dict:
    return {
        "id": str(f.id),
        "contract_id": str(f.contract_id),
        "contract_title": contract.title if contract else None,
        "clause": {
            "id": str(clause.id),
            "section_number": clause.section_number,
            "heading": clause.heading,
            "text": clause.text,
        }
        if clause
        else None,
        "domain": f.domain,
        "title": f.title,
        "severity": f.severity,
        "crs": f.crs,
        "scores": {"impact": f.impact, "likelihood": f.likelihood, "exposure": f.exposure, "confidence": f.confidence},
        "evidence_quote": f.evidence_quote,
        "reasoning": f.reasoning,
        "regulation_refs": f.regulation_refs,
        "recommended_action": f.recommended_action,
        "proposed_redline": f.proposed_redline,
        "owner_role": f.owner_role,
        "sla_days": f.sla_days,
        "source": f.source,
        "status": f.status,
        "assignee_email": f.assignee_email,
        "due_at": f.due_at.isoformat() if f.due_at else None,
        "review_notes": f.review_notes,
        "jira_key": f.jira_key,
        "decided_at": f.decided_at.isoformat() if f.decided_at else None,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


def _query(ctx: OrgContext, status: str | None, severity: str | None, contract_id: str | None):
    q = (
        select(Finding, Clause, Contract)
        .join(Contract, Contract.id == Finding.contract_id)
        .outerjoin(Clause, Clause.id == Finding.clause_id)
        .where(Finding.org_id == ctx.org_id)
    )
    if status:
        q = q.where(Finding.status == status)
    if severity:
        q = q.where(Finding.severity == severity)
    if contract_id:
        q = q.where(Finding.contract_id == contract_id)
    return q.order_by(Finding.crs.desc(), Finding.created_at)


@router.get("")
def list_findings(
    status: Literal["open", "approved", "rejected", "dispatched", "resolved"] | None = None,
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] | None = None,
    contract_id: str | None = None,
    limit: int = Query(200, ge=1, le=1000),
    ctx: OrgContext = Depends(get_org_context),
) -> list[dict]:
    rows = ctx.db.execute(_query(ctx, status, severity, contract_id).limit(limit)).all()
    return [_out(f, cl, co) for f, cl, co in rows]


@router.get("/export.csv")
def export_csv(contract_id: str | None = None, ctx: OrgContext = Depends(get_org_context)) -> StreamingResponse:
    rows = ctx.db.execute(_query(ctx, None, None, contract_id)).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "contract",
            "section",
            "severity",
            "crs",
            "title",
            "evidence",
            "regulations",
            "recommended_action",
            "proposed_redline",
            "status",
            "assignee",
            "due",
            "jira",
        ]
    )
    for f, cl, co in rows:
        w.writerow(
            [
                co.title,
                cl.section_number if cl else "",
                f.severity,
                f.crs,
                f.title,
                f.evidence_quote,
                "; ".join(r.get("code", "") for r in f.regulation_refs or []),
                f.recommended_action,
                f.proposed_redline,
                f.status,
                f.assignee_email or "",
                f.due_at.date().isoformat() if f.due_at else "",
                f.jira_key or "",
            ]
        )
    audit.record(ctx.db, ctx.org_id, "findings.exported", actor=ctx.user, details={"rows": len(rows)})
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=riskwise-findings.csv"},
    )


def _get(ctx: OrgContext, finding_id: str) -> Finding:
    f = ctx.db.scalar(select(Finding).where(Finding.id == finding_id, Finding.org_id == ctx.org_id))
    if f is None:
        raise HTTPException(404, "Finding not found")
    return f


@router.get("/{finding_id}")
def get_finding(finding_id: str, ctx: OrgContext = Depends(get_org_context)) -> dict:
    f = _get(ctx, finding_id)
    clause = ctx.db.get(Clause, f.clause_id) if f.clause_id else None
    return _out(f, clause, ctx.db.get(Contract, f.contract_id))


class Decision(BaseModel):
    decision: Literal["approve", "reject"]
    assignee_email: EmailStr | None = None
    proposed_redline: str | None = Field(default=None, max_length=20000)
    notes: str = Field(default="", max_length=5000)


@router.post("/{finding_id}/decision")
def decide(finding_id: str, body: Decision, ctx: OrgContext = Depends(reviewer)) -> dict:
    f = _get(ctx, finding_id)
    if f.status != FindingStatus.open.value:
        raise HTTPException(409, f"Finding is already {f.status}")
    now = datetime.now(UTC)
    before_redline = f.proposed_redline
    if body.proposed_redline is not None:
        f.proposed_redline = body.proposed_redline
    f.review_notes = body.notes
    f.decided_by = ctx.user.id
    f.decided_at = now
    if body.decision == "approve":
        f.status = FindingStatus.approved.value
        f.assignee_email = body.assignee_email
        f.due_at = now + timedelta(days=f.sla_days)
    else:
        f.status = FindingStatus.rejected.value
    audit.record(
        ctx.db,
        ctx.org_id,
        "finding.approved" if body.decision == "approve" else "finding.rejected",
        actor=ctx.user,
        target_type="finding",
        target_id=f.id,
        details={
            "assignee": body.assignee_email,
            "notes": body.notes,
            "redline_edited": body.proposed_redline is not None and body.proposed_redline != before_redline,
        },
    )
    return _out(f)


@router.post("/{finding_id}/dispatch")
def dispatch(finding_id: str, ctx: OrgContext = Depends(reviewer)) -> dict:
    """Send an approved finding to the org's Jira and Slack."""
    f = _get(ctx, finding_id)
    if f.status != FindingStatus.approved.value:
        raise HTTPException(409, "Only approved findings can be dispatched")
    s = ctx.db.get(OrgSettings, ctx.org_id)
    contract = ctx.db.get(Contract, f.contract_id)
    result: dict = {"jira_key": None, "slack": False}
    try:
        token = decrypt(s.jira_token_enc)
        if s.jira_base_url and s.jira_email and token and s.jira_project_key:
            try:
                f.jira_key = create_issue(
                    base_url=s.jira_base_url,
                    email=s.jira_email,
                    token=token,
                    project_key=s.jira_project_key,
                    summary=f"[RISKWISE] {contract.title}: {f.title}",
                    severity=f.severity,
                    evidence=f.evidence_quote,
                    reasoning=f.reasoning,
                    redline=f.proposed_redline,
                    due_date=f.due_at.date().isoformat() if f.due_at else None,
                )
                result["jira_key"] = f.jira_key
            except JiraError as exc:
                raise HTTPException(502, str(exc)) from exc
        hook = decrypt(s.slack_webhook_enc)
        if hook:
            result["slack"] = slack_post(
                hook,
                f"{f.severity}: {f.title}",
                [
                    f"*Contract:* {contract.title}",
                    f"*Owner:* {f.assignee_email or f.owner_role}",
                    f"*Due:* {f.due_at.date().isoformat() if f.due_at else 'n/a'}",
                    f"*Jira:* {f.jira_key or 'not configured'}",
                ],
            )
    except SecretsNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    if not result["jira_key"] and not result["slack"]:
        raise HTTPException(422, "No Jira or Slack integration is configured for this organization")
    f.status = FindingStatus.dispatched.value
    audit.record(
        ctx.db, ctx.org_id, "finding.dispatched", actor=ctx.user, target_type="finding", target_id=f.id, details=result
    )
    return {**_out(f), "dispatch": result}
