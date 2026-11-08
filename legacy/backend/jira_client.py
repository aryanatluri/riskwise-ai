import os
import base64
import json
import uuid
from typing import Dict, Any, Optional

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "https://apexfinancial.atlassian.net").rstrip("/")
JIRA_API_EMAIL = os.getenv("JIRA_API_EMAIL", "")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "RISK")

# Local in-memory store for demo / prototype tracking
DISPATCHED_JIRA_ISSUES: Dict[str, Dict[str, Any]] = {}

def create_jira_issue(
    summary: str,
    severity: str,
    redline: str,
    evidence: str,
    assignee_email: str,
    due_days: int = 5,
    custom_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates an Issue in Jira Cloud REST API v3 using Atlassian Document Format (ADF).
    If Jira credentials are not configured, runs in high-fidelity prototype simulation mode.
    """
    issue_number = len(DISPATCHED_JIRA_ISSUES) + 104
    issue_key = custom_key or f"{JIRA_PROJECT_KEY}-{issue_number}"
    jira_url = f"{JIRA_BASE_URL}/browse/{issue_key}"

    # Rich Atlassian Document Format (ADF) description
    adf_desc = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "heading",
                "attrs": {"level": 3},
                "content": [{"type": "text", "text": "Contractual Risk Remediation Required"}]
            },
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Original Contract Evidence: ", "marks": [{"type": "strong"}]}]
            },
            {
                "type": "blockquote",
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": evidence}]}]
            },
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Mandatory Redline Replacement: ", "marks": [{"type": "strong"}]}]
            },
            {
                "type": "codeBlock",
                "attrs": {"language": "markdown"},
                "content": [{"type": "text", "text": redline}]
            },
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Audited SLA Target: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": f"Must be resolved within {due_days} business days."}
                ]
            }
        ]
    }

    record = {
        "key": issue_key,
        "url": jira_url,
        "summary": summary,
        "severity": severity,
        "priority": "Highest" if severity == "CRITICAL" else "High",
        "assignee": assignee_email,
        "status": "In Progress",
        "redline": redline,
        "evidence": evidence,
        "adf_description": adf_desc,
        "labels": ["riskwise-ai", "compliance-gap", severity.lower()]
    }

    # Attempt live API call if credentials provided
    if JIRA_API_EMAIL and JIRA_API_TOKEN and not JIRA_BASE_URL.endswith("apexfinancial.atlassian.net"):
        try:
            import httpx
            auth_str = base64.b64encode(f"{JIRA_API_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
            headers = {"Authorization": f"Basic {auth_str}", "Content-Type": "application/json"}
            payload = {
                "fields": {
                    "project": {"key": JIRA_PROJECT_KEY},
                    "summary": summary,
                    "description": adf_desc,
                    "issuetype": {"name": "Task"},
                    "priority": {"name": record["priority"]},
                    "labels": record["labels"]
                }
            }
            with httpx.Client(timeout=6.0) as client:
                res = client.post(f"{JIRA_BASE_URL}/rest/api/3/issue", headers=headers, json=payload)
                if res.status_code in (200, 201):
                    data = res.json()
                    record["key"] = data.get("key", issue_key)
                    record["url"] = f"{JIRA_BASE_URL}/browse/{record['key']}"
        except Exception as e:
            record["api_note"] = f"Simulated mode (Live dispatch fallback: {str(e)})"

    DISPATCHED_JIRA_ISSUES[record["key"]] = record
    return record
