from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import OrgContext, admin, get_current_user, get_org_context
from app.db import get_db
from app.engine.packs import PACKS
from app.models import Membership, Organization, Role, User
from app.services import audit
from app.services.orgs import create_org, list_orgs

router = APIRouter(prefix="/api/v1", tags=["organizations"])


class OrgCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    jurisdiction: Literal["IN", "EU"] = "IN"
    sector: str = "BFSI"
    regulation_packs: list[str] | None = None


def _org_out(o: Organization, role: str) -> dict:
    return {
        "id": str(o.id),
        "name": o.name,
        "jurisdiction": o.jurisdiction,
        "sector": o.sector,
        "regulation_packs": o.regulation_packs,
        "role": role,
    }


@router.post("/orgs", status_code=201)
def create(body: OrgCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    if body.regulation_packs and any(p not in PACKS for p in body.regulation_packs):
        raise HTTPException(422, "Unknown regulation pack")
    org = create_org(db, user, body.name, body.jurisdiction, body.sector, body.regulation_packs)
    return _org_out(org, Role.admin.value)


@router.get("/orgs")
def mine(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    return [_org_out(o, r) for o, r in list_orgs(db, user)]


@router.get("/org/members")
def members(ctx: OrgContext = Depends(get_org_context)) -> list[dict]:
    rows = ctx.db.execute(
        select(User, Membership.role)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.org_id == ctx.org_id)
        .order_by(User.email)
    ).all()
    return [{"user_id": str(u.id), "email": u.email, "name": u.name, "role": r} for u, r in rows]


class MemberAdd(BaseModel):
    email: EmailStr
    role: Literal["admin", "reviewer", "viewer"] = "viewer"


@router.post("/org/members", status_code=201)
def add_member(body: MemberAdd, ctx: OrgContext = Depends(admin)) -> dict:
    user = ctx.db.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    if user is None:
        raise HTTPException(404, "That person needs to sign in once before they can be added")
    m = ctx.db.get(Membership, (ctx.org_id, user.id))
    if m:
        m.role = body.role
    else:
        ctx.db.add(Membership(org_id=ctx.org_id, user_id=user.id, role=body.role))
    audit.record(
        ctx.db,
        ctx.org_id,
        "member.upserted",
        actor=ctx.user,
        target_type="user",
        target_id=user.id,
        details={"email": user.email, "role": body.role},
    )
    return {"user_id": str(user.id), "email": user.email, "role": body.role}


@router.delete("/org/members/{user_id}", status_code=204)
def remove_member(user_id: str, ctx: OrgContext = Depends(admin)) -> None:
    m = ctx.db.scalar(select(Membership).where(Membership.org_id == ctx.org_id, Membership.user_id == user_id))
    if m is None:
        raise HTTPException(404, "Member not found")
    admins = ctx.db.scalar(
        select(func.count())
        .select_from(Membership)
        .where(Membership.org_id == ctx.org_id, Membership.role == Role.admin.value)
    )
    if m.role == Role.admin.value and admins <= 1:
        raise HTTPException(409, "An organization needs at least one admin")
    ctx.db.delete(m)
    audit.record(ctx.db, ctx.org_id, "member.removed", actor=ctx.user, target_type="user", target_id=user_id)
