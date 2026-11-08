import os
import re
import json
import uuid
import copy
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request, Query, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from sample_data import INITIAL_REVIEW_THREADS, MASTER_REGULATIONS, INTERNAL_POLICIES, EMPLOYEES, MASTER_GAP_MATRIX
from riskwise_agent import RiskwiseAgentEngine, calculate_crs, RiskFinding
from jira_client import create_jira_issue, DISPATCHED_JIRA_ISSUES
from slack_client import send_slack_alert, SLACK_ALERT_FEED
from jira_webhook import router as webhook_router, handle_jira_webhook, WEBHOOK_AUDIT_LOGS
from sla_monitor import send_manager_escalation_email, ESCALATION_EMAIL_LOGS

app = FastAPI(
    title="RISKWISE AI: Enterprise Risk Copilot & Autonomous Action Agent",
    description="Transforms unstructured legal contracts, policies, and statutory regulations into actionable enterprise risk intelligence.",
    version="2.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router)

# In-memory dynamic review threads store (initialized from sample data)
ACTIVE_THREADS: Dict[str, Dict[str, Any]] = {
    t["thread_id"]: copy.deepcopy(t) for t in INITIAL_REVIEW_THREADS
}

# Pre-populate sample dispatched Jira tasks for realistic initial state
def init_sample_jira_tasks():
    global DISPATCHED_JIRA_ISSUES
    DISPATCHED_JIRA_ISSUES.clear()
    create_jira_issue(
        summary="Vendor Breach Notification SLA Compliance (CloudStack)",
        severity="CRITICAL",
        redline="Vendor shall notify Customer in writing within twelve (12) hours of any security event.",
        evidence="Vendor will notify within 5 business days after confirmation.",
        assignee_email="arun.sharma@apexfinancial.com",
        due_days=2,
        custom_key="RISK-101"
    )
    # Set one as resolved for demonstration of bi-directional closure
    DISPATCHED_JIRA_ISSUES["RISK-101"]["status"] = "RESOLVED"
    DISPATCHED_JIRA_ISSUES["RISK-101"]["resolved_by"] = "Kavita Deshmukh (Legal Counsel)"
    DISPATCHED_JIRA_ISSUES["RISK-101"]["resolved_at"] = "2026-10-20T14:32:00Z"

    create_jira_issue(
        summary="Sovereign Cloud Data Localization Addendum (CloudStack)",
        severity="CRITICAL",
        redline="Customer telemetry and databases shall remain hosted within India sovereign territory.",
        evidence="Vendor reserves right to mirror telemetry across global clusters without notice.",
        assignee_email="kavita.deshmukh@apexfinancial.com",
        due_days=3,
        custom_key="RISK-102"
    )

init_sample_jira_tasks()
agent_engine = RiskwiseAgentEngine()

# --- Request / Response Models ---
class ActionDecision(BaseModel):
    action_id: str
    approved: bool
    override_assignee: Optional[str] = None
    override_redline: Optional[str] = None
    review_notes: Optional[str] = ""

class ResumeReviewRequest(BaseModel):
    reviewer_email: str = "compliance-officer@apexfinancial.com"
    decisions: List[ActionDecision]

class ClauseAnalysisRequest(BaseModel):
    contract_title: str = "Custom Vendor Agreement"
    clause_text: str
    section_number: str = "1.0"
    section_title: str = "Uploaded Clause"
    page_number: int = 1

class AgentConfigUpdate(BaseModel):
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = "gemini-2.0-flash"

# --- API Endpoints ---

@app.get("/api/v1/overview")
def get_executive_overview():
    """Returns top-level enterprise risk metrics and executive ROI."""
    pending_count = sum(1 for t in ACTIVE_THREADS.values() if t.get("status") == "AWAITING_APPROVAL")
    dispatched_count = len(DISPATCHED_JIRA_ISSUES)
    resolved_count = sum(1 for t in DISPATCHED_JIRA_ISSUES.values() if t.get("status") == "RESOLVED")
    overdue_count = sum(1 for t in DISPATCHED_JIRA_ISSUES.values() if t.get("status") == "OVERDUE")

    return {
        "kpis": {
            "contracts_analyzed": 28,
            "pending_human_reviews": pending_count,
            "dispatched_tasks": dispatched_count,
            "resolved_tasks": resolved_count,
            "overdue_escalations": overdue_count,
            "avg_review_turnaround": "14.2 minutes",
            "manual_baseline_turnaround": "21 business days",
            "turnaround_reduction_pct": "98.8%",
            "statutory_liability_shielded": "₹500+ Crore ($60M+ USD)"
        },
        "enterprise_workspaces": [
            {"id": "ws-apex", "name": "Apex Financial Enterprises", "jurisdiction": "IND", "sector": "BFSI"}
        ],
        "engine_info": agent_engine.get_model_status()
    }

@app.get("/api/v1/agent/status")
def get_agent_status():
    """Returns the live AI engine status (Google Gemini vs Deterministic Engine)."""
    return agent_engine.get_model_status()

@app.post("/api/v1/agent/config")
def update_agent_config(payload: AgentConfigUpdate):
    """Configures the Google Gemini API key or model name dynamically."""
    if payload.gemini_api_key is not None:
        status = agent_engine.configure_gemini(
            api_key=payload.gemini_api_key,
            model_name=payload.gemini_model or "gemini-2.0-flash"
        )
        return {"success": True, "status": status}
    return {"success": False, "status": agent_engine.get_model_status()}

@app.get("/api/v1/matrix/gap-overview")
def get_gap_matrix_overview():
    """Returns the comprehensive Policy ↔ Contract Gap comparison matrix."""
    return {
        "contract": "CloudStack Global Services - Master Cloud Services Agreement (2026)",
        "internal_standard": "Apex Financial Enterprise Security Baseline",
        "rows": MASTER_GAP_MATRIX
    }

@app.get("/api/v1/reviews/pending")
def get_pending_reviews():
    """Returns all paused review threads waiting for compliance approval."""
    results = []
    for t_id, thread in ACTIVE_THREADS.items():
        if thread.get("status") == "AWAITING_APPROVAL":
            results.append({
                "thread_id": t_id,
                "contract_id": thread.get("contract_id"),
                "contract_title": thread.get("contract_title"),
                "counterparty": thread.get("counterparty"),
                "section_title": thread.get("section_title"),
                "page_number": thread.get("page_number", 1),
                "section_number": thread.get("section_number", ""),
                "highest_severity": thread.get("severity", "HIGH"),
                "composite_risk_score": thread.get("quantitative_metrics", {}).get("composite_risk_score", 8.0),
                "pending_actions_count": len(thread.get("pending_actions", []))
            })
    return results

@app.get("/api/v1/reviews/{thread_id}")
def get_review_detail(thread_id: str):
    """Returns complete deep-dive inspection payload for a paused review checkpoint."""
    thread = ACTIVE_THREADS.get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Review thread not found.")
    return thread

@app.post("/api/v1/reviews/{thread_id}/resume")
def resume_review_thread(thread_id: str, payload: ResumeReviewRequest):
    """
    Unfreezes the LangGraph agent workflow with compliance reviewer decisions.
    Dispatches Jira tasks, Slack Block Kit cards, and pre-formatted vendor email drafts.
    """
    thread = ACTIVE_THREADS.get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Review thread not found.")

    decisions_by_id = {d.action_id: d for d in payload.decisions}
    dispatched_items = []

    for action in thread.get("pending_actions", []):
        dec = decisions_by_id.get(action["action_id"])
        if dec and not dec.approved:
            continue

        final_redline = (dec.override_redline if dec and dec.override_redline else None) or action.get("proposed_redline")
        final_owner = (dec.override_assignee if dec and dec.override_assignee else None) or action.get("suggested_owner")

        # 1. Create formatted Jira issue in Atlassian Document Format (ADF)
        jira_res = create_jira_issue(
            summary=action.get("summary", "Contract Risk Remediation"),
            severity=action.get("severity", "HIGH"),
            redline=final_redline,
            evidence=thread.get("raw_clause_text", ""),
            assignee_email=final_owner,
            due_days=action.get("sla_days", 5)
        )

        # 2. Dispatch Slack interactive Block Kit card
        slack_res = send_slack_alert(
            jira_key=jira_res["key"],
            jira_url=jira_res["url"],
            summary=action.get("summary", ""),
            severity=action.get("severity", "HIGH"),
            owner=final_owner,
            redline=final_redline
        )

        dispatched_items.append({
            "action_id": action["action_id"],
            "jira_issue_key": jira_res["key"],
            "jira_url": jira_res["url"],
            "owner": final_owner,
            "redline": final_redline,
            "slack_alert_sent": True,
            "vendor_email_ready": bool(thread.get("vendor_email"))
        })

    thread["status"] = "COMPLETED"
    thread["reviewer_decisions"] = [d.model_dump() for d in payload.decisions]
    thread["dispatched_items"] = dispatched_items
    thread["reviewed_at"] = datetime.now(timezone.utc).isoformat()

    return {
        "status": "COMPLETED",
        "thread_id": thread_id,
        "dispatched_count": len(dispatched_items),
        "dispatched_actions": dispatched_items,
        "vendor_email": thread.get("vendor_email")
    }

@app.post("/api/v1/reviews/reset")
def reset_demo_state():
    """
    1-Click Demo Reset: Restores the review queue, Jira backlog, and audit logs
    to their initial demo state.
    """
    global ACTIVE_THREADS
    ACTIVE_THREADS = {t["thread_id"]: copy.deepcopy(t) for t in INITIAL_REVIEW_THREADS}
    init_sample_jira_tasks()
    SLACK_ALERT_FEED.clear()
    WEBHOOK_AUDIT_LOGS.clear()
    ESCALATION_EMAIL_LOGS.clear()
    return {
        "success": True,
        "message": "Demo state successfully reset to initial pre-configured walkthrough state.",
        "active_threads_count": len(ACTIVE_THREADS)
    }

@app.post("/api/v1/analyze/clause")
def analyze_custom_clause(payload: ClauseAnalysisRequest):
    """
    Live Interactive Sandbox: Ingests any arbitrary contract clause, runs the 5-stage
    agentic model, computes Composite Risk Score (CRS), and pre-stages it for human review.
    """
    findings = agent_engine.analyze_clause(
        payload.clause_text,
        metadata={"section": payload.section_number, "page": payload.page_number}
    )

    if not findings:
        raise HTTPException(status_code=400, detail="Could not analyze clause.")

    primary = findings[0]
    thread_id = f"thread-custom-{uuid.uuid4().hex[:8]}"

    new_thread = {
        "thread_id": thread_id,
        "contract_id": f"contract-{uuid.uuid4().hex[:6]}",
        "contract_title": payload.contract_title,
        "counterparty": "Custom Uploaded Counterparty",
        "section_title": f"{payload.section_number} - {payload.section_title}",
        "page_number": payload.page_number,
        "section_number": payload.section_number,
        "raw_clause_text": payload.clause_text,
        "normalized_summary": primary.downstream_dispatch.ticket_summary,
        "retrieved_policies": [primary.internal_policy_benchmark],
        "retrieved_regulations": primary.regulatory_statutory_benchmark,
        "quantitative_metrics": primary.quantitative_metrics.model_dump(),
        "severity": primary.severity_classification,
        "status": "AWAITING_APPROVAL",
        "explainable_ai": primary.explainable_ai.model_dump() if primary.explainable_ai else None,
        "vendor_email": primary.vendor_email.model_dump() if primary.vendor_email else None,
        "pending_actions": [
            {
                "action_id": f"act-{uuid.uuid4().hex[:6]}",
                "severity": primary.severity_classification,
                "summary": primary.downstream_dispatch.ticket_summary,
                "suggested_owner": primary.remediation.suggested_owner,
                "suggested_owner_name": primary.remediation.suggested_owner_name or primary.remediation.suggested_owner,
                "proposed_redline": primary.remediation.proposed_contract_redline,
                "sla_days": primary.remediation.sla_resolution_days,
                "ticket_priority": primary.downstream_dispatch.ticket_priority
            }
        ]
    }
    ACTIVE_THREADS[thread_id] = new_thread

    return {
        "thread_id": thread_id,
        "finding": primary.model_dump(),
        "ready_for_review": True
    }

@app.post("/api/v1/analyze/demo-contract")
def load_and_analyze_demo_agreement():
    """
    1-Click Demo Ingestion: Ingests the pre-packaged CloudStack 2026 Vendor Agreement,
    runs the 5-stage agent analysis across all 4 key sections, and populates the review queue.
    """
    demo_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "demo_sample",
        "CloudStack_Vendor_Agreement_2026.txt"
    )

    if not os.path.exists(demo_file):
        raise HTTPException(status_code=404, detail="Demo agreement exhibit not found.")

    with open(demo_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Split into sections
    sections = [
        {
            "section": "Section 8.1",
            "title": "Data Residency and Processing",
            "page": 4,
            "text": "Vendor reserves the right to transfer, mirror, and store Customer telemetry and analytical audit logs across any of Vendor’s global cloud clusters (including data centers located in North America, Southeast Asia, and Eastern Europe) without prior written notice, to ensure continuous platform load balancing."
        },
        {
            "section": "Section 14.2",
            "title": "Breach Notification SLA",
            "page": 6,
            "text": "In the event of a confirmed security incident or unauthorized access resulting in disclosure of Customer confidential records, Vendor shall notify Customer in writing within five (5) business days after internal technical confirmation that an unauthorized disclosure has occurred."
        },
        {
            "section": "Section 18.1",
            "title": "Encryption & Key Management",
            "page": 8,
            "text": "Customer records stored in multi-tenant buckets shall be protected by standard platform-level encryption (AES-128 or Vendor proprietary key schemes). Custom key management is available solely under premium enterprise add-on tiers."
        },
        {
            "section": "Section 21.1",
            "title": "Limitation of Liability Super-Cap",
            "page": 9,
            "text": "Vendor’s total cumulative liability arising out of or related to this Agreement, including data breach damages, regulatory penalties, or confidentiality indemnities, shall be strictly capped at the total amount actually paid by Customer to Vendor in the one (1) month preceding the incident ($4,850 USD)."
        }
    ]

    checkpoints_created = []
    for sec in sections:
        findings = agent_engine.analyze_clause(sec["text"], metadata={"section": sec["section"], "page": sec["page"]})
        if findings:
            f = findings[0]
            tid = f"thread-csa-{sec['section'].replace('Section ', '').replace('.', '-')}"
            ACTIVE_THREADS[tid] = {
                "thread_id": tid,
                "contract_id": "csa-apex-8821",
                "contract_title": "CloudStack Global Services - Master Cloud Services Agreement (2026)",
                "counterparty": "CloudStack Global Services Inc.",
                "section_title": f"{sec['section']} - {sec['title']}",
                "page_number": sec["page"],
                "section_number": sec["section"],
                "raw_clause_text": sec["text"],
                "normalized_summary": f.downstream_dispatch.ticket_summary,
                "retrieved_policies": [f.internal_policy_benchmark],
                "retrieved_regulations": f.regulatory_statutory_benchmark,
                "quantitative_metrics": f.quantitative_metrics.model_dump(),
                "severity": f.severity_classification,
                "status": "AWAITING_APPROVAL",
                "explainable_ai": f.explainable_ai.model_dump() if f.explainable_ai else None,
                "vendor_email": f.vendor_email.model_dump() if f.vendor_email else None,
                "pending_actions": [
                    {
                        "action_id": f"act-{tid}",
                        "severity": f.severity_classification,
                        "summary": f.downstream_dispatch.ticket_summary,
                        "suggested_owner": f.remediation.suggested_owner,
                        "suggested_owner_name": f.remediation.suggested_owner_name or f.remediation.suggested_owner,
                        "proposed_redline": f.remediation.proposed_contract_redline,
                        "sla_days": f.remediation.sla_resolution_days,
                        "ticket_priority": f.downstream_dispatch.ticket_priority
                    }
                ]
            }
            checkpoints_created.append(tid)

    return {
        "success": True,
        "contract": "CloudStack Global Services (2026)",
        "clauses_analyzed": len(sections),
        "checkpoints_created": checkpoints_created,
        "message": f"Successfully parsed agreement and created {len(checkpoints_created)} paused review gates in the dashboard."
    }

@app.post("/api/v1/analyze/upload")
async def upload_contract_file(
    file: UploadFile = File(...),
    contract_title: str = Form("Uploaded Agreement")
):
    """
    Accepts PDF, DOCX, or TXT file uploads, extracts clauses, and benchmarks them.
    """
    filename = file.filename or "contract.txt"
    content_bytes = await file.read()
    extracted_text = ""

    if filename.endswith(".pdf"):
        try:
            import pypdf, io
            reader = pypdf.PdfReader(io.BytesIO(content_bytes))
            for page in reader.pages:
                extracted_text += (page.extract_text() or "") + "\n\n"
        except Exception as e:
            extracted_text = f"Error reading PDF: {e}"
    elif filename.endswith(".docx"):
        try:
            import zipfile, xml.etree.ElementTree as ET, io
            with zipfile.ZipFile(io.BytesIO(content_bytes)) as z:
                xml_content = z.read("word/document.xml")
                tree = ET.fromstring(xml_content)
                texts = []
                for elem in tree.iter():
                    if elem.tag.endswith("}p"):
                        p = "".join(n.text for n in elem.iter() if n.tag.endswith("}t") and n.text)
                        if p: texts.append(p)
                extracted_text = "\n\n".join(texts)
        except Exception as e:
            extracted_text = f"Error reading DOCX: {e}"
    else:
        extracted_text = content_bytes.decode("utf-8", errors="replace")

    paragraphs = [p.strip() for p in extracted_text.split("\n\n") if len(p.strip()) > 40]
    analyzed_count = 0

    for i, para in enumerate(paragraphs[:8]):
        findings = agent_engine.analyze_clause(para, metadata={"page": (i // 3) + 1, "section": f"Section {i+1}"})
        if findings:
            analyzed_count += 1
            f = findings[0]
            tid = f"thread-upload-{uuid.uuid4().hex[:6]}"
            ACTIVE_THREADS[tid] = {
                "thread_id": tid,
                "contract_id": f"upload-{uuid.uuid4().hex[:4]}",
                "contract_title": contract_title,
                "counterparty": "Contract Counterparty",
                "section_title": f"Paragraph {i+1} Review",
                "page_number": (i // 3) + 1,
                "section_number": str(i+1),
                "raw_clause_text": para,
                "normalized_summary": f.downstream_dispatch.ticket_summary,
                "retrieved_policies": [f.internal_policy_benchmark],
                "retrieved_regulations": f.regulatory_statutory_benchmark,
                "quantitative_metrics": f.quantitative_metrics.model_dump(),
                "severity": f.severity_classification,
                "status": "AWAITING_APPROVAL",
                "explainable_ai": f.explainable_ai.model_dump() if f.explainable_ai else None,
                "vendor_email": f.vendor_email.model_dump() if f.vendor_email else None,
                "pending_actions": [
                    {
                        "action_id": f"act-{uuid.uuid4().hex[:6]}",
                        "severity": f.severity_classification,
                        "summary": f.downstream_dispatch.ticket_summary,
                        "suggested_owner": f.remediation.suggested_owner,
                        "suggested_owner_name": f.remediation.suggested_owner_name or f.remediation.suggested_owner,
                        "proposed_redline": f.remediation.proposed_contract_redline,
                        "sla_days": f.remediation.sla_resolution_days,
                        "ticket_priority": f.downstream_dispatch.ticket_priority
                    }
                ]
            }

    return {
        "filename": filename,
        "paragraphs_found": len(paragraphs),
        "risk_checkpoints_created": analyzed_count,
        "message": f"Successfully parsed {filename} and created {analyzed_count} paused review gates in the dashboard."
    }

@app.get("/api/v1/jira/tasks")
def list_jira_tasks():
    """Lists all active and resolved Jira tickets dispatched by the agent."""
    return list(DISPATCHED_JIRA_ISSUES.values())

@app.post("/api/v1/jira/tasks/{key}/resolve")
def simulate_jira_ticket_resolution(key: str):
    """
    Interactive Simulation: Simulates a user closing the ticket in Atlassian Jira.
    Triggers the Jira Webhook endpoint to demonstrate bi-directional closure!
    """
    if key not in DISPATCHED_JIRA_ISSUES:
        raise HTTPException(status_code=404, detail="Jira ticket not found.")

    DISPATCHED_JIRA_ISSUES[key]["status"] = "RESOLVED"
    DISPATCHED_JIRA_ISSUES[key]["resolved_by"] = "Aditi Rao (Compliance Lead)"
    DISPATCHED_JIRA_ISSUES[key]["resolved_at"] = datetime.now(timezone.utc).isoformat()

    WEBHOOK_AUDIT_LOGS.insert(0, {
        "event": "jira:issue_updated",
        "jira_key": key,
        "status": "RESOLVED",
        "resolver": "Aditi Rao (Compliance Lead)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "detail": f"Bi-directional sync confirmed: Jira issue {key} marked RESOLVED. Finding closed in compliance audit ledger."
    })

    return {
        "success": True,
        "message": f"Ticket {key} resolved in Jira. Bi-directional webhook triggered.",
        "ticket": DISPATCHED_JIRA_ISSUES[key]
    }

@app.post("/api/v1/sla/simulate-breach")
def simulate_sla_breach(jira_key: Optional[str] = None):
    """
    Interactive Simulation: Triggers the 24/7 SLA Watchdog overdue condition (>3 days),
    demonstrating the automated executive managerial escalation email.
    """
    target_key = jira_key or (list(DISPATCHED_JIRA_ISSUES.keys())[0] if DISPATCHED_JIRA_ISSUES else "RISK-104")
    issue = DISPATCHED_JIRA_ISSUES.get(target_key, {
        "summary": "Breach Notification SLA 12h Redline Execution",
        "severity": "CRITICAL",
        "assignee": "arun.sharma@apexfinancial.com",
        "redline": "Vendor shall notify Customer in writing within twelve (12) hours of any security event."
    })

    issue["status"] = "OVERDUE"

    res = send_manager_escalation_email(
        mgr_email="priya.nair@apexfinancial.com",
        mgr_name="Priya Nair (VP of Risk & Compliance)",
        emp_name="Arun Sharma",
        emp_email="arun.sharma@apexfinancial.com",
        jira_key=target_key,
        summary=issue.get("summary", "Contractual Remediation"),
        severity=issue.get("severity", "CRITICAL"),
        days_overdue=3.4,
        redline=issue.get("redline", "")
    )

    return {
        "success": True,
        "message": "24/7 SLA Watchdog triggered: Managerial escalation dispatched to Priya Nair (VP of Risk)",
        "escalation_record": res
    }

@app.get("/api/v1/sla/status")
def get_sla_status():
    """Returns SLA Watchdog metrics and escalation email logs."""
    return {
        "watchdog_state": "ACTIVE",
        "interval_seconds": 3600,
        "recent_escalations": ESCALATION_EMAIL_LOGS,
        "webhook_audit_trail": WEBHOOK_AUDIT_LOGS,
        "slack_alerts": SLACK_ALERT_FEED
    }

@app.get("/api/v1/benchmarks")
def get_benchmarks():
    """Returns statutory regulations, corporate policies, and employee routing matrix."""
    return {
        "regulations": MASTER_REGULATIONS,
        "policies": INTERNAL_POLICIES,
        "employees": EMPLOYEES
    }

# Mount frontend directory for UI assets
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>RISKWISE AI Backend Running. Frontend index.html not found.</h1>")
