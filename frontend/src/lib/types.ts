export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
export type FindingStatus = "open" | "approved" | "rejected" | "dispatched" | "resolved";
export type Role = "admin" | "reviewer" | "viewer";

export interface Org {
  id: string;
  name: string;
  jurisdiction: "IN" | "EU";
  sector: string;
  regulation_packs: string[];
  role: Role;
}

export interface Contract {
  id: string;
  title: string;
  counterparty: string;
  contract_type: string;
  file_name: string;
  status: string;
  created_at: string | null;
  open_findings: number;
}

export interface Clause {
  id: string;
  idx?: number;
  section_number: string;
  heading: string;
  text: string;
}

export interface Run {
  id: string;
  mode: string;
  provider: string | null;
  model: string | null;
  status: string;
  stats: Record<string, number | string>;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface ContractDetail extends Contract {
  clauses: Clause[];
  runs: Run[];
}

export interface RegulationRef {
  code: string;
  regulation: string;
  reference: string;
  summary: string;
  penalty: string;
}

export interface Finding {
  id: string;
  contract_id: string;
  contract_title: string | null;
  clause: Clause | null;
  domain: string;
  title: string;
  severity: Severity;
  crs: number;
  scores: { impact: number; likelihood: number; exposure: number; confidence: number };
  evidence_quote: string;
  reasoning: string;
  regulation_refs: RegulationRef[];
  recommended_action: string;
  proposed_redline: string;
  owner_role: string;
  sla_days: number;
  source: "rules" | "llm";
  status: FindingStatus;
  assignee_email: string | null;
  due_at: string | null;
  review_notes: string;
  jira_key: string | null;
  decided_at: string | null;
  created_at: string | null;
}

export interface Policy {
  id: string;
  code: string;
  title: string;
  domain: string;
  mandate: string;
  criticality: Severity;
  constraints: Record<string, unknown>;
  redline_template: string;
  owner_role: string;
  sla_days: number;
  active: boolean;
}

export interface OrgSettings {
  analysis_mode: "rules_only" | "hybrid";
  llm: {
    provider: string | null;
    model: string | null;
    endpoint: string | null;
    api_version: string | null;
    api_key_set: boolean;
    api_key_last4: string | null;
  };
  jira: { base_url: string | null; email: string | null; project_key: string | null; token_set: boolean };
  slack_webhook_set: boolean;
  jira_webhook_secret_set: boolean;
  escalation_email: string | null;
  sla_escalation_days: number;
}

export interface AuditEntry {
  id: number;
  at: string;
  actor: string;
  action: string;
  target_type: string;
  target_id: string;
  details: Record<string, unknown>;
}

export interface Member {
  user_id: string;
  email: string;
  name: string;
  role: Role;
}
