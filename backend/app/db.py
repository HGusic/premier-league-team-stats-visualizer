from __future__ import annotations

import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "app.db"


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, typedef: str) -> None:
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {typedef}")


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                espn_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                abbreviation TEXT NOT NULL,
                slug TEXT,
                league TEXT NOT NULL,
                logo_url TEXT,
                color TEXT,
                alternate_color TEXT
            );

            CREATE TABLE IF NOT EXISTS ingest_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                season_year INTEGER NOT NULL,
                team_espn_id TEXT NOT NULL,
                detail_json TEXT
            );

            CREATE TABLE IF NOT EXISTS team_stat_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_espn_id TEXT NOT NULL,
                season_year INTEGER NOT NULL,
                season_type INTEGER NOT NULL DEFAULT 1,
                ingested_at TEXT NOT NULL,
                source_count INTEGER NOT NULL DEFAULT 0,
                UNIQUE(team_espn_id, season_year, season_type)
            );

            CREATE TABLE IF NOT EXISTS team_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                category TEXT NOT NULL,
                name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                abbreviation TEXT,
                value REAL,
                display_value TEXT,
                per_game_value REAL,
                rank INTEGER,
                rank_display_value TEXT,
                FOREIGN KEY(snapshot_id) REFERENCES team_stat_snapshots(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_team_stats_snapshot
                ON team_stats(snapshot_id);

            CREATE TABLE IF NOT EXISTS league_stat_aggregates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_year INTEGER NOT NULL,
                season_type INTEGER NOT NULL DEFAULT 1,
                league TEXT NOT NULL,
                source TEXT NOT NULL,
                category TEXT NOT NULL,
                name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                abbreviation TEXT,
                team_count INTEGER NOT NULL,
                avg_value REAL,
                min_value REAL,
                min_team_espn_id TEXT,
                min_team_name TEXT,
                max_value REAL,
                max_team_espn_id TEXT,
                max_team_name TEXT,
                avg_per_game REAL,
                min_per_game REAL,
                min_per_game_team_espn_id TEXT,
                min_per_game_team_name TEXT,
                max_per_game REAL,
                max_per_game_team_espn_id TEXT,
                max_per_game_team_name TEXT,
                ingested_at TEXT NOT NULL,
                UNIQUE(season_year, season_type, league, source, name, display_name)
            );

            CREATE INDEX IF NOT EXISTS idx_league_stat_aggregates_season
                ON league_stat_aggregates(season_year, season_type, league);
            """
        )
        _ensure_column(conn, "teams", "color", "TEXT")
        _ensure_column(conn, "teams", "alternate_color", "TEXT")
