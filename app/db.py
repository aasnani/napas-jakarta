"""Optional PostgreSQL repository for normalized structured measurements."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from .models import Measurement

MEASUREMENT_SCHEMA = """
CREATE TABLE IF NOT EXISTS measurements (
  station_id TEXT NOT NULL,
  station_name TEXT NOT NULL,
  district TEXT NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL,
  pollutant TEXT NOT NULL,
  concentration DOUBLE PRECISION,
  concentration_unit TEXT NOT NULL,
  ispu_value INTEGER NOT NULL,
  ispu_category TEXT NOT NULL,
  source TEXT NOT NULL,
  averaging_period TEXT,
  quality_flag TEXT,
  fetched_at TIMESTAMPTZ,
  PRIMARY KEY (station_id, observed_at, pollutant)
)
;
ALTER TABLE measurements ADD COLUMN IF NOT EXISTS averaging_period TEXT;
ALTER TABLE measurements ADD COLUMN IF NOT EXISTS quality_flag TEXT;
ALTER TABLE measurements ADD COLUMN IF NOT EXISTS fetched_at TIMESTAMPTZ;
"""


def publish_measurements(measurements: Iterable[Measurement], dsn: str) -> int:
    """Upsert normalized observations and return the number published."""
    rows = list(measurements)
    import psycopg

    try:
        with psycopg.connect(dsn) as connection:
            connection.execute(MEASUREMENT_SCHEMA)
            for item in rows:
                connection.execute(
                    """INSERT INTO measurements
                    (station_id, station_name, district, observed_at, pollutant,
                    concentration, concentration_unit, ispu_value, ispu_category, source,
                    averaging_period, quality_flag, fetched_at)
                    VALUES (%(station_id)s, %(station_name)s, %(district)s, %(observed_at)s,
                            %(pollutant)s, %(concentration)s, %(concentration_unit)s,
                        %(ispu_value)s, %(ispu_category)s, %(source)s,
                        %(averaging_period)s, %(quality_flag)s, %(fetched_at)s)
                    ON CONFLICT (station_id, observed_at, pollutant) DO UPDATE SET
                      station_name = EXCLUDED.station_name,
                      district = EXCLUDED.district,
                      concentration = EXCLUDED.concentration,
                      concentration_unit = EXCLUDED.concentration_unit,
                  ispu_value = EXCLUDED.ispu_value,
                  ispu_category = EXCLUDED.ispu_category,
                  source = EXCLUDED.source,
                  averaging_period = EXCLUDED.averaging_period,
                  quality_flag = EXCLUDED.quality_flag,
                  fetched_at = EXCLUDED.fetched_at""",
                    item.__dict__,
                )
            connection.commit()
    except psycopg.Error as exc:
        raise RuntimeError("could not publish measurements to PostgreSQL") from exc
    return len(rows)


def load_measurements_from_db(dsn: str) -> list[Measurement]:
    """Read observations from PostgreSQL; callers should provide a CSV fallback."""
    import psycopg

    try:
        with psycopg.connect(dsn) as connection:
            rows = connection.execute(
                """SELECT station_id, station_name, district, observed_at, pollutant,
                          concentration, concentration_unit, ispu_value, ispu_category, source,
                          averaging_period, quality_flag, fetched_at
                   FROM measurements ORDER BY observed_at DESC"""
            ).fetchall()
    except psycopg.Error as exc:
        raise RuntimeError("could not read measurements from PostgreSQL") from exc
    return [
        Measurement(
            station_id=row[0],
            station_name=row[1],
            district=row[2],
            observed_at=row[3] if isinstance(row[3], datetime) else datetime.fromisoformat(row[3]),
            pollutant=row[4],
            concentration=float(row[5]) if row[5] is not None else None,
            concentration_unit=row[6],
            ispu_value=int(row[7]),
            ispu_category=row[8],
            source=row[9],
            averaging_period=row[10],
            quality_flag=row[11],
            fetched_at=row[12],
        )
        for row in rows
    ]
