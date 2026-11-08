import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ErrorNote, Sev, formatDate } from "../components/bits";
import { api } from "../lib/api";
import { canReview, isAdmin, useSession } from "../lib/session";
import type { ContractDetail as Detail, Finding } from "../lib/types";
import { useLoad } from "../lib/useLoad";

export function ContractDetail() {
  const { id } = useParams();
  const { org } = useSession();
  const nav = useNavigate();
  const { data, error, reload } = useLoad(
    async () => {
      const [c, f] = await Promise.all([
        api.get<Detail>(`/api/v1/contracts/${id}`),
        api.get<Finding[]>(`/api/v1/findings?contract_id=${id}`),
      ]);
      return { c, f };
    },
    [id, org?.id],
  );
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  if (error) return <ErrorNote error={error} />;
  if (!data) return null;
  const { c, f } = data;
  const byClause = new Map<string, Finding[]>();
  for (const x of f) {
    if (x.status === "rejected" || !x.clause) continue;
    byClause.set(x.clause.id, [...(byClause.get(x.clause.id) ?? []), x]);
  }
  const missing = f.filter((x) => !x.clause && x.status !== "rejected");
  const run = c.runs[0];

  return (
    <>
      <div className="page-head">
        <div>
          <p className="small" style={{ marginTop: 0 }}>
            <Link to="/contracts">Contracts</Link>
          </p>
          <h1>{c.title}</h1>
          <p>
            {c.counterparty ? `${c.counterparty}, ` : ""}uploaded {formatDate(c.created_at)}
            {run &&
              `. Checked with ${run.mode === "hybrid" ? `policy rules and AI (${run.provider})` : "policy rules"}: ${
                run.stats.findings ?? 0
              } findings across ${run.stats.clauses ?? 0} clauses.`}
          </p>
        </div>
        <div className="row">
          <Link className="btn btn-primary" to={`/review?contract=${c.id}&status=`}>
            Review findings
          </Link>
          {canReview(org) && (
            <button
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                setActionError(null);
                try {
                  await api.post(`/api/v1/contracts/${c.id}/analyze`);
                  reload();
                } catch (e) {
                  setActionError(e instanceof Error ? e.message : String(e));
                } finally {
                  setBusy(false);
                }
              }}
            >
              {busy ? "Checking…" : "Check again"}
            </button>
          )}
          {isAdmin(org) && (
            <button
              className="btn-danger"
              onClick={async () => {
                if (!confirm(`Delete "${c.title}" and all its findings? The audit log keeps a record of the deletion.`))
                  return;
                await api.del(`/api/v1/contracts/${c.id}`);
                nav("/contracts");
              }}
            >
              Delete
            </button>
          )}
        </div>
      </div>
      <ErrorNote error={actionError} />
      {run?.error && <div className="notice">Last check had a problem: {run.error}</div>}

      {missing.length > 0 && (
        <div className="panel" style={{ marginBottom: "1.25rem" }}>
          <div className="panel-head">
            <h3>Missing from this contract</h3>
          </div>
          <div className="panel-body stack" style={{ gap: "0.5rem" }}>
            {missing.map((m) => (
              <div key={m.id} className="row">
                <Sev s={m.severity} /> <span>{m.title.replace(/^Missing clause: /, "")}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="panel">
        <div className="panel-head">
          <h3>Clauses</h3>
          <span className="small muted">Flagged clauses are tinted red</span>
        </div>
        <div className="clauses">
          {c.clauses.map((cl) => {
            const flags = byClause.get(cl.id) ?? [];
            return (
              <div key={cl.id} className={`clause${flags.length ? " flagged" : ""}`}>
                <div className="no">{cl.section_number || (cl.idx ?? 0) + 1}</div>
                <div>
                  <div className="text">{cl.text}</div>
                  {flags.length > 0 && (
                    <div className="flags">
                      {flags.map((x) => (
                        <Link key={x.id} to={`/review?contract=${c.id}&status=`} className="small">
                          <Sev s={x.severity} /> {x.title}
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}
