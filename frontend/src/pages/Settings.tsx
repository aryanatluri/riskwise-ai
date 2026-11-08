import { useState, type FormEvent, type ReactNode } from "react";
import { ErrorNote } from "../components/bits";
import { api } from "../lib/api";
import { useSession } from "../lib/session";
import type { Member, OrgSettings } from "../lib/types";
import { useLoad } from "../lib/useLoad";

const PROVIDERS: Record<string, { label: string; model: string; needsEndpoint?: boolean; help: string }> = {
  gemini: { label: "Google Gemini (paid tier)", model: "Model", help: "Use a key from a Cloud project with billing on. Free-tier keys let Google train on your contracts." },
  azure_openai: { label: "Azure OpenAI", model: "Deployment name", needsEndpoint: true, help: "Pick a deployment in an Azure region that meets your data-residency rules." },
  openai: { label: "OpenAI", model: "Model", help: "Uses your organization's OpenAI API key." },
  anthropic: { label: "Anthropic", model: "Model", help: "Uses your organization's Anthropic API key." },
};

export function Settings() {
  const { org } = useSession();
  const { data, error, setData } = useLoad(() => api.get<OrgSettings>("/api/v1/org/settings"), [org?.id]);
  if (error) return <ErrorNote error={error} />;
  if (!data) return null;
  return (
    <>
      <div className="page-head">
        <div>
          <h1>Settings</h1>
          <p>Secrets you enter here are encrypted and never shown again.</p>
        </div>
      </div>
      <div className="stack" style={{ gap: "1.5rem", maxWidth: "52rem" }}>
        <AiSection s={data} onSaved={setData} />
        <IntegrationsSection s={data} onSaved={setData} />
        <MembersSection />
      </div>
    </>
  );
}

function Section({ title, intro, children }: { title: string; intro: string; children: ReactNode }) {
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>{title}</h2>
          <p className="small muted" style={{ marginTop: "0.25rem", maxWidth: "62ch" }}>
            {intro}
          </p>
        </div>
      </div>
      <div className="panel-body stack">{children}</div>
    </section>
  );
}

function useSave(onSaved: (s: OrgSettings) => void) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  async function save(body: unknown) {
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      onSaved(await api.put<OrgSettings>("/api/v1/org/settings", body));
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }
  return { busy, error, saved, save };
}

function AiSection({ s, onSaved }: { s: OrgSettings; onSaved: (s: OrgSettings) => void }) {
  const [provider, setProvider] = useState(s.llm.provider ?? "gemini");
  const [model, setModel] = useState(s.llm.model ?? "");
  const [endpoint, setEndpoint] = useState(s.llm.endpoint ?? "");
  const [apiVersion, setApiVersion] = useState(s.llm.api_version ?? "");
  const [key, setKey] = useState("");
  const [test, setTest] = useState<string | null>(null);
  const { busy, error, saved, save } = useSave(onSaved);
  const meta = PROVIDERS[provider];

  async function submit(e: FormEvent) {
    e.preventDefault();
    await save({
      llm: {
        provider,
        model: model || null,
        endpoint: endpoint || null,
        api_version: apiVersion || null,
        ...(key ? { api_key: key } : {}),
      },
    });
    setKey("");
  }

  return (
    <Section
      title="AI review"
      intro="Policy rules always run and cost nothing. Turn on AI review to also have your own AI provider read each risky clause. Your contracts go only to the provider and region you choose, on your key."
    >
      <div className="row">
        <label className="row">
          <input
            type="radio"
            name="mode"
            style={{ width: "auto" }}
            checked={s.analysis_mode === "rules_only"}
            onChange={() => save({ analysis_mode: "rules_only" })}
          />
          Policy rules only
        </label>
        <label className="row">
          <input
            type="radio"
            name="mode"
            style={{ width: "auto" }}
            checked={s.analysis_mode === "hybrid"}
            disabled={!s.llm.api_key_set}
            onChange={() => save({ analysis_mode: "hybrid" })}
          />
          Policy rules and AI review
        </label>
      </div>
      {!s.llm.api_key_set && <p className="small muted">Add your AI provider below to turn on AI review.</p>}

      <form className="stack" onSubmit={submit}>
        <div className="grid-2">
          <div className="field">
            <label htmlFor="prov">Provider</label>
            <select id="prov" value={provider} onChange={(e) => setProvider(e.target.value)}>
              {Object.entries(PROVIDERS).map(([k, v]) => (
                <option key={k} value={k}>
                  {v.label}
                </option>
              ))}
            </select>
            <span className="hint">{meta.help}</span>
          </div>
          <div className="field">
            <label htmlFor="model">{meta.model}</label>
            <input id="model" value={model} onChange={(e) => setModel(e.target.value)} required />
          </div>
        </div>
        {meta.needsEndpoint && (
          <div className="grid-2">
            <div className="field">
              <label htmlFor="endpoint">Endpoint</label>
              <input
                id="endpoint"
                placeholder="https://your-resource.openai.azure.com"
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="apiv">API version</label>
              <input id="apiv" placeholder="2024-10-21" value={apiVersion} onChange={(e) => setApiVersion(e.target.value)} />
            </div>
          </div>
        )}
        <div className="field">
          <label htmlFor="key">API key</label>
          <input
            id="key"
            type="password"
            autoComplete="off"
            placeholder={s.llm.api_key_set ? `Saved key ending ${s.llm.api_key_last4}. Enter a new one to replace it.` : ""}
            value={key}
            onChange={(e) => setKey(e.target.value)}
          />
        </div>
        <ErrorNote error={error} />
        <div className="row">
          <button className="btn-primary" disabled={busy}>
            Save AI provider
          </button>
          <button
            type="button"
            disabled={!s.llm.api_key_set}
            onClick={async () => {
              setTest("Testing…");
              const r = await api.post<{ ok: boolean; error?: string }>("/api/v1/org/settings/llm/test");
              setTest(r.ok ? "Connection works" : `Connection failed: ${r.error}`);
            }}
          >
            Test connection
          </button>
          {saved && <span className="ok">Saved</span>}
          {test && <span className={test.startsWith("Connection works") ? "ok" : "small muted"}>{test}</span>}
        </div>
      </form>
    </Section>
  );
}

function IntegrationsSection({ s, onSaved }: { s: OrgSettings; onSaved: (s: OrgSettings) => void }) {
  const [jiraUrl, setJiraUrl] = useState(s.jira.base_url ?? "");
  const [jiraEmail, setJiraEmail] = useState(s.jira.email ?? "");
  const [jiraProject, setJiraProject] = useState(s.jira.project_key ?? "");
  const [jiraToken, setJiraToken] = useState("");
  const [slack, setSlack] = useState("");
  const [escalation, setEscalation] = useState(s.escalation_email ?? "");
  const [days, setDays] = useState(s.sla_escalation_days);
  const [secret, setSecret] = useState<{ secret: string; webhook_url: string } | null>(null);
  const { busy, error, saved, save } = useSave(onSaved);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const body: Record<string, unknown> = { sla_escalation_days: days };
    if (escalation) body.escalation_email = escalation;
    if (jiraUrl || jiraEmail || jiraProject || jiraToken)
      body.jira = {
        base_url: jiraUrl || null,
        email: jiraEmail || null,
        project_key: jiraProject || null,
        ...(jiraToken ? { token: jiraToken } : {}),
      };
    if (slack) body.slack_webhook = slack;
    await save(body);
    setJiraToken("");
    setSlack("");
  }

  return (
    <Section
      title="Tickets, alerts and escalation"
      intro="Approved findings can open a Jira ticket and post to Slack. Closing the ticket in Jira marks the finding resolved. Overdue fixes are escalated by email."
    >
      <form className="stack" onSubmit={submit}>
        <h3>Jira</h3>
        <div className="grid-2">
          <div className="field">
            <label htmlFor="j-url">Jira site</label>
            <input id="j-url" placeholder="https://yourbank.atlassian.net" value={jiraUrl} onChange={(e) => setJiraUrl(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="j-proj">Project key</label>
            <input id="j-proj" placeholder="RISK" value={jiraProject} onChange={(e) => setJiraProject(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="j-email">Jira account email</label>
            <input id="j-email" type="email" value={jiraEmail} onChange={(e) => setJiraEmail(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="j-token">API token</label>
            <input
              id="j-token"
              type="password"
              autoComplete="off"
              placeholder={s.jira.token_set ? "Saved. Enter a new one to replace it." : ""}
              value={jiraToken}
              onChange={(e) => setJiraToken(e.target.value)}
            />
          </div>
        </div>
        <div className="row">
          <button
            type="button"
            onClick={async () => setSecret(await api.post("/api/v1/org/settings/jira-webhook-secret"))}
          >
            {s.jira_webhook_secret_set ? "Replace Jira webhook secret" : "Create Jira webhook secret"}
          </button>
          <span className="small muted">Lets Jira tell RISKWISE when a ticket is closed.</span>
        </div>
        {secret && (
          <div className="notice">
            Copy this now; it won't be shown again. In Jira, add a webhook to{" "}
            <code>{window.location.origin.replace(/:\d+$/, "")}{secret.webhook_url}</code> with secret{" "}
            <code>{secret.secret}</code>.
          </div>
        )}

        <h3>Slack</h3>
        <div className="field">
          <label htmlFor="slack">Incoming webhook URL</label>
          <input
            id="slack"
            type="url"
            placeholder={s.slack_webhook_set ? "Saved. Enter a new one to replace it." : "https://hooks.slack.com/services/…"}
            value={slack}
            onChange={(e) => setSlack(e.target.value)}
          />
        </div>

        <h3>Escalation</h3>
        <div className="grid-2">
          <div className="field">
            <label htmlFor="esc">Escalate overdue fixes to</label>
            <input id="esc" type="email" placeholder="head-of-risk@yourbank.com" value={escalation} onChange={(e) => setEscalation(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="days">Days overdue before escalating</label>
            <input id="days" type="number" min={1} max={60} value={days} onChange={(e) => setDays(+e.target.value)} />
          </div>
        </div>
        <ErrorNote error={error} />
        <div className="row">
          <button className="btn-primary" disabled={busy}>
            Save integrations
          </button>
          {saved && <span className="ok">Saved</span>}
        </div>
      </form>
    </Section>
  );
}

function MembersSection() {
  const { org } = useSession();
  const { data, reload } = useLoad(() => api.get<Member[]>("/api/v1/org/members"), [org?.id]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("reviewer");
  const [error, setError] = useState<string | null>(null);

  async function add(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/api/v1/org/members", { email, role });
      setEmail("");
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <Section
      title="People"
      intro="Reviewers can upload contracts and decide on findings. Viewers can read. Admins also manage settings, policies and people."
    >
      <table className="ledger">
        <thead>
          <tr>
            <th>Email</th>
            <th>Role</th>
          </tr>
        </thead>
        <tbody>
          {(data ?? []).map((m) => (
            <tr key={m.user_id}>
              <td>{m.email}</td>
              <td className="small">{m.role[0].toUpperCase() + m.role.slice(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <form className="row" onSubmit={add} style={{ alignItems: "flex-end" }}>
        <div className="field" style={{ flex: 1, minWidth: "14rem" }}>
          <label htmlFor="m-email">Add someone by email</label>
          <input id="m-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="field" style={{ width: "9rem" }}>
          <label htmlFor="m-role">Role</label>
          <select id="m-role" value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="reviewer">Reviewer</option>
            <option value="viewer">Viewer</option>
            <option value="admin">Admin</option>
          </select>
        </div>
        <button>Add person</button>
      </form>
      <p className="small muted">They need to sign in once before you can add them.</p>
      <ErrorNote error={error} />
    </Section>
  );
}
