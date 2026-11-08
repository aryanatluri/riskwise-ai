import os
import hmac
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Query, HTTPException
from typing import Dict, Any

from jira_client import DISPATCHED_JIRA_ISSUES

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])

JIRA_WEBHOOK_SECRET = os.getenv("JIRA_WEBHOOK_SECRET", "super_secret_webhook_key_123")
DONE_STATUSES = {"done", "complete", "resolved", "closed"}

WEBHOOK_AUDIT_LOGS = []

@router.post("/jira")
async def handle_jira_webhook(request: Request, secret: str = Query(None)):
    """
    Receives Jira status change events and automatically marks risk findings as RESOLVED.
    Uses constant-time HMAC secret validation to prevent spoofing.
    """
    if not secret or not hmac.compare_digest(secret, JIRA_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Unauthorized webhook call.")

    payload = await request.json()
    event_type = payload.get("webhookEvent")

    if event_type != "jira:issue_updated":
        return {"status": "ignored", "reason": f"Unhandled event type {event_type}"}

    issue = payload.get("issue", {})
    issue_key = issue.get("key")
    fields = issue.get("fields", {})
    status_cat = fields.get("status", {}).get("statusCategory", {}).get("key", "").lower()
    status_name = fields.get("status", {}).get("name", "Resolved")

    if status_cat not in DONE_STATUSES and status_name.lower() not in DONE_STATUSES:
        return {"status": "ignored", "reason": "Issue is not yet in a closed status category."}

    resolver = payload.get("user", {}).get("displayName", "Legal Counsel / Jira User")
    now_iso = datetime.now(timezone.utc).isoformat()

    # Update in-memory tracked issue
    if issue_key in DISPATCHED_JIRA_ISSUES:
        DISPATCHED_JIRA_ISSUES[issue_key]["status"] = "RESOLVED"
        DISPATCHED_JIRA_ISSUES[issue_key]["resolved_by"] = resolver
        DISPATCHED_JIRA_ISSUES[issue_key]["resolved_at"] = now_iso

    log_entry = {
        "event": "jira_resolved",
        "jira_key": issue_key,
        "resolver": resolver,
        "timestamp": now_iso,
        "detail": f"Ticket {issue_key} marked as '{status_name}' in Atlassian Jira. Risk finding updated to RESOLVED in compliance audit trail."
    }
    WEBHOOK_AUDIT_LOGS.insert(0, log_entry)

    return {
        "status": "success",
        "jira_issue_key": issue_key,
        "resolved_by": resolver,
        "compliance_status": "RESOLVED",
        "timestamp": now_iso
    }
