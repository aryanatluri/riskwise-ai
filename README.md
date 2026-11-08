# RISKWISE AI

Contract risk review for banks, NBFCs, insurers and fintechs. Upload a vendor contract,
get clause-level findings checked against **your own policies** and the regulations that
apply to you, then approve, assign and track the fixes.

- **Bring your own LLM key.** Each organization plugs in its own Gemini, Azure OpenAI,
  OpenAI or Anthropic key, in the region it chooses. Contracts never go to a shared key.
- **Rules-only mode.** Works with no LLM at all: a deterministic engine driven by each
  org's policy thresholds.
- **Self-hostable.** One `docker compose up` inside the client's own cloud.
- **Built for audit.** Every decision lands in an append-only audit log. Tenants are
  isolated twice: in the app and with Postgres row-level security.

> Status: v0.2. Backend (API, engine, workflow) and web app are in place. The original
> prototype and the no-login sales demo for Dad live in `legacy/`.

## How a contract is analysed

1. Text is extracted (PDF, DOCX, TXT) and split into clauses by their numbering.
2. **Rules pass** on every clause: breach notice windows, data location, encryption,
   liability caps and sub-contracting, using the org's own thresholds.
3. **LLM pass** (hybrid mode only) on clauses that touch a risk area, capped per run,
   with schema-enforced JSON output.
4. **Guardrails:** an LLM finding is dropped unless its evidence quote appears word for
   word in the clause, and unless it cites a real policy rule. Risk scores (CRS) are
   computed in code, never by the model.
5. **Contract-level checks** for clauses that must exist (audit rights, exit assistance).
6. **Citations** are attached by code from the org's regulation packs. The model never
   writes legal citations.

```
CRS = min(10, ((impact x 0.6 + likelihood x 0.4) x exposure) / 7.5 x 10)
severity: >= 8 critical, >= 6 high, >= 4 medium, else low
```

## Run locally

Needs Python 3.12+ and Postgres 16.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/riskwise
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs. In dev mode, get a token from `POST /api/v1/dev/token`,
create an org with `POST /api/v1/orgs`, then send `Authorization: Bearer <token>` and
`X-Org-Id: <org id>` on every call.

Then the web app, in a second terminal:

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies /api to the backend on :8000
```

Sign in with any email (dev mode), create an organization, and upload
`backend/tests/fixtures/cloudstack.txt` from the Contracts page.

Or call the API directly with the sample contract:

```bash
curl -X POST localhost:8000/api/v1/contracts \
  -H "Authorization: Bearer $TOKEN" -H "X-Org-Id: $ORG" \
  -F file=@tests/fixtures/cloudstack.txt -F title="CloudStack MSA"
```

## Tests and evals

```bash
cd backend
pytest -q                 # needs a riskwise_test database (see tests/conftest.py)
python -m evals.run_eval  # precision/recall on labelled contracts in evals/cases
```

Tests should run as a non-superuser Postgres role, so row-level security is really
enforced (CI does this).

## Deploy

**Hosted (free tiers):** API container on Google Cloud Run, Postgres + Auth on Supabase,
frontend on Cloudflare Pages (`npm run build`, publish `frontend/dist`, set
`VITE_API_URL`, `VITE_AUTH_MODE=supabase`, `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`),
hourly SLA sweep from GitHub Actions
(`.github/workflows/sla-sweep.yml`). Set `AUTH_MODE=oidc` with your Supabase issuer and
JWKS URL. Run `alembic upgrade head` as a one-off job before each release.

**Self-hosted:** see `docker-compose.yml`. Point `OIDC_*` at the client's SSO
(Azure AD, Okta).

See `.env.example` for every setting.

## API at a glance

| Area | Endpoints |
| --- | --- |
| Account | `GET /api/v1/me`, `POST /api/v1/orgs`, `GET /api/v1/orgs`, `/api/v1/org/members` |
| Settings | `GET/PUT /api/v1/org/settings`, `POST .../llm/test`, `POST .../jira-webhook-secret` |
| Policies | `GET/POST /api/v1/policies`, `PATCH /api/v1/policies/{id}` |
| Contracts | `POST /api/v1/contracts` (upload + analyse), `GET`, `POST /{id}/analyze`, `DELETE` |
| Findings | `GET /api/v1/findings`, `POST /{id}/decision`, `POST /{id}/dispatch`, `GET /export.csv` |
| Ops | `GET /api/v1/audit`, `POST /api/v1/webhooks/jira/{org_id}`, `POST /api/v1/jobs/sla-sweep` |
| Reference | `GET /api/v1/packs` |

## Important

The regulation packs in `app/engine/packs` are a starting point written by the product
team and are marked `reviewed: false`. They must be reviewed by a qualified lawyer
before any client relies on them. RISKWISE supports reviewers; it does not give legal
advice.
