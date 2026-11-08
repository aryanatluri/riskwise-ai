import { useState } from "react";
import { DOMAIN_LABEL, ErrorNote, Sev } from "../components/bits";
import { api } from "../lib/api";
import { isAdmin, useSession } from "../lib/session";
import type { Policy, Severity } from "../lib/types";
import { useLoad } from "../lib/useLoad";

export function Policies() {
  const { org } = useSession();
  const { data, error, reload } = useLoad(() => api.get<Policy[]>("/api/v1/policies"), [org?.id]);
  const [editing, setEditing] = useState<string | null>(null);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Policies</h1>
          <p>
            Your vendor contract rules. Every contract is checked against these, so tune the limits to match your own
            policy documents.
          </p>
        </div>
      </div>
      <ErrorNote error={error} />
      <table className="ledger">
        <thead>
          <tr>
            <th style={{ width: "6rem" }}>Code</th>
            <th>Rule</th>
            <th>Area</th>
            <th>Severity</th>
            <th>Owner</th>
            <th>Status</th>
            {isAdmin(org) && <th />}
          </tr>
        </thead>
        <tbody>
          {(data ?? []).map((p) =>
            editing === p.id ? (
              <tr key={p.id}>
                <td colSpan={7}>
                  <PolicyEditor
                    p={p}
                    onClose={() => setEditing(null)}
                    onSaved={() => {
                      setEditing(null);
                      reload();
                    }}
                  />
                </td>
              </tr>
            ) : (
              <tr key={p.id} style={p.active ? undefined : { opacity: 0.55 }}>
                <td>
                  <code>{p.code}</code>
                </td>
                <td>
                  <strong>{p.title}</strong>
                  <div className="small muted" style={{ maxWidth: "60ch" }}>
                    {p.mandate}
                  </div>
                </td>
                <td className="small">{DOMAIN_LABEL[p.domain] ?? p.domain}</td>
                <td>
                  <Sev s={p.criticality} />
                </td>
                <td className="small">{p.owner_role}</td>
                <td className="small">{p.active ? "On" : "Off"}</td>
                {isAdmin(org) && (
                  <td>
                    <button className="btn-quiet" onClick={() => setEditing(p.id)}>
                      Edit
                    </button>
                  </td>
                )}
              </tr>
            ),
          )}
        </tbody>
      </table>
    </>
  );
}

function PolicyEditor({ p, onClose, onSaved }: { p: Policy; onClose: () => void; onSaved: () => void }) {
  const [title, setTitle] = useState(p.title);
  const [mandate, setMandate] = useState(p.mandate);
  const [criticality, setCriticality] = useState<Severity>(p.criticality);
  const [constraints, setConstraints] = useState(JSON.stringify(p.constraints, null, 2));
  const [redline, setRedline] = useState(p.redline_template);
  const [owner, setOwner] = useState(p.owner_role);
  const [sla, setSla] = useState(p.sla_days);
  const [active, setActive] = useState(p.active);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(constraints);
    } catch {
      setError("Limits must be valid JSON, for example {\"max_hours\": 24}");
      return;
    }
    try {
      await api.patch(`/api/v1/policies/${p.id}`, {
        title,
        mandate,
        criticality,
        constraints: parsed,
        redline_template: redline,
        owner_role: owner,
        sla_days: sla,
        active,
      });
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <div className="stack" style={{ padding: "0.5rem 0" }}>
      <div className="grid-2">
        <div className="field">
          <label htmlFor="p-title">Rule</label>
          <input id="p-title" value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div className="row" style={{ alignItems: "flex-end" }}>
          <div className="field" style={{ flex: 1 }}>
            <label htmlFor="p-sev">Severity</label>
            <select id="p-sev" value={criticality} onChange={(e) => setCriticality(e.target.value as Severity)}>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label htmlFor="p-owner">Owner team</label>
            <input id="p-owner" value={owner} onChange={(e) => setOwner(e.target.value)} />
          </div>
          <div className="field" style={{ width: "7rem" }}>
            <label htmlFor="p-sla">Days to fix</label>
            <input id="p-sla" type="number" min={1} max={90} value={sla} onChange={(e) => setSla(+e.target.value)} />
          </div>
        </div>
      </div>
      <div className="field">
        <label htmlFor="p-mandate">What the policy requires</label>
        <textarea id="p-mandate" rows={2} value={mandate} onChange={(e) => setMandate(e.target.value)} />
      </div>
      <div className="grid-2">
        <div className="field">
          <label htmlFor="p-limits">Limits the checker uses</label>
          <textarea
            id="p-limits"
            className="json-edit"
            value={constraints}
            onChange={(e) => setConstraints(e.target.value)}
          />
          <span className="hint">For example max_hours, allowed_regions, min_cap_usd.</span>
        </div>
        <div className="field">
          <label htmlFor="p-redline">Standard replacement wording</label>
          <textarea id="p-redline" value={redline} onChange={(e) => setRedline(e.target.value)} />
        </div>
      </div>
      <label className="row small">
        <input type="checkbox" style={{ width: "auto" }} checked={active} onChange={(e) => setActive(e.target.checked)} />
        Check contracts against this rule
      </label>
      <ErrorNote error={error} />
      <div className="row">
        <button className="btn-primary" onClick={save}>
          Save rule
        </button>
        <button className="btn-quiet" onClick={onClose}>
          Cancel
        </button>
      </div>
    </div>
  );
}
