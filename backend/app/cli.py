"""Command-line ingest for offline / AWS scheduled runs.

Examples:
  PYTHONPATH=. uv run python -m app.cli ingest
  PYTHONPATH=. uv run python -m app.cli ingest --season-year 2026
  PYTHONPATH=. uv run python -m app.cli ingest --scope team --team-espn-id 364
"""

from __future__ import annotations

import argparse
import json
import sys

from app.db import init_db
from app.ingest import get_teams, ingest_league_team_stats, ingest_team_stats


def cmd_ingest(args: argparse.Namespace) -> int:
    init_db()
    if args.scope == "team":
        if not args.team_espn_id:
            print("error: --team-espn-id is required when --scope team", file=sys.stderr)
            return 2
        teams = get_teams()
        team = next((row for row in teams if row["espn_id"] == args.team_espn_id), None)
        if team is None:
            print(f"error: team {args.team_espn_id} not found", file=sys.stderr)
            return 1
        result = ingest_team_stats(team=team, season_year=args.season_year)
    else:
        result = ingest_league_team_stats(season_year=args.season_year)

    print(json.dumps(result, indent=2, default=str))
    status = str(result.get("status") or "")
    return 0 if status in {"success", "partial"} or "teams" in result else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="app.cli",
        description="Premier League stats ingest CLI (run outside the web UI).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser(
        "ingest",
        help="Fetch ESPN team stats into SQLite snapshots and recompute ranks.",
    )
    ingest.add_argument(
        "--scope",
        choices=("league", "team"),
        default="league",
        help="Ingest all Premier League clubs (default) or one team.",
    )
    ingest.add_argument(
        "--team-espn-id",
        default=None,
        help="ESPN team id when --scope team (e.g. 364 for Liverpool).",
    )
    ingest.add_argument(
        "--season-year",
        type=int,
        default=2026,
        help="Season year to ingest (default: 2026).",
    )
    ingest.set_defaults(func=cmd_ingest)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
