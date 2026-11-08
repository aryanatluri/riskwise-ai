import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import set_tenant
from app.engine.packs import DEFAULT_PACKS, default_policy_rules
from app.models import Membership, Organization, OrgSettings, PolicyRule, Role, User
from app.services import audit


def create_org(
    db: Session, user: User, name: str, jurisdiction: str, sector: str, packs: list[str] | None = None
) -> Organization:
    org = Organization(
        id=uuid.uuid4(),
        name=name,
        jurisdiction=jurisdiction,
        sector=sector,
        regulation_packs=packs or DEFAULT_PACKS.get(jurisdiction, []),
    )
    db.add(org)
    db.flush()
    db.add(Membership(org_id=org.id, user_id=user.id, role=Role.admin.value))
    set_tenant(db, org.id)
    db.add(OrgSettings(org_id=org.id))
    for r in default_policy_rules(jurisdiction):
        db.add(PolicyRule(org_id=org.id, **r))
    audit.record(
        db,
        org.id,
        "org.created",
        actor=user,
        target_type="org",
        target_id=org.id,
        details={"name": name, "packs": org.regulation_packs},
    )
    db.flush()
    return org


def list_orgs(db: Session, user: User) -> list[tuple[Organization, str]]:
    rows = db.execute(
        select(Organization, Membership.role)
        .join(Membership, Membership.org_id == Organization.id)
        .where(Membership.user_id == user.id)
        .order_by(Organization.created_at)
    ).all()
    return [(o, r) for o, r in rows]
