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

The eight initial supplier records, their capabilities, prices, and evidence are
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

The smoke request uses `foundation-smoke-v1` and sends `store=false` to the Responses API. Do not run it in automated checks.

## Checks

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
