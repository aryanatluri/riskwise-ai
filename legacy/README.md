# 🛡️ RISKWISE AI: Enterprise Risk Copilot & Autonomous Action Agent

> **Turn unstructured contracts, corporate policies, and statutory regulations into actionable enterprise risk intelligence.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Google Gemini](https://img.shields.io/badge/Google%20GenAI-Gemini%202.0%20Flash-4285F4.svg?style=flat&logo=google)](https://ai.google.dev)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests Passing](https://img.shields.io/badge/Tests-17%2F17%20Passing-brightgreen.svg)]()

---

## 📌 Executive Summary & The Problem

Enterprises receive thousands of pages of unstructured, risk-critical documents: Vendor Master Services Agreements (MSAs), Statements of Work (SOWs), Data Processing Addenda (DPAs), and jurisdictional regulations (CERT-In 2022, DPDPA 2023, EU GDPR, RBI Outsourcing Directions).

Today, legal and compliance teams review these manually line-by-line. This manual bottleneck causes **multi-week procurement delays**, **unassigned risk accountability**, and **blind-spot non-compliance** resulting in statutory penalties up to ₹250 Crore ($30M USD).

### Why Generic AI Chatbots Fail
Generic chatbots are passive: they wait for human prompts, return informal summaries, and lack accountability. Risks remain trapped inside the chat window.

**RISKWISE AI** is an **Autonomous Action Agent**. It executes a full 5-stage lifecycle:
$$\text{Detect} \longrightarrow \text{Understand} \longrightarrow \text{Decide} \longrightarrow \text{Act} \longrightarrow \text{Monitor}$$

---

## 🚀 Key Innovations & Features

1. **Google Gemini 2.0 Flash + Deterministic Rule Engine**:
   - Meaningful Gen-AI implementation using Google's official `google-genai` SDK.
   - Structured JSON output with zero-latency deterministic fallback for 100% reliable offline demonstrations.
2. **Explainable AI (XAI)**:
   - Every AI finding includes: $\text{Claim} \rightarrow \text{Verbatim Evidence} \rightarrow \text{Policy Requirement} \rightarrow \text{Statutory Law} \rightarrow \text{Conflict Reasoning} \rightarrow \text{Confidence \%}$.
3. **Objective Composite Risk Score (CRS)**:
   $$\text{CRS} = \min\left(10.0, \, \frac{(\text{Impact} \times 0.6 + \text{Likelihood} \times 0.4) \times \text{Exposure Multiplier}}{7.5} \times 10.0\right)$$
4. **Policy ↔ Contract Gap Matrix**:
   - Instant visual comparison of contract terms vs. corporate policies across Breach SLAs, Sovereign Data Residency, Liability Super-Caps, and Encryption.
5. **Human-in-the-Loop Review Gates & Autonomous Actions**:
   - Creates Atlassian Jira tasks in rich Atlassian Document Format (ADF).
   - Posts Slack Block Kit interactive notification cards.
   - Drafts executive Vendor Negotiation Notice emails.
6. **Bi-Directional Closure via Webhooks**:
   - Closing an issue in Jira automatically triggers HMAC-secured webhooks to mark compliance findings as `RESOLVED`.
7. **24/7 SLA Watchdog Daemon**:
   - Background monitor automatically raises overdue ticket priorities and emails executive HTML memos to department VPs for tickets overdue by >3 days.

---

## ⚡ Quick Start (Run Locally in Seconds)

### 1. Launch with One Command
```bash
cd "riskwise_aiproject"
./run.sh
```
*`run.sh` will activate `.venv`, run the 17-point test suite, and start the FastAPI server on [http://localhost:8000](http://localhost:8000).*

### 2. Manual Launch
```bash
cd "riskwise_aiproject"
source .venv/bin/activate
export PYTHONPATH="$PWD/backend:$PYTHONPATH"
uvicorn api_server:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

Open your browser to:
👉 **[http://localhost:8000](http://localhost:8000)**

---

## 🎬 3-Minute Video / Live Demonstration Flow

| Time | Stage | Action in UI | Key Takeaway |
|---|---|---|---|
| **0:00–0:20** | **The Problem** | View Executive Header KPIs (14.2 min review vs 21 days manual) | Real risk is hidden in paperwork already signed. |
| **0:20–0:40** | **Introduction** | Show RISKWISE AI branding and active Google Gemini status | Autonomous Agent, not a passive chatbot. |
| **0:40–1:40** | **Live Ingestion** | Click **"⚡ 1-Click Load & Ingest Demo Contract"** on Sandbox tab | Within seconds, 4 compliance gaps are benchmarked. |
| **1:40–2:20** | **Inspection & Action** | Open **Section 14.2 (Breach SLA)**. View Explainable AI Box & Gap Matrix. Click **"Authorize & Resume Engine"** | Creates Jira Task (ADF) + Slack card + Vendor Email. |
| **2:20–2:45** | **Bi-Directional Sync & SLA Watchdog** | Go to **Dispatch Tab** & click **"Simulate Mark 'Done' in Jira"** &rarr; Finding closes! Go to **Watchdog Tab** & click **"Simulate >3-Day Breach"** | Executive HTML memo sent to VP of Risk. |
| **2:45–3:00** | **Closing** | Show 5-Stage Agentic Architecture tab | *"RISKWISE AI doesn't just tell companies what went wrong. It takes action."* |

---

## 📂 Project Structure

```
riskwise_aiproject/
├── backend/
│   ├── api_server.py           # FastAPI server & REST endpoints
│   ├── riskwise_agent.py       # Google Gemini 2.0 & Deterministic Rule Engine
│   ├── sample_data.py          # Benchmark regulations, internal policies, employees
│   ├── jira_client.py          # Jira REST v3 (Atlassian Document Format)
│   ├── slack_client.py         # Slack Block Kit notification cards
│   ├── jira_webhook.py         # Bi-directional webhook receiver
│   ├── sla_monitor.py          # 24/7 SLA Watchdog & managerial HTML email generator
│   ├── requirements.txt        # Backend dependencies
│   ├── test_suite.py           # Automated unit & integration tests (17 tests)
│   └── Dockerfile              # Container spec for Cloud Run / Docker
├── frontend/
│   ├── index.html              # Complete SPA Dashboard (Tailwind CSS + Lucide)
│   └── src/
│       └── RiskReviewQueue.tsx # React TypeScript component
├── db/
│   └── init.sql                # PostgreSQL + pgvector relational/vector schema
├── demo_sample/
│   └── CloudStack_Vendor_Agreement_2026.txt  # Sample enterprise agreement
├── Dockerfile                  # Root container build
├── docker-compose.yml          # Multi-container local stack (App + PostgreSQL pgvector)
├── run.sh                      # 1-click startup script
└── README.md                   # Complete documentation
```

---

## 🧪 Testing & Verification

Run the complete automated test suite:
```bash
python backend/test_suite.py
```
Output:
```
.................
----------------------------------------------------------------------
Ran 17 tests in 0.056s

OK
```

---

## ☁️ Cloud Deployment (Google Cloud Run)

To deploy on **Google Cloud Run**:
```bash
# 1. Build and push container to Google Artifact Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/riskwise-ai:v1

# 2. Deploy to Cloud Run
gcloud run deploy riskwise-ai \
  --image gcr.io/YOUR_PROJECT_ID/riskwise-ai:v1 \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY="YOUR_GEMINI_KEY",GEMINI_MODEL="gemini-2.0-flash"
```
