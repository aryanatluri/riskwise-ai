import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { DOMAIN_LABEL, ErrorNote, Sev, Status, formatDate } from "../components/bits";
import { Redline } from "../components/Redline";
import { api } from "../lib/api";
import { canReview, useSession } from "../lib/session";
import type { Finding, FindingStatus, Severity } from "../lib/types";
import { useLoad } from "../lib/useLoad";

export function Review() {
  const { org } = useSession();
  const [params, setParams] = useSearchParams();
  const status = (params.get("status") ?? "open") as FindingStatus | "";
  const severity = (params.get("severity") ?? "") as Severity | "";
  const contractId = params.get("contract") ?? "";
  const qs = new URLSearchParams();
  if (status) qs.set("status", status);
  if (severity) qs.set("severity", severity);
  if (contractId) qs.set("contract_id", contractId);

  const { data, error, loading, reload } = useLoad(
    () => api.get<Finding[]>(`/api/v1/findings?${qs.toString()}`),
    [qs.toString(), org?.id],
  );
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const findings = useMemo(() => data ?? [], [data]);
  const selected = findings.find((f) => f.id === selectedId) ?? findings[0] ?? null;

  useEffect(() => {
    if (selectedId && !findings.some((f) => f.id === selectedId)) setSelectedId(null);
  }, [findings, selectedId]);

  function setFilter(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Review queue</h1>
          <p>Risks found in your contracts, highest risk first. Approve to assign a fix, or accept the risk.</p>
        </div>
        <a
          className="btn"
          href="#export"
          onClick={async (e) => {
            e.preventDefault();
            const blob = await api.blob(`/api/v1/findings/export.csv${contractId ? `?contract_id=${contractId}` : ""}`);
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "riskwise-findings.csv";
            a.click();
            URL.revokeObjectURL(url);
          }}
        >
          Export CSV
        </a>
      </div>

      <div className="filters" role="group" aria-label="Filters">
        <select aria-label="Status" value={status} onChange={(e) => setFilter("status", e.target.value)}>
          <option value="open">Needs review</option>
          <option value="approved">Approved</option>
          <option value="dispatched">Sent to Jira</option>
          <option value="resolved">Resolved</option>
          <option value="rejected">Accepted risk</option>
          <option value="">All statuses</option>
        </select>
        <select aria-label="Severity" value={severity} onChange={(e) => setFilter("severity", e.target.value)}>
          <option value="">All severities</option>
          <option value="CRITICAL">Critical</option>
          <option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option>
          <option value="LOW">Low</option>
        </select>
        {contractId && (
          <button className="btn-quiet" onClick={() => setFilter("contract", "")}>
            Showing one contract. Show all
          </button>
        )}
      </div>

      <ErrorNote error={error} />
      {!loading && findings.length === 0 && !error ? (
        <div className="empty">
          <h3>{status === "open" ? "Nothing waiting for review" : "No findings match these filters"}</h3>
          <p>
            {status === "open" ? (
              <>
                Upload a contract on the <Link to="/contracts">Contracts</Link> page to check it against your policies.
              </>
            ) : (
              "Try a different status or severity."
            )}
          </p>
        </div>
      ) : (
        <div className="review">
          <ul className="queue" aria-label="Findings">
            {findings.map((f) => (
              <li key={f.id} className={selected?.id === f.id ? "selected" : ""}>
                <button onClick={() => setSelectedId(f.id)} aria-current={selected?.id === f.id}>
                  <span className={`bar ${f.severity}`} aria-hidden="true" />
                  <span>
                    <span className="q-title">{f.title}</span>
                    <span className="q-meta" style={{ display: "block" }}>
                      {f.contract_title}
                      {f.clause?.section_number ? `, clause ${f.clause.section_number}` : ", whole contract"}
                    </span>
                  </span>
                  <span className={`q-crs sev-${f.severity}`} title="Composite risk score out of 10">
                    {f.crs.toFixed(1)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          {selected && <FindingDetail key={selected.id} f={selected} canAct={canReview(org)} onChanged={reload} />}
        </div>
      )}
    </>
  );
}

function FindingDetail({ f, canAct, onChanged }: { f: Finding; canAct: boolean; onChanged: () => void }) {
  const [redline, setRedline] = useState(f.proposed_redline);
  const [assignee, setAssignee] = useState(f.assignee_email ?? "");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function act(fn: () => Promise<unknown>, done: string) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      setMessage(done);
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="panel" aria-labelledby="finding-title">
      <div className="panel-body stack" style={{ gap: "1.5rem" }}>
        <div className="detail-head">
          <div className="stack" style={{ gap: "0.5rem" }}>
            <div className="row">
              <Sev s={f.severity} />
              <Status s={f.status} />
              <span className="small muted">{DOMAIN_LABEL[f.domain] ?? f.domain}</span>
            </div>
            <h2 id="finding-title">{f.title}</h2>
            <p className="small muted">
              {f.contract_title}, found by {f.source === "llm" ? "AI review" : "policy rules"}
            </p>
          </div>
          <div className="crs-figure">
            <strong className={`sev-${f.severity}`}>{f.crs.toFixed(1)}</strong>
            <span>risk score / 10</span>
          </div>
        </div>

        <Redline clause={f.clause} quote={f.evidence_quote} proposal={redline} />

        <section className="stack" style={{ gap: "0.5rem" }}>
          <h3>Why it matters</h3>
          <p style={{ maxWidth: "70ch" }}>{f.reasoning}</p>
          {f.recommended_action && (
            <p style={{ maxWidth: "70ch" }}>
              <strong>Recommended:</strong> {f.recommended_action}
            </p>
          )}
        </section>

        {f.regulation_refs.length > 0 && (
          <section className="stack" style={{ gap: "0.75rem" }}>
            <h3>Regulations involved</h3>
            <ul className="refs">
              {f.regulation_refs.map((r) => (
                <li key={r.code}>
                  <div className="ref-name">
                    {r.regulation}, {r.reference}
                  </div>
                  <div className="small">{r.summary}</div>
                  {r.penalty && <div className="ref-penalty">{r.penalty}</div>}
                </li>
              ))}
            </ul>
          </section>
        )}

        <dl className="facts">
          <dt>Impact</dt>
          <dd>{f.scores.impact} of 5</dd>
          <dt>Likelihood</dt>
          <dd>{f.scores.likelihood} of 5</dd>
          <dt>Data exposure</dt>
          <dd>×{f.scores.exposure}</dd>
          <dt>Owner</dt>
          <dd>{f.assignee_email || f.owner_role}</dd>
          {f.due_at && (
            <>
              <dt>Due</dt>
              <dd>{formatDate(f.due_at)}</dd>
            </>
          )}
          {f.jira_key && (
            <>
              <dt>Jira</dt>
              <dd>{f.jira_key}</dd>
            </>
          )}
          {f.review_notes && (
            <>
              <dt>Review notes</dt>
              <dd>{f.review_notes}</dd>
            </>
          )}
        </dl>

        {canAct && f.status === "open" && (
          <section className="decision stack">
            <h3>Decision</h3>
            <div className="field">
              <label htmlFor="redline">Proposed wording</label>
              <textarea id="redline" value={redline} onChange={(e) => setRedline(e.target.value)} rows={4} />
              <span className="hint">Edits show in the marked-up clause above.</span>
            </div>
            <div className="grid-2">
              <div className="field">
                <label htmlFor="assignee">Assign to</label>
                <input
                  id="assignee"
                  type="email"
                  placeholder={`${f.owner_role} lead's email`}
                  value={assignee}
                  onChange={(e) => setAssignee(e.target.value)}
                />
                <span className="hint">Due in {f.sla_days} days from approval.</span>
              </div>
              <div className="field">
                <label htmlFor="notes">Notes for the record</label>
                <input id="notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
              </div>
            </div>
            <ErrorNote error={error} />
            <div className="row">
              <button
                className="btn-primary"
                disabled={busy}
                onClick={() =>
                  act(
                    () =>
                      api.post(`/api/v1/findings/${f.id}/decision`, {
                        decision: "approve",
                        assignee_email: assignee || null,
                        proposed_redline: redline,
                        notes,
                      }),
                    "Approved",
                  )
                }
              >
                Approve and assign
              </button>
              <button
                disabled={busy}
                onClick={() =>
                  act(
                    () => api.post(`/api/v1/findings/${f.id}/decision`, { decision: "reject", notes }),
                    "Marked as accepted risk",
                  )
                }
              >
                Accept the risk
              </button>
            </div>
          </section>
        )}

        {canAct && f.status === "approved" && (
          <section className="decision stack">
            <ErrorNote error={error} />
            <div className="row">
              <button
                className="btn-primary"
                disabled={busy}
                onClick={() => act(() => api.post(`/api/v1/findings/${f.id}/dispatch`), "Sent")}
              >
                Send to Jira and Slack
              </button>
              <span className="small muted">Uses the integrations set up in Settings.</span>
            </div>
          </section>
        )}
        {message && <p className="ok">{message}</p>}
      </div>
    </article>
  );
}
