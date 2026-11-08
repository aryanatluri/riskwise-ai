import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.db import new_session, set_tenant, system_session
from app.jobs.sla import sla_sweep
from app.models import Finding
from tests.conftest import token_for


def make_org(client, email="admin@bank.in", name="Bank One", jurisdiction="IN"):
    h = token_for(client, email)
    r = client.post("/api/v1/orgs", json={"name": name, "jurisdiction": jurisdiction}, headers=h)
    assert r.status_code == 201, r.text
    org = r.json()
    return {**h, "X-Org-Id": org["id"]}, org


def upload(client, h, data, name="cloudstack.txt"):
    r = client.post(
        "/api/v1/contracts",
        headers=h,
        files={"file": (name, data, "text/plain")},
        data={"title": "CloudStack MSA", "counterparty": "CloudStack"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_requires_auth(client):
    assert client.get("/api/v1/orgs").status_code == 401
    assert client.get("/api/v1/orgs", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_org_created_with_baseline_policies_and_packs(client):
    h, org = make_org(client)
    assert org["role"] == "admin" and org["regulation_packs"] == ["india_bfsi"]
    codes = {p["code"] for p in client.get("/api/v1/policies", headers=h).json()}
    assert {"SEC-01", "DATA-01", "LEG-01"} <= codes
    packs = client.get("/api/v1/packs").json()
    assert all(p["reviewed"] is False for p in packs)


def test_upload_analyze_review_flow(client, demo_contract):
    h, _ = make_org(client)
    out = upload(client, h, demo_contract)
    assert out["run"]["status"] == "completed" and out["run"]["mode"] == "rules_only"
    assert out["run"]["stats"]["findings"] == 6

    findings = client.get("/api/v1/findings?status=open", headers=h).json()
    assert len(findings) == 6
    top = findings[0]
    assert top["severity"] == "CRITICAL" and top["clause"]["section_number"] == "14.2"
    assert top["regulation_refs"] and top["proposed_redline"]

    r = client.post(
        f"/api/v1/findings/{top['id']}/decision",
        headers=h,
        json={
            "decision": "approve",
            "assignee_email": "infosec@bank.in",
            "notes": "agreed",
            "proposed_redline": "Vendor shall notify within 6 hours.",
        },
    )
    assert r.status_code == 200 and r.json()["status"] == "approved" and r.json()["due_at"]
    assert (
        client.post(f"/api/v1/findings/{top['id']}/decision", headers=h, json={"decision": "reject"}).status_code == 409
    )

    # No integrations configured yet.
    assert client.post(f"/api/v1/findings/{top['id']}/dispatch", headers=h).status_code == 422

    csv_text = client.get("/api/v1/findings/export.csv", headers=h).text
    assert "CloudStack MSA" in csv_text and "IN-CERTIN-6H" in csv_text

    actions = [a["action"] for a in client.get("/api/v1/audit", headers=h).json()]
    for a in ("org.created", "contract.uploaded", "analysis.completed", "finding.approved", "findings.exported"):
        assert a in actions

    # Re-analysis keeps decided findings and replaces open ones.
    cid = out["contract"]["id"]
    assert client.post(f"/api/v1/contracts/{cid}/analyze", headers=h).status_code == 200
    statuses = sorted(f["status"] for f in client.get(f"/api/v1/findings?contract_id={cid}", headers=h).json())
    assert statuses.count("approved") == 1 and statuses.count("open") == 6


def test_tenant_isolation(client, demo_contract):
    ha, org_a = make_org(client, "a@bank-a.in", "Bank A")
    upload(client, ha, demo_contract)
    hb, org_b = make_org(client, "b@bank-b.in", "Bank B")

    # B cannot act inside A's org.
    hb_on_a = {**hb, "X-Org-Id": org_a["id"]}
    assert client.get("/api/v1/findings", headers=hb_on_a).status_code == 404
    assert client.get("/api/v1/findings", headers=hb).json() == []
    fid = client.get("/api/v1/findings", headers=ha).json()[0]["id"]
    assert client.get(f"/api/v1/findings/{fid}", headers=hb).status_code == 404

    # Second lock: even a raw query pinned to org B sees none of A's rows (RLS).
    db = new_session()
    try:
        set_tenant(db, org_b["id"])
        assert db.scalars(select(Finding)).all() == []
        set_tenant(db, None)
        assert db.scalars(select(Finding)).all() == []
    finally:
        db.close()


def test_roles(client, demo_contract):
    h_admin, org = make_org(client)
    h_viewer = {**token_for(client, "viewer@bank.in"), "X-Org-Id": org["id"]}
    client.get("/api/v1/me", headers=h_viewer)  # first sign-in creates the user
    r = client.post("/api/v1/org/members", headers=h_admin, json={"email": "viewer@bank.in", "role": "viewer"})
    assert r.status_code == 201
    assert client.get("/api/v1/findings", headers=h_viewer).status_code == 200
    assert (
        client.post(
            "/api/v1/contracts", headers=h_viewer, files={"file": ("c.txt", demo_contract, "text/plain")}
        ).status_code
        == 403
    )
    assert client.put("/api/v1/org/settings", headers=h_viewer, json={"sla_escalation_days": 5}).status_code == 403
    assert client.get("/api/v1/audit", headers=h_viewer).status_code == 403
    me_id = client.get("/api/v1/me", headers=h_admin).json()["id"]
    assert client.delete(f"/api/v1/org/members/{me_id}", headers=h_admin).status_code == 409  # last admin


def test_settings_secrets_are_write_only(client):
    h, _ = make_org(client)
    assert client.put("/api/v1/org/settings", headers=h, json={"analysis_mode": "hybrid"}).status_code == 422
    r = client.put(
        "/api/v1/org/settings",
        headers=h,
        json={
            "llm": {"provider": "gemini", "model": "gemini-x", "api_key": "AIza-secret-key-9876"},
            "slack_webhook": "https://hooks.slack.com/services/T/B/X",
            "analysis_mode": "hybrid",
        },
    )
    assert r.status_code == 200, r.text
    body = json.dumps(r.json())
    assert "AIza-secret" not in body and "hooks.slack.com" not in body
    assert r.json()["llm"]["api_key_last4"] == "9876" and r.json()["analysis_mode"] == "hybrid"


def test_upload_validation(client):
    h, _ = make_org(client)
    r = client.post("/api/v1/contracts", headers=h, files={"file": ("x.exe", b"MZ...", "application/octet-stream")})
    assert r.status_code == 422


def test_dispatch_and_jira_webhook_round_trip(client, demo_contract, monkeypatch):
    h, org = make_org(client)
    upload(client, h, demo_contract)
    client.put(
        "/api/v1/org/settings",
        headers=h,
        json={
            "jira": {
                "base_url": "https://bank.atlassian.net",
                "email": "bot@bank.in",
                "project_key": "RISK",
                "token": "jira-token-123",
            },
        },
    )
    monkeypatch.setattr("app.api.routes.findings.create_issue", lambda **kw: "RISK-7")
    fid = client.get("/api/v1/findings", headers=h).json()[0]["id"]
    client.post(f"/api/v1/findings/{fid}/decision", headers=h, json={"decision": "approve"})
    r = client.post(f"/api/v1/findings/{fid}/dispatch", headers=h)
    assert r.status_code == 200 and r.json()["jira_key"] == "RISK-7" and r.json()["status"] == "dispatched"

    secret = client.post("/api/v1/org/settings/jira-webhook-secret", headers=h).json()["secret"]
    payload = json.dumps(
        {"issue": {"key": "RISK-7", "fields": {"status": {"name": "Done"}}}, "user": {"displayName": "Kavita"}}
    ).encode()
    url = f"/api/v1/webhooks/jira/{org['id']}"
    assert client.post(url, content=payload, headers={"X-Hub-Signature": "sha256=deadbeef"}).status_code == 401
    sig = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    r = client.post(url, content=payload, headers={"X-Hub-Signature": sig})
    assert r.status_code == 200 and r.json()["resolved"] == fid
    assert client.get(f"/api/v1/findings/{fid}", headers=h).json()["status"] == "resolved"


def test_sla_sweep_escalates_overdue_findings(client, demo_contract):
    h, _ = make_org(client)
    upload(client, h, demo_contract)
    client.put(
        "/api/v1/org/settings", headers=h, json={"escalation_email": "vp-risk@bank.in", "sla_escalation_days": 3}
    )
    fid = client.get("/api/v1/findings", headers=h).json()[0]["id"]
    client.post(f"/api/v1/findings/{fid}/decision", headers=h, json={"decision": "approve"})

    assert client.post("/api/v1/jobs/sla-sweep").status_code == 401
    r = client.post("/api/v1/jobs/sla-sweep", headers={"X-Job-Token": "test-job-token"})
    assert r.json()["escalated"] == 0  # not overdue yet

    with system_session() as db:
        future = datetime.now(UTC) + timedelta(days=30)
        assert sla_sweep(db, now=future)["escalated"] == 1
    with system_session() as db:
        assert sla_sweep(db, now=future + timedelta(days=1))["escalated"] == 0  # only once
    assert "finding.escalated" in [a["action"] for a in client.get("/api/v1/audit", headers=h).json()]


def test_audit_log_is_append_only(client):
    make_org(client)
    with pytest.raises(DBAPIError):
        with system_session() as db:
            db.execute(text("UPDATE audit_log SET action = 'tampered'"))


def test_delete_contract_removes_data(client, demo_contract):
    h, _ = make_org(client)
    cid = upload(client, h, demo_contract)["contract"]["id"]
    assert client.delete(f"/api/v1/contracts/{cid}", headers=h).status_code == 204
    assert client.get(f"/api/v1/contracts/{cid}", headers=h).status_code == 404
    assert client.get("/api/v1/findings", headers=h).json() == []
