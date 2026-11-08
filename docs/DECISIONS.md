# Decisions log

Newest first. Each entry: what we decided, why, and what would change our mind.

## 2026-11-08: Defaults chosen while building v0.2

Aryan was away when these came up, so these are the defaults. All are easy to change.

| Question | Default | Why |
| --- | --- | --- |
| First market | India BFSI | Dad's network; DPDPA, CERT-In and RBI outsourcing rules create the pain. EU pack (GDPR, DORA) ships too. |
| First deployment model | Hosted + BYOK | Fastest to pilot. Self-host compose file exists for banks that need it. |
| LLM providers at launch | Gemini, Azure OpenAI (plus OpenAI, Anthropic) | Gemini paid tier and Azure OpenAI are what Indian BFSI security teams most often already approve. |

## Bring your own key, never a shared free key

Free LLM tiers allow the provider to use prompts and responses to improve its products,
and free Gemini cannot serve users in the EEA, Switzerland or the UK at all. Client
contracts are confidential and often contain personal data. So each org supplies its own
key, stored encrypted (Fernet, `ENCRYPTION_KEY`), and RISKWISE pays nothing per analysis.

## LLM calls over plain HTTPS, not SDKs

Four providers in about 200 lines, no SDK version churn, and easy to test with
`httpx.MockTransport`. Each provider uses its native structured-output feature.
**Not yet done:** AWS Bedrock, which needs SigV4 request signing. Add it with `boto3`'s
Converse API when the first Bedrock client appears.

## The LLM never writes citations or scores

The model returns findings tied to the org's policy rule codes. Code then checks the quote
is verbatim, computes CRS, and attaches regulation references from the packs. A hallucinated
quote or law in front of a bank's legal team would end the pilot.

## Rules pass always runs; the LLM replaces it per clause and domain

Rules are free and deterministic, so they always run. If the LLM produces a verified finding
for the same clause and domain, it replaces the rules finding, because it explains more. If the LLM
fails or is unavailable, the rules results still stand.

## Clauses sent to the LLM are pre-filtered and capped

Only clauses that match a risk domain go to the LLM, at most `MAX_LLM_CLAUSES_PER_RUN`
(default 60) per run. This keeps the client's bill predictable.

## Two locks on tenant isolation

App queries always filter by `org_id`. Postgres row-level security (`FORCE`d, keyed on
`app.current_org` per transaction) is the second lock. Jobs that span orgs set
`app.bypass_rls`. The app must connect as a role without `BYPASSRLS`, or RLS does nothing.

## No pgvector yet

The prototype's schema had pgvector for retrieval. An org has tens of policy rules, which fit in
one prompt, so retrieval adds cost and complexity for no gain today. Revisit when orgs upload
long policy documents and we need to pull relevant passages from them.

## Analysis runs inside the upload request

Simple and fine on Cloud Run (long request timeouts). Move to a queue if contracts with
hundreds of LLM-checked clauses become common.

## Members must sign in once before being added

Avoids linking accounts by email across identity providers, which is a known takeover risk.
Proper email invitations come with the frontend.

## Known gaps (next up)

- Web frontend (React + Vite) to replace `legacy/frontend/index.html`
- Policy upload: extract rules from a client's policy PDF with the LLM, then human confirmation
- PDF and DOCX exports of findings and redlines
- Microsoft Teams notifications
- S3-compatible storage backend for hosted file storage
- Nightly `pg_dump` backups (Supabase free tier has none)
- Legal review of the regulation packs
- Real (anonymised) contracts in `evals/cases`. The current cases were written by us, so
  the 100% eval score is optimistic.
