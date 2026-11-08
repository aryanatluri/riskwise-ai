"""The analysis pipeline. Pure functions: no database, easy to test and evaluate.

contract text -> clauses -> rules hits (+ LLM hits on relevant clauses) -> guardrails
-> merged hits with regulation references attached by code.
"""

import logging
import re
import unicodedata
from dataclasses import dataclass, field

from app.engine.llm import LLMClient, LLMError
from app.engine.packs import DOMAINS, mandates_for
from app.engine.rules import RuleView, check_clause, check_presence, detect_domains
from app.engine.scoring import Hit, clamp
from app.engine.segmentation import Segment, segment

log = logging.getLogger("riskwise.engine")

FINDINGS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["findings"],
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "rule_code",
                    "domain",
                    "title",
                    "evidence_quote",
                    "reasoning",
                    "impact",
                    "likelihood",
                    "exposure_multiplier",
                    "confidence",
                    "recommended_action",
                    "proposed_redline",
                ],
                "properties": {
                    "rule_code": {"type": "string", "description": "A policy rule code from the list, or GENERAL"},
                    "domain": {"type": "string", "enum": DOMAINS},
                    "title": {"type": "string", "description": "Under 90 characters"},
                    "evidence_quote": {"type": "string", "description": "Exact words copied from the clause"},
                    "reasoning": {"type": "string"},
                    "impact": {"type": "number", "description": "1 (minor) to 5 (severe)"},
                    "likelihood": {"type": "number", "description": "1 (rare) to 5 (almost certain)"},
                    "exposure_multiplier": {"type": "number", "description": "1.0 to 1.5; higher for sensitive data"},
                    "confidence": {"type": "number", "description": "0 to 1"},
                    "recommended_action": {"type": "string"},
                    "proposed_redline": {"type": "string", "description": "Replacement contract wording"},
                },
            },
        }
    },
}

SYSTEM_PROMPT = """You are a contract risk analyst for a regulated financial institution.
You review ONE clause of a vendor contract against the institution's own policy rules.

Rules:
- Report a finding only when the clause conflicts with a listed policy rule, or (rule_code GENERAL)
  when it clearly weakens the institution's position on incident handling, data protection,
  liability, audit, sub-contracting or exit.
- evidence_quote MUST be copied word for word from the clause. Never paraphrase it.
- Do not cite laws or regulations; the system attaches citations itself.
- If the clause is acceptable, return an empty findings list.
- Write plainly. The reader is a compliance officer, not a lawyer."""


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip().lower()


def evidence_is_verbatim(quote: str, clause_text: str) -> bool:
    q = _norm(quote).strip(" .\"'")
    return len(q) >= 12 and q in _norm(clause_text)


def _rules_block(rules: list[RuleView]) -> str:
    lines = []
    for r in rules:
        lines.append(f"- {r.code} [{r.domain}, {r.criticality}] {r.title}: {r.mandate} Constraints: {r.constraints}")
    return "\n".join(lines)


@dataclass
class AnalysisResult:
    segments: list[Segment]
    hits: list[Hit]
    stats: dict = field(default_factory=dict)


def analyze_text(
    text: str,
    rules: list[RuleView],
    pack_keys: list[str],
    llm: LLMClient | None = None,
    *,
    max_clauses: int = 400,
    max_llm_clauses: int = 60,
) -> AnalysisResult:
    segments = segment(text, max_segments=max_clauses)
    stats = {
        "clauses": len(segments),
        "llm_calls": 0,
        "llm_errors": 0,
        "llm_findings": 0,
        "dropped_unverified": 0,
        "dropped_unknown_rule": 0,
        "rules_findings": 0,
    }
    rule_by_code = {r.code: r for r in rules}
    hits: list[Hit] = []

    # 1. Rules pass on every clause (free, deterministic).
    rules_hits: dict[int, list[Hit]] = {}
    for seg in segments:
        hs = check_clause(rules, seg.text)
        for h in hs:
            h.clause_index = seg.idx
        if hs:
            rules_hits[seg.idx] = hs
    stats["rules_findings"] = sum(len(v) for v in rules_hits.values())

    # 2. LLM pass on clauses that touch a risk domain (cost control), capped per run.
    llm_hits: dict[int, list[Hit]] = {}
    if llm is not None:
        candidates = [s for s in segments if detect_domains(s.text)][:max_llm_clauses]
        stats["llm_skipped_cap"] = max(0, len([s for s in segments if detect_domains(s.text)]) - len(candidates))
        rules_text = _rules_block(rules)
        for seg in candidates:
            user = (
                f"Policy rules:\n{rules_text}\n\n"
                f'Clause {seg.section_number or seg.idx + 1} ({seg.heading}):\n"""\n{seg.text}\n"""'
            )
            try:
                stats["llm_calls"] += 1
                data = llm.structured(SYSTEM_PROMPT, user, FINDINGS_SCHEMA, name="report_findings")
            except LLMError as exc:
                stats["llm_errors"] += 1
                stats["llm_last_error"] = str(exc)
                if exc.fatal:
                    break
                continue
            for raw in data.get("findings", []) or []:
                h = _hit_from_llm(raw, seg, rule_by_code, stats)
                if h:
                    llm_hits.setdefault(seg.idx, []).append(h)
        stats["llm_findings"] = sum(len(v) for v in llm_hits.values())

    # 3. Merge: per clause, an LLM finding replaces the rules finding for the same domain.
    for seg in segments:
        from_llm = llm_hits.get(seg.idx, [])
        llm_domains = {h.domain for h in from_llm}
        hits.extend(from_llm)
        hits.extend(h for h in rules_hits.get(seg.idx, []) if h.domain not in llm_domains)

    # 4. Contract-level checks for clauses that must exist.
    hits.extend(check_presence(rules, [s.text for s in segments]))

    # 5. Citations attached by code, from the org's regulation packs.
    for h in hits:
        h.regulation_refs = [
            {
                "code": m.code,
                "regulation": m.regulation,
                "reference": m.reference,
                "summary": m.summary,
                "penalty": m.penalty,
            }
            for m in mandates_for(pack_keys, h.domain)
        ]

    hits.sort(key=lambda h: -h.crs)
    stats["findings"] = len(hits)
    return AnalysisResult(segments=segments, hits=hits, stats=stats)


def _num(raw: dict, key: str, default: float) -> float:
    try:
        return float(raw.get(key, default))
    except (TypeError, ValueError):
        return default


def _hit_from_llm(raw: dict, seg: Segment, rule_by_code: dict[str, RuleView], stats: dict) -> Hit | None:
    if not isinstance(raw, dict):
        return None
    quote = str(raw.get("evidence_quote") or "")
    if not evidence_is_verbatim(quote, seg.text):
        stats["dropped_unverified"] += 1
        return None
    code = str(raw.get("rule_code") or "GENERAL").strip()
    rule = rule_by_code.get(code)
    if rule is None and code != "GENERAL":
        stats["dropped_unknown_rule"] += 1
        return None
    domain = rule.domain if rule else str(raw.get("domain") or "other")
    if domain not in DOMAINS:
        domain = "other"
    return Hit(
        domain=domain,
        title=str(raw.get("title") or "Contract risk")[:200],
        evidence_quote=quote.strip(),
        reasoning=str(raw.get("reasoning") or ""),
        impact=clamp(_num(raw, "impact", 3), 1, 5),
        likelihood=clamp(_num(raw, "likelihood", 3), 1, 5),
        exposure=clamp(_num(raw, "exposure_multiplier", 1.2), 1.0, 1.5),
        confidence=clamp(_num(raw, "confidence", 0.7), 0, 1),
        source="llm",
        rule_code=rule.code if rule else None,
        recommended_action=str(raw.get("recommended_action") or ""),
        proposed_redline=str(raw.get("proposed_redline") or ""),
        clause_index=seg.idx,
    )
