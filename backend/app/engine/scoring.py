"""Composite Risk Score (CRS) and severity. Always computed in code, never by the LLM."""

from dataclasses import dataclass, field

CRITICALITY_BASE = {
    "CRITICAL": (5.0, 4.5),
    "HIGH": (4.5, 3.8),
    "MEDIUM": (3.5, 3.0),
    "LOW": (2.5, 2.5),
}


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def calculate_crs(impact: float, likelihood: float, exposure: float) -> float:
    """CRS = min(10, ((impact * 0.6 + likelihood * 0.4) * exposure) / 7.5 * 10).

    impact and likelihood are 1-5, exposure is 1.0-1.5, so the raw maximum is 7.5 -> 10.0.
    """
    impact = clamp(impact, 1, 5)
    likelihood = clamp(likelihood, 1, 5)
    exposure = clamp(exposure, 1.0, 1.5)
    raw = (impact * 0.6 + likelihood * 0.4) * exposure
    return round(clamp(raw / 7.5 * 10.0, 1.0, 10.0), 1)


def severity_for(crs: float) -> str:
    if crs >= 8.0:
        return "CRITICAL"
    if crs >= 6.0:
        return "HIGH"
    if crs >= 4.0:
        return "MEDIUM"
    return "LOW"


@dataclass
class Hit:
    """One detected risk, before it is saved as a Finding."""

    domain: str
    title: str
    evidence_quote: str
    reasoning: str
    impact: float
    likelihood: float
    exposure: float
    confidence: float
    source: str  # "rules" | "llm"
    rule_code: str | None = None
    recommended_action: str = ""
    proposed_redline: str = ""
    clause_index: int | None = None  # None = contract-level (e.g. a missing clause)
    regulation_refs: list[dict] = field(default_factory=list)

    @property
    def crs(self) -> float:
        return calculate_crs(self.impact, self.likelihood, self.exposure)

    @property
    def severity(self) -> str:
        return severity_for(self.crs)
