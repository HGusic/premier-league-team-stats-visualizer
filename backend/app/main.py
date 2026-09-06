from __future__ import annotations

import os

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.ingest import (
    get_league_average_profile,
    get_team_profile,
    get_teams,
    ingest_league_team_stats,
    ingest_team_stats,
)

app = FastAPI(title="Premier League Team Tracker API")

# Comma-separated origins for production (e.g. https://your-domain.com).
_cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    # Sync all Premier League clubs so the team bar is populated.
    get_teams()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/teams")
def list_teams() -> dict:
    return {"teams": get_teams()}


@app.post("/api/ingest/team-stats")
def run_team_stats_ingest(
    team_espn_id: str | None = Query(default=None),
    season_year: int = Query(default=2026),
    scope: str = Query(default="league", pattern="^(league|team)$"),
    x_ingest_token: str | None = Header(default=None, alias="X-Ingest-Token"),
) -> dict:
    """
    Ingest team statistics into SQLite snapshots.

    Disabled unless INGEST_API_TOKEN is set in the environment, and the request
    sends the same value in the X-Ingest-Token header. Prefer the CLI for AWS:

      PYTHONPATH=. uv run python -m app.cli ingest --season-year 2026
    """
    expected = os.getenv("INGEST_API_TOKEN", "").strip()
    if not expected or x_ingest_token != expected:
        raise HTTPException(
            status_code=403,
            detail="Ingest API disabled. Use `python -m app.cli ingest` or set INGEST_API_TOKEN.",
        )

    if scope == "team":
        if not team_espn_id:
            raise HTTPException(
                status_code=400, detail="team_espn_id is required when scope=team"
            )
        teams = get_teams()
        team = next((row for row in teams if row["espn_id"] == team_espn_id), None)
        if team is None:
            raise HTTPException(status_code=404, detail="Team not found")
        return ingest_team_stats(team=team, season_year=season_year)

    return ingest_league_team_stats(season_year=season_year)


@app.get("/api/league/average-profile")
def league_average_profile(season_year: int = Query(default=2026)) -> dict:
    return get_league_average_profile(season_year=season_year)


@app.get("/api/teams/{team_espn_id}/profile")
def team_profile(
    team_espn_id: str,
    season_year: int = Query(default=2026),
) -> dict:
    if team_espn_id == "__average__":
        return get_league_average_profile(season_year=season_year)
    profile = get_team_profile(team_espn_id, season_year=season_year)
    if profile is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return profile
