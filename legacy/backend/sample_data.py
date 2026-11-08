import uuid
from typing import Dict, Any, List

# Master Statutory Regulations Repository
MASTER_REGULATIONS = [
    {
        "reg_id": "reg-cert-in",
        "name": "CERT-In Cyber Directions (2022)",
        "jurisdiction": "India",
        "category": "Cybersecurity & Incident Reporting",
        "enforcement_body": "Indian Computer Emergency Response Team (CERT-In)",
        "statutory_penalty_summary": "Up to 1 year imprisonment and heavy operational sanctions for non-reporting within 6 hours.",
        "mandates": [
            {
                "section": "Direction 6(1)",
                "topic": "Mandatory 6-Hour Cyber Breach Reporting",
                "rule": "Any cyber incident or unauthorized data access must be reported to CERT-In within 6 hours of noticing.",
                "sla_hours_max": 6,
                "mandatory": True
            }
        ]
    },
    {
        "reg_id": "reg-dpdpa",
        "name": "DPDPA 2023 (Digital Personal Data Protection Act)",
        "jurisdiction": "India",
        "category": "Data Privacy & Governance",
        "enforcement_body": "Data Protection Board of India (DPBI)",
        "statutory_penalty_summary": "Statutory fines up to ₹250 Crore (~$30M USD) per incident for failure to prevent or report data breach.",
        "mandates": [
            {
                "section": "Section 8(6)",
                "topic": "Notice of Personal Data Breach",
                "rule": "Data Fiduciaries must notify each affected Data Principal and the Board of any personal data breach without undue delay.",
                "penalty_exposure": "Up to ₹250 Crore",
                "mandatory": True
            },
            {
                "section": "Section 16",
                "topic": "Cross-Border Transfer Restrictions",
                "rule": "Personal data may only be transferred to jurisdictions not explicitly restricted by the Central Government.",
                "mandatory": True
            }
        ]
    },
    {
        "reg_id": "reg-gdpr",
        "name": "EU GDPR (General Data Protection Regulation)",
        "jurisdiction": "European Union",
        "category": "Data Privacy",
        "enforcement_body": "European Data Protection Board (EDPB)",
        "statutory_penalty_summary": "Fines up to €20 Million or 4% of total worldwide annual turnover, whichever is higher.",
        "mandates": [
            {
                "section": "Article 33",
                "topic": "72-Hour Supervisory Authority Notification",
                "rule": "In the case of a personal data breach, the controller shall without undue delay and, where feasible, not later than 72 hours after having become aware of it, notify the competent supervisory authority.",
                "sla_hours_max": 72,
                "mandatory": True
            },
            {
                "section": "Article 28",
                "topic": "Processor Obligations & Sub-processor Consent",
                "rule": "The processor shall not engage another processor without prior specific or general written authorization of the controller.",
                "mandatory": True
            }
        ]
    },
    {
        "reg_id": "reg-dora",
        "name": "EU DORA (Digital Operational Resilience Act 2025)",
        "jurisdiction": "European Union / BFSI",
        "category": "Financial Services Resilience",
        "enforcement_body": "European Banking Authority (EBA)",
        "statutory_penalty_summary": "Periodic penalty payments up to 1% of the average daily worldwide turnover for critical ICT third-party service providers.",
        "mandates": [
            {
                "section": "Article 28(2)",
                "topic": "ICT Third-Party Risk Management",
                "rule": "Financial entities must mandate full audit rights and immediate security incident escalation in all ICT outsourcing agreements.",
                "mandatory": True
            }
        ]
    },
    {
        "reg_id": "reg-rbi",
        "name": "RBI Master Directions on Outsourcing of IT Services (2023)",
        "jurisdiction": "India / BFSI",
        "category": "Banking Supervision",
        "enforcement_body": "Reserve Bank of India (RBI)",
        "statutory_penalty_summary": "Suspension of vendor onboarding, severe financial penalties, and supervisory intervention.",
        "mandates": [
            {
                "section": "Direction 11.2",
                "topic": "Data Localization & Direct Audit Rights",
                "rule": "Regulated entities must ensure that all data and records are stored domestically and are accessible for direct RBI inspection without hindrance.",
                "mandatory": True
            }
        ]
    }
]

# Internal Corporate Policies
INTERNAL_POLICIES = [
    {
        "policy_code": "SEC-POL-04",
        "title": "Enterprise InfoSec & Incident Response Policy",
        "department": "Information Security (CISO Office)",
        "version": "v3.2",
        "effective_date": "2025-01-01",
        "rules": [
            {
                "clause_code": "SEC-POL-04.Sec14",
                "domain": "Vendor Breach Notification SLA",
                "mandate": "Third-party vendors must notify Apex Financial in writing within twenty-four (24) hours of any suspected or confirmed breach.",
                "criticality": "CRITICAL",
                "benchmark_constraints": {"sla_hours_max": 24}
            },
            {
                "clause_code": "SEC-POL-04.Sec22",
                "domain": "Data Residency & Sovereign Boundary",
                "mandate": "All customer production records and database snapshots must remain hosted within domestic sovereign cloud data centers.",
                "criticality": "CRITICAL",
                "benchmark_constraints": {"domestic_only": True}
            }
        ]
    },
    {
        "policy_code": "CLOUD-SEC-09",
        "title": "Third-Party Cloud Security Standards",
        "department": "Enterprise Architecture",
        "version": "v2.1",
        "effective_date": "2025-03-15",
        "rules": [
            {
                "clause_code": "CLOUD-SEC-09.Sec8",
                "domain": "Encryption In-Transit & At-Rest",
                "mandate": "All customer data at rest must use AES-256 encryption with customer-managed keys (CMK) and TLS 1.3 in transit.",
                "criticality": "HIGH",
                "benchmark_constraints": {"cipher": "AES-256", "tls": "1.3", "cmk_required": True}
            }
        ]
    },
    {
        "policy_code": "LEG-POL-02",
        "title": "Contractual Indemnity & Liability Guardrails",
        "department": "Legal & Commercial Affairs",
        "version": "v4.0",
        "effective_date": "2024-11-01",
        "rules": [
            {
                "clause_code": "LEG-POL-02.Sec5",
                "domain": "Limitation of Liability Caps",
                "mandate": "Vendor liability caps for data breach or confidentiality breaches must be uncapped or at least equal to 12 months fees ($2,000,000 USD minimum super-cap).",
                "criticality": "HIGH",
                "benchmark_constraints": {"min_liability_cap_months": 12, "min_supercap_usd": 2000000}
            }
        ]
    }
]

# Employee Directory (for automated ticketing & escalation routing)
EMPLOYEES = [
    {
        "email": "arun.sharma@apexfinancial.com",
        "name": "Arun Sharma",
        "role": "Lead InfoSec Operations",
        "department": "InfoSec",
        "manager_email": "priya.nair@apexfinancial.com",
        "manager_name": "Priya Nair (VP of Risk & Compliance)"
    },
    {
        "email": "kavita.deshmukh@apexfinancial.com",
        "name": "Kavita Deshmukh",
        "role": "Senior Legal Counsel",
        "department": "Legal",
        "manager_email": "rajesh.verma@apexfinancial.com",
        "manager_name": "Rajesh Verma (General Counsel)"
    },
    {
        "email": "compliance-officer@apexfinancial.com",
        "name": "Aditi Rao",
        "role": "Principal Compliance Officer",
        "department": "Compliance",
        "manager_email": "priya.nair@apexfinancial.com",
        "manager_name": "Priya Nair (VP of Risk & Compliance)"
    }
]

# Master Policy ↔ Contract Gap Matrix (Featured in Pitch & Architecture guides)
MASTER_GAP_MATRIX = [
    {
        "domain": "Incident Reporting SLA",
        "policy_code": "SEC-POL-04.Sec14",
        "policy_requirement": "Mandatory written notice within 24 hours of any suspected incident",
        "contract_terms": "Vendor notifies within 5 business days (120 hours) after internal confirmation",
        "status": "CRITICAL_GAP",
        "statutory_law": "CERT-In 6-Hour Reporting / DPDPA Section 8(6)",
        "exposure": "₹250 Cr statutory penalty & criminal liability for delayed breach notification",
        "recommended_action": "Execute redline enforcing 12-hour SLA notice and immediate technical telemetry"
    },
    {
        "domain": "Data Residency & Sovereign Boundary",
        "policy_code": "SEC-POL-04.Sec22",
        "policy_requirement": "Customer telemetry & databases must remain strictly within domestic sovereign boundary",
        "contract_terms": "Vendor reserves right to mirror telemetry globally across foreign clusters without notice",
        "status": "CRITICAL_GAP",
        "statutory_law": "DPDPA 2023 Section 16 & RBI Outsourcing Directions",
        "exposure": "Regulatory non-compliance, cross-border jurisdictional subpoena exposure",
        "recommended_action": "Execute Sovereign Cloud Addendum mandating domestic-only hosting"
    },
    {
        "domain": "Limitation of Liability Super-Cap",
        "policy_code": "LEG-POL-02.Sec5",
        "policy_requirement": "Data breach & regulatory fines must be uncapped or have $2M min super-cap",
        "contract_terms": "Cumulative liability capped at 1 month SaaS fee ($4,850 USD)",
        "status": "HIGH_GAP",
        "statutory_law": "DPDPA 2023 & GDPR Statutory Fines",
        "exposure": "Apex Financial bears 99.8% of catastrophic vendor breach liabilities",
        "recommended_action": "Insert $5,000,000 USD Super-Cap carveout for confidentiality and regulatory fines"
    },
    {
        "domain": "Encryption & Key Management",
        "policy_code": "CLOUD-SEC-09.Sec8",
        "policy_requirement": "AES-256 encryption at rest with Customer-Managed Keys (CMK) and TLS 1.3 in-transit",
        "contract_terms": "AES-128 or Vendor proprietary key schemes; CMK only available on premium tier",
        "status": "HIGH_GAP",
        "statutory_law": "ISO 27001 Annex A.10 & RBI Cyber Security Guidelines",
        "exposure": "Multi-tenant key compromise risk and regulatory audit failure",
        "recommended_action": "Redline Section 18.1 to mandate AES-256 and CMK at zero additional surcharge"
    },
    {
        "domain": "Audit Rights & Regulatory Access",
        "policy_code": "SEC-POL-04.Sec30",
        "policy_requirement": "Annual SOC 2 Type II reports and customer right to conduct independent audits",
        "contract_terms": "Vendor provides annual SOC 2 Type II report upon 30 days written notice",
        "status": "COMPLIANT",
        "statutory_law": "EU DORA Article 28 / RBI BFSI Audit Mandate",
        "exposure": "None identified - terms satisfy enterprise governance requirements",
        "recommended_action": "Maintain existing clause wording; schedule annual audit verification"
    }
]

# Initial Pre-Configured Paused Review Threads for Interactive Demo
INITIAL_REVIEW_THREADS = [
    {
        "thread_id": "thread-csa-14-2",
        "contract_id": "csa-apex-8821",
        "contract_title": "CloudStack Global Services - Master Cloud Services Agreement (2026)",
        "counterparty": "CloudStack Global Services Inc.",
        "section_title": "Section 14.2 - Breach Notification SLA Gap",
        "page_number": 6,
        "section_number": "14.2",
        "raw_clause_text": "In the event of a confirmed security incident or unauthorized access resulting in disclosure of Customer confidential records, Vendor shall notify Customer in writing within five (5) business days after internal technical confirmation that an unauthorized disclosure has occurred.",
        "normalized_summary": "Vendor commits to notify customer of a confirmed security breach only within 5 business days (120 hours).",
        "explainable_ai": {
            "claim": "Contractual breach reporting window exceeds statutory and corporate ceilings by 96+ hours.",
            "evidence_quote": "Vendor shall notify Customer in writing within five (5) business days after internal technical confirmation (Section 14.2, Page 6).",
            "policy_mandate": "SEC-POL-04.Sec14 requires vendor breach notification within twenty-four (24) hours.",
            "regulatory_exposure": "CERT-In Direction 6(1) requires reporting within 6 hours. DPDPA 2023 Section 8(6) penalizes non-reporting up to ₹250 Crore.",
            "conflict_reasoning": "A 5 business day delay (120 hours) prevents Apex Financial from fulfilling its statutory 6-hour CERT-In filing and 72-hour GDPR supervisory notifications.",
            "confidence_pct": 98.4
        },
        "retrieved_policies": [
            {
                "policy_code": "SEC-POL-04",
                "clause_code": "SEC-POL-04.Sec14",
                "title": "Enterprise InfoSec & Incident Response Policy",
                "mandate": "Third-party vendors must notify Apex Financial in writing within twenty-four (24) hours of any suspected or confirmed breach.",
                "criticality": "CRITICAL",
                "delta": "Contract allows 120 hours (5 business days) vs. Mandatory 24 hours. Gap of +96 hours puts Apex Financial in direct statutory default."
            }
        ],
        "retrieved_regulations": [
            {
                "regulation_name": "CERT-In Cyber Directions (2022)",
                "section": "Direction 6(1)",
                "topic": "Mandatory 6-Hour Reporting",
                "rule": "Mandates breach reporting to CERT-In within 6 hours of occurrence.",
                "delta": "A 5-day vendor notification guarantee guarantees Apex Financial will fail the statutory 6-hour CERT-In filing deadline."
            },
            {
                "regulation_name": "DPDPA 2023",
                "section": "Section 8(6)",
                "topic": "Data Breach Notification to DPBI",
                "rule": "Mandatory prompt notification to Data Protection Board of India. Non-compliance exposes firm to fines up to ₹250 Crore.",
                "delta": "Severe regulatory liability exposure up to ₹250 Crore."
            },
            {
                "regulation_name": "EU GDPR",
                "section": "Article 33",
                "topic": "72-Hour Supervisory Authority SLA",
                "rule": "Supervisory authority notification must occur within 72 hours.",
                "delta": "120 hours vendor SLA breaches GDPR 72-hour ceiling."
            }
        ],
        "quantitative_metrics": {
            "impact_score": 5.0,
            "likelihood_score": 4.5,
            "exposure_multiplier": 1.45,
            "composite_risk_score": 9.2,
            "confidence_score": 0.98,
            "formula_explanation": "min(10.0, (Impact: 5.0 * 0.6 + Likelihood: 4.5 * 0.4) * Multiplier: 1.45) = 9.2 / 10.0"
        },
        "severity": "CRITICAL",
        "status": "AWAITING_APPROVAL",
        "vendor_email": {
            "to": "legal@cloudstack-global.com",
            "subject": "Apex Financial Redline: Master Agreement CSA-2026-APEX-8821 (Section 14.2 SLA)",
            "body": "Dear CloudStack Legal Team,\n\nDuring our automated enterprise risk benchmarking of Agreement CSA-2026-APEX-8821, our compliance engine flagged Section 14.2. As a regulated financial institution, Apex Financial is statutorily bound by CERT-In Cyber Directions (6-hour mandate) and DPDPA 2023 Section 8(6).\n\nA 5-day breach notification window exposes our organization to catastrophic statutory non-compliance. We have approved the following required redline replacement:\n\n'In the event of any security incident, suspected vulnerability exploitation, or unauthorized disclosure involving Customer data, Vendor shall notify Customer in writing within twelve (12) hours of first detection. Vendor shall immediately provide forensic telemetry and a designated incident liaison.'\n\nPlease incorporate this revision into the execution copy.\n\nSincerely,\nArun Sharma\nLead InfoSec Operations, Apex Financial Enterprises Ltd."
        },
        "pending_actions": [
            {
                "action_id": "act-csa-breach-sla",
                "severity": "CRITICAL",
                "summary": "Execute Contractual Redline on Section 14.2: Mandate 12-Hour Breach Notification SLA (CloudStack Inc.)",
                "suggested_owner": "arun.sharma@apexfinancial.com",
                "suggested_owner_name": "Arun Sharma (Lead InfoSec)",
                "proposed_redline": "In the event of any security incident, suspected vulnerability exploitation, or unauthorized disclosure involving Customer data, Vendor shall notify Customer in writing within twelve (12) hours of first detection. Vendor shall immediately provide forensic telemetry and a designated incident liaison.",
                "sla_days": 2,
                "ticket_priority": "Highest"
            }
        ]
    },
    {
        "thread_id": "thread-csa-8-1",
        "contract_id": "csa-apex-8821",
        "contract_title": "CloudStack Global Services - Master Cloud Services Agreement (2026)",
        "counterparty": "CloudStack Global Services Inc.",
        "section_title": "Section 8.1 - Global Telemetry & Cross-Border Sovereign Data Routing",
        "page_number": 4,
        "section_number": "8.1",
        "raw_clause_text": "Vendor reserves the right to transfer, mirror, and store Customer telemetry and analytical audit logs across any of Vendor’s global cloud clusters (including data centers located in North America, Southeast Asia, and Eastern Europe) without prior written notice, to ensure continuous platform load balancing.",
        "normalized_summary": "Vendor reserves unilateral right to store and route telemetry records globally across unlisted jurisdictions without customer consent.",
        "explainable_ai": {
            "claim": "Unilateral cross-border mirroring violates domestic sovereign data localization mandates.",
            "evidence_quote": "Vendor reserves the right to transfer, mirror, and store Customer telemetry across global clusters without prior written notice (Section 8.1, Page 4).",
            "policy_mandate": "SEC-POL-04.Sec22 mandates all customer records and telemetry remain hosted in domestic sovereign data centers.",
            "regulatory_exposure": "DPDPA 2023 Section 16 & RBI Outsourcing Directions strictly restrict unauthorized foreign data transfers.",
            "conflict_reasoning": "Uncontrolled data mirroring across unapproved foreign cloud clusters compromises statutory sovereign protection.",
            "confidence_pct": 95.8
        },
        "retrieved_policies": [
            {
                "policy_code": "SEC-POL-04",
                "clause_code": "SEC-POL-04.Sec22",
                "title": "Enterprise InfoSec & Incident Response Policy",
                "mandate": "All customer production records and database snapshots must remain hosted within domestic sovereign cloud data centers.",
                "criticality": "CRITICAL",
                "delta": "Unrestricted foreign mirroring violates domestic data localization standards."
            }
        ],
        "retrieved_regulations": [
            {
                "regulation_name": "DPDPA 2023",
                "section": "Section 16",
                "topic": "Cross-Border Personal Data Restrictions",
                "rule": "Cross-border transfers are subject to central government gazette notifications and strict fiduciary security controls.",
                "delta": "Exposes firm to cross-border transfer violations and potential revocation of financial operating license."
            },
            {
                "regulation_name": "RBI Outsourcing Directions (2023)",
                "section": "Direction 11.2",
                "topic": "Domestic Storage Mandate",
                "rule": "All banking customer telemetry must remain within India's jurisdiction.",
                "delta": "Mirroring to North America or Eastern Europe triggers direct RBI regulatory intervention."
            }
        ],
        "quantitative_metrics": {
            "impact_score": 4.8,
            "likelihood_score": 4.0,
            "exposure_multiplier": 1.35,
            "composite_risk_score": 8.8,
            "confidence_score": 0.95,
            "formula_explanation": "min(10.0, (Impact: 4.8 * 0.6 + Likelihood: 4.0 * 0.4) * Multiplier: 1.35) = 8.8 / 10.0"
        },
        "severity": "CRITICAL",
        "status": "AWAITING_APPROVAL",
        "vendor_email": {
            "to": "legal@cloudstack-global.com",
            "subject": "Apex Financial Redline: Master Agreement CSA-2026-APEX-8821 (Section 8.1 Data Residency)",
            "body": "Dear CloudStack Legal Team,\n\nRegarding Section 8.1 of Agreement CSA-2026-APEX-8821, Apex Financial is subject to mandatory domestic data residency under RBI Master Directions and DPDPA 2023 Section 16.\n\nWe cannot agree to global unannounced telemetry replication across non-sovereign jurisdictions. Please apply our required addendum:\n\n'Vendor expressly covenants that all Customer data, metadata, audit telemetry, and analytical derivatives shall remain strictly hosted and processed within Customer\\'s primary domestic jurisdiction (India / EU). No cross-border transfer shall occur without prior explicit written authorization from Customer.'\n\nThank you,\nKavita Deshmukh\nSenior Legal Counsel, Apex Financial Enterprises Ltd."
        },
        "pending_actions": [
            {
                "action_id": "act-csa-data-residency",
                "severity": "CRITICAL",
                "summary": "Enforce Sovereign Cloud Data Residency Addendum (CloudStack Section 8.1)",
                "suggested_owner": "kavita.deshmukh@apexfinancial.com",
                "suggested_owner_name": "Kavita Deshmukh (Senior Legal Counsel)",
                "proposed_redline": "Vendor expressly covenants that all Customer data, metadata, audit telemetry, and analytical derivatives shall remain strictly hosted and processed within Customer's primary domestic jurisdiction (India / EU). No cross-border transfer shall occur without prior explicit written authorization from Customer.",
                "sla_days": 3,
                "ticket_priority": "Highest"
            }
        ]
    },
    {
        "thread_id": "thread-csa-21-1",
        "contract_id": "csa-apex-8821",
        "contract_title": "CloudStack Global Services - Master Cloud Services Agreement (2026)",
        "counterparty": "CloudStack Global Services Inc.",
        "section_title": "Section 21.1 - Disproportionate $4,850 Liability Cap for Breach Penalties",
        "page_number": 9,
        "section_number": "21.1",
        "raw_clause_text": "Vendor’s total cumulative liability arising out of or related to this Agreement, including data breach damages, regulatory penalties, or confidentiality indemnities, shall be strictly capped at the total amount actually paid by Customer to Vendor in the one (1) month preceding the incident ($4,850 USD).",
        "normalized_summary": "Vendor caps total liability for data breach damages and regulatory fines to 1 month's SaaS fees ($4,850 USD).",
        "explainable_ai": {
            "claim": "Artificial $4,850 liability cap leaves enterprise 99.8% unshielded against statutory breach damages.",
            "evidence_quote": "Vendor total cumulative liability including data breach damages capped at 1 month fees ($4,850 USD) (Section 21.1, Page 9).",
            "policy_mandate": "LEG-POL-02.Sec5 prohibits capping data breach indemnity below $2,000,000 USD or 12 months fees.",
            "regulatory_exposure": "DPDPA 2023 imposes direct fines up to ₹250 Crore on the data fiduciary, unrecoverable from vendor under current clause.",
            "conflict_reasoning": "A $4,850 recovery ceiling creates an untenable commercial imbalance where vendor retains minimal accountability for catastrophic operational failures.",
            "confidence_pct": 94.2
        },
        "retrieved_policies": [
            {
                "policy_code": "LEG-POL-02",
                "clause_code": "LEG-POL-02.Sec5",
                "title": "Contractual Indemnity & Liability Guardrails",
                "mandate": "Vendor liability caps for data breach or confidentiality breaches must be uncapped or at least equal to 12 months fees ($2,000,000 USD minimum super-cap).",
                "criticality": "HIGH",
                "delta": "A $4,850 cap leaves Apex Financial bearing 99.8% of any multi-million dollar regulatory or customer loss."
            }
        ],
        "retrieved_regulations": [
            {
                "regulation_name": "DPDPA 2023 / GDPR",
                "section": "Statutory Fines",
                "topic": "Liability Disparity",
                "rule": "Statutory fines are levied directly against the Data Fiduciary (Apex Financial).",
                "delta": "If CloudStack causes a breach, Apex is exposed to up to ₹250 Crore while CloudStack's legal exposure is capped at $4,850."
            }
        ],
        "quantitative_metrics": {
            "impact_score": 5.0,
            "likelihood_score": 3.8,
            "exposure_multiplier": 1.30,
            "composite_risk_score": 8.4,
            "confidence_score": 0.94,
            "formula_explanation": "min(10.0, (Impact: 5.0 * 0.6 + Likelihood: 3.8 * 0.4) * Multiplier: 1.30) = 8.4 / 10.0"
        },
        "severity": "HIGH",
        "status": "AWAITING_APPROVAL",
        "vendor_email": {
            "to": "legal@cloudstack-global.com",
            "subject": "Apex Financial Redline: Master Agreement CSA-2026-APEX-8821 (Section 21.1 Liability Super-Cap)",
            "body": "Dear CloudStack Legal Team,\n\nWe have completed our commercial risk audit of Agreement CSA-2026-APEX-8821. Section 21.1 caps total cumulative liability for regulatory fines and data breach damages at $4,850 USD.\n\nUnder corporate policy LEG-POL-02, Apex Financial cannot accept liabilities of this magnitude being limited to one month of SaaS subscription fees. We propose our standard enterprise super-cap carveout:\n\n'Notwithstanding anything to the contrary, the limitations of liability in Section 21.1 shall NOT apply to breaches of confidentiality, data protection obligations, or indemnification for regulatory fines. For data protection breaches, Vendor\\'s liability shall be subject to a dedicated Super-Cap of $5,000,000 USD or total fees paid in the preceding 24 months, whichever is greater.'\n\nPlease let us know once this has been accepted.\n\nBest regards,\nKavita Deshmukh\nSenior Legal Counsel, Apex Financial Enterprises Ltd."
        },
        "pending_actions": [
            {
                "action_id": "act-csa-liability-supercap",
                "severity": "HIGH",
                "summary": "Negotiate Super-Cap Indemnification for Data Breaches and Regulatory Fines (Section 21.1)",
                "suggested_owner": "kavita.deshmukh@apexfinancial.com",
                "suggested_owner_name": "Kavita Deshmukh (Senior Legal Counsel)",
                "proposed_redline": "Notwithstanding anything to the contrary, the limitations of liability in Section 21.1 shall NOT apply to breaches of confidentiality, data protection obligations, or indemnification for regulatory fines. For data protection breaches, Vendor's liability shall be subject to a dedicated Super-Cap of $5,000,000 USD or total fees paid in the preceding 24 months, whichever is greater.",
                "sla_days": 4,
                "ticket_priority": "High"
            }
        ]
    },
    {
        "thread_id": "thread-csa-18-1",
        "contract_id": "csa-apex-8821",
        "contract_title": "CloudStack Global Services - Master Cloud Services Agreement (2026)",
        "counterparty": "CloudStack Global Services Inc.",
        "section_title": "Section 18.1 - Encryption at Rest & Customer-Managed Key Governance",
        "page_number": 8,
        "section_number": "18.1",
        "raw_clause_text": "Customer records stored in multi-tenant buckets shall be protected by standard platform-level encryption (AES-128 or Vendor proprietary key schemes). Custom key management is available solely under premium enterprise add-on tiers.",
        "normalized_summary": "Vendor defaults to weak AES-128 / proprietary keys with customer-managed keys gated behind paid tiers.",
        "explainable_ai": {
            "claim": "Platform-level AES-128 and lack of Customer-Managed Keys (CMK) breaches baseline banking security standards.",
            "evidence_quote": "Customer records stored in multi-tenant buckets shall be protected by standard platform-level encryption (AES-128 or Vendor proprietary key schemes) (Section 18.1, Page 8).",
            "policy_mandate": "CLOUD-SEC-09.Sec8 mandates AES-256 with Customer-Managed Keys (CMK) and TLS 1.3 in transit.",
            "regulatory_exposure": "ISO/IEC 27001 Annex A.10 & RBI Cyber Security Guidelines require standardized cryptographic controls for sensitive records.",
            "conflict_reasoning": "Proprietary or 128-bit key schemes without CMK access leave Apex Financial vulnerable to multi-tenant cryptographic compromise without forensic auditability.",
            "confidence_pct": 96.5
        },
        "retrieved_policies": [
            {
                "policy_code": "CLOUD-SEC-09",
                "clause_code": "CLOUD-SEC-09.Sec8",
                "title": "Third-Party Cloud Security Standards",
                "mandate": "All customer data at rest must use AES-256 encryption with customer-managed keys (CMK) and TLS 1.3 in transit.",
                "criticality": "HIGH",
                "delta": "AES-128 and proprietary key schemes fall below enterprise security baseline; CMK must not be gated."
            }
        ],
        "retrieved_regulations": [
            {
                "regulation_name": "ISO/IEC 27001 (Control A.10)",
                "section": "A.10.1 Cryptographic Controls",
                "topic": "Enterprise Encryption Standards",
                "rule": "Organizations must enforce industry-standard robust key management and encryption algorithms.",
                "delta": "AES-128 is flagged as non-conforming for BFSI financial data."
            },
            {
                "regulation_name": "RBI Cyber Security Framework",
                "section": "Annex 1, Item 4",
                "topic": "Key Management Integrity",
                "rule": "Regulated entities must maintain sovereign control over cryptographic keys used for customer data encryption.",
                "delta": "Vendor-controlled proprietary keys breach RBI custodial governance."
            }
        ],
        "quantitative_metrics": {
            "impact_score": 4.5,
            "likelihood_score": 3.5,
            "exposure_multiplier": 1.30,
            "composite_risk_score": 7.8,
            "confidence_score": 0.96,
            "formula_explanation": "min(10.0, (Impact: 4.5 * 0.6 + Likelihood: 3.5 * 0.4) * Multiplier: 1.30) = 7.8 / 10.0"
        },
        "severity": "HIGH",
        "status": "AWAITING_APPROVAL",
        "vendor_email": {
            "to": "security@cloudstack-global.com",
            "subject": "Apex Financial Redline: Master Agreement CSA-2026-APEX-8821 (Section 18.1 Encryption Standards)",
            "body": "Dear CloudStack Security & Commercial Team,\n\nIn reviewing Section 18.1 of Agreement CSA-2026-APEX-8821, our InfoSec architecture team identified that platform default encryption utilizes AES-128 with proprietary key schemes, and that Customer-Managed Keys (CMK) are restricted to premium add-ons.\n\nUnder Apex Financial Policy CLOUD-SEC-09.Sec8 and RBI Cyber Security Guidelines, AES-256 encryption with CMK integration is a mandatory pre-condition for processing our workloads.\n\nWe require the following replacement wording at standard contract tiers:\n\n'Vendor covenants that all Customer records stored at rest shall be encrypted using AES-256 standard and integrated with Customer-Managed Keys (CMK via AWS KMS / Azure Key Vault / Google Cloud KMS) without additional licensing fees. All data in transit shall enforce TLS 1.3 encryption.'\n\nKind regards,\nArun Sharma\nLead InfoSec Operations, Apex Financial Enterprises Ltd."
        },
        "pending_actions": [
            {
                "action_id": "act-csa-encryption-cmk",
                "severity": "HIGH",
                "summary": "Mandate AES-256 Encryption & Zero-Cost Customer Key Management (Section 18.1)",
                "suggested_owner": "arun.sharma@apexfinancial.com",
                "suggested_owner_name": "Arun Sharma (Lead InfoSec)",
                "proposed_redline": "Vendor covenants that all Customer records stored at rest shall be encrypted using AES-256 standard and integrated with Customer-Managed Keys (CMK via AWS KMS / Azure Key Vault / Google Cloud KMS) without additional licensing fees. All data in transit shall enforce TLS 1.3 encryption.",
                "sla_days": 3,
                "ticket_priority": "High"
            }
        ]
    }
]
