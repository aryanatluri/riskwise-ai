"""Append-only audit trail. Regulated buyers need to show who approved what, and when."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def record(
    db: Session,
    org_id: uuid.UUID,
    action: str,
    *,
    actor: User | None = None,
    actor_label: str = "",
    target_type: str = "",
    target_id: Any = "",
    details: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            org_id=org_id,
            actor_user_id=actor.id if actor else None,
            actor_label=actor_label or (actor.email if actor else "system"),
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id else "",
            details=details or {},
        )
    )
