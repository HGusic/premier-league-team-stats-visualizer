from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import httpx

from app.db import get_connection, init_db
from app.ingest.espn import (
    DEFAULT_LEAGUE,
    LIVERPOOL,
    _client,
    fetch_core_team_statistics,
    fetch_league_teams,
    fetch_site_team_statistics,
    fetch_standings_by_team,
    fetch_team_record,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_GAMES_PLAYED_NAMES = {
    "gamesplayed",
    "appearances",
}

_SKIP_PER_GAME_HINTS = (
    "percent",
    "percentage",
    "%",
    "average",
    "avg",
    "rate",
    "ratio",
    "ppg",
    "pergame",
    "per_game",
    "rating",
    "summary",
    "standing",
)

# Lower numeric value is better (rank 1 = lowest).
_LOWER_IS_BETTER_HINTS = (
    "against",
    "conceded",
    "loss",
    "losses",
    "foul",
    "yellow",
    "red",
    "card",
    "offside",
    "inaccurate",
    "miss",
    "faced",
    "shotsfaced",
    "goalsagainst",
    "goalsconceded",
    "suffered",
    "dnp",
    "didnotplay",
    "suspension",
    "owngoal",
    "duellost",
    "duelslost",
    "tackleslost",
    "inneffectivetackles",
    "timestackled",
    "tackled",
    "unclaimed",
    "offtarget",
)


def _round2(value: float) -> float:
    return round(float(value), 2)


def _stat_rank_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("source") or ""),
        str(row.get("name") or ""),
        str(row.get("display_name") or ""),
    )


def compute_league_aggregates(
    league_rows: dict[str, list[dict[str, Any]]],
    teams_by_id: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    """Build min / max / average rows for every numeric league stat."""
    buckets: dict[tuple[str, str, str], list[tuple[str, dict[str, Any]]]] = defaultdict(
        list
    )
    meta: dict[tuple[str, str, str], dict[str, Any]] = {}

    for team_id, rows in league_rows.items():
        for row in rows:
            key = _stat_rank_key(row)
            meta[key] = {
                "source": row.get("source") or "",
                "category": row.get("category") or "",
                "name": row.get("name") or "",
                "display_name": row.get("display_name") or "",
                "abbreviation": row.get("abbreviation"),
            }
            buckets[key].append((team_id, row))

    aggregates: list[dict[str, Any]] = []
    for key, entries in buckets.items():
        value_entries = [
            (team_id, row)
            for team_id, row in entries
            if isinstance(row.get("value"), (int, float))
        ]
        per_game_entries = [
            (team_id, row)
            for team_id, row in entries
            if isinstance(row.get("per_game_value"), (int, float))
        ]
        if not value_entries and not per_game_entries:
            continue

        info = meta[key]
        row_out: dict[str, Any] = {
            **info,
            "team_count": len({team_id for team_id, _ in entries}),
            "avg_value": None,
            "min_value": None,
            "min_team_espn_id": None,
            "min_team_name": None,
            "max_value": None,
            "max_team_espn_id": None,
            "max_team_name": None,
            "avg_per_game": None,
            "min_per_game": None,
            "min_per_game_team_espn_id": None,
            "min_per_game_team_name": None,
            "max_per_game": None,
            "max_per_game_team_espn_id": None,
            "max_per_game_team_name": None,
        }

        if value_entries:
            values = [float(row["value"]) for _, row in value_entries]
            min_team_id, min_row = min(value_entries, key=lambda item: float(item[1]["value"]))
            max_team_id, max_row = max(value_entries, key=lambda item: float(item[1]["value"]))
            row_out["avg_value"] = _round2(sum(values) / len(values))
            row_out["min_value"] = _round2(float(min_row["value"]))
            row_out["max_value"] = _round2(float(max_row["value"]))
            row_out["min_team_espn_id"] = min_team_id
            row_out["max_team_espn_id"] = max_team_id
            row_out["min_team_name"] = teams_by_id.get(min_team_id, {}).get("name")
            row_out["max_team_name"] = teams_by_id.get(max_team_id, {}).get("name")

        if per_game_entries:
            values = [float(row["per_game_value"]) for _, row in per_game_entries]
            min_team_id, min_row = min(
                per_game_entries, key=lambda item: float(item[1]["per_game_value"])
            )
            max_team_id, max_row = max(
                per_game_entries, key=lambda item: float(item[1]["per_game_value"])
            )
            row_out["avg_per_game"] = _round2(sum(values) / len(values))
            row_out["min_per_game"] = _round2(float(min_row["per_game_value"]))
            row_out["max_per_game"] = _round2(float(max_row["per_game_value"]))
            row_out["min_per_game_team_espn_id"] = min_team_id
            row_out["max_per_game_team_espn_id"] = max_team_id
            row_out["min_per_game_team_name"] = teams_by_id.get(min_team_id, {}).get(
                "name"
            )
            row_out["max_per_game_team_name"] = teams_by_id.get(max_team_id, {}).get(
                "name"
            )

        aggregates.append(row_out)

    aggregates.sort(key=lambda row: (row["source"], row["category"], row["display_name"]))
    return aggregates


def persist_league_aggregates(
    aggregates: list[dict[str, Any]],
    *,
    season_year: int,
    season_type: int,
    league: str,
) -> int:
    ingested_at = _now()
    with get_connection() as conn:
        conn.execute(
            """
            DELETE FROM league_stat_aggregates
            WHERE season_year = ? AND season_type = ? AND league = ?
            """,
            (season_year, season_type, league),
        )
        conn.executemany(
            """
            INSERT INTO league_stat_aggregates (
                season_year, season_type, league, source, category, name, display_name,
                abbreviation, team_count,
                avg_value, min_value, min_team_espn_id, min_team_name,
                max_value, max_team_espn_id, max_team_name,
                avg_per_game, min_per_game, min_per_game_team_espn_id, min_per_game_team_name,
                max_per_game, max_per_game_team_espn_id, max_per_game_team_name,
                ingested_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?,
                ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?,
                ?
            )
            """,
            [
                (
                    season_year,
                    season_type,
                    league,
                    row["source"],
                    row["category"],
                    row["name"],
                    row["display_name"],
                    row.get("abbreviation"),
                    row["team_count"],
                    row.get("avg_value"),
                    row.get("min_value"),
                    row.get("min_team_espn_id"),
                    row.get("min_team_name"),
                    row.get("max_value"),
                    row.get("max_team_espn_id"),
                    row.get("max_team_name"),
                    row.get("avg_per_game"),
                    row.get("min_per_game"),
                    row.get("min_per_game_team_espn_id"),
                    row.get("min_per_game_team_name"),
                    row.get("max_per_game"),
                    row.get("max_per_game_team_espn_id"),
                    row.get("max_per_game_team_name"),
                    ingested_at,
                )
                for row in aggregates
            ],
        )
    return len(aggregates)


def rebuild_league_aggregates_from_db(
    season_year: int = 2026,
    season_type: int = 1,
    league: str = DEFAULT_LEAGUE,
) -> int:
    """Recompute aggregates from stored team snapshots (e.g. after single-team ingest)."""
    teams = ensure_league_teams(league)
    teams_by_id = {team["espn_id"]: team for team in teams}
    league_rows = _load_league_stat_maps(season_year, season_type)
    if not league_rows:
        return 0
    aggregates = compute_league_aggregates(league_rows, teams_by_id)
    return persist_league_aggregates(
        aggregates,
        season_year=season_year,
        season_type=season_type,
        league=league,
    )


def normalize_stat_values(rows: list[dict[str, Any]]) -> None:
    """Round numeric values to 2 decimals before per-game and rank calculations."""
    for row in rows:
        value = row.get("value")
        if isinstance(value, (int, float)):
            normalized = _round2(value)
            row["value"] = normalized
            # Keep display in sync when the field is numeric / mirrors value.
            display = row.get("display_value")
            if display is None or display == "" or _is_numeric_display(display):
                row["display_value"] = f"{normalized:.2f}"

        per_game = row.get("per_game_value")
        if isinstance(per_game, (int, float)):
            row["per_game_value"] = _round2(per_game)


def repair_espn_save_percentage(rows: list[dict[str, Any]]) -> None:
    """
    ESPN core stats often return savePct off by 100x (e.g. 0.0069 instead of 0.69).

    Recompute as saves / (saves + goals conceded), the standard shot-stopping rate.
    """
    by_name: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("source") != "core_statistics":
            continue
        name = row.get("name")
        if name:
            by_name[str(name)] = row

    save_row = by_name.get("savePct")
    saves_row = by_name.get("saves")
    goals_row = by_name.get("goalsConceded")
    if save_row is None or saves_row is None or goals_row is None:
        return

    saves = saves_row.get("value")
    goals = goals_row.get("value")
    if not isinstance(saves, (int, float)) or not isinstance(goals, (int, float)):
        return
    if saves < 0 or goals < 0:
        return

    shots_on_target_faced = float(saves) + float(goals)
    if shots_on_target_faced <= 0:
        save_pct = 0.0
    else:
        save_pct = float(saves) / shots_on_target_faced

    save_row["value"] = _round2(save_pct)
    save_row["display_value"] = f"{save_pct:.2f}"
    save_row["per_game_value"] = None


def repair_espn_penalty_stats(rows: list[dict[str, Any]]) -> None:
    """
    ESPN often leaves penaltyKicksFaced at 0 even when pens were conceded.

    Prefer penaltyKickConceded, else saved + goals conceded, and recompute save %.
    """
    by_name: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("source") != "core_statistics":
            continue
        name = row.get("name")
        if name:
            by_name[str(name)] = row

    faced_row = by_name.get("penaltyKicksFaced")
    conceded_row = by_name.get("penaltyKickConceded")
    goals_row = by_name.get("penaltyGoalsConceded")
    saved_row = by_name.get("penaltyKicksSaved")
    save_pct_row = by_name.get("penaltyKickSavePct")

    def _num(row: dict[str, Any] | None) -> float:
        if row is None:
            return 0.0
        value = row.get("value")
        return float(value) if isinstance(value, (int, float)) else 0.0

    faced = _num(faced_row)
    conceded = _num(conceded_row)
    goals = _num(goals_row)
    saved = _num(saved_row)
    derived_faced = max(conceded, saved + goals, faced)

    if faced_row is not None and derived_faced != faced:
        faced_row["value"] = _round2(derived_faced)
        faced_row["display_value"] = (
            str(int(derived_faced))
            if float(derived_faced).is_integer()
            else f"{derived_faced:.2f}"
        )

    if save_pct_row is not None:
        if derived_faced <= 0:
            save_pct = 0.0
        else:
            save_pct = saved / derived_faced
        save_pct_row["value"] = _round2(save_pct)
        save_pct_row["display_value"] = f"{save_pct:.2f}"
        save_pct_row["per_game_value"] = None


def repair_espn_inaccurate_crosses(rows: list[dict[str, Any]]) -> None:
    """
    ESPN returns inaccurateCrosses as 0 for every club.

    Derive as totalCrosses - accurateCrosses when that residual is positive.
    """
    by_name: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("source") != "core_statistics":
            continue
        name = row.get("name")
        if name:
            by_name[str(name)] = row

    inaccurate_row = by_name.get("inaccurateCrosses")
    total_row = by_name.get("totalCrosses")
    accurate_row = by_name.get("accurateCrosses")
    if inaccurate_row is None or total_row is None or accurate_row is None:
        return

    total = total_row.get("value")
    accurate = accurate_row.get("value")
    if not isinstance(total, (int, float)) or not isinstance(accurate, (int, float)):
        return

    derived = max(0.0, float(total) - float(accurate))
    current = inaccurate_row.get("value")
    if isinstance(current, (int, float)) and abs(float(current) - derived) < 0.005:
        return

    inaccurate_row["value"] = _round2(derived)
    inaccurate_row["display_value"] = (
        str(int(derived)) if float(derived).is_integer() else f"{derived:.2f}"
    )


def _is_numeric_display(display: Any) -> bool:
    if display is None:
        return False
    text = str(display).strip().replace(",", "")
    if text.endswith("%"):
        text = text[:-1].strip()
    if text.startswith("+"):
        text = text[1:]
    try:
        float(text)
        return True
    except ValueError:
        return False


def _resolve_games_played(rows: list[dict[str, Any]]) -> float | None:
    preferred_sources = ("standings", "team_record", "core_statistics")
    for source in preferred_sources:
        for row in rows:
            if row.get("source") != source:
                continue
            name = (row.get("name") or "").lower().replace("_", "")
            if name not in _GAMES_PLAYED_NAMES:
                continue
            value = row.get("value")
            if isinstance(value, (int, float)) and value > 0:
                return float(value)
    return None


def _should_compute_per_game(row: dict[str, Any]) -> bool:
    if row.get("value") is None:
        return False
    if row.get("per_game_value") is not None:
        return False

    name = (row.get("name") or "").lower().replace("_", "")
    if name in _GAMES_PLAYED_NAMES:
        return False
    if name in {"homegamesplayed", "awaygamesplayed"}:
        return False

    haystack = " ".join(
        [
            str(row.get("name") or ""),
            str(row.get("display_name") or ""),
            str(row.get("abbreviation") or ""),
        ]
    ).lower()
    # Word-boundary match so "rate" does not skip "accuratePasses".
    for hint in _SKIP_PER_GAME_HINTS:
        if hint == "%":
            if "%" in haystack:
                return False
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(hint)}(?![a-z0-9])", haystack):
            return False
    return True


def apply_per_game_values(
    rows: list[dict[str, Any]], games_played: float | None = None
) -> float | None:
    games_played = games_played if games_played is not None else _resolve_games_played(rows)
    if not games_played or games_played <= 0:
        return None

    games_played = _round2(games_played)
    for row in rows:
        if not _should_compute_per_game(row):
            # Still normalize any ESPN-provided per-game values.
            per_game = row.get("per_game_value")
            if isinstance(per_game, (int, float)):
                row["per_game_value"] = _round2(per_game)
            continue
        value = row.get("value")
        if not isinstance(value, (int, float)):
            continue
        row["per_game_value"] = _round2(float(value) / games_played)
    return games_played


def _lower_is_better(row: dict[str, Any]) -> bool:
    haystack = " ".join(
        [
            str(row.get("name") or ""),
            str(row.get("display_name") or ""),
            str(row.get("abbreviation") or ""),
        ]
    ).lower().replace(" ", "").replace("_", "")
    return any(hint.replace(" ", "") in haystack for hint in _LOWER_IS_BETTER_HINTS)


def apply_league_ranks(team_rows: dict[str, list[dict[str, Any]]]) -> int:
    """Assign competition ranks across teams for each comparable stat."""
    buckets: dict[tuple[str, str, str], list[tuple[str, dict[str, Any]]]] = defaultdict(
        list
    )
    for team_id, rows in team_rows.items():
        for row in rows:
            if not isinstance(row.get("value"), (int, float)):
                continue
            buckets[_stat_rank_key(row)].append((team_id, row))

    ranked_stats = 0
    for entries in buckets.values():
        if len(entries) < 2:
            continue
        sample = entries[0][1]
        reverse = not _lower_is_better(sample)
        # Stable sort: value, then team id for ties → competition ranking
        ordered = sorted(
            entries,
            key=lambda item: (float(item[1]["value"]), item[0]),
            reverse=reverse,
        )
        previous_value: float | None = None
        previous_rank = 0
        for index, (_team_id, row) in enumerate(ordered, start=1):
            value = float(row["value"])
            if previous_value is not None and value == previous_value:
                rank = previous_rank
            else:
                rank = index
                previous_rank = rank
                previous_value = value
            row["rank"] = rank
            row["rank_display_value"] = f"{rank}"
            ranked_stats += 1
    return ranked_stats


def upsert_teams(teams: list[dict[str, str]]) -> None:
    init_db()
    with get_connection() as conn:
        conn.executemany(
            """
            INSERT INTO teams (
                espn_id, name, abbreviation, slug, league, logo_url, color, alternate_color
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(espn_id) DO UPDATE SET
                name=excluded.name,
                abbreviation=excluded.abbreviation,
                slug=excluded.slug,
                league=excluded.league,
                logo_url=excluded.logo_url,
                color=excluded.color,
                alternate_color=excluded.alternate_color
            """,
            [
                (
                    team["espn_id"],
                    team["name"],
                    team["abbreviation"],
                    team.get("slug"),
                    team["league"],
                    team.get("logo_url"),
                    team.get("color") or None,
                    team.get("alternate_color") or None,
                )
                for team in teams
            ],
        )


def ensure_league_teams(league: str = DEFAULT_LEAGUE) -> list[dict[str, str]]:
    """Sync Premier League clubs from ESPN into SQLite."""
    try:
        teams = fetch_league_teams(league)
    except Exception:
        # Offline / ESPN failure fallback: keep whatever is already stored.
        existing = get_teams(sync=False)
        if existing:
            return [
                {
                    "espn_id": row["espn_id"],
                    "name": row["name"],
                    "abbreviation": row["abbreviation"],
                    "slug": row.get("slug") or "",
                    "league": row["league"],
                    "logo_url": row.get("logo_url") or "",
                    "color": row.get("color") or "",
                    "alternate_color": row.get("alternate_color") or "",
                }
                for row in existing
            ]
        upsert_teams([LIVERPOOL])
        return [LIVERPOOL]
    upsert_teams(teams)
    return teams


def _persist_team_snapshot(
    team: dict[str, str],
    season_year: int,
    season_type: int,
    collected: list[dict[str, Any]],
    source_counts: dict[str, int],
    errors: list[str],
    games_played: float | None,
    run_id: int | None,
) -> dict[str, Any]:
    ingested_at = _now()
    with get_connection() as conn:
        conn.execute(
            """
            DELETE FROM team_stat_snapshots
            WHERE team_espn_id = ? AND season_year = ? AND season_type = ?
            """,
            (team["espn_id"], season_year, season_type),
        )
        cur = conn.execute(
            """
            INSERT INTO team_stat_snapshots (
                team_espn_id, season_year, season_type, ingested_at, source_count
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                team["espn_id"],
                season_year,
                season_type,
                ingested_at,
                len(source_counts),
            ),
        )
        snapshot_id = int(cur.lastrowid)
        conn.executemany(
            """
            INSERT INTO team_stats (
                snapshot_id, source, category, name, display_name, abbreviation,
                value, display_value, per_game_value, rank, rank_display_value
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    snapshot_id,
                    row["source"],
                    row["category"],
                    row["name"],
                    row["display_name"],
                    row.get("abbreviation"),
                    row.get("value"),
                    row.get("display_value"),
                    row.get("per_game_value"),
                    row.get("rank"),
                    row.get("rank_display_value"),
                )
                for row in collected
            ],
        )

        status = "success" if not errors else ("partial" if collected else "failed")
        detail = {
            "source_counts": source_counts,
            "stat_count": len(collected),
            "games_played": games_played,
            "errors": errors,
            "snapshot_id": snapshot_id,
        }
        if run_id is not None:
            conn.execute(
                """
                UPDATE ingest_runs
                SET finished_at = ?, status = ?, detail_json = ?
                WHERE id = ?
                """,
                (ingested_at, status, json.dumps(detail), run_id),
            )

    return {
        "snapshot_id": snapshot_id,
        "status": status,
        "stat_count": len(collected),
        "games_played": games_played,
        "source_counts": source_counts,
        "errors": errors,
        "ingested_at": ingested_at,
        "team_espn_id": team["espn_id"],
        "season_year": season_year,
        "run_id": run_id,
    }


def collect_team_stats(
    team: dict[str, str],
    season_year: int,
    season_type: int = 1,
    *,
    client: httpx.Client | None = None,
    standings_rows: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int], list[str], float | None]:
    collected: list[dict[str, Any]] = []
    source_counts: dict[str, int] = {}
    errors: list[str] = []

    fetchers: list[tuple[str, Any]] = [
        (
            "core_statistics",
            lambda: fetch_core_team_statistics(
                team["league"],
                season_year,
                team["espn_id"],
                season_type,
                client=client,
            ),
        ),
        (
            "team_record",
            lambda: fetch_team_record(team["league"], team["espn_id"], client=client),
        ),
        (
            "site_statistics",
            lambda: fetch_site_team_statistics(
                team["league"], team["espn_id"], client=client
            ),
        ),
    ]

    for source_name, fetcher in fetchers:
        try:
            rows = fetcher()
            source_counts[source_name] = len(rows)
            collected.extend(rows)
        except Exception as exc:  # noqa: BLE001
            source_counts[source_name] = 0
            errors.append(f"{source_name}: {exc}")

    if standings_rows is not None:
        source_counts["standings"] = len(standings_rows)
        collected.extend(standings_rows)
    else:
        try:
            from app.ingest.espn import fetch_standings_stats

            rows = fetch_standings_stats(
                team["league"], season_year, team["espn_id"], client=client
            )
            source_counts["standings"] = len(rows)
            collected.extend(rows)
        except Exception as exc:  # noqa: BLE001
            source_counts["standings"] = 0
            errors.append(f"standings: {exc}")

    normalize_stat_values(collected)
    repair_espn_save_percentage(collected)
    repair_espn_penalty_stats(collected)
    repair_espn_inaccurate_crosses(collected)
    games_played = apply_per_game_values(collected)
    return collected, source_counts, errors, games_played


def ingest_team_stats(
    team: dict[str, str] | None = None,
    season_year: int = 2026,
    season_type: int = 1,
    *,
    apply_ranks: bool = True,
) -> dict[str, Any]:
    """Fetch one team's endpoints into a SQLite snapshot."""
    teams = ensure_league_teams()
    if team is None:
        team = next((t for t in teams if t["espn_id"] == LIVERPOOL["espn_id"]), teams[0])
    else:
        # Prefer DB/ESPN-synced metadata when available.
        matched = next((t for t in teams if t["espn_id"] == team["espn_id"]), None)
        if matched:
            team = matched
        else:
            upsert_teams([team])

    started = _now()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO ingest_runs (started_at, status, season_year, team_espn_id, detail_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (started, "running", season_year, team["espn_id"], None),
        )
        run_id = int(cur.lastrowid)

    with _client() as client:
        collected, source_counts, errors, games_played = collect_team_stats(
            team, season_year, season_type, client=client
        )

    if apply_ranks:
        # Rank using this team plus any already-stored league snapshots.
        league_rows = _load_league_stat_maps(season_year, season_type)
        league_rows[team["espn_id"]] = collected
        apply_league_ranks(league_rows)
        others = {
            team_id: rows
            for team_id, rows in league_rows.items()
            if team_id != team["espn_id"]
        }
        _rewrite_ranked_snapshots(others, season_year, season_type)

    result = _persist_team_snapshot(
        team,
        season_year,
        season_type,
        collected,
        source_counts,
        errors,
        games_played,
        run_id,
    )
    aggregate_count = rebuild_league_aggregates_from_db(
        season_year=season_year,
        season_type=season_type,
        league=team["league"],
    )
    result["aggregate_count"] = aggregate_count
    return result


def _load_league_stat_maps(
    season_year: int, season_type: int
) -> dict[str, list[dict[str, Any]]]:
    with get_connection() as conn:
        snapshots = conn.execute(
            """
            SELECT id, team_espn_id
            FROM team_stat_snapshots
            WHERE season_year = ? AND season_type = ?
            """,
            (season_year, season_type),
        ).fetchall()
        out: dict[str, list[dict[str, Any]]] = {}
        for snap in snapshots:
            rows = conn.execute(
                """
                SELECT source, category, name, display_name, abbreviation,
                       value, display_value, per_game_value, rank, rank_display_value
                FROM team_stats
                WHERE snapshot_id = ?
                """,
                (snap["id"],),
            ).fetchall()
            out[str(snap["team_espn_id"])] = [dict(row) for row in rows]
    return out


def _rewrite_ranked_snapshots(
    league_rows: dict[str, list[dict[str, Any]]],
    season_year: int,
    season_type: int,
) -> None:
    """Update already-stored teams with newly computed ranks (except caller may rewrite after)."""
    with get_connection() as conn:
        for team_id, rows in league_rows.items():
            snap = conn.execute(
                """
                SELECT id FROM team_stat_snapshots
                WHERE team_espn_id = ? AND season_year = ? AND season_type = ?
                """,
                (team_id, season_year, season_type),
            ).fetchone()
            if snap is None:
                continue
            conn.execute("DELETE FROM team_stats WHERE snapshot_id = ?", (snap["id"],))
            conn.executemany(
                """
                INSERT INTO team_stats (
                    snapshot_id, source, category, name, display_name, abbreviation,
                    value, display_value, per_game_value, rank, rank_display_value
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        snap["id"],
                        row["source"],
                        row["category"],
                        row["name"],
                        row["display_name"],
                        row.get("abbreviation"),
                        row.get("value"),
                        row.get("display_value"),
                        row.get("per_game_value"),
                        row.get("rank"),
                        row.get("rank_display_value"),
                    )
                    for row in rows
                ],
            )


def ingest_league_team_stats(
    season_year: int = 2026,
    season_type: int = 1,
    league: str = DEFAULT_LEAGUE,
) -> dict[str, Any]:
    """Ingest all league teams, then fill rank columns from league-wide comparison."""
    teams = ensure_league_teams(league)
    started = _now()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO ingest_runs (started_at, status, season_year, team_espn_id, detail_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (started, "running", season_year, f"league:{league}", None),
        )
        run_id = int(cur.lastrowid)

    team_results: list[dict[str, Any]] = []
    league_rows: dict[str, list[dict[str, Any]]] = {}
    standings_by_team: dict[str, list[dict[str, Any]]] = {}

    with _client() as client:
        try:
            standings_by_team = fetch_standings_by_team(
                league, season_year, client=client
            )
        except Exception as exc:  # noqa: BLE001
            standings_error = str(exc)
        else:
            standings_error = None

        for team in teams:
            collected, source_counts, errors, games_played = collect_team_stats(
                team,
                season_year,
                season_type,
                client=client,
                standings_rows=standings_by_team.get(team["espn_id"], []),
            )
            if standings_error and "standings" not in {
                e.split(":", 1)[0] for e in errors
            }:
                errors.append(f"standings: {standings_error}")
            league_rows[team["espn_id"]] = collected
            team_results.append(
                {
                    "team_espn_id": team["espn_id"],
                    "name": team["name"],
                    "stat_count": len(collected),
                    "games_played": games_played,
                    "source_counts": source_counts,
                    "errors": errors,
                }
            )

    ranked_values = apply_league_ranks(league_rows)

    teams_by_id = {team["espn_id"]: team for team in teams}
    aggregates = compute_league_aggregates(league_rows, teams_by_id)
    aggregate_count = persist_league_aggregates(
        aggregates,
        season_year=season_year,
        season_type=season_type,
        league=league,
    )

    persisted: list[dict[str, Any]] = []
    for team in teams:
        collected = league_rows[team["espn_id"]]
        meta = next(r for r in team_results if r["team_espn_id"] == team["espn_id"])
        persisted.append(
            _persist_team_snapshot(
                team,
                season_year,
                season_type,
                collected,
                meta["source_counts"],
                meta["errors"],
                meta["games_played"],
                run_id=None,
            )
        )

    finished = _now()
    success_teams = sum(1 for row in persisted if row["status"] != "failed")
    status = (
        "success"
        if success_teams == len(teams)
        else ("partial" if success_teams else "failed")
    )
    detail = {
        "team_count": len(teams),
        "success_teams": success_teams,
        "ranked_stat_values": ranked_values,
        "aggregate_count": aggregate_count,
        "teams": team_results,
    }
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE ingest_runs
            SET finished_at = ?, status = ?, detail_json = ?
            WHERE id = ?
            """,
            (finished, status, json.dumps(detail), run_id),
        )

    return {
        "run_id": run_id,
        "status": status,
        "season_year": season_year,
        "league": league,
        "team_count": len(teams),
        "success_teams": success_teams,
        "ranked_stat_values": ranked_values,
        "aggregate_count": aggregate_count,
        "ingested_at": finished,
        "teams": persisted,
    }


def get_teams(*, sync: bool = True) -> list[dict[str, Any]]:
    if sync:
        ensure_league_teams()
    else:
        init_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT espn_id, name, abbreviation, slug, league, logo_url, color, alternate_color
            FROM teams
            ORDER BY name
            """
        ).fetchall()
    return [dict(row) for row in rows]


# Composite radar profiles — keep in sync with frontend section metrics.
# Metrics default to core_statistics; overrides pick another ESPN source.
PROFILE_METRIC_SOURCES: dict[str, str] = {
    "pointsAgainst": "standings",
}

PROFILE_METRIC_SETS: dict[str, tuple[str, ...]] = {
    "tackle": (
        "totalTackles",
        "inneffectiveTackles",
        "effectiveTackles",
        "tacklePct",
    ),
    "recovery": (
        "totalClearance",
        "defensiveActions",
        "interceptions",
        "recoveries",
    ),
    "defensive": (
        "shotsFaced",
        "pointsAgainst",
        "cleanSheet",
        "blockedShots",
    ),
    "duel": (
        "duelsLost",
        "duels",
        "duelWinPct",
        "duelsWon",
    ),
    "setPieces": (
        "lostCorners",
        "wonCorners",
        "penaltyGoalsConceded",
        "penaltyKickConceded",
    ),
    "discipline": (
        "foulsCommitted",
        "foulsSuffered",
        "redCards",
        "yellowCards",
    ),
    "shotStopping": (
        "saves",
        "savePct",
        "bigChanceSaves",
        "pointsAgainst",
    ),
    "boxCommand": (
        "punches",
        "smothers",
        "crossesCaught",
    ),
    "facingPenalties": (
        "penaltyKickConceded",
        "penaltyKicksSaved",
        "penaltyKickSavePct",
        "penaltyGoalsConceded",
    ),
    "ballControl": (
        "possessionPct",
        "totalPasses",
        "accuratePasses",
        "passPct",
    ),
    "ballSecurity": (
        "inaccuratePasses",
        "timesTackled",
        "recoveries",
        "duelsWon",
    ),
    "crossing": (
        "totalCrosses",
        "accurateCrosses",
        "inaccurateCrosses",
        "crossPct",
    ),
    "longBalls": (
        "totalLongBalls",
        "accurateLongBalls",
        "inaccurateLongBalls",
        "longballPct",
    ),
    "throughBalls": (
        "totalThroughBalls",
        "accurateThroughBalls",
        "inaccurateThroughBalls",
        "throughBallPct",
    ),
    "chancePassing": (
        "shotAssists",
        "goalAssists",
        "bigChanceCreated",
        "avgExpectedGoals",
    ),
    "scoring": (
        "totalGoals",
        "goalAssists",
        "gameWinningGoals",
        "goalConversion",
    ),
    "shooting": (
        "totalShots",
        "shotsOnTarget",
        "shotsOffTarget",
        "shotPct",
    ),
    "chanceCreation": (
        "bigChanceCreated",
        "shotAssists",
        "avgExpectedGoals",
        "headedGoals",
    ),
    "shotVariety": (
        "leftFootedShots",
        "rightFootedShots",
        "freeKickGoals",
        "penaltyKickGoals",
    ),
}

# Section overall ranks = unique 1–20 averages of the listed profile ranks.
PROFILE_SECTION_OVERALLS: dict[str, tuple[str, ...]] = {
    "defense": ("tackle", "recovery", "defensive", "duel"),
    "setPiecesDiscipline": ("setPieces", "discipline"),
    "goalkeeping": ("shotStopping", "boxCommand", "facingPenalties"),
    "possession": ("ballControl", "ballSecurity"),
    "passing": ("crossing", "longBalls", "throughBalls", "chancePassing"),
    "offense": ("scoring", "shooting", "chanceCreation", "shotVariety"),
}


def compute_league_profile_ranks(
    season_year: int = 2026,
    season_type: int = 1,
) -> dict[str, dict[str, int]]:
    """
    Normalize each profile's metric ranks into one unique league rank per team.

    Lower average metric-rank is better. Ties broken by rank-sum, then team id,
    so no two teams share a profile rank.
    """
    league_rows = _load_league_stat_maps(season_year, season_type)
    if not league_rows:
        return {}

    # team -> profile -> list of metric ranks
    team_profile_ranks: dict[str, dict[str, list[int]]] = {
        team_id: {profile: [] for profile in PROFILE_METRIC_SETS}
        for team_id in league_rows
    }

    for team_id, rows in league_rows.items():
        by_name: dict[str, int] = {}
        for row in rows:
            name = row.get("name")
            rank = row.get("rank")
            if not isinstance(rank, int) or not name:
                continue
            expected_source = PROFILE_METRIC_SOURCES.get(
                str(name), "core_statistics"
            )
            if row.get("source") != expected_source:
                continue
            by_name[str(name)] = rank
        for profile, metric_names in PROFILE_METRIC_SETS.items():
            ranks = [by_name[name] for name in metric_names if name in by_name]
            team_profile_ranks[team_id][profile] = ranks

    result: dict[str, dict[str, int]] = {
        team_id: {} for team_id in league_rows
    }

    for profile in PROFILE_METRIC_SETS:
        scored: list[tuple[float, float, str]] = []
        for team_id, profiles in team_profile_ranks.items():
            ranks = profiles[profile]
            if not ranks:
                # Missing data sorts last.
                scored.append((10_000.0, 10_000.0, team_id))
                continue
            avg_rank = sum(ranks) / len(ranks)
            sum_rank = float(sum(ranks))
            scored.append((avg_rank, sum_rank, team_id))

        # Unique ordering: best average first; no shared places.
        scored.sort(key=lambda item: (item[0], item[1], item[2]))
        for index, (_avg, _sum, team_id) in enumerate(scored, start=1):
            result[team_id][profile] = index

    # Overall section ranks from their profile ranks (unique 1–20 each).
    for overall_key, profile_keys in PROFILE_SECTION_OVERALLS.items():
        overall_scored: list[tuple[float, float, str]] = []
        for team_id, profiles in result.items():
            ranks = [profiles[key] for key in profile_keys if key in profiles]
            if not ranks:
                overall_scored.append((10_000.0, 10_000.0, team_id))
                continue
            overall_scored.append(
                (sum(ranks) / len(ranks), float(sum(ranks)), team_id)
            )
        overall_scored.sort(key=lambda item: (item[0], item[1], item[2]))
        for index, (_avg, _sum, team_id) in enumerate(overall_scored, start=1):
            result[team_id][overall_key] = index

    return result


def _ordinal(value: int) -> str:
    mod100 = value % 100
    if 11 <= mod100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def _find_named_stat(
    stats: list[dict[str, Any]], *, source: str, name: str
) -> dict[str, Any] | None:
    for row in stats:
        if row.get("source") == source and row.get("name") == name:
            return row
    return None


def build_team_snapshot_header(
    team: dict[str, Any], stats: list[dict[str, Any]]
) -> dict[str, Any]:
    """Compose the Team Profile headline: name · pos · pts · W-D-L * next match."""
    rank_row = _find_named_stat(stats, source="standings", name="rank") or _find_named_stat(
        stats, source="team_record", name="rank"
    )
    points_row = _find_named_stat(
        stats, source="standings", name="points"
    ) or _find_named_stat(stats, source="team_record", name="points")
    record_row = _find_named_stat(
        stats, source="standings", name="overall"
    ) or _find_named_stat(stats, source="team_record", name="summary")

    position: str | None = None
    position_rank: int | None = None
    if rank_row and isinstance(rank_row.get("value"), (int, float)):
        position_rank = int(rank_row["value"])
        position = _ordinal(position_rank)

    points: str | None = None
    if points_row and isinstance(points_row.get("value"), (int, float)):
        pts_value = float(points_row["value"])
        pts_text = str(int(pts_value)) if pts_value.is_integer() else f"{pts_value:.2f}"
        points = f"{pts_text} pts"

    record = None
    if record_row and record_row.get("display_value"):
        record = str(record_row["display_value"])

    team_name = str(team.get("name") or "Team")
    headline = " ".join(
        [
            team_name,
            position or "—",
            points or "—",
            record or "—",
        ]
    )

    return {
        "headline": headline,
        "team_name": team_name,
        "position": position,
        "position_rank": position_rank,
        "points": points,
        "record": record,
    }


def get_team_profile(team_espn_id: str, season_year: int = 2026) -> dict[str, Any] | None:
    ensure_league_teams()
    with get_connection() as conn:
        team = conn.execute(
            """
            SELECT espn_id, name, abbreviation, slug, league, logo_url, color, alternate_color
            FROM teams WHERE espn_id = ?
            """,
            (team_espn_id,),
        ).fetchone()
        if team is None:
            return None

        snapshot = conn.execute(
            """
            SELECT id, season_year, season_type, ingested_at, source_count
            FROM team_stat_snapshots
            WHERE team_espn_id = ? AND season_year = ?
            ORDER BY ingested_at DESC
            LIMIT 1
            """,
            (team_espn_id, season_year),
        ).fetchone()

        stats: list[dict[str, Any]] = []
        if snapshot is not None:
            stats = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT source, category, name, display_name, abbreviation,
                           value, display_value, per_game_value, rank, rank_display_value
                    FROM team_stats
                    WHERE snapshot_id = ?
                    ORDER BY source, category, display_name
                    """,
                    (snapshot["id"],),
                ).fetchall()
            ]

    team_dict = dict(team)
    return {
        "team": team_dict,
        "season_year": season_year,
        "snapshot": dict(snapshot) if snapshot else None,
        "stats": stats,
        "aggregates": get_league_average_profile(season_year=season_year).get(
            "aggregates", []
        ),
        "profile_ranks": compute_league_profile_ranks(season_year=season_year).get(
            str(team_espn_id), {}
        ),
        "header": build_team_snapshot_header(team_dict, stats),
        "view": "team",
    }


def get_league_average_profile(
    season_year: int = 2026,
    season_type: int = 1,
    league: str = DEFAULT_LEAGUE,
) -> dict[str, Any]:
    """League min / max / average profile for the Average top-bar view."""
    init_db()
    with get_connection() as conn:
        meta = conn.execute(
            """
            SELECT ingested_at, COUNT(*) AS stat_count
            FROM league_stat_aggregates
            WHERE season_year = ? AND season_type = ? AND league = ?
            """,
            (season_year, season_type, league),
        ).fetchone()
        rows = conn.execute(
            """
            SELECT source, category, name, display_name, abbreviation, team_count,
                   avg_value, min_value, min_team_espn_id, min_team_name,
                   max_value, max_team_espn_id, max_team_name,
                   avg_per_game, min_per_game, min_per_game_team_espn_id, min_per_game_team_name,
                   max_per_game, max_per_game_team_espn_id, max_per_game_team_name
            FROM league_stat_aggregates
            WHERE season_year = ? AND season_type = ? AND league = ?
            ORDER BY source, category, display_name
            """,
            (season_year, season_type, league),
        ).fetchall()

    aggregates = [dict(row) for row in rows]
    ingested_at = meta["ingested_at"] if meta and meta["stat_count"] else None
    return {
        "view": "average",
        "season_year": season_year,
        "league": league,
        "team": {
            "espn_id": "__average__",
            "name": "League Average",
            "abbreviation": "AVG",
            "slug": "league-average",
            "league": league,
            "logo_url": None,
            "color": None,
            "alternate_color": None,
        },
        "snapshot": (
            {
                "id": None,
                "season_year": season_year,
                "season_type": season_type,
                "ingested_at": ingested_at,
                "source_count": None,
                "stat_count": len(aggregates),
            }
            if ingested_at
            else None
        ),
        "aggregates": aggregates,
        "stats": [],
        "header": {
            "headline": "League Average",
            "team_name": "League Average",
            "position": None,
            "position_rank": None,
            "points": None,
            "record": None,
        },
    }
