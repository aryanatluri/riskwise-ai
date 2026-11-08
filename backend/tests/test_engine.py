from pathlib import Path

import pytest

from app.engine.analyzer import analyze_text, evidence_is_verbatim
from app.engine.llm import LLMError
from app.engine.packs import default_policy_rules
from app.engine.rules import RuleView, parse_hours
from app.engine.scoring import calculate_crs, severity_for
from app.engine.segmentation import segment

DEMO = (Path(__file__).parent / "fixtures" / "cloudstack.txt").read_text()


def rules(jurisdiction: str = "IN") -> list[RuleView]:
    keys = ("code", "title", "domain", "mandate", "criticality", "constraints", "redline_template")
    return [RuleView(**{k: r[k] for k in keys}) for r in default_policy_rules(jurisdiction)]


def test_crs_formula_matches_prototype():
    assert calculate_crs(5, 4.5, 1.45) == 9.3  # (5*.6 + 4.5*.4) * 1.45 / 7.5 * 10 = 9.28
    assert calculate_crs(5, 5, 1.5) == 10.0
    assert calculate_crs(1, 1, 1.0) == 1.3
    assert calculate_crs(99, 99, 9) == 10.0  # clamped
    assert severity_for(8.0) == "CRITICAL" and severity_for(7.9) == "HIGH" and severity_for(3.9) == "LOW"


def test_segmentation_uses_numbering():
    segs = segment(DEMO)
    assert [s.section_number for s in segs] == ["1.1", "8.1", "14.1", "14.2", "14.3", "18.1", "21.1"]
    assert segs[3].heading == "Breach Notification SLA"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("within five (5) business days", 120),
        ("within 72 hours", 72),
        ("within twenty-four hours", 24),
        ("within 2 weeks", 336),
    ],
)
def test_parse_hours(text, expected):
    assert min(parse_hours(text)) == expected


def test_rules_only_finds_all_demo_risks():
    res = analyze_text(DEMO, rules(), ["india_bfsi"])
    by_code = {h.rule_code: h for h in res.hits}
    assert set(by_code) == {"SEC-01", "DATA-01", "SEC-02", "LEG-01", "LEG-02", "LEG-04"}
    assert by_code["SEC-01"].severity == "CRITICAL"
    assert "120h" in by_code["SEC-01"].title
    # Every clause-level finding quotes the contract verbatim.
    clause_text = {s.idx: s.text for s in res.segments}
    for h in res.hits:
        if h.clause_index is not None:
            assert evidence_is_verbatim(h.evidence_quote, clause_text[h.clause_index])
    # Citations come from the pack, attached by code.
    assert any(r["code"] == "IN-CERTIN-6H" for r in by_code["SEC-01"].regulation_refs)
    # Sorted by risk.
    assert res.hits[0].crs >= res.hits[-1].crs


def test_compliant_contract_has_no_clause_findings():
    good = """
1. INCIDENTS
1.1 Vendor shall notify Customer within 12 hours of becoming aware of any security incident.
2. DATA
2.1 All Customer data shall be stored only in India. Vendor shall not transfer data outside India without prior written consent.
3. AUDIT
3.1 Vendor shall permit Customer and the RBI to audit and inspect its systems.
4. EXIT
4.1 On termination Vendor shall provide transition assistance and return of all Customer data.
"""
    res = analyze_text(good, rules(), ["india_bfsi"])
    assert res.hits == []


def test_eu_jurisdiction_uses_eu_pack():
    res = analyze_text(DEMO, rules("EU"), ["eu_finance"])
    refs = {r["code"] for h in res.hits for r in h.regulation_refs}
    assert "EU-GDPR-33" in refs and not any(c.startswith("IN-") for c in refs)


class FakeLLM:
    """Returns canned findings per clause; records calls."""

    def __init__(self, responses=None, error: LLMError | None = None):
        self.responses = responses or {}
        self.error = error
        self.calls = 0

    def structured(self, system, user, schema, name="result"):
        self.calls += 1
        if self.error:
            raise self.error
        for marker, data in self.responses.items():
            if marker in user:
                return data
        return {"findings": []}


def _llm_finding(quote, code="SEC-01", domain="breach_notification", title="LLM breach finding"):
    return {
        "rule_code": code,
        "domain": domain,
        "title": title,
        "evidence_quote": quote,
        "reasoning": "r",
        "impact": 5,
        "likelihood": 5,
        "exposure_multiplier": 1.5,
        "confidence": 0.9,
        "recommended_action": "a",
        "proposed_redline": "p",
    }


def test_llm_finding_replaces_rules_finding_for_same_domain():
    quote = "Vendor shall notify Customer in writing within five (5) business days"
    llm = FakeLLM({"Breach Notification SLA": {"findings": [_llm_finding(quote)]}})
    res = analyze_text(DEMO, rules(), ["india_bfsi"], llm)
    breach = [h for h in res.hits if h.domain == "breach_notification"]
    assert len(breach) == 1 and breach[0].source == "llm" and breach[0].title == "LLM breach finding"
    assert breach[0].crs == 10.0  # computed in code from the LLM's scores
    assert res.stats["llm_findings"] == 1


def test_llm_invented_quote_is_dropped_and_rules_finding_kept():
    llm = FakeLLM({"Breach Notification SLA": {"findings": [_llm_finding("Vendor may notify whenever it likes")]}})
    res = analyze_text(DEMO, rules(), ["india_bfsi"], llm)
    assert res.stats["dropped_unverified"] == 1
    breach = [h for h in res.hits if h.domain == "breach_notification"]
    assert len(breach) == 1 and breach[0].source == "rules"


def test_llm_unknown_rule_code_is_dropped_but_general_is_kept():
    q = "failure to report within this window shall not constitute a material breach"
    llm = FakeLLM(
        {
            "Customer agrees that failure": {
                "findings": [
                    _llm_finding(q, code="MADE-UP-9"),
                    _llm_finding(q, code="GENERAL", domain="other", title="Late reporting waived as a breach"),
                ]
            }
        }
    )
    res = analyze_text(DEMO, rules(), ["india_bfsi"], llm)
    assert res.stats["dropped_unknown_rule"] == 1
    assert any(h.title == "Late reporting waived as a breach" and h.domain == "other" for h in res.hits)


def test_llm_fatal_error_stops_calls_but_rules_still_run():
    llm = FakeLLM(error=LLMError("bad key", fatal=True))
    res = analyze_text(DEMO, rules(), ["india_bfsi"], llm)
    assert llm.calls == 1 and res.stats["llm_errors"] == 1
    assert len(res.hits) == 6


def test_llm_call_cap():
    llm = FakeLLM()
    res = analyze_text(DEMO, rules(), ["india_bfsi"], llm, max_llm_clauses=2)
    assert llm.calls == 2 and res.stats["llm_skipped_cap"] > 0
