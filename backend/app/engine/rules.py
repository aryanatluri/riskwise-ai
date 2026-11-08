"""Rules-only engine: deterministic checks driven by each org's own policy thresholds.

Free, fast, explainable, and the fallback when an org has no LLM key. It is
deliberately conservative: it flags what it can parse with confidence and leaves
subtle drafting issues to the LLM path.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass

from app.engine.scoring import CRITICALITY_BASE, Hit, clamp

# --- Domain detection (also used to decide which clauses are worth an LLM call) ---
DOMAIN_PATTERNS: dict[str, re.Pattern] = {
    "breach_notification": re.compile(
        r"\b(breach|security incident|data incident|unauthori[sz]ed (access|disclosure)|cyber incident)\b", re.I
    ),
    "data_residency": re.compile(
        r"\b(data residency|data locali[sz]ation|transfer|mirror|replicat\w*|cross[- ]border|offshore|"
        r"data cent(er|re)s?|hosted|stor(e|ed|age) (in|within|outside)|location of (processing|data))\b",
        re.I,
    ),
    "encryption": re.compile(r"\b(encrypt\w*|aes[- ]?\d+|tls|key management|cryptograph\w*)\b", re.I),
    "liability_cap": re.compile(
        r"\b(limitation of liability|liability cap|(aggregate|cumulative|total|maximum) liability)\b", re.I
    ),
    "audit_rights": re.compile(
        r"\b(rights? to (audit|inspect)|audit rights|inspection rights|audit (and|&) inspect\w*|right of access|"
        r"(may|shall|entitled to|permit\w*|allow\w*)\b.{0,60}\b(audit|inspect)\b(?! logs?)|"
        r"(conduct|perform|carry out)\w* (an )?(audit|inspection)s?)",
        re.I,
    ),
    "subcontracting": re.compile(r"\b(sub-?contract\w*|sub-?processors?|sub-?vendors?)\b", re.I),
    "termination_exit": re.compile(
        r"\b(exit (plan|assistance|management|strategy)|transition (assistance|services)|"
        r"return (of )?(all )?(customer )?data|deletion of (customer )?data)\b",
        re.I,
    ),
}

SENSITIVE = re.compile(
    r"\b(personal data|customer (data|records)|confidential|pii|financial|banking|payment|account)\b", re.I
)

WORD_NUMBERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "twelve": 12,
    "fifteen": 15,
    "twenty": 20,
    "thirty": 30,
    "forty-eight": 48,
    "seventy-two": 72,
    "twenty-four": 24,
}
DURATION = re.compile(
    r"(?:(\d+)|\b(" + "|".join(sorted(WORD_NUMBERS, key=len, reverse=True)) + r")\b)\s*(?:\(\d+\)\s*)?"
    r"(business\s+days?|working\s+days?|calendar\s+days?|days?|hours?|weeks?)",
    re.I,
)


def detect_domains(text: str) -> set[str]:
    found = {d for d, p in DOMAIN_PATTERNS.items() if p.search(text)}
    if MOVE.search(text) and FOREIGN.search(text):  # e.g. "store records at its centres in Singapore"
        found.add("data_residency")
    return found


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.;])\s+(?=[A-Z(])", text)
    return [p for p in parts if p.strip()]


def sentence_with(text: str, pattern: re.Pattern) -> str:
    for s in sentences(text):
        if pattern.search(s):
            return s.strip()
    return text.strip()[:500]


def parse_hours(s: str) -> list[float]:
    out = []
    for m in DURATION.finditer(s):
        n = int(m.group(1)) if m.group(1) else WORD_NUMBERS[m.group(2).lower()]
        unit = m.group(3).lower()
        if unit.startswith("hour"):
            out.append(float(n))
        elif unit.startswith("week"):
            out.append(n * 168.0)
        else:
            out.append(n * 24.0)  # business days are at least this long
    return out


def parse_usd(s: str) -> list[float]:
    out = []
    for m in re.finditer(r"(?:\$|USD|US\$)\s?([\d,]+(?:\.\d+)?)\s*(million|m\b|k\b)?", s, re.I):
        v = float(m.group(1).replace(",", ""))
        mult = (m.group(2) or "").lower()
        if mult in ("million", "m"):
            v *= 1_000_000
        elif mult == "k":
            v *= 1_000
        out.append(v)
    for m in re.finditer(r"([\d,]+(?:\.\d+)?)\s*(?:USD|US dollars)", s, re.I):
        out.append(float(m.group(1).replace(",", "")))
    return out


def parse_months(s: str) -> list[int]:
    out = []
    for m in re.finditer(r"(?:(\d+)|\b(" + "|".join(WORD_NUMBERS) + r")\b)\s*(?:\(\d+\)\s*)?months?", s, re.I):
        out.append(int(m.group(1)) if m.group(1) else WORD_NUMBERS[m.group(2).lower()])
    return out


@dataclass
class RuleView:
    """The parts of a PolicyRule the engine needs (decoupled from the ORM)."""

    code: str
    title: str
    domain: str
    mandate: str
    criticality: str
    constraints: dict
    redline_template: str = ""


def _hit(
    rule: RuleView,
    clause_text: str,
    evidence: str,
    title: str,
    reasoning: str,
    action: str,
    *,
    likelihood_bump: float = 0.0,
    confidence: float = 0.9,
) -> Hit:
    impact, likelihood = CRITICALITY_BASE.get(rule.criticality, CRITICALITY_BASE["HIGH"])
    exposure = 1.45 if SENSITIVE.search(clause_text) else 1.2
    try:
        redline = rule.redline_template.format(**rule.constraints)
    except (KeyError, IndexError, ValueError):
        redline = rule.redline_template
    return Hit(
        domain=rule.domain,
        title=title,
        evidence_quote=evidence,
        reasoning=reasoning,
        impact=impact,
        likelihood=clamp(likelihood + likelihood_bump, 1, 5),
        exposure=exposure,
        confidence=confidence,
        source="rules",
        rule_code=rule.code,
        recommended_action=action,
        proposed_redline=redline,
    )


NOTIFY = re.compile(r"\b(notif\w*|inform\w*|report\w*)\b", re.I)
PRIOR_CONSENT = re.compile(r"\bprior (specific |express )?(written )?(consent|approval|authori[sz]ation)\b", re.I)


def check_breach_notification(rule: RuleView, text: str) -> Hit | None:
    max_h = float(rule.constraints.get("max_hours", 24))
    candidates = [s for s in sentences(text) if NOTIFY.search(s) and DOMAIN_PATTERNS["breach_notification"].search(s)]
    for s in candidates:
        hours = parse_hours(s)
        if hours and min(hours) > max_h:
            got = min(hours)
            return _hit(
                rule,
                text,
                s.strip(),
                f"Breach notice window of {got:g}h exceeds the {max_h:g}h policy limit",
                f"The clause gives the vendor {got:g} hours to notify; policy {rule.code} allows at most "
                f"{max_h:g}. Regulatory clocks (e.g. CERT-In's 6 hours) start when the incident is noticed, "
                "so a long vendor window can make them impossible to meet.",
                f"Reduce the vendor notice window to {max_h:g} hours or less from awareness.",
                likelihood_bump=0.5 if got >= 3 * max_h else 0.0,
                confidence=0.95,
            )
    for s in candidates:
        if re.search(
            r"\b(commercially )?reasonable (time|period)|as soon as (reasonably )?practicable\b", s, re.I
        ) and not parse_hours(s):
            return _hit(
                rule,
                text,
                s.strip(),
                "Breach notice has no fixed deadline",
                f"The vendor's notice obligation has no hard time limit, while policy {rule.code} requires "
                f"{max_h:g} hours.",
                f"Replace the open-ended wording with a fixed {max_h:g}-hour deadline.",
                confidence=0.8,
            )
    return None


FOREIGN = re.compile(
    r"\b(global|worldwide|any (of )?(vendor'?s?|its) (global )?(cloud )?(data cent(er|re)s?|clusters?|regions?|"
    r"locations?)|outside (of )?(india|the eu|the eea)|offshore|cross[- ]border|north america|united states|usa|"
    r"europe|southeast asia|singapore|philippines|united kingdom|asia[- ]pacific|other countries|"
    r"any (other )?(country|countries|jurisdiction)|where (the )?(vendor|provider|supplier) operates)\b",
    re.I,
)
MOVE = re.compile(r"\b(transfer\w*|mirror\w*|replicat\w*|stor(e|ed|ing)|process\w*|host\w*|rout\w*)\b", re.I)


def check_data_residency(rule: RuleView, text: str) -> Hit | None:
    for s in sentences(text):
        if MOVE.search(s) and FOREIGN.search(s):
            if rule.constraints.get("require_prior_consent", True) and PRIOR_CONSENT.search(s):
                return None
            no_notice = bool(re.search(r"without (any )?(prior )?(written )?notice", s, re.I))
            allowed = ", ".join(rule.constraints.get("allowed_regions", []))
            return _hit(
                rule,
                text,
                s.strip(),
                "Vendor may move data outside approved regions" + (" without notice" if no_notice else ""),
                f"The clause lets the vendor store or move data in locations outside {allowed or 'approved regions'} "
                f"without the prior written approval policy {rule.code} requires.",
                "Restrict storage and processing to approved regions; require prior written approval "
                "for any other location.",
                likelihood_bump=0.5 if no_notice else 0.0,
                confidence=0.9,
            )
    return None


def check_encryption(rule: RuleView, text: str) -> Hit | None:
    min_bits = int(rule.constraints.get("min_aes_bits", 256))
    problems = []
    evidence = ""
    for s in sentences(text):
        bits = [int(b) for b in re.findall(r"aes[- ]?(\d{3})", s, re.I)]
        if bits and min(bits) < min_bits:
            problems.append(f"AES-{min(bits)} is below the AES-{min_bits} minimum")
            evidence = evidence or s.strip()
        if (
            rule.constraints.get("require_cmk")
            and re.search(r"key", s, re.I)
            and re.search(
                r"\b(proprietary|vendor[- ]managed|premium|add-?on|additional (fee|charge|cost)|enterprise tier)\b",
                s,
                re.I,
            )
        ):
            problems.append("customer-managed keys are not provided as standard")
            evidence = evidence or s.strip()
        tls = [float(v) for v in re.findall(r"tls\s*v?(1\.[0-3])", s, re.I)]
        min_tls = float(rule.constraints.get("min_tls", 1.2))
        if tls and min(tls) < min_tls:
            problems.append(f"TLS {min(tls)} is below TLS {min_tls}")
            evidence = evidence or s.strip()
    if not problems:
        return None
    return _hit(
        rule,
        text,
        evidence,
        "Encryption below policy baseline",
        f"Against policy {rule.code}: " + "; ".join(dict.fromkeys(problems)) + ".",
        "Require AES-256 at rest with customer-managed keys at no extra cost, and modern TLS in transit.",
        confidence=0.9,
    )


CARVE_OUT = re.compile(
    r"shall not apply to .{0,120}(data|confidential|security|privacy)|"
    r"(excluding|except for|other than) .{0,80}(data protection|confidentiality|data breach)",
    re.I,
)


def check_liability_cap(rule: RuleView, text: str) -> Hit | None:
    if not DOMAIN_PATTERNS["liability_cap"].search(text) or CARVE_OUT.search(text):
        return None
    min_cap = float(rule.constraints.get("min_cap_usd", 0))
    min_months = int(rule.constraints.get("min_months_fees", 0))
    s = sentence_with(text, re.compile(r"cap|liabilit", re.I))
    amounts = parse_usd(s)
    months = parse_months(s)
    reasons = []
    if amounts and min_cap and min(amounts) < min_cap:
        reasons.append(f"the cap of USD {min(amounts):,.0f} is below the USD {min_cap:,.0f} minimum")
    if months and min_months and min(months) < min_months:
        reasons.append(f"the cap is {min(months)} month(s) of fees against a {min_months}-month minimum")
    if not reasons:
        return None
    covers_breach = bool(re.search(r"data breach|regulatory (penalt|fine)|confidentiality", s, re.I))
    return _hit(
        rule,
        text,
        s.strip(),
        "Liability cap too low for data breach exposure",
        f"Against policy {rule.code}: "
        + "; ".join(reasons)
        + ", with no carve-out for data protection"
        + (" (data breach and regulatory penalties are explicitly inside the cap)." if covers_breach else "."),
        "Carve data protection, confidentiality and regulatory fines out of the general cap, under a super-cap.",
        likelihood_bump=0.5 if covers_breach else 0.0,
        confidence=0.9,
    )


def check_subcontracting(rule: RuleView, text: str) -> Hit | None:
    if not rule.constraints.get("require_prior_consent", True):
        return None
    for s in sentences(text):
        permissive = re.search(r"\b(may|right|freely|at its discretion)\b", s, re.I)
        if DOMAIN_PATTERNS["subcontracting"].search(s) and permissive:
            if PRIOR_CONSENT.search(s):
                return None
            return _hit(
                rule,
                text,
                s.strip(),
                "Sub-contracting allowed without prior consent",
                f"The vendor can sub-contract or add sub-processors without the prior written consent policy "
                f"{rule.code} requires.",
                "Require prior written consent for sub-contractors and keep the vendor fully liable for them.",
                confidence=0.85,
            )
    return None


CLAUSE_CHECKS: dict[str, Callable[[RuleView, str], Hit | None]] = {
    "breach_notification": check_breach_notification,
    "data_residency": check_data_residency,
    "encryption": check_encryption,
    "liability_cap": check_liability_cap,
    "subcontracting": check_subcontracting,
}

# Domains whose policy says "the contract must contain this" (checked across the whole contract).
PRESENCE_DOMAINS = ("audit_rights", "termination_exit")


def check_clause(rules: list[RuleView], clause_text: str) -> list[Hit]:
    domains = detect_domains(clause_text)
    hits = []
    for rule in rules:
        fn = CLAUSE_CHECKS.get(rule.domain)
        if fn and rule.domain in domains:
            h = fn(rule, clause_text)
            if h:
                hits.append(h)
    return hits


def check_presence(rules: list[RuleView], clause_texts: list[str]) -> list[Hit]:
    hits = []
    for rule in rules:
        if rule.domain not in PRESENCE_DOMAINS or not rule.constraints.get("required"):
            continue
        pattern = DOMAIN_PATTERNS[rule.domain]
        if any(pattern.search(t) for t in clause_texts):
            continue
        impact, likelihood = CRITICALITY_BASE.get(rule.criticality, CRITICALITY_BASE["HIGH"])
        hits.append(
            Hit(
                domain=rule.domain,
                title=f"Missing clause: {rule.title}",
                evidence_quote="",
                reasoning=f"No clause in the contract covers this. Policy {rule.code}: {rule.mandate}",
                impact=impact,
                likelihood=likelihood,
                exposure=1.2,
                confidence=0.75,
                source="rules",
                rule_code=rule.code,
                recommended_action="Add a clause covering this requirement.",
                proposed_redline=rule.redline_template,
                clause_index=None,
            )
        )
    return hits
