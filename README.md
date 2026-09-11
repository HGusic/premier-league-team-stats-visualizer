# Premier League Team Stats Visualizer

Local-first app that ingests Premier League club stats from ESPN, stores season snapshots in SQLite, and visualizes ranked radar profiles in a Next.js UI.

For system design, data flow, and module layout, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Stack

| Layer | Tech |
| --- | --- |
| Frontend | Next.js (App Router), React, Recharts |
| Backend | FastAPI, httpx |
| Data | SQLite (`backend/data/app.db`) |
| Ingest | CLI (`python -m app.cli ingest`) + optional token-gated HTTP endpoint |

## Prerequisites

- **Python** 3.11+
- **[uv](https://docs.astral.sh/uv/)** (backend package manager)
- **Node.js** 20+ and npm (frontend)

## Run locally

### 1. Backend API

```bash
cd backend
uv sync
PYTHONPATH=. uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Health check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 2. Ingest league stats (required once)

In another terminal:

```bash
cd backend
./ingest.sh
# or:
PYTHONPATH=. uv run python -m app.cli ingest --season-year 2026
```

This pulls ESPN team/standings stats for all Premier League clubs, writes snapshots + ranks into SQLite, and builds league aggregates used by the radars.

Single-team ingest:

```bash
PYTHONPATH=. uv run python -m app.cli ingest --scope team --team-espn-id 364 --season-year 2026
```

### 3. Frontend

```bash
cd frontend
npm ci
npm run dev
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000) or [http://localhost:3000](http://localhost:3000).

The Next.js dev server **rewrites** `/api/*` and `/health` to the backend (`API_PROXY_TARGET`, default `http://127.0.0.1:8000`), so the browser stays same-origin on either host.

## Environment variables

### Backend

| Variable | Purpose | Default |
| --- | --- | --- |
| `CORS_ORIGINS` | Comma-separated allowed browser origins | `http://localhost:3000,http://127.0.0.1:3000` |
| `INGEST_API_TOKEN` | If set, enables `POST /api/ingest/team-stats` when the request sends matching `X-Ingest-Token` | unset (HTTP ingest disabled) |

### Frontend

| Variable | Purpose | Default |
| --- | --- | --- |
| `API_PROXY_TARGET` | Backend origin for Next rewrites (server-side) | `http://127.0.0.1:8000` |
| `NEXT_PUBLIC_API_BASE` | Browser API base URL; leave empty to use same-origin `/api` via rewrites | empty |

## Production notes

- Prefer the **CLI + cron** for ingest (already used on Lightsail); keep `INGEST_API_TOKEN` unset unless you intentionally expose HTTP ingest.
- SQLite lives on disk at `backend/data/app.db` — use persistent storage (not ephemeral containers without a volume).
- For a public domain, set `CORS_ORIGINS` to your HTTPS origins and terminate TLS at nginx/Caddy (or similar).

## License / data

Stats are sourced from public ESPN endpoints for personal/visualization use. ESPN terms apply to the upstream data.
