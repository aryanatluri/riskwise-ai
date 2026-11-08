import os
import smtplib
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any, List

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "https://apexfinancial.atlassian.net").rstrip("/")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.office365.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "compliance-bot@apexfinancial.com")
SMTP_PASS = os.getenv("SMTP_PASSWORD", "")

ESCALATION_EMAIL_LOGS: List[Dict[str, Any]] = []

def send_manager_escalation_email(
    mgr_email: str,
    mgr_name: str,
    emp_name: str,
    emp_email: str,
    jira_key: str,
    summary: str,
    severity: str,
    days_overdue: float,
    redline: str
) -> Dict[str, Any]:
    """
    Sends an executive HTML escalation email to the department VP/Manager.
    If SMTP credentials are not configured, records the full HTML memo in
    the escalation audit log for instant inspection in the UI.
    """
    jira_url = f"{JIRA_BASE_URL}/browse/{jira_key}"
    subject = f"🔴 ESCALATION [L2]: Audit SLA Breach on {jira_key} ({severity}) - Assignee: {emp_name}"

    html = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f19; color: #f1f5f9; padding: 24px; margin: 0;">
    <div style="max-width: 600px; margin: auto; background-color: #111827; border: 1px solid #374151; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #dc2626; padding: 16px 24px; color: #ffffff;">
            <h2 style="margin: 0; font-size: 18px; text-transform: uppercase; letter-spacing: 1px;">🚨 SLA Breach Escalation Notice (> 3 Days Overdue)</h2>
        </div>
        <div style="padding: 24px;">
            <p style="font-size: 15px; color: #e5e7eb; margin-top: 0;">Dear <strong>{mgr_name}</strong>,</p>
            <p style="font-size: 14px; color: #9ca3af; line-height: 1.6;">
                A high-liability contractual risk remediation assigned to your direct report 
                <strong style="color: #60a5fa;">{emp_name}</strong> (<a href="mailto:{emp_email}" style="color: #93c5fd;">{emp_email}</a>) 
                is currently <strong style="color: #f87171;">{days_overdue:.1f} days past the compliance SLA deadline</strong>.
            </p>
            
            <div style="background-color: #1f2937; border-left: 4px solid #ef4444; padding: 14px 18px; margin: 20px 0; border-radius: 4px;">
                <p style="margin: 0 0 8px 0; font-size: 13px; color: #9ca3af;"><strong>Jira Ticket:</strong> <a href="{jira_url}" style="color: #38bdf8; text-decoration: none; font-weight: bold;">{jira_key}</a></p>
                <p style="margin: 0 0 8px 0; font-size: 13px; color: #9ca3af;"><strong>Remediation Target:</strong> <span style="color: #f3f4f6;">{summary}</span></p>
                <p style="margin: 0; font-size: 13px; color: #9ca3af;"><strong>Risk Classification:</strong> <span style="color: #ef4444; font-weight: bold;">{severity}</span></p>
            </div>

            <p style="font-size: 13px; font-weight: bold; color: #d1d5db; margin-bottom: 6px;">Approved Legal Redline Awaiting Vendor Counterparty Signature:</p>
            <div style="background-color: #030712; border: 1px solid #1f2937; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 12px; color: #34d399; white-space: pre-wrap; line-height: 1.5;">{redline}</div>

            <p style="font-size: 13px; color: #9ca3af; margin-top: 20px;">
                Please coordinate with your team member to finalize this execution immediately to protect the enterprise against statutory fines under CERT-In Directions and DPDPA 2023.
            </p>
        </div>
        <div style="background-color: #0f172a; padding: 12px 24px; border-top: 1px solid #1f2937; font-size: 11px; color: #64748b; text-align: center;">
            RISKWISE AI Autonomous SLA Watchdog Engine • Automated Compliance Dispatch
        </div>
    </div>
</body>
</html>"""

    sent_smtp = False
    if SMTP_PASS and SMTP_USER and "company.com" not in SMTP_USER:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = SMTP_USER
            msg["To"] = mgr_email
            msg["Cc"] = emp_email
            msg.attach(MIMEText(html, "html"))
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(SMTP_USER, [mgr_email, emp_email], msg.as_string())
            sent_smtp = True
        except Exception:
            sent_smtp = False

    escalation_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "jira_key": jira_key,
        "manager_email": mgr_email,
        "manager_name": mgr_name,
        "employee_name": emp_name,
        "employee_email": emp_email,
        "days_overdue": round(days_overdue, 1),
        "severity": severity,
        "summary": summary,
        "sent_smtp": sent_smtp,
        "subject": subject,
        "html_body": html
    }
    ESCALATION_EMAIL_LOGS.insert(0, escalation_entry)
    return escalation_entry
