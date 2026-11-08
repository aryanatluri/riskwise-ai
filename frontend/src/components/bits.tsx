import type { FindingStatus, Severity } from "../lib/types";

const SEV_LABEL: Record<Severity, string> = { CRITICAL: "Critical", HIGH: "High", MEDIUM: "Medium", LOW: "Low" };

export function Sev({ s }: { s: Severity }) {
  return <span className={`sev sev-${s}`}>{SEV_LABEL[s]}</span>;
}

const STATUS_LABEL: Record<FindingStatus, string> = {
  open: "Needs review",
  approved: "Approved",
  rejected: "Accepted risk",
  dispatched: "Sent to Jira",
  resolved: "Resolved",
};

export function Status({ s }: { s: FindingStatus }) {
  return <span className={`status status-${s}`}>{STATUS_LABEL[s]}</span>;
}

export const DOMAIN_LABEL: Record<string, string> = {
  breach_notification: "Breach notification",
  data_residency: "Data location",
  encryption: "Encryption",
  liability_cap: "Liability",
  audit_rights: "Audit rights",
  subcontracting: "Sub-contracting",
  termination_exit: "Exit and data return",
  other: "Other",
};

export function ErrorNote({ error }: { error: string | null }) {
  if (!error) return null;
  return (
    <div className="error" role="alert">
      {error}
    </div>
  );
}

export function formatDate(iso: string | null) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}
