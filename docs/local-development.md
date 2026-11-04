# Local development

## Prerequisites

- Node.js 22 and pnpm 10
- Python 3.11 and uv
- Docker Desktop with Docker Compose

## Configure and start

1. Copy `.env.example` to `.env` to configure the local PostgreSQL databases and API database URL.
2. Copy `apps/web/.env.example` to `apps/web/.env.local` only when FastAPI is not running at `http://localhost:8000`.
3. Start PostgreSQL with `docker compose up -d postgres`.
4. From the repository root, install the web dependencies with `pnpm install`.
5. From `apps/api`, install the API environment with `uv sync --dev`.
6. Start FastAPI from `apps/api` with `uv run --env-file ../../.env uvicorn sourcepilot.main:app --reload --port 8000`.
7. Start the web app from the repository root with `pnpm --filter @sourcepilot/web dev`.

Open `http://localhost:3000`. The browser requests `/api/health`; Next.js proxies that request to FastAPI `http://localhost:8000/health` by default.

## PostgreSQL reachability

After starting Compose, run `docker compose ps`. The `postgres` service must report `healthy`. For the explicit database readiness check, run `docker compose exec postgres pg_isready -U sourcepilot -d sourcepilot`; it should report that the server is accepting connections.

The API and Alembic migration commands use `DATABASE_URL`; migration commands fail clearly when it is missing. The existing health endpoint does not open a database connection. `TEST_DATABASE_URL` is required only for persistence/integration tests; it must name a different PostgreSQL database from `DATABASE_URL`.

## Anonymous demo sessions

`DEMO_SESSION_TTL_SECONDS` controls the fixed lifetime of anonymous demo sessions and defaults to 86400 seconds (24 hours). Activity updates only the session's `last_seen_at`; it does not extend the lifetime. `DEMO_SESSION_COOKIE_SECURE` defaults to `false` for local HTTP development. Set it to `true` for every HTTPS deployment so the HttpOnly, same-site session cookie is transmitted only over HTTPS.

## Migrations and persistence tests

From `apps/api`, after PostgreSQL is healthy:

```text
uv run --env-file ../../.env alembic upgrade head
uv run --env-file ../../.env alembic current
uv run --env-file ../../.env pytest
```

Generate future migrations only after changing persistence models, then review the generated revision before committing it:

```text
uv run --env-file ../../.env alembic revision --autogenerate -m "describe the schema change"
```

The Compose service creates the local `sourcepilot_test` database for a fresh PostgreSQL volume. If the volume existed before M0-U2, create it once with `docker compose exec postgres createdb -U sourcepilot sourcepilot_test`. Persistence tests require `TEST_DATABASE_URL` and reset only that database through Alembic. Their safety checks reject a URL that targets the same PostgreSQL database as `DATABASE_URL`.

## Synthetic supplier catalog

The 15 supplier records, their capabilities, prices, and evidence are
fictional. The seed command is explicit and safe to repeat; it updates only
fixture-owned records and does not run during API startup. After migration,
run this from `apps/api`:

```text
uv run --env-file ../../.env python -m sourcepilot.suppliers.seed
```

Inspect the seeded names and evidence with PostgreSQL:

```text
docker compose exec postgres psql -U sourcepilot -d sourcepilot -c "SELECT name, country, general_moq FROM suppliers ORDER BY name;"
docker compose exec postgres psql -U sourcepilot -d sourcepilot -c "SELECT s.name, e.claim_key, e.source_label, e.evidence_state, e.evidence_text FROM supplier_evidence e JOIN suppliers s ON s.id = e.supplier_id ORDER BY s.name, e.claim_key, e.source_label;"
```

## AI foundation smoke check

AI configuration is lazy: `OPENAI_API_KEY` and `SOURCEPILOT_AI_MODEL` are required only when an AI operation runs, never during API startup or automated tests. CI and pytest use model-client fakes and must not call OpenAI.

The following command is a manual, opt-in live check. It requires a valid API key, a configured model name, a migrated database, and an existing `DemoSession` UUID. It creates exactly one `AIRun` and prints its ID and terminal status:

```text
uv run --env-file ../../.env python -m sourcepilot.ai.smoke --demo-session-id <demo-session-uuid>
```

The smoke request uses `foundation-smoke-v2` and sends `store=false` to the Responses API. Do not run it in automated checks.

## Checks

### Deterministic browser workflow (M5-U3)

The browser suite runs the real web/API/PostgreSQL/PDF path with a test-only
model client. It never calls a live provider. Suppliers, PDFs, extraction outputs,
and the scenario contract are synthetic. The advisory fixture deliberately returns
no suggested supplier; only the browser user's explicit decision records a preference.
The existing PDFs retain their original shipping destinations and unknowns, even
when they differ from the Sydney Brief.

After installing the existing web/API dependencies and starting PostgreSQL, provision
the disposable database once:

```text
docker compose exec -T postgres createdb -U sourcepilot sourcepilot_e2e
pnpm --filter @sourcepilot/web exec playwright install chromium
```

Export all three URLs before running. Use your configured credentials; these values
are the local Compose defaults. PowerShell:

```powershell
$env:DATABASE_URL = 'postgresql+psycopg://sourcepilot:sourcepilot@127.0.0.1:5432/sourcepilot'
$env:TEST_DATABASE_URL = 'postgresql+psycopg://sourcepilot:sourcepilot@127.0.0.1:5432/sourcepilot_test'
$env:E2E_DATABASE_URL = 'postgresql+psycopg://sourcepilot:sourcepilot@127.0.0.1:5432/sourcepilot_e2e'
pnpm test:e2e
```

For POSIX shells, use `export KEY=value` for the same URLs. Run from the repository
root; commands start and stop their own API and production-built web server on
127.0.0.1 ports 18000 and 13000. Occupied ports cause failure rather than server reuse.
The runner owns temporary document storage and removes it after either success or
failure, including on Windows where server termination may bypass Python cleanup.

`pnpm test:e2e` runs the golden path once, then the six independent targeted scenarios
(correction/provenance, failed-PDF manual fallback, abandoned-processing retry,
supplier staleness, comparison/advice staleness, session isolation). Targets still run
if the golden path fails, and the command retains a failing exit status.
`pnpm test:e2e:repeat` runs the golden path three consecutive times; all commands use
one worker and zero retries. `pnpm test:e2e:targeted` runs only the independent targets.
Do not run E2E commands concurrently with each other; each invocation resets its database.
Pytest uses its separate database and may run independently.

The launcher refuses reset unless every guard passes: explicit valid URLs/credentials, E2E name
`sourcepilot_e2e`, loopback-only resolution, existing identity checks against both
protected databases, distinct database names, and a successful connection confirming
the database name and user. It pins the resolved loopback address/port and verifies the
connected libpq endpoint. All inherited `PG*` settings are rejected, including host-address,
service-file, options, and multi-host routing overrides; unset them before E2E commands.
Errors abort before writes. Validation, reset, migrations, and catalog seeding share one
open connection and transaction; migrations cannot fall back to another connection.
The abandoned-processing helper additionally requires
the exact project/quote IDs and designated first abandoned upload before aging its timestamp;
normal application reads and Retry processing perform recovery.

Stage-labelled reports live in `apps/web/playwright-report`, failure screenshots/traces
in `apps/web/test-results`, and captured server/runner output in `apps/web/e2e-logs`.
CI separately requires the three golden runs and the targeted suite, even after a
golden failure, and retains sanitized diagnostics for three days. Each upload is gated
by successful sanitization and contains only `apps/web/e2e-upload/<stage>/diagnostics.zip`.
Raw reports/traces/logs are never uploaded. Sanitization covers Cookie/Set-Cookie headers,
browser cookie storage, session-token fields, encoded buffers/attachments, nested trace
ZIPs, and the compressed report embedded in HTML. Unknown binary attachments are redacted;
stage errors, timings, network status, reports, and credential-free screenshots remain.
Raw local artifacts can contain anonymous-session cookies; do not share or commit them.
Run `node scripts/test-e2e-artifacts.mjs` to generate a deliberate Playwright failure and
verify that the actual upload bundle contains no known dummy token while retaining diagnostics.
Live-model quality and live-provider E2E remain separate and unverified.

Run these from the repository root:

```text
pnpm lint
pnpm typecheck
pnpm test
pnpm build
docker compose config --quiet
```

Run these from `apps/api`:

```text
uv run ruff check .
uv run pyright
uv run --env-file ../../.env pytest
```


## Public-demo security prerequisites

`API_MAX_REQUEST_BYTES` is a positive integer, defaulting to 1,000,000 bytes.
The existing middleware rejects oversized non-upload HTTP bodies before parsing,
including streamed bodies without a trustworthy Content-Length, with HTTP 413 and
`REQUEST_TOO_LARGE`. PDF uploads retain `QUOTE_PDF_MAX_BYTES` plus 65,536 bytes
of multipart overhead and the existing `UPLOAD_TOO_LARGE` contract. File and page
limits still apply independently.

HTTPS with `DEMO_SESSION_COOKIE_SECURE=true`, same-site frontend/API routing and
private document storage are deployment prerequisites. Hosting-level abuse controls
and deployment configuration remain deferred to M6-U6. Per-request body limits do
not bound repeated anonymous sessions, aggregate storage or repeated paid model calls.
The E2E expiry helper exists only under `tests/e2e_support`, uses the existing isolated
database guard, and requires a designated single-project fixture; there is no HTTP
expiry endpoint. Automated targeted checks do not constitute independent Browser QA.
