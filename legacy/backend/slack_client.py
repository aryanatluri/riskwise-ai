import os
import json
from typing import Dict, Any, List

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# In-memory alert feed for dashboard preview
SLACK_ALERT_FEED: List[Dict[str, Any]] = []

def send_slack_alert(
    jira_key: str,
    jira_url: str,
    summary: str,
    severity: str,
    owner: str,
    redline: str
) -> Dict[str, Any]:
    """
    Dispatches an interactive Block Kit notification card into Slack.
    If SLACK_WEBHOOK_URL is not provided, stores the Block Kit payload
    for high-fidelity preview in the web UI.
    """
    badge_emoji = "🚨" if severity == "CRITICAL" else "⚠️"
    color_bar = "#ef4444" if severity == "CRITICAL" else "#f59e0b"

    payload = {
        "channel": "#compliance-risk-alerts",
        "attachments": [
            {
                "color": color_bar,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{badge_emoji} RISKWISE AI: {severity} Risk Action Created",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Jira Issue:*\n<{jira_url}|{jira_key}>"},
                            {"type": "mrkdwn", "text": f"*Assigned Owner:*\n`{owner}`"}
                        ]
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*Remediation Objective:*\n{summary}"}
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*Approved Replacement Redline:*\n```{redline}```"}
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "View in Jira", "emoji": True},
                                "url": jira_url,
                                "style": "primary"
                            },
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "Audit Trail", "emoji": True},
                                "value": f"audit_{jira_key}"
                            }
                        ]
                    }
                ]
            }
        ]
    }

    sent_live = False
    if SLACK_WEBHOOK_URL and "hooks.slack.com" in SLACK_WEBHOOK_URL:
        try:
            import httpx
            with httpx.Client(timeout=5.0) as client:
                res = client.post(SLACK_WEBHOOK_URL, json=payload)
                sent_live = res.status_code == 200
        except Exception:
            sent_live = False

    alert_record = {
        "jira_key": jira_key,
        "jira_url": jira_url,
        "summary": summary,
        "severity": severity,
        "owner": owner,
        "redline": redline,
        "sent_live": sent_live,
        "payload": payload
    }
    SLACK_ALERT_FEED.insert(0, alert_record)
    return alert_record
