"""Railway hourly cron entrypoint for station and daily city-history refreshes.

Railway cron services have one schedule. This process therefore runs the
official station refresh every time and dispatches the more expensive
historical refresh once per UTC day. ``RUN_HISTORICAL=1`` supports a manual
one-off run from Railway's service shell.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

from monitoring.logging import cleanup_expired_interactions, interaction_retention_days

from .flow import run_ingestion
from .historical import refresh_city_history


def main() -> dict[str, object]:
    station_result = run_ingestion(os.getenv("DATA_DIR", "data"))
    configured_hour = int(os.getenv("HISTORICAL_REFRESH_UTC_HOUR", "17"))
    now = datetime.now(UTC)
    run_historical = os.getenv("RUN_HISTORICAL", "").strip().lower() in {"1", "true", "yes"}
    run_historical = run_historical or now.hour == configured_hour
    result: dict[str, object] = {
        "ran_at_utc": now.isoformat(),
        "station_refresh": station_result,
        "historical_refresh_due": run_historical,
    }
    if run_historical:
        result["historical_refresh"] = refresh_city_history(
            os.getenv(
                "HISTORICAL_OUTPUT",
                "data/processed/historical_city_air_quality.csv",
            ),
            past_days=int(os.getenv("HISTORICAL_REFRESH_DAYS", "92")),
        )
    postgres_dsn = os.getenv("POSTGRES_DSN", "").strip()
    if postgres_dsn:
        result["retention_cleanup"] = {
            "retention_days": interaction_retention_days(),
            "deleted_interactions": cleanup_expired_interactions(postgres_dsn),
        }
    print(result)
    return result


if __name__ == "__main__":
    main()
