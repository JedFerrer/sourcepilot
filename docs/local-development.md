# Local development

## Prerequisites

- Node.js 22 and pnpm 10
- Python 3.11 and uv
- Docker Desktop with Docker Compose

## Configure and start

Run root commands from the repository root; keep the API and web server in separate terminals.

1. Copy `.env.example` to `.env` to configure the local PostgreSQL databases and API database URL. For interactive AI actions, also complete [model configuration](#model-configuration).
2. Copy `apps/web/.env.example` to `apps/web/.env.local` only when FastAPI is not running at `http://localhost:8000`.
3. Start PostgreSQL with `docker compose up -d postgres` and verify [database readiness](#postgresql-reachability).
4. From the repository root, install the web dependencies with `pnpm install`.
5. From `apps/api`, install the API environment with `uv sync --dev --locked`.
6. From `apps/api`, apply the [existing migrations](#migrations-and-persistence-tests), then run the [supplier seed command](#synthetic-supplier-catalog). Both are required before using the workflow; startup does not seed the catalog.
7. Start FastAPI from `apps/api` with `uv run --env-file ../../.env uvicorn sourcepilot.main:app --loop sourcepilot.comparison.lifecycle:comparison_loop --reload --port 8000`. Keep the explicit loop option without `--reload` and with workers too: Windows psycopg async requires a Selector loop.
8. Start the web app from the repository root with `pnpm --filter @sourcepilot/web dev`.

Open `http://localhost:3000`. The browser requests `/api/health`; Next.js proxies that request to FastAPI `http://localhost:8000/health` by default.

## Model configuration

Set `OPENAI_API_KEY` and `SOURCEPILOT_AI_MODEL` in the root `.env` before starting the API to use **Analyze request**, **Get clarification questions**, PDF quote extraction, supplier explanations or **Analyze Comparison**. Use a model available to your account that supports the application's structured-output and tool-calling requests. There is no default model. These actions invoke the live provider and can incur charges; live output is variable and retains the [documented quality limitations](../README.md#known-quality-and-ux-limitations).

Configuration is read lazily: API startup, manual editing, deterministic comparison and normal automated checks do not require model credentials. The automated browser suite supplies its own test-only model; it is not an interactive demo mode. Keep model credentials server-side, outside version control and out of `apps/web/.env.local`. The startup command above loads the root `.env`; restart the API after changing it.

Langfuse is disabled by default and is not a startup or demo prerequisite. Its existing optional installation/configuration instructions and unverified hosted-visibility limitation are in [AI observability](development/OBSERVABILITY.md).

## Local PDF storage

The default `DOCUMENT_STORAGE_BACKEND=local` stores original PDFs privately under `apps/api/.local-quote-documents`. Leaving `DOCUMENT_STORAGE_LOCAL_DIR` empty uses that default; set it to an absolute writable directory to override it. Storage directories are created on upload. They are not web assets and should not be committed or shared.

`QUOTE_PDF_MAX_BYTES` defaults to 10,000,000 file bytes and `QUOTE_PDF_MAX_PAGES` to 15. Only text-extractable PDFs are supported; scanned/image-only files need manual entry. The existing S3-compatible adapter is available, but production storage and deployment remain M6-U6 work.

## PostgreSQL reachability

After starting Compose, run `docker compose ps`. The `postgres` service must report `healthy`. For the explicit database readiness check, run `docker compose exec postgres pg_isready -U sourcepilot -d sourcepilot`; it should report that the server is accepting connections.

The API and Alembic migration commands use `DATABASE_URL`; migration commands fail clearly when it is missing. The existing health endpoint does not open a database connection. `TEST_DATABASE_URL` is required only for persistence/integration tests; it must name a different PostgreSQL database from `DATABASE_URL`.

## Anonymous demo sessions

`DEMO_SESSION_TTL_SECONDS` controls the fixed lifetime of anonymous demo sessions and defaults to 86400 seconds (24 hours). Activity updates only the session's `last_seen_at`; it does not extend the lifetime. `DEMO_SESSION_COOKIE_SECURE` defaults to `false` for local HTTP development. Set it to `true` for every HTTPS deployment so the HttpOnly, same-site session cookie is transmitted only over HTTPS.

## Migrations and persistence tests

For initial setup, run from `apps/api` after PostgreSQL is healthy:

```text
uv run --env-file ../../.env alembic upgrade head
uv run --env-file ../../.env alembic current
```

Persistence tests are a separate check, not a setup requirement: `uv run --env-file ../../.env pytest` from `apps/api` uses the isolated test database described below.

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

Inspect the seeded names and evidence from the repository root with PostgreSQL:

```text
docker compose exec postgres psql -U sourcepilot -d sourcepilot -c "SELECT name, country, general_moq FROM suppliers ORDER BY name;"
docker compose exec postgres psql -U sourcepilot -d sourcepilot -c "SELECT s.name, e.claim_key, e.source_label, e.evidence_state, e.evidence_text FROM supplier_evidence e JOIN suppliers s ON s.id = e.supplier_id ORDER BY s.name, e.claim_key, e.source_label;"
```

## Manual demo walkthrough

Complete setup and seeding above, then open `http://localhost:3000`. Use one browser session for the walkthrough. All suppliers, quotes and evidence are fictional. This is a manual live-provider walkthrough when AI actions are used; the separate [deterministic browser suite](#deterministic-browser-workflow-m5-u3) is the reproducible automated path. A useful AI answer or a suggested supplier is not guaranteed.

### 1. Brief

Fill **Project name** with a descriptive demo name and **What do you want to source?** with the existing [scenario](../apps/api/tests/e2e_support/scenario.json) request:

> Source 2,000 custom cosmetic travel bags made from recycled polyester with a custom logo. Target unit cost below USD 5, delivery to Sydney, preferred GRS certification. Delivery timing is not decided yet.

Choose **Create project**, then **Analyze request**. Review the result rather than assuming it matches the fixture. Check **Product name** (`custom cosmetic travel bags`), **Category** (`cosmetic travel bags`), **Requested quantity** (`2000`), **Destination** (`Sydney`) and **Target unit price (optional)** (`5`). Ensure recycled polyester and custom branding are **Required**, with GRS certification **Preferred**, using each requirement's **Importance** selector.

Save any corrections with **Save Brief** before requesting clarification. For the missing timing, choose **Get clarification questions** when available, set **Delivery answer** to `2026-12-15` (the fixed synthetic scenario date), and **Save answers**. If analysis/clarification fails or leaves incorrect data, use the existing Brief editor; choose **Delivery target type: Date**, fill **Delivery date**, and correct/add requirements there. This fixture date demonstrates the flow, not a current delivery promise. Choose **Save Brief**, resolve any remaining readiness messages, review the saved requirements and choose **Approve Brief**.

### 2. Suppliers

Choose **Discover Suppliers**. The seeded cosmetic-bag scenario produces five candidates; a differently interpreted category can change the results. Review requirement findings and **Available evidence**; **Explain this supplier** requests optional AI explanation. Unknown or conflicting evidence must remain visible.

On Harbor Pouch Works, Willow Stitch Studio and Moss Thread Bags, choose **Add to shortlist**, then **Review selected suppliers** and **Approve Shortlist**. If discovery returns no candidates, use **Review Brief** to check the saved category and requirements, save/reapprove if required by readiness, then discover again.

### 3. Quotes

Use **Upload PDF quote** on each matching supplier card. The files are in `apps/api/tests/fixtures/quote_pdfs`:

| Supplier | PDF |
| --- | --- |
| Harbor Pouch Works | [harbor_primary.pdf](../apps/api/tests/fixtures/quote_pdfs/harbor_primary.pdf) |
| Willow Stitch Studio | [willow_primary.pdf](../apps/api/tests/fixtures/quote_pdfs/willow_primary.pdf) |
| Moss Thread Bags | [moss_primary.pdf](../apps/api/tests/fixtures/quote_pdfs/moss_primary.pdf) |

Process, review and save one quote before moving to the next. **Save a manual draft before uploading another quote:** an explicit upload can discard unsaved edits on another card, as recorded in [M6-U4](implementation/M6-U4.md).

After **NEEDS REVIEW**, inspect current values, origins, extracted values and **PDF source evidence**. All three primary PDFs quote 2,000 units in USD, but their shipping text names **Manila**, while the Brief requests **Sydney**. Preserve this mismatch; the quotes do not establish delivery to Sydney. Willow leaves preferred GRS certification unstated and Moss leaves sample lead time unstated. Keep unknowns and conflicts visible; see the [fixture guide](../apps/api/tests/fixtures/quote_pdfs/README.md) for the full corpus.

Use **Edit PDF draft** and **Save draft** for corrections. An optional provenance demonstration, matching the existing browser test, changes Harbor's **Unit price** from the PDF's USD 4.60 to a hypothetical user-confirmed USD 4.50. The current origin becomes **USER CORRECTED**, while the PDF still supports 4.60; do not describe 4.50 as extracted evidence. Otherwise correct only actual extraction mistakes against the PDF. Choose **Review for confirmation**, then **Confirm Quote** for each reviewed quote. Uploading or saving alone does not confirm it.

### 4. Comparison

With the approved shortlist and at least two confirmed quotes, choose **Generate Comparison**. Review the factual table, requirement states, warnings and **Source details**. Three confirmed quotes show the intended primary scenario; fewer confirmed quotes leave the remaining supplier data incomplete.

Choose **Analyze Comparison** to request optional tradeoff analysis. A valid result may say **No supplier suggested yet**. A failed analysis offers **Retry analysis** and does not erase the factual comparison. Neither outcome chooses a preferred supplier. If upstream inputs change, follow supplier re-evaluation guidance and use **Regenerate Comparison** before requesting current advice.

### 5. Decision

Review the evidence and uncertainties, choose **Preferred supplier**, optionally enter **Decision notes**, then choose **Mark as Preferred Supplier**. Reload to inspect the saved preference; **Back to projects** returns to the dashboard. This records the user's choice only: it sends no message, order or payment.

### Failed PDF recovery

In a separate demo project with an approved shortlist, upload [image_only.pdf](../apps/api/tests/fixtures/quote_pdfs/image_only.pdf) for Harbor. It has no extractable text and should reach **FAILED**. Choose **Enter quote manually**; for the synthetic fallback example enter **Quoted quantity** `2000`, **Unit price** `4.50` and **Original currency (three-letter code)** `USD`, leaving unstated fields blank. These are user-entered demonstration values, not facts extracted from the failed file.

Choose **Save manual draft**, **Review for confirmation**, then **Confirm Quote**. Add and confirm Willow's quote (by its primary PDF or manual entry) to enable **Generate Comparison**. Save each draft before another upload. For other failures, **Retry processing** retries extraction; **Retry status check**, when shown, only rereads status and does not restart processing.

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

# Comparison analysis time limits

The comparison analysis and advice endpoints use one cooperative deadline, starting at API middleware entry before body parsing and dependencies. Configure `NEXT_PUBLIC_SOURCEPILOT_ANALYSIS_TIMEOUT_SECONDS` (default 180), `SOURCEPILOT_ANALYSIS_ATTEMPT_SECONDS` (default 60), and `SOURCEPILOT_ANALYSIS_CLEANUP_SECONDS` (default 5). Values must be positive and finite; total must exceed cleanup. Cleanup and attempted response handoff are inside the total. Attempts, tools, database waits, retry backoff, repair and final verification do not reset the clock. SDK retries remain disabled; the existing single application retry remains. This supersedes the unconditional deadline interpretation: synchronous stalls and OS resolver helpers can outlast the target. Late advice is rejected; timely response delivery and complete cleanup are not guaranteed.

Use `--loop sourcepilot.comparison.lifecycle:comparison_loop` for Uvicorn, including normal, reload and multi-worker launches. This supplies the Selector loop required by async psycopg on Windows and the comparison helper tracker. The lifespan validates the loop and warms credential-free SDK platform/header caches, TLS context, response classes and database dialect before accepting requests. Startup may wait and has no request deadline; it performs no provider call or database connection. Request-owned sessions, NullPool engines and provider clients remain exclusive. The existing installed libpq must be at least 17 for nonblocking cancellation; startup fails explicitly otherwise. No dependency is installed by this check. Windows and local Linux execution are regression-tested. The completed [M4-U7 Linux verification](implementation/evidence/M4-U7/linux-corrections/summary.txt) used WSL Ubuntu 26.04, Python 3.11.15, the asyncio Selector loop and locked dependencies: the full backend suite passed 3,677 tests, and 430 targeted tests also passed. This is local WSL evidence, not hosted CI, native-Linux deployment, macOS or sustained multi-worker load certification. Alternate uvloop configuration is not covered. The report retains its historical pending-gate wording; the [current M4-U7 Done Check](implementation/M4-U7-analyze-comparison-defect.md#done-check--2026-11-05-asiamanila) records the subsequent review, Browser QA and Done Check completion.

`SOURCEPILOT_ANALYSIS_CAPACITY` is a positive integer, default **2 per API worker**. Two permits modest concurrent use while bounding active-or-draining comparison owners; it is a conservative V1 default, not a throughput benchmark. Exhaustion rejects promptly with 503 / `COMPARISON_ANALYSIS_BUSY`, without a waiting queue or model invocation. Each request retains its slot until the underlying resolver/platform futures actually finish and owned resources are confirmed released. A cancelled asyncio wrapper does not release a running helper. An unconfirmed provider close remains quarantined and may require application restart; no detached cleanup worker is started. Multi-worker deployments multiply capacity; this is not a global paid-call limit.

Terminal bookkeeping receives up to 40% of the cleanup reserve; each provider/session/engine close attempt receives up to 15%, always clamped to the original total. Session closure and engine disposal are independently attempted even after error, cancellation or total exhaustion. Zero-time entry is logged as incomplete, never claimed as graceful release. Failed database cleanup attempts close only that request's locally owned libpq sockets; this does not prove immediate server-side cancellation or rollback. Unconfirmed resource release retains capacity. A missing terminal trace is possible, and a commit already sent can succeed after local cancellation. A recorded COMPLETED run describes validated computation, not successful browser delivery.

Application shutdown stops admission, cancels active requests and waits up to five seconds in its lifecycle hook; final Python executor shutdown may still wait for OS helpers. CLI/live-eval entry points share one top-level lifecycle per invocation. Direct synchronous compatibility calls own a top-level lifecycle whose shutdown may wait; neither CLI process exit nor application process exit has the HTTP timing guarantee.

Set the public total consistently in the API environment and the frontend build environment. Rebuild the frontend after changing it. The proxy waits total + 10 seconds and the browser total + 15 seconds; comparison verification reads have a 15-second limit. Hosting request limits must accommodate these margins when deployment is configured.

Timeout normally returns a recoverable error and requires explicit Retry analysis. If response sending itself stalls or headers were already sent, the backend can abort delivery instead of providing a new JSON envelope. Closing the browser connection does not confirm server cancellation: the request can continue to its cooperative cutoff, and OS helpers can continue afterward. Remote provider processing/billing may continue after local cancellation. Advice remains response-only, so navigating away cannot recover it later. Ambiguous connection loss delays retry in the mounted page to avoid overlapping requests; there is no cross-tab deduplication or durable job service.
