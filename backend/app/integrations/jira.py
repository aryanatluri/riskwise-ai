"""Jira Cloud REST v3: create an issue for an approved finding (per-org credentials)."""

import base64

import httpx


class JiraError(RuntimeError):
    pass


def _adf(paragraphs: list[tuple[str, str]]) -> dict:
    content = []
    for heading, body in paragraphs:
        if not body:
            continue
        content.append({"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": heading}]})
        content.append({"type": "paragraph", "content": [{"type": "text", "text": body[:30000]}]})
    return {"type": "doc", "version": 1, "content": content}


PRIORITY = {"CRITICAL": "Highest", "HIGH": "High", "MEDIUM": "Medium", "LOW": "Low"}


def create_issue(
    *,
    base_url: str,
    email: str,
    token: str,
    project_key: str,
    summary: str,
    severity: str,
    evidence: str,
    reasoning: str,
    redline: str,
    due_date: str | None,
    transport: httpx.BaseTransport | None = None,
) -> str:
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    fields = {
        "project": {"key": project_key},
        "summary": summary[:250],
        "issuetype": {"name": "Task"},
        "priority": {"name": PRIORITY.get(severity, "Medium")},
        "labels": ["riskwise", f"severity-{severity.lower()}"],
        "description": _adf(
            [("Contract evidence", evidence), ("Why this matters", reasoning), ("Proposed redline", redline)]
        ),
    }
    if due_date:
        fields["duedate"] = due_date
    with httpx.Client(timeout=15, transport=transport) as client:
        r = client.post(
            f"{base_url.rstrip('/')}/rest/api/3/issue",
            headers={"Authorization": f"Basic {auth}", "Accept": "application/json"},
            json={"fields": fields},
        )
    if r.status_code >= 400:
        raise JiraError(f"Jira returned HTTP {r.status_code}")
    return r.json()["key"]
