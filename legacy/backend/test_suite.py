import os
import sys
import unittest

# Ensure backend directory is in python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from starlette.testclient import TestClient
from api_server import app, ACTIVE_THREADS
from riskwise_agent import RiskwiseAgentEngine, calculate_crs

class TestRiskwiseAgent(unittest.TestCase):
    def setUp(self):
        self.engine = RiskwiseAgentEngine()

    def test_crs_calculation(self):
        # Raw base: 5.0 * 0.6 + 4.5 * 0.4 = 3.0 + 1.8 = 4.8. Mult: 1.45 => 6.96.
        # Normalized: (6.96 / 7.5) * 10 = 9.28 -> 9.3
        crs = calculate_crs(5.0, 4.5, 1.45)
        self.assertGreaterEqual(crs, 1.0)
        self.assertLessEqual(crs, 10.0)
        self.assertAlmostEqual(crs, 9.3, delta=0.2)

    def test_breach_sla_detection(self):
        clause = "Vendor shall notify Customer in writing within five (5) business days after internal confirmation."
        findings = self.engine.analyze_clause(clause, {"section": "14.2", "page": 6})
        self.assertGreaterEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f.severity_classification, "CRITICAL")
        self.assertIn("twelve (12) hours", f.remediation.proposed_contract_redline)
        self.assertIsNotNone(f.explainable_ai)
        self.assertIsNotNone(f.vendor_email)
        self.assertIn("CERT-In", f.explainable_ai.regulatory_exposure)

    def test_data_residency_detection(self):
        clause = "Vendor reserves the right to transfer, mirror, and store Customer telemetry across any global clusters."
        findings = self.engine.analyze_clause(clause, {"section": "8.1", "page": 4})
        self.assertGreaterEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f.severity_classification, "CRITICAL")
        self.assertIn("domestic jurisdiction", f.remediation.proposed_contract_redline)

    def test_liability_supercap_detection(self):
        clause = "Vendor cumulative liability capped at total amount paid in 1 month preceding incident ($4,850 USD)."
        findings = self.engine.analyze_clause(clause, {"section": "21.1", "page": 9})
        self.assertGreaterEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f.severity_classification, "HIGH")
        self.assertIn("Super-Cap", f.remediation.proposed_contract_redline)

    def test_encryption_detection(self):
        clause = "Customer records stored in multi-tenant buckets protected by platform-level AES-128 or Vendor proprietary key schemes."
        findings = self.engine.analyze_clause(clause, {"section": "18.1", "page": 8})
        self.assertGreaterEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f.severity_classification, "HIGH")
        self.assertIn("AES-256", f.remediation.proposed_contract_redline)

    def test_model_status(self):
        status = self.engine.get_model_status()
        self.assertIn("active_engine", status)
        self.assertTrue(status["explainable_ai_enabled"])


class TestRiskwiseAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Ensure fresh state
        self.client.post("/api/v1/reviews/reset")

    def test_serve_index_html(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("RISKWISE AI", res.text)
        self.assertIn("Human Review Queue", res.text)

    def test_overview_kpis(self):
        res = self.client.get("/api/v1/overview")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("kpis", data)
        self.assertGreaterEqual(data["kpis"]["pending_human_reviews"], 1)
        self.assertEqual(data["kpis"]["avg_review_turnaround"], "14.2 minutes")

    def test_agent_status(self):
        res = self.client.get("/api/v1/agent/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("active_engine", data)

    def test_gap_matrix_overview(self):
        res = self.client.get("/api/v1/matrix/gap-overview")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(len(data["rows"]), 4)

    def test_pending_reviews_list(self):
        res = self.client.get("/api/v1/reviews/pending")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data), 4)

    def test_review_detail(self):
        res = self.client.get("/api/v1/reviews/thread-csa-14-2")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["severity"], "CRITICAL")
        self.assertIn("explainable_ai", data)
        self.assertIn("vendor_email", data)

    def test_review_resume_and_dispatch(self):
        payload = {
            "reviewer_email": "compliance@apexfinancial.com",
            "decisions": [
                {
                    "action_id": "act-csa-breach-sla",
                    "approved": True,
                    "override_redline": "Vendor shall report within 12 hours.",
                    "override_assignee": "arun.sharma@apexfinancial.com"
                }
            ]
        }
        res = self.client.post("/api/v1/reviews/thread-csa-14-2/resume", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(data["dispatched_count"], 1)
        self.assertTrue(data["dispatched_actions"][0]["slack_alert_sent"])

    def test_jira_tasks_and_bi_directional_webhook(self):
        res = self.client.get("/api/v1/jira/tasks")
        self.assertEqual(res.status_code, 200)
        tasks = res.json()
        self.assertGreaterEqual(len(tasks), 1)

        # Resolve one task
        resolve_res = self.client.post("/api/v1/jira/tasks/RISK-102/resolve")
        self.assertEqual(resolve_res.status_code, 200)
        resolve_data = resolve_res.json()
        self.assertEqual(resolve_data["ticket"]["status"], "RESOLVED")

    def test_sla_breach_simulation(self):
        res = self.client.post("/api/v1/sla/simulate-breach")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("escalation_record", data)
        self.assertIn("Priya Nair", data["escalation_record"]["manager_name"])

    def test_clause_analysis_sandbox(self):
        payload = {
            "contract_title": "Enterprise Cloud SaaS",
            "clause_text": "Vendor total liability capped at $1,000.",
            "section_number": "19.0",
            "section_title": "Liability",
            "page_number": 5
        }
        res = self.client.post("/api/v1/analyze/clause", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["ready_for_review"])
        self.assertIn("thread_id", data)

    def test_demo_contract_1click_ingestion(self):
        res = self.client.post("/api/v1/analyze/demo-contract")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["clauses_analyzed"], 4)

if __name__ == "__main__":
    unittest.main()
