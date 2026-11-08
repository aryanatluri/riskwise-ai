from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import OrgContext, admin, get_org_context
from app.engine.packs import DOMAINS
from app.models import PolicyRule
from app.services import audit

router = APIRouter(prefix="/api/v1/policies", tags=["policies"])

Criticality = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]


def _out(r: PolicyRule) -> dict:
    return {
        "id": str(r.id),
        "code": r.code,
        "title": r.title,
        "domain": r.domain,
        "mandate": r.mandate,
        "criticality": r.criticality,
        "constraints": r.constraints,
        "redline_template": r.redline_template,
        "owner_role": r.owner_role,
        "sla_days": r.sla_days,
        "active": r.active,
    }


class PolicyIn(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    title: str = Field(min_length=3, max_length=255)
    domain: Literal[tuple(DOMAINS)]  # type: ignore[valid-type]
    mandate: str = Field(min_length=10)
    criticality: Criticality = "HIGH"
    constraints: dict = Field(default_factory=dict)
    redline_template: str = ""
    owner_role: str = "Legal"
    sla_days: int = Field(default=5, ge=1, le=90)
    active: bool = True


class PolicyPatch(BaseModel):
    title: str | None = None
    mandate: str | None = None
    criticality: Criticality | None = None
    constraints: dict | None = None
    redline_template: str | None = None
    owner_role: str | None = None
    sla_days: int | None = Field(default=None, ge=1, le=90)
    active: bool | None = None


@router.get("")
def list_rules(ctx: OrgContext = Depends(get_org_context)) -> list[dict]:
    rows = ctx.db.scalars(select(PolicyRule).where(PolicyRule.org_id == ctx.org_id).order_by(PolicyRule.code))
    return [_out(r) for r in rows]


@router.post("", status_code=201)
def create_rule(body: PolicyIn, ctx: OrgContext = Depends(admin)) -> dict:
    r = PolicyRule(org_id=ctx.org_id, **body.model_dump())
    ctx.db.add(r)
    try:
        ctx.db.flush()
    except IntegrityError as exc:
        raise HTTPException(409, "A rule with this code already exists") from exc
    audit.record(
        ctx.db,
        ctx.org_id,
        "policy.created",
        actor=ctx.user,
        target_type="policy",
        target_id=r.id,
        details={"code": r.code},
    )
    return _out(r)


def _get(ctx: OrgContext, rule_id: str) -> PolicyRule:
    r = ctx.db.scalar(select(PolicyRule).where(PolicyRule.id == rule_id, PolicyRule.org_id == ctx.org_id))
    if r is None:
        raise HTTPException(404, "Policy rule not found")
    return r


@router.patch("/{rule_id}")
def update_rule(rule_id: str, body: PolicyPatch, ctx: OrgContext = Depends(admin)) -> dict:
    r = _get(ctx, rule_id)
    changes = body.model_dump(exclude_none=True)
    for k, v in changes.items():
        setattr(r, k, v)
    audit.record(
        ctx.db,
        ctx.org_id,
        "policy.updated",
        actor=ctx.user,
        target_type="policy",
        target_id=r.id,
        details={"code": r.code, "fields": sorted(changes)},
    )
    return _out(r)
