from __future__ import annotations

from typing import Any

import httpx

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://www.espn.com/",
}

LIVERPOOL = {
    "espn_id": "364",
    "name": "Liverpool",
    "abbreviation": "LIV",
    "slug": "eng.liverpool",
    "league": "eng.1",
    "logo_url": "https://a.espncdn.com/i/teamlogos/soccer/500/364.png",
    "color": "d11317",
    "alternate_color": "FFFFFF",
}

DEFAULT_LEAGUE = "eng.1"


def _client() -> httpx.Client:
    return httpx.Client(headers=HEADERS, timeout=30.0, follow_redirects=True)


def fetch_json(url: str, client: httpx.Client | None = None) -> Any:
    if client is None:
        with _client() as owned:
            response = owned.get(url)
            response.raise_for_status()
            return response.json()
    response = client.get(url)
    response.raise_for_status()
    return response.json()


def fetch_league_teams(league: str = DEFAULT_LEAGUE) -> list[dict[str, str]]:
    """Return all clubs for a league from ESPN's teams endpoint."""
    urls = [
        f"http://site.api.espn.com/apis/site/v2/sports/soccer/{league}/teams",
        f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/teams",
    ]
    payload = None
    last_error: Exception | None = None
    for url in urls:
        try:
            payload = fetch_json(url)
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    if payload is None:
        raise RuntimeError(f"league teams fetch failed: {last_error}")

    sports = payload.get("sports") or []
    leagues = (sports[0].get("leagues") if sports else None) or []
    raw_teams = (leagues[0].get("teams") if leagues else None) or []
    teams: list[dict[str, str]] = []
    for item in raw_teams:
        team = item.get("team") or {}
        logos = team.get("logos") or []
        logo_url = ""
        if logos:
            logo_url = str(logos[0].get("href") or "")
        espn_id = str(team.get("id") or "")
        if not espn_id:
            continue
        color = str(team.get("color") or "").strip().lstrip("#")
        alternate_color = str(team.get("alternateColor") or "").strip().lstrip("#")
        teams.append(
            {
                "espn_id": espn_id,
                "name": str(team.get("displayName") or team.get("name") or espn_id),
                "abbreviation": str(team.get("abbreviation") or ""),
                "slug": str(team.get("slug") or ""),
                "league": league,
                "logo_url": logo_url,
                "color": color,
                "alternate_color": alternate_color,
            }
        )
    teams.sort(key=lambda row: row["name"].lower())
    return teams


def fetch_core_team_statistics(
    league: str,
    season_year: int,
    team_espn_id: str,
    season_type: int = 1,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    url = (
        "https://sports.core.api.espn.com/v2/sports/soccer/"
        f"leagues/{league}/seasons/{season_year}/types/{season_type}/"
        f"teams/{team_espn_id}/statistics"
    )
    payload = fetch_json(url, client=client)
    rows: list[dict[str, Any]] = []
    categories = (payload.get("splits") or {}).get("categories") or []
    for category in categories:
        category_name = category.get("displayName") or category.get("name") or "Unknown"
        for stat in category.get("stats") or []:
            rows.append(
                {
                    "source": "core_statistics",
                    "category": category_name,
                    "name": stat.get("name") or "",
                    "display_name": stat.get("displayName") or stat.get("name") or "",
                    "abbreviation": stat.get("abbreviation"),
                    "value": _as_float(stat.get("value")),
                    "display_value": _as_str(stat.get("displayValue")),
                    "per_game_value": _as_float(stat.get("perGameValue")),
                    "rank": _as_int(stat.get("rank")),
                    "rank_display_value": _as_str(stat.get("rankDisplayValue")),
                }
            )
    return rows


def fetch_team_record(
    league: str, team_espn_id: str, client: httpx.Client | None = None
) -> list[dict[str, Any]]:
    url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{league}/teams/{team_espn_id}"
    payload = fetch_json(url, client=client)
    team = payload.get("team") or {}
    rows: list[dict[str, Any]] = []

    standing_summary = team.get("standingSummary")
    if standing_summary:
        rows.append(
            {
                "source": "team_profile",
                "category": "Profile",
                "name": "standingSummary",
                "display_name": "Standing Summary",
                "abbreviation": None,
                "value": None,
                "display_value": str(standing_summary),
                "per_game_value": None,
                "rank": None,
                "rank_display_value": None,
            }
        )

    for item in (team.get("record") or {}).get("items") or []:
        record_type = item.get("description") or item.get("type") or "Record"
        summary = item.get("summary")
        if summary is not None:
            rows.append(
                {
                    "source": "team_record",
                    "category": record_type,
                    "name": "summary",
                    "display_name": "Record Summary",
                    "abbreviation": None,
                    "value": None,
                    "display_value": str(summary),
                    "per_game_value": None,
                    "rank": None,
                    "rank_display_value": None,
                }
            )
        for stat in item.get("stats") or []:
            rows.append(
                {
                    "source": "team_record",
                    "category": record_type,
                    "name": stat.get("name") or "",
                    "display_name": _titleize(stat.get("name") or ""),
                    "abbreviation": None,
                    "value": _as_float(stat.get("value")),
                    "display_value": _as_str(stat.get("displayValue") or stat.get("value")),
                    "per_game_value": None,
                    "rank": None,
                    "rank_display_value": None,
                }
            )
    return rows


def _standings_rows_from_entry(entry: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, stat in enumerate(entry.get("stats") or [], start=1):
        rows.append(
            {
                "source": "standings",
                "category": "Standings",
                "name": stat.get("name") or f"stat_{idx}",
                "display_name": stat.get("displayName")
                or stat.get("shortDisplayName")
                or stat.get("name")
                or f"Stat {idx}",
                "abbreviation": stat.get("abbreviation"),
                "value": _as_float(stat.get("value")),
                "display_value": _as_str(stat.get("displayValue")),
                "per_game_value": None,
                "rank": None,
                "rank_display_value": None,
            }
        )
    if entry.get("note"):
        rows.append(
            {
                "source": "standings",
                "category": "Standings",
                "name": "note",
                "display_name": "Note",
                "abbreviation": None,
                "value": None,
                "display_value": str(entry["note"]),
                "per_game_value": None,
                "rank": None,
                "rank_display_value": None,
            }
        )
    return rows


def fetch_standings_by_team(
    league: str, season_year: int, client: httpx.Client | None = None
) -> dict[str, list[dict[str, Any]]]:
    """Fetch league standings once; map team espn_id -> standings stat rows."""
    urls = [
        f"http://site.api.espn.com/apis/v2/sports/soccer/{league}/standings?season={season_year}",
        f"https://site.web.api.espn.com/apis/v2/sports/soccer/{league}/standings?season={season_year}",
    ]
    payload = None
    last_error: Exception | None = None
    for url in urls:
        try:
            payload = fetch_json(url, client=client)
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    if payload is None:
        raise RuntimeError(f"standings fetch failed: {last_error}")

    by_team: dict[str, list[dict[str, Any]]] = {}
    for child in payload.get("children") or []:
        entries = ((child.get("standings") or {}).get("entries")) or []
        for entry in entries:
            team = entry.get("team") or {}
            team_id = str(team.get("id") or "")
            if not team_id:
                continue
            by_team[team_id] = _standings_rows_from_entry(entry)
    return by_team


def fetch_standings_stats(
    league: str,
    season_year: int,
    team_espn_id: str,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    by_team = fetch_standings_by_team(league, season_year, client=client)
    return by_team.get(str(team_espn_id), [])


def fetch_site_team_statistics(
    league: str, team_espn_id: str, client: httpx.Client | None = None
) -> list[dict[str, Any]]:
    """Best-effort site/web statistics endpoint (often sparse early season)."""
    url = (
        "https://site.web.api.espn.com/apis/site/v2/sports/soccer/"
        f"{league}/teams/{team_espn_id}/statistics"
    )
    payload = fetch_json(url, client=client)
    rows: list[dict[str, Any]] = []
    results = payload.get("results") or {}
    if not results:
        return rows

    stats = results.get("stats") or results.get("categories") or []
    if isinstance(stats, dict):
        stats = [stats]
    for category in stats:
        category_name = (
            category.get("displayName") or category.get("name") or "Site Statistics"
        )
        for stat in category.get("stats") or category.get("names") or []:
            if isinstance(stat, str):
                continue
            rows.append(
                {
                    "source": "site_statistics",
                    "category": category_name,
                    "name": stat.get("name") or "",
                    "display_name": stat.get("displayName") or stat.get("name") or "",
                    "abbreviation": stat.get("abbreviation"),
                    "value": _as_float(stat.get("value")),
                    "display_value": _as_str(stat.get("displayValue")),
                    "per_game_value": _as_float(stat.get("perGameValue")),
                    "rank": _as_int(stat.get("rank")),
                    "rank_display_value": _as_str(stat.get("rankDisplayValue")),
                }
            )
    return rows


def fetch_team_next_matchup(
    league: str, team_espn_id: str, client: httpx.Client | None = None
) -> dict[str, Any] | None:
    """Return the team's next scheduled matchup from the ESPN team page."""
    url = f"http://site.api.espn.com/apis/site/v2/sports/soccer/{league}/teams/{team_espn_id}"
    payload = fetch_json(url, client=client)
    team = payload.get("team") or {}
    events = team.get("nextEvent") or []
    if not events:
        return None

    event = events[0] if isinstance(events, list) else events
    if not isinstance(event, dict):
        return None

    competitions = event.get("competitions") or []
    competition = competitions[0] if competitions else {}
    competitors = competition.get("competitors") or []
    home_away = None
    opponent_name = None
    opponent_abbr = None
    for competitor in competitors:
        competitor_team = competitor.get("team") or {}
        competitor_id = str(competitor_team.get("id") or competitor.get("id") or "")
        if competitor_id == str(team_espn_id):
            home_away = competitor.get("homeAway")
        else:
            opponent_name = (
                competitor_team.get("displayName")
                or competitor_team.get("shortDisplayName")
                or competitor_team.get("abbreviation")
            )
            opponent_abbr = (
                competitor_team.get("abbreviation")
                or competitor_team.get("shortDisplayName")
                or opponent_name
            )

    if not opponent_name:
        # Fallback from event name like "Fulham at Liverpool"
        opponent_name = event.get("shortName") or event.get("name") or "TBD"
    if not opponent_abbr:
        short_name = str(event.get("shortName") or "")
        # e.g. "FUL @ LIV" → pick the other side later; keep short fallback
        opponent_abbr = short_name.split()[0] if short_name else "TBD"

    venue = "H" if home_away == "home" else "A" if home_away == "away" else "?"
    abbr = str(opponent_abbr).upper()
    matchup_label = f"NXT {venue} {abbr}"

    status = ((competition.get("status") or {}).get("type") or {})
    when_raw = (
        status.get("shortDetail")
        or status.get("detail")
        or event.get("date")
        or competition.get("date")
    )
    when_display = _match_date_only(str(when_raw) if when_raw else None)

    return {
        "label": matchup_label,
        "opponent": opponent_name,
        "opponent_abbreviation": abbr,
        "home_away": home_away,
        "venue": venue,
        "date": event.get("date") or competition.get("date"),
        "when_display": when_display,
        "event_name": event.get("name"),
        "short_name": event.get("shortName"),
    }


def _match_date_only(when: str | None) -> str | None:
    """Keep the date portion and drop kickoff time (e.g. '9/12 - 10:00 AM EDT')."""
    if not when:
        return None
    text = when.strip()
    if " - " in text:
        return text.split(" - ", 1)[0].strip()
    lowered = text.lower()
    at_idx = lowered.find(" at ")
    if at_idx > 0 and any(ch.isdigit() for ch in text[at_idx + 4 : at_idx + 8]):
        return text[:at_idx].strip().rstrip(",")
    # ISO datetime → M/D
    if "T" in text and text[:4].isdigit():
        try:
            date_part = text.split("T", 1)[0]
            year, month, day = date_part.split("-")
            return f"{int(month)}/{int(day)}"
        except ValueError:
            return text
    return text


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _titleize(name: str) -> str:
    spaced = name.replace("_", " ")
    return " ".join(part.capitalize() for part in spaced.split())
