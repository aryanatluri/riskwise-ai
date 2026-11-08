"""SLA watchdog. Run hourly by any scheduler (GitHub Actions cron in the hosted setup).

Findings that are approved or dispatched and overdue by more than the org's
escalation threshold get one escalation email and an audit entry.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.notify import send_email
from app.models import Contract, Finding, Organization, OrgSettings
from app.services import audit


def sla_sweep(db: Session, now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
    escalated, emailed = 0, 0
    rows = db.execute(
        select(Finding, OrgSettings, Organization, Contract)
        .join(OrgSettings, OrgSettings.org_id == Finding.org_id)
        .join(Organization, Organization.id == Finding.org_id)
        .join(Contract, Contract.id == Finding.contract_id)
        .where(
            Finding.status.in_(["approved", "dispatched"]), Finding.due_at.is_not(None), Finding.escalated_at.is_(None)
        )
    ).all()
    for f, s, org, contract in rows:
        if f.due_at + timedelta(days=s.sla_escalation_days) > now:
            continue
        days_over = (now - f.due_at).days
        f.escalated_at = now
        escalated += 1
        to = s.escalation_email
        sent = False
        if to:
            sent = send_email(
                to,
                f"[RISKWISE] Overdue {f.severity} finding: {f.title}",
                (
                    f"{org.name}: a {f.severity} contract risk is {days_over} days past its due date.\n\n"
                    f"Contract: {contract.title}\nFinding: {f.title}\nOwner: {f.assignee_email or f.owner_role}\n"
                    f"Jira: {f.jira_key or 'n/a'}\n\nEvidence: {f.evidence_quote}\n"
                ),
            )
            emailed += int(sent)
        audit.record(
            db,
            f.org_id,
            "finding.escalated",
            actor_label="system:sla",
            target_type="finding",
            target_id=f.id,
            details={"days_overdue": days_over, "emailed": sent, "to": to},
        )
    return {"checked": len(rows), "escalated": escalated, "emailed": emailed}
