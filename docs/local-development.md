# Local development

## Prerequisites

- Node.js 22 and pnpm 10
- Python 3.11 and uv
- Docker Desktop with Docker Compose

## Configure and start

1. Copy `.env.example` to `.env` to override the local PostgreSQL defaults if needed.
2. Copy `apps/web/.env.example` to `apps/web/.env.local` only when FastAPI is not running at `http://localhost:8000`.
3. Start PostgreSQL with `docker compose up -d postgres`.
4. From the repository root, install the web dependencies with `pnpm install`.
5. From `apps/api`, install the API environment with `uv sync --dev`.
6. Start FastAPI from `apps/api` with `uv run uvicorn sourcepilot.main:app --reload --port 8000`.
7. Start the web app from the repository root with `pnpm --filter @sourcepilot/web dev`.

Open `http://localhost:3000`. The browser requests `/api/health`; Next.js proxies that request to FastAPI `http://localhost:8000/health` by default.

## PostgreSQL reachability

After starting Compose, run `docker compose ps`. The `postgres` service must report `healthy`. For the explicit database readiness check, run `docker compose exec postgres pg_isready -U sourcepilot -d sourcepilot`; it should report that the server is accepting connections.

M0-U1 does not connect the application to PostgreSQL. Database configuration remains at the Compose and local-environment boundary until the persistence unit.

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
uv run pytest
```
