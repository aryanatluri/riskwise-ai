"""Regulation packs and default policy baselines.

IMPORTANT: these packs are a starting point written by the product team, not legal
advice. Every pack carries `reviewed: False` until a qualified lawyer signs it off,
and the UI must show that status to clients.

Regulation references are attached to findings by code (from the domain), never
by the LLM, so the product cannot invent a citation.
"""

from dataclasses import dataclass, field

DOMAINS = [
    "breach_notification",
    "data_residency",
    "encryption",
    "liability_cap",
    "audit_rights",
    "subcontracting",
    "termination_exit",
    "other",
]


@dataclass(frozen=True)
class Mandate:
    code: str
    regulation: str
    reference: str
    jurisdiction: str
    summary: str
    domains: tuple[str, ...]
    penalty: str = ""


@dataclass(frozen=True)
class Pack:
    key: str
    title: str
    jurisdiction: str
    reviewed: bool
    mandates: tuple[Mandate, ...] = field(default_factory=tuple)


INDIA_BFSI = Pack(
    key="india_bfsi",
    title="India BFSI baseline",
    jurisdiction="IN",
    reviewed=False,
    mandates=(
        Mandate(
            code="IN-CERTIN-6H",
            regulation="CERT-In Directions under Section 70B(6) of the IT Act (April 2022)",
            reference="Direction (ii)",
            jurisdiction="IN",
            summary="Specified cyber incidents must be reported to CERT-In within 6 hours of noticing them. "
            "A vendor notice window longer than this makes the regulated entity's deadline unreachable.",
            domains=("breach_notification",),
        ),
        Mandate(
            code="IN-DPDPA-8-6",
            regulation="Digital Personal Data Protection Act, 2023",
            reference="Section 8(6)",
            jurisdiction="IN",
            summary="A Data Fiduciary must intimate the Data Protection Board and each affected Data "
            "Principal of a personal data breach.",
            domains=("breach_notification",),
            penalty="Up to Rs 200 crore for failing to notify a breach (Schedule)",
        ),
        Mandate(
            code="IN-DPDPA-8-5",
            regulation="Digital Personal Data Protection Act, 2023",
            reference="Section 8(5)",
            jurisdiction="IN",
            summary="A Data Fiduciary must take reasonable security safeguards, including over its Data "
            "Processors, to prevent personal data breaches.",
            domains=("encryption", "liability_cap"),
            penalty="Up to Rs 250 crore for failing to take reasonable security safeguards (Schedule)",
        ),
        Mandate(
            code="IN-DPDPA-16",
            regulation="Digital Personal Data Protection Act, 2023",
            reference="Section 16",
            jurisdiction="IN",
            summary="The Central Government may restrict transfers of personal data to notified countries; "
            "sectoral rules that require stricter localisation continue to apply.",
            domains=("data_residency",),
        ),
        Mandate(
            code="IN-RBI-PAYDATA",
            regulation="RBI directive on Storage of Payment System Data (April 2018)",
            reference="Directive",
            jurisdiction="IN",
            summary="Payment system data must be stored only in India. Relevant where the vendor handles "
            "payment data.",
            domains=("data_residency",),
        ),
        Mandate(
            code="IN-RBI-ITOS",
            regulation="RBI Master Direction on Outsourcing of Information Technology Services (2023)",
            reference="Contractual requirements",
            jurisdiction="IN",
            summary="IT outsourcing agreements of regulated entities must cover audit and inspection access "
            "(including for RBI), controls on sub-contracting, incident reporting, data location and "
            "confidentiality, and termination with an exit strategy.",
            domains=("audit_rights", "subcontracting", "termination_exit", "data_residency", "breach_notification"),
        ),
    ),
)

EU_FINANCE = Pack(
    key="eu_finance",
    title="EU financial services baseline",
    jurisdiction="EU",
    reviewed=False,
    mandates=(
        Mandate(
            code="EU-GDPR-33",
            regulation="General Data Protection Regulation (EU) 2016/679",
            reference="Article 33",
            jurisdiction="EU",
            summary="Controllers notify the supervisory authority within 72 hours of becoming aware of a "
            "personal data breach; processors must notify the controller without undue delay.",
            domains=("breach_notification",),
            penalty="Up to EUR 10M or 2% of worldwide annual turnover (Art. 83(4))",
        ),
        Mandate(
            code="EU-GDPR-28",
            regulation="General Data Protection Regulation (EU) 2016/679",
            reference="Article 28",
            jurisdiction="EU",
            summary="Processor contracts must require prior authorisation for sub-processors and allow "
            "audits and inspections by the controller.",
            domains=("subcontracting", "audit_rights"),
        ),
        Mandate(
            code="EU-GDPR-32",
            regulation="General Data Protection Regulation (EU) 2016/679",
            reference="Article 32",
            jurisdiction="EU",
            summary="Appropriate technical measures, including encryption, must secure personal data.",
            domains=("encryption",),
        ),
        Mandate(
            code="EU-GDPR-CH5",
            regulation="General Data Protection Regulation (EU) 2016/679",
            reference="Chapter V (Articles 44-49)",
            jurisdiction="EU",
            summary="Transfers of personal data outside the EEA need an adequacy decision or appropriate "
            "safeguards.",
            domains=("data_residency",),
        ),
        Mandate(
            code="EU-DORA-30",
            regulation="Digital Operational Resilience Act (EU) 2022/2554",
            reference="Article 30",
            jurisdiction="EU",
            summary="ICT service contracts of financial entities must specify data processing locations, "
            "incident assistance, sub-contracting conditions, termination rights and, for critical "
            "functions, audit access and exit strategies.",
            domains=("data_residency", "breach_notification", "subcontracting", "termination_exit", "audit_rights"),
        ),
    ),
)

PACKS: dict[str, Pack] = {p.key: p for p in (INDIA_BFSI, EU_FINANCE)}
DEFAULT_PACKS = {"IN": ["india_bfsi"], "EU": ["eu_finance"]}


def mandates_for(pack_keys: list[str], domain: str) -> list[Mandate]:
    out: list[Mandate] = []
    for key in pack_keys:
        pack = PACKS.get(key)
        if pack:
            out.extend(m for m in pack.mandates if domain in m.domains)
    return out


def default_policy_rules(jurisdiction: str) -> list[dict]:
    """A BFSI baseline every new org starts from. Clients edit these to match their own policies."""
    regions = ["India"] if jurisdiction == "IN" else ["EU", "EEA"]
    region_words = "India" if jurisdiction == "IN" else "the EU/EEA"
    return [
        {
            "code": "SEC-01",
            "title": "Vendor breach notification within 24 hours",
            "domain": "breach_notification",
            "mandate": "Vendors must notify us in writing within 24 hours of any suspected or confirmed "
            "security incident affecting our data.",
            "criticality": "CRITICAL",
            "constraints": {"max_hours": 24},
            "redline_template": "Vendor shall notify Customer in writing without undue delay and in any event "
            "within {max_hours} hours of becoming aware of any actual or suspected security incident "
            "affecting Customer data, and shall provide all information Customer reasonably requires to "
            "meet its own regulatory reporting obligations.",
            "owner_role": "InfoSec",
            "sla_days": 2,
        },
        {
            "code": "DATA-01",
            "title": f"Data stays in {region_words} unless we approve in writing",
            "domain": "data_residency",
            "mandate": f"Customer data, backups and telemetry must be stored and processed only in "
            f"{region_words}. Any other location needs our prior written approval.",
            "criticality": "CRITICAL",
            "constraints": {"allowed_regions": regions, "require_prior_consent": True},
            "redline_template": f"Vendor shall store and process all Customer data, including backups, logs "
            f"and telemetry, solely within {region_words}. Vendor shall not transfer, replicate or mirror "
            f"Customer data outside {region_words} without Customer's prior written approval.",
            "owner_role": "Legal",
            "sla_days": 3,
        },
        {
            "code": "SEC-02",
            "title": "AES-256 at rest with customer-managed keys",
            "domain": "encryption",
            "mandate": "Our data at rest must use AES-256 or stronger with customer-managed keys, and "
            "TLS 1.2 or higher in transit.",
            "criticality": "HIGH",
            "constraints": {"min_aes_bits": 256, "require_cmk": True, "min_tls": 1.2},
            "redline_template": "Vendor shall encrypt all Customer data at rest using AES-256 or stronger, "
            "with keys managed by Customer through a key management service of Customer's choice, at no "
            "additional charge, and shall use TLS 1.2 or higher for all data in transit.",
            "owner_role": "InfoSec",
            "sla_days": 5,
        },
        {
            "code": "LEG-01",
            "title": "Data breach liability carve-out or super-cap",
            "domain": "liability_cap",
            "mandate": "Liability for data protection breaches, confidentiality and regulatory fines must be "
            "uncapped or subject to a super-cap of at least 12 months' fees and USD 2,000,000.",
            "criticality": "HIGH",
            "constraints": {"min_cap_usd": 2_000_000, "min_months_fees": 12},
            "redline_template": "The limitations in this Section shall not apply to Vendor's breach of its "
            "data protection, security or confidentiality obligations, or to regulatory fines arising from "
            "them, for which Vendor's liability shall be capped at the greater of USD 2,000,000 and the fees "
            "paid in the twenty-four (24) months preceding the claim.",
            "owner_role": "Legal",
            "sla_days": 5,
        },
        {
            "code": "LEG-02",
            "title": "Audit and inspection rights",
            "domain": "audit_rights",
            "mandate": "Contracts must give us, our auditors and our regulators the right to audit and "
            "inspect the vendor's relevant records, systems and premises.",
            "criticality": "HIGH",
            "constraints": {"required": True},
            "redline_template": "Vendor shall permit Customer, its auditors and any regulator with "
            "jurisdiction over Customer to audit and inspect Vendor's books, records, systems and premises "
            "relevant to the Services, on reasonable notice, and shall cooperate fully with such audits.",
            "owner_role": "Compliance",
            "sla_days": 5,
        },
        {
            "code": "LEG-03",
            "title": "Sub-contracting only with prior written consent",
            "domain": "subcontracting",
            "mandate": "Vendors may not sub-contract services or use sub-processors without our prior "
            "written consent, and remain fully liable for their sub-contractors.",
            "criticality": "HIGH",
            "constraints": {"require_prior_consent": True},
            "redline_template": "Vendor shall not sub-contract any part of the Services or engage any "
            "sub-processor without Customer's prior written consent, and shall remain fully liable for the "
            "acts and omissions of its sub-contractors.",
            "owner_role": "Legal",
            "sla_days": 5,
        },
        {
            "code": "LEG-04",
            "title": "Exit assistance and data return",
            "domain": "termination_exit",
            "mandate": "Contracts must include exit assistance and the return and certified deletion of our "
            "data on termination.",
            "criticality": "MEDIUM",
            "constraints": {"required": True},
            "redline_template": "On expiry or termination, Vendor shall provide reasonable transition "
            "assistance, return all Customer data in a commonly used format, and certify its secure "
            "deletion within thirty (30) days.",
            "owner_role": "Legal",
            "sla_days": 7,
        },
    ]
