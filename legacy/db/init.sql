-- ============================================================================
-- RISKWISE AI: Enterprise Hybrid Relational & Vector Database Schema (PostgreSQL + pgvector)
-- ============================================================================

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 2. Organizations & Multi-Tenant Workspaces
CREATE TABLE IF NOT EXISTS organizations (
    org_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_name VARCHAR(255) NOT NULL,
    primary_jurisdiction VARCHAR(64) NOT NULL DEFAULT 'IND', -- e.g., IND, USA, EU
    industry_sector VARCHAR(64) NOT NULL,                    -- e.g., BFSI, SaaS, HealthTech
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Master External Statutory Regulations
CREATE TABLE IF NOT EXISTS regulations (
    reg_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,                              -- e.g., 'DPDPA 2023', 'GDPR', 'CERT-In 2022'
    jurisdiction VARCHAR(64) NOT NULL,                       -- e.g., 'India', 'European Union'
    category VARCHAR(64) NOT NULL,                           -- e.g., 'Data Privacy', 'Cybersecurity'
    enforcement_body VARCHAR(255),                           -- e.g., 'DPBI', 'EDPB', 'CERT-In'
    statutory_penalty_summary TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS regulatory_mandates (
    mandate_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reg_id UUID REFERENCES regulations(reg_id) ON DELETE CASCADE,
    section_reference VARCHAR(128) NOT NULL,                 -- e.g., 'Section 6(1)', 'Article 33'
    topic VARCHAR(128) NOT NULL,                             -- e.g., 'Breach Notification SLA'
    rule_description TEXT NOT NULL,
    mandatory_metric VARCHAR(255),                           -- e.g., 'max_hours: 6', 'dpa_required: true'
    embedding vector(1536),                                  -- 1536-dim semantic coordinates
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Internal Corporate Policies & Rules
CREATE TABLE IF NOT EXISTS internal_policies (
    policy_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    policy_code VARCHAR(64) NOT NULL,                        -- e.g., 'SEC-POL-04'
    title VARCHAR(255) NOT NULL,                             -- e.g., 'InfoSec & Data Protection Policy'
    department VARCHAR(64) NOT NULL,                         -- e.g., 'InfoSec', 'Legal'
    version VARCHAR(32) NOT NULL,
    effective_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS policy_rules (
    rule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    policy_id UUID REFERENCES internal_policies(policy_id) ON DELETE CASCADE,
    clause_code VARCHAR(64) NOT NULL,                        -- e.g., 'SEC-POL-04.Sec6'
    domain VARCHAR(64) NOT NULL,                             -- e.g., 'Incident Notification'
    mandate_stance TEXT NOT NULL,                            -- e.g., 'Breaches must be notified within 24 hrs.'
    fallback_stance TEXT,                                    -- Minimum acceptable stance
    criticality VARCHAR(32) NOT NULL,                        -- 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    benchmark_constraints JSONB,                             -- e.g., {"sla_hours_max": 24}
    embedding vector(1536)
);

-- 5. Uploaded Contracts & Parsed Clauses
CREATE TABLE IF NOT EXISTS contracts_source (
    contract_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    vendor_counterparty VARCHAR(255) NOT NULL,
    contract_type VARCHAR(64) NOT NULL,                      -- e.g., 'Master Services Agreement'
    governing_law VARCHAR(64),
    effective_date DATE,
    sha256_hash VARCHAR(64) UNIQUE NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS contract_clause_chunks (
    chunk_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id UUID REFERENCES contracts_source(contract_id) ON DELETE CASCADE,
    page_number INT NOT NULL,
    section_number VARCHAR(64),
    section_title VARCHAR(255),
    raw_clause_text TEXT NOT NULL,
    normalized_clause_summary TEXT,
    embedding vector(1536)
);

-- 6. Cross-Referenced Risk Findings
CREATE TABLE IF NOT EXISTS risk_findings_log (
    finding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id UUID REFERENCES contracts_source(contract_id) ON DELETE CASCADE,
    chunk_id UUID REFERENCES contract_clause_chunks(chunk_id),
    matched_rule_id UUID REFERENCES policy_rules(rule_id),
    matched_mandate_id UUID REFERENCES regulatory_mandates(mandate_id),
    severity VARCHAR(32) NOT NULL,                           -- 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    compliance_status VARCHAR(32) NOT NULL,                  -- 'NON_COMPLIANT_GAP', 'PARTIAL_GAP', 'COMPLIANT', 'RESOLVED'
    evidence_quote TEXT NOT NULL,
    policy_delta_summary TEXT NOT NULL,
    impact_analysis JSONB NOT NULL,
    recommended_redline TEXT NOT NULL,                       -- Replacement contract clause
    confidence_score NUMERIC(4, 2) NOT NULL,
    composite_risk_score NUMERIC(4, 2) NOT NULL,             -- Calculated CRS (1.0 - 10.0)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Autonomous Action & Escalation Tracker
CREATE TABLE IF NOT EXISTS agent_actions_tracker (
    action_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    finding_id UUID REFERENCES risk_findings_log(finding_id) ON DELETE CASCADE,
    suggested_owner VARCHAR(255) NOT NULL,
    deadline TIMESTAMP WITH TIME ZONE NOT NULL,
    action_status VARCHAR(32) DEFAULT 'PENDING_APPROVAL',    -- 'PENDING_APPROVAL', 'DISPATCHED', 'RESOLVED', 'OVERDUE'
    jira_issue_key VARCHAR(64),
    notification_payload JSONB,                              -- Pre-drafted alert payload
    last_escalated_at TIMESTAMP WITH TIME ZONE,
    escalation_count INT DEFAULT 0,
    manager_escalated_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- 8. Corporate Hierarchy Directory for Manager Escalations
CREATE TABLE IF NOT EXISTS organization_employees (
    employee_email VARCHAR(255) PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    department VARCHAR(64) NOT NULL,
    manager_email VARCHAR(255) NOT NULL,
    manager_name VARCHAR(255) NOT NULL
);

-- 9. Sub-Second Semantic Retrieval Indexes
CREATE INDEX IF NOT EXISTS idx_policy_rules_vector ON policy_rules USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_regulatory_mandates_vector ON regulatory_mandates USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_contract_clause_vector ON contract_clause_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================================================
-- SEED DATA: Pre-Configured Regulations, Internal Policies & Employee Hierarchy
-- ============================================================================

INSERT INTO organizations (org_id, org_name, primary_jurisdiction, industry_sector)
VALUES ('a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d', 'Apex Financial Enterprises', 'IND', 'BFSI')
ON CONFLICT (org_id) DO NOTHING;

-- External Regulations
INSERT INTO regulations (reg_id, name, jurisdiction, category, enforcement_body, statutory_penalty_summary)
VALUES 
('11111111-1111-1111-1111-111111111111', 'CERT-In Cyber Directions 2022', 'India', 'Cybersecurity', 'Indian Computer Emergency Response Team', 'Up to 1 year imprisonment and heavy operational sanctions for non-reporting within 6 hours.'),
('22222222-2222-2222-2222-222222222222', 'DPDPA 2023 (Digital Personal Data Protection Act)', 'India', 'Data Privacy', 'Data Protection Board of India (DPBI)', 'Fines up to ₹250 Crore per incident for failure to prevent or report data breach.'),
('33333333-3333-3333-3333-333333333333', 'EU GDPR (General Data Protection Regulation)', 'European Union', 'Data Privacy', 'European Data Protection Board (EDPB)', 'Fines up to €20 Million or 4% of total worldwide annual turnover.')
ON CONFLICT (reg_id) DO NOTHING;

-- Mandates
INSERT INTO regulatory_mandates (mandate_id, reg_id, section_reference, topic, rule_description, mandatory_metric)
VALUES
('aaaa1111-aaaa-1111-aaaa-111111111111', '11111111-1111-1111-1111-111111111111', 'Direction 6(1)', 'Cyber Incident Reporting SLA', 'All cyber incidents and security breaches must be mandatorily reported to CERT-In within 6 hours of noticing.', 'max_hours: 6'),
('bbbb2222-bbbb-2222-bbbb-222222222222', '22222222-2222-2222-2222-222222222222', 'Section 8(6)', 'Data Breach Notification', 'Data Fiduciaries must notify each affected Data Principal and the Board of any personal data breach without undue delay.', 'dpa_required: true'),
('cccc3333-cccc-3333-cccc-333333333333', '33333333-3333-3333-3333-333333333333', 'Article 33', 'Supervisory Breach Notification SLA', 'Personal data breaches must be notified to the supervisory authority within 72 hours of becoming aware.', 'max_hours: 72')
ON CONFLICT (mandate_id) DO NOTHING;

-- Internal Policies
INSERT INTO internal_policies (policy_id, org_id, policy_code, title, department, version, effective_date, is_active)
VALUES
('p1111111-p111-1111-p111-111111111111', 'a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d', 'SEC-POL-04', 'Enterprise InfoSec & Incident Response Policy', 'InfoSec', 'v3.2', '2025-01-01', TRUE),
('p2222222-p222-2222-p222-222222222222', 'a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d', 'CLOUD-SEC-09', 'Third-Party Vendor Cloud Architecture Standards', 'Security & Architecture', 'v2.1', '2025-03-15', TRUE)
ON CONFLICT (policy_id) DO NOTHING;

-- Internal Rules
INSERT INTO policy_rules (rule_id, policy_id, clause_code, domain, mandate_stance, fallback_stance, criticality, benchmark_constraints)
VALUES
('r1111111-r111-1111-r111-111111111111', 'p1111111-p111-1111-p111-111111111111', 'SEC-POL-04.Sec14', 'Incident Notification SLA', 'Third-party vendors must notify Apex Financial in writing within twenty-four (24) hours of any suspected or confirmed breach.', 'Maximum 48 hours with executive approval.', 'CRITICAL', '{"sla_hours_max": 24}'),
('r2222222-r222-2222-r222-222222222222', 'p1111111-p111-1111-p111-111111111111', 'SEC-POL-04.Sec22', 'Data Residency & Sovereignty', 'All production customer telemetry and database snapshots must remain hosted within the domestic territory (India / EU sovereign cloud).', 'Cross-border transfer only with explicit DPA and encryption.', 'CRITICAL', '{"data_residency_required": true}'),
('r3333333-r333-3333-r333-333333333333', 'p2222222-p222-2222-p222-222222222222', 'CLOUD-SEC-09.Sec8', 'Encryption In-Transit & At-Rest', 'All enterprise customer data at rest must use AES-256 encryption with customer-managed keys (CMK) and TLS 1.3 in transit.', 'TLS 1.2 minimum acceptable.', 'HIGH', '{"cipher": "AES-256"}')
ON CONFLICT (rule_id) DO NOTHING;

-- Employee Hierarchy
INSERT INTO organization_employees (employee_email, full_name, department, manager_email, manager_name)
VALUES
('arun.sharma@apexfinancial.com', 'Arun Sharma', 'InfoSec Operations', 'priya.nair@apexfinancial.com', 'Priya Nair (VP of Risk & Compliance)'),
('kavita.deshmukh@apexfinancial.com', 'Kavita Deshmukh', 'Legal Counsel', 'rajesh.verma@apexfinancial.com', 'Rajesh Verma (General Counsel)'),
('compliance-officer@apexfinancial.com', 'Aditi Rao', 'Compliance Review', 'priya.nair@apexfinancial.com', 'Priya Nair (VP of Risk & Compliance)')
ON CONFLICT (employee_email) DO NOTHING;
