# Architecture

How the Premier League Team Stats Visualizer is put together: services, data flow, modules, and ranking.

## Overview

```
┌─────────────────────┐     rewrite /api/*      ┌──────────────────────┐
│  Next.js (3000)     │ ───────────────────────►│  FastAPI (8000)      │
│  Team bar, radars,  │                         │  /api/teams          │
│  profile sections   │◄── JSON profiles ───────│  /api/teams/{id}/…   │
└─────────────────────┘                         │  /api/league/…       │
                                                └──────────┬───────────┘
                                                           │
                                                ┌──────────▼───────────┐
                                                │  SQLite app.db       │
                                                │  teams, snapshots,   │
                                                │  stats, aggregates   │
                                                └──────────▲───────────┘
                                                           │
                                                ┌──────────┴───────────┐
                                                │  Ingest CLI / HTTP   │
                                                │  ESPN site APIs      │
                                                └──────────────────────┘
```

| Layer | Responsibility |
| --- | --- |
| Frontend | Team selection UI, radar sections, legend/compare views |
| API | Read profiles, teams, and league averages from SQLite |
| SQLite | Persistent season snapshots, per-stat ranks, league aggregates |
| Ingest | Pull ESPN data, repair known quirks, compute ranks/aggregates |

## Data flow

1. **Ingest** fetches club roster + per-team core statistics, team record, and league standings from ESPN.
2. Rows are normalized into `team_stats` under a per-team **snapshot** (`team_stat_snapshots`), keyed by `team_espn_id` + season.
3. **League ranks** and **min/max/avg aggregates** are computed across clubs (including lower-is-better metrics such as goals against).
4. ESPN quirks are repaired where needed (e.g. save %, inaccurate crosses, penalty faced counts).
5. The API serves:
   - team list
   - team profile (stats + header + composite radar ranks)
   - league-average profile
6. The UI maps fixed **metric sets** into radar sections (Defense, Offense, Possession, Passing, Goalkeeping, Set Pieces & Discipline). Composite profile ranks stay in sync via `PROFILE_METRIC_SETS` in `backend/app/ingest/__init__.py` and the matching frontend section components.

## Storage model

| Table | Role |
| --- | --- |
| `teams` | Club metadata (ESPN id, name, colors, logo) |
| `team_stat_snapshots` | One snapshot per team/season (ingest point-in-time) |
| `team_stats` | Individual stats for a snapshot (source, category, value, rank, per-game) |
| `league_stat_aggregates` | League min/max/avg (and per-game bounds) per stat |
| `ingest_runs` | Ingest run audit trail |

SQLite path: `backend/data/app.db`.

Stat **sources** commonly include:

- `core_statistics` — ESPN team statistics payload
- `standings` — league table fields (e.g. `pointsAgainst` for Goals Against)
- `team_record` — W-D-L / points style record fields

## API surface

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Liveness |
| `GET /api/teams` | Club list for the team bar |
| `GET /api/teams/{espn_id}/profile` | Full team profile for radars + header |
| `GET /api/league/average-profile` | League-average view |
| `POST /api/ingest/team-stats` | Optional HTTP ingest (disabled unless `INGEST_API_TOKEN` is set) |

The frontend normally calls same-origin `/api/*`, which Next.js rewrites to the FastAPI origin (`API_PROXY_TARGET`).

## Key backend modules

| Path | Role |
| --- | --- |
| `backend/app/main.py` | FastAPI routes, CORS, optional HTTP ingest gate |
| `backend/app/db.py` | SQLite schema + connection |
| `backend/app/ingest/espn.py` | ESPN HTTP clients (teams, stats, standings) |
| `backend/app/ingest/__init__.py` | Ingest orchestration, ranks, aggregates, profile builders |
| `backend/app/cli.py` | Offline ingest entrypoint for local/cron/AWS |

## Key frontend modules

| Path | Role |
| --- | --- |
| `frontend/src/app/page.tsx` | Shell, team selection, profile loading, beta notice |
| `frontend/src/app/TeamBar.tsx` | Infinite horizontal club scroller |
| `frontend/src/app/StatRadarProfile.tsx` | Shared radar + legend + 0→max scaling |
| `frontend/src/app/*Section.tsx` | Section-specific metric definitions |
| `frontend/next.config.ts` | Dev-origin allowlist + API rewrites |

## Ranking model

- Individual stats get competition ranks across the 20 clubs.
- Each radar **profile** averages its metric ranks into a unique 1–20 profile rank.
- Each **section** averages its profile ranks into a section overall rank.
- Radar fill uses a 0→league-max scale (inverted when lower is better), not the ordinal rank itself.

Metric→source overrides (example): Goals Against uses standings `pointsAgainst`, not goalkeeping `goalsConceded`. Keep frontend section metrics and `PROFILE_METRIC_SETS` / `PROFILE_METRIC_SOURCES` aligned.

## Deployment shape

A single persistent host (e.g. Lightsail) fits this design:

- nginx → Next.js
- Next.js rewrites `/api` → local FastAPI
- SQLite on local disk
- cron/systemd timer for weekly ingest

Amplify (or similar) can host the frontend alone, but the API, SQLite file, and scheduled ingest still need a persistent compute target unless the data layer is redesigned (e.g. managed SQL).
