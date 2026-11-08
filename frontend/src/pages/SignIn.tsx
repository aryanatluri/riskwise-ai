import { useState, type FormEvent } from "react";
import { ErrorNote } from "../components/bits";
import { authMode, signIn } from "../lib/auth";
import { useSession } from "../lib/session";

export function SignIn() {
  const { refresh } = useSession();
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await signIn(email.trim());
      if (result === "sent") setSent(true);
      else await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          RISKWISE
        </div>
        {sent ? (
          <div className="stack">
            <h1>Check your email</h1>
            <p className="muted">We sent a sign-in link to {email}. Open it on this device.</p>
          </div>
        ) : (
          <form className="stack" onSubmit={submit}>
            <h1>Sign in</h1>
            <p className="muted">Review vendor contracts against your own policies.</p>
            <div className="field">
              <label htmlFor="email">Work email</label>
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <ErrorNote error={error} />
            <button className="btn-primary" disabled={busy}>
              {authMode === "supabase" ? "Email me a sign-in link" : "Sign in"}
            </button>
            {authMode === "dev" && <p className="small muted">Development sign-in: no password needed.</p>}
          </form>
        )}
      </div>
    </div>
  );
}
