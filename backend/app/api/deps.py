"""Request dependencies: who is calling, which org they act in, and what they may do."""

import uuid
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db, set_tenant
from app.models import Membership, Role, User
from app.security.auth import verify_token

_bearer = HTTPBearer(auto_error=False)

ROLE_RANK = {Role.viewer.value: 0, Role.reviewer.value: 1, Role.admin.value: 2}


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    ident = verify_token(creds.credentials)
    user = db.scalar(select(User).where(User.issuer == ident.issuer, User.subject == ident.subject))
    if user is None:
        user = User(issuer=ident.issuer, subject=ident.subject, email=ident.email, name=ident.name)
        db.add(user)
        db.flush()
    elif ident.email and user.email != ident.email:
        user.email = ident.email
    return user


@dataclass
class OrgContext:
    org_id: uuid.UUID
    user: User
    role: str
    db: Session

    def require(self, minimum: Role) -> None:
        if ROLE_RANK[self.role] < ROLE_RANK[minimum.value]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires {minimum.value} role")


def get_org_context(
    x_org_id: uuid.UUID = Header(..., alias="X-Org-Id"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrgContext:
    m = db.scalar(select(Membership).where(Membership.org_id == x_org_id, Membership.user_id == user.id))
    if m is None:
        # 404, not 403: don't confirm that another org exists.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    set_tenant(db, x_org_id)
    return OrgContext(org_id=x_org_id, user=user, role=m.role, db=db)


def reviewer(ctx: OrgContext = Depends(get_org_context)) -> OrgContext:
    ctx.require(Role.reviewer)
    return ctx


def admin(ctx: OrgContext = Depends(get_org_context)) -> OrgContext:
    ctx.require(Role.admin)
    return ctx
