import { useRef, useState, type DragEvent, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ErrorNote, formatDate } from "../components/bits";
import { api } from "../lib/api";
import { canReview, useSession } from "../lib/session";
import type { Contract, Run } from "../lib/types";
import { useLoad } from "../lib/useLoad";

export function Contracts() {
  const { org } = useSession();
  const nav = useNavigate();
  const { data, error, loading, reload } = useLoad(() => api.get<Contract[]>("/api/v1/contracts"), [org?.id]);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Contracts</h1>
          <p>Upload a vendor contract to check it against your policies. PDF, Word or text, up to 15 MB.</p>
        </div>
      </div>
      {canReview(org) && <Upload onDone={(id) => nav(`/review?contract=${id}`)} afterUpload={reload} />}
      <ErrorNote error={error} />
      {!loading && data?.length === 0 ? (
        <div className="empty" style={{ marginTop: "1.5rem" }}>
          <h3>No contracts yet</h3>
          <p>Your first upload takes a few seconds. Findings appear in the review queue.</p>
        </div>
      ) : (
        <table className="ledger" style={{ marginTop: "1.5rem" }}>
          <thead>
            <tr>
              <th>Contract</th>
              <th>Counterparty</th>
              <th>Uploaded</th>
              <th>Status</th>
              <th className="num">Needs review</th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((c) => (
              <tr key={c.id} className="clickable" onClick={() => nav(`/contracts/${c.id}`)}>
                <td>
                  <a
                    href={`/contracts/${c.id}`}
                    onClick={(e) => {
                      e.preventDefault();
                      nav(`/contracts/${c.id}`);
                    }}
                  >
                    {c.title}
                  </a>
                  <div className="small muted">{c.file_name}</div>
                </td>
                <td>{c.counterparty || <span className="muted">Not set</span>}</td>
                <td>{formatDate(c.created_at)}</td>
                <td>{c.status === "failed" ? <span className="sev sev-CRITICAL">Analysis failed</span> : "Analysed"}</td>
                <td className="num">
                  {c.open_findings ? <strong className="sev-CRITICAL">{c.open_findings}</strong> : "0"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

function Upload({ onDone, afterUpload }: { onDone: (contractId: string) => void; afterUpload: () => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [counterparty, setCounterparty] = useState("");
  const [over, setOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setOver(false);
    const f = e.dataTransfer.files[0];
    if (f) pick(f);
  }
  function pick(f: File) {
    setFile(f);
    if (!title) setTitle(f.name.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " "));
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    const fd = new FormData();
    fd.append("file", file);
    fd.append("title", title);
    fd.append("counterparty", counterparty);
    try {
      const out = await api.post<{ contract: Contract; run: Run }>("/api/v1/contracts", fd);
      afterUpload();
      if (out.run.status === "failed") setError(`Analysis failed: ${out.run.error}`);
      else onDone(out.contract.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      className={`dropzone${over ? " over" : ""}`}
      onSubmit={submit}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={onDrop}
    >
      <div className="stack" style={{ gap: "0.75rem" }}>
        <div className="row">
          <button type="button" onClick={() => input.current?.click()}>
            Choose file
          </button>
          <span className="small muted">{file ? file.name : "or drop a contract here"}</span>
          <input
            ref={input}
            type="file"
            hidden
            accept=".pdf,.docx,.txt,.md"
            onChange={(e) => e.target.files?.[0] && pick(e.target.files[0])}
          />
        </div>
        <div className="grid-2">
          <div className="field">
            <label htmlFor="c-title">Contract name</label>
            <input id="c-title" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="c-cp">Counterparty</label>
            <input id="c-cp" value={counterparty} onChange={(e) => setCounterparty(e.target.value)} />
          </div>
        </div>
        <ErrorNote error={error} />
      </div>
      <button className="btn-primary" disabled={!file || busy}>
        {busy ? "Checking contract…" : "Check contract"}
      </button>
    </form>
  );
}
