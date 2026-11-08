import { ErrorNote } from "../components/bits";
import { api } from "../lib/api";
import { useSession } from "../lib/session";
import type { AuditEntry } from "../lib/types";
import { useLoad } from "../lib/useLoad";

const ACTION_LABEL: Record<string, string> = {
  "org.created": "Created the organization",
  "contract.uploaded": "Uploaded a contract",
  "contract.deleted": "Deleted a contract",
  "analysis.completed": "Contract checked",
  "analysis.failed": "Contract check failed",
  "finding.approved": "Approved a finding",
  "finding.rejected": "Accepted a risk",
  "finding.dispatched": "Sent a finding to Jira/Slack",
  "finding.resolved": "Finding resolved in Jira",
  "finding.escalated": "Overdue finding escalated",
  "findings.exported": "Exported findings",
  "settings.updated": "Changed settings",
  "settings.webhook_secret_rotated": "Replaced the Jira webhook secret",
  "policy.created": "Added a policy rule",
  "policy.updated": "Changed a policy rule",
  "member.upserted": "Added or changed a person",
  "member.removed": "Removed a person",
};

function summary(e: AuditEntry): string {
  const d = e.details as Record<string, unknown>;
  if (e.action === "analysis.completed") return `${d.findings} findings, ${d.mode === "hybrid" ? "rules and AI" : "rules only"}`;
  if (e.action === "contract.uploaded" || e.action === "contract.deleted") return String(d.file_name ?? d.title ?? "");
  if (e.action === "settings.updated") return ((d.changed as string[]) ?? []).join(", ");
  if (e.action === "policy.updated" || e.action === "policy.created") return String(d.code ?? "");
  if (e.action === "member.upserted") return `${d.email} as ${d.role}`;
  if (e.action === "finding.approved" && d.assignee) return `assigned to ${d.assignee}`;
  if (e.action === "finding.escalated") return `${d.days_overdue} days overdue`;
  if (e.action === "finding.resolved") return String(d.jira_key ?? "");
  return "";
}

export function Audit() {
  const { org } = useSession();
  const { data, error } = useLoad(() => api.get<AuditEntry[]>("/api/v1/audit?limit=500"), [org?.id]);
  return (
    <>
      <div className="page-head">
        <div>
          <h1>Audit log</h1>
          <p>Everything people and the system did in this organization. Entries can't be edited or deleted.</p>
        </div>
      </div>
      <ErrorNote error={error} />
      <table className="ledger">
        <thead>
          <tr>
            <th style={{ width: "11rem" }}>When</th>
            <th>Who</th>
            <th>What</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          {(data ?? []).map((e) => (
            <tr key={e.id}>
              <td className="small" style={{ whiteSpace: "nowrap" }}>
                {new Date(e.at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}
              </td>
              <td className="small">{e.actor}</td>
              <td>{ACTION_LABEL[e.action] ?? e.action}</td>
              <td className="small muted">{summary(e)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
