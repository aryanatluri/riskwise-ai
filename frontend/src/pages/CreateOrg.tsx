import { useState, type FormEvent } from "react";
import { ErrorNote } from "../components/bits";
import { api } from "../lib/api";
import { useSession } from "../lib/session";
import type { Org } from "../lib/types";

export function CreateOrg() {
  const { refresh, selectOrg } = useSession();
  const [name, setName] = useState("");
  const [jurisdiction, setJurisdiction] = useState<"IN" | "EU">("IN");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const org = await api.post<Org>("/api/v1/orgs", { name, jurisdiction, sector: "BFSI" });
      try {
        localStorage.setItem("riskwise.org", org.id);
      } catch {
        /* ignore */
      }
      await refresh();
      selectOrg(org.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <form className="auth-card stack" onSubmit={submit}>
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          RISKWISE
        </div>
        <h1>Set up your organization</h1>
        <p className="muted">
          You start with a baseline of BFSI vendor policies and the regulations for your region. You can edit all of
          them afterwards.
        </p>
        <div className="field">
          <label htmlFor="org-name">Organization name</label>
          <input id="org-name" required minLength={2} value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="jur">Where you are regulated</label>
          <select id="jur" value={jurisdiction} onChange={(e) => setJurisdiction(e.target.value as "IN" | "EU")}>
            <option value="IN">India (RBI, CERT-In, DPDPA)</option>
            <option value="EU">European Union (GDPR, DORA)</option>
          </select>
        </div>
        <ErrorNote error={error} />
        <button className="btn-primary" disabled={busy}>
          Create organization
        </button>
      </form>
    </div>
  );
}
