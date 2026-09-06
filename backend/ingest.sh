#!/usr/bin/env bash
# Run league ingest outside the web UI (local or AWS cron / ECS scheduled task).
set -euo pipefail
cd "$(dirname "$0")"
PYTHONPATH=. uv run python -m app.cli ingest --season-year "${SEASON_YEAR:-2026}" "$@"
