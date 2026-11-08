"""Slack incoming webhooks and SMTP email. Both are per-org and optional."""

import smtplib
from email.message import EmailMessage

import httpx

from app.config import get_settings


def slack_post(webhook_url: str, title: str, lines: list[str], transport: httpx.BaseTransport | None = None) -> bool:
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": title[:150]}},
        {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)[:2900]}},
    ]
    with httpx.Client(timeout=10, transport=transport) as client:
        r = client.post(webhook_url, json={"text": title, "blocks": blocks})
    return r.status_code < 400


def send_email(to: str, subject: str, text: str, html: str | None = None) -> bool:
    s = get_settings()
    if not s.smtp_host:
        return False
    msg = EmailMessage()
    msg["From"] = s.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as smtp:
        smtp.starttls()
        if s.smtp_user:
            smtp.login(s.smtp_user, s.smtp_password)
        smtp.send_message(msg)
    return True
