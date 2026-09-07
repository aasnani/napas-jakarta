"""TTL-backed runtime data access for a sleeping, database-backed deployment.

The web process keeps a packaged CSV snapshot so a database outage does not
make the demo unusable. When PostgreSQL is configured, this repository polls
it at a bounded interval and refreshes the in-process lists in place; callers
that already imported those lists therefore see new ingestion results without
requiring a process restart or redeploy.
"""

from __future__ import annotations

import os
from pathlib import Path
from threading import RLock
from time import monotonic

from .data import load_documents, load_measurements
from .history import load_historical_city
from .models import Document, Measurement


class RuntimeRepository:
    """Read local fallback files and optionally refresh from Railway Postgres."""

    def __init__(self, data_dir: str | Path, dsn: str = "", ttl_seconds: float | None = None):
        self.data_dir = Path(data_dir)
        self.dsn = dsn.strip()
        configured_ttl = ttl_seconds
        if configured_ttl is None:
            configured_ttl = float(os.getenv("RUNTIME_REFRESH_TTL_SECONDS", "60"))
        self.ttl_seconds = max(5.0, configured_ttl)
        self._lock = RLock()
        self._measurements: list[Measurement] | None = None
        self._historical: list[dict] | None = None
        self._measurement_checked_at = 0.0
        self._historical_checked_at = 0.0
        self.last_measurement_source = "local"
        self.last_historical_source = "local"
        self.last_database_error: str | None = None

    def documents(self) -> list[Document]:
        return load_documents(self.data_dir / "docs")

    def _local_measurements(self) -> list[Measurement]:
        processed = self.data_dir / "processed" / "measurements.csv"
        path = processed if processed.exists() else self.data_dir / "demo" / "measurements.csv"
        return load_measurements(path)

    def _local_historical(self) -> list[dict]:
        return load_historical_city(self.data_dir / "processed" / "historical_city_air_quality.csv")

    def measurements(self, force: bool = False) -> list[Measurement]:
        with self._lock:
            now = monotonic()
            if (
                not force
                and self._measurements is not None
                and now - self._measurement_checked_at < self.ttl_seconds
            ):
                return list(self._measurements)
            local = self._local_measurements()
            selected = local
            source = "local"
            self.last_database_error = None
            if self.dsn:
                try:
                    from .db import load_measurements_from_db

                    stored = load_measurements_from_db(self.dsn)
                    if stored:
                        selected = stored
                        source = "postgres"
                except (ImportError, OSError, RuntimeError, ValueError) as exc:
                    self.last_database_error = str(exc)
            self._measurements = selected
            self._measurement_checked_at = now
            self.last_measurement_source = source
            return list(selected)

    def historical(self, force: bool = False) -> list[dict]:
        with self._lock:
            now = monotonic()
            if (
                not force
                and self._historical is not None
                and now - self._historical_checked_at < self.ttl_seconds
            ):
                return list(self._historical)
            local = self._local_historical()
            selected = local
            source = "local"
            if self.dsn:
                try:
                    from .db import load_historical_city_from_db

                    stored = load_historical_city_from_db(self.dsn)
                    if stored:
                        selected = stored
                        source = "postgres"
                except (ImportError, OSError, RuntimeError, ValueError) as exc:
                    self.last_database_error = str(exc)
            self._historical = selected
            self._historical_checked_at = now
            self.last_historical_source = source
            return list(selected)

