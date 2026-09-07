import sys
from datetime import UTC, datetime
from types import SimpleNamespace

from app.models import Measurement
from app.runtime_data import RuntimeRepository


def _measurement(value: int) -> Measurement:
    return Measurement(
        station_id="station-1",
        station_name="Station 1",
        district="Jakarta Pusat",
        observed_at=datetime(2026, 9, 7, tzinfo=UTC),
        pollutant="PM2.5",
        concentration=float(value),
        concentration_unit="µg/m³",
        ispu_value=value,
        ispu_category="SEDANG",
        source="official",
    )


def test_runtime_prefers_postgres_and_refreshes_after_ttl(monkeypatch):
    repo = RuntimeRepository("data", "postgres://example", ttl_seconds=5)
    values = [[_measurement(42)], [_measurement(84)]]

    def fake_load(_dsn):
        return values.pop(0)

    monkeypatch.setattr("app.db.load_measurements_from_db", fake_load)
    assert repo.measurements(force=True)[0].ispu_value == 42
    # A normal request within the TTL does not repeat the database query.
    assert repo.measurements()[0].ispu_value == 42
    assert repo.measurements(force=True)[0].ispu_value == 84
    assert repo.last_measurement_source == "postgres"


def test_runtime_falls_back_to_packaged_snapshot_when_database_fails(monkeypatch):
    repo = RuntimeRepository("data", "postgres://example", ttl_seconds=5)

    def fail_load(_dsn):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr("app.db.load_measurements_from_db", fail_load)
    rows = repo.measurements(force=True)
    assert rows
    assert repo.last_measurement_source == "local"
    assert repo.last_database_error == "database unavailable"


def test_publish_historical_city_converts_csv_blanks_to_null(monkeypatch):
    calls = []

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query, params=None):
            calls.append((query, params))

        def commit(self):
            pass

    class FakeError(Exception):
        pass

    fake_psycopg = SimpleNamespace(connect=lambda _dsn: FakeConnection(), Error=FakeError)
    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)
    from app.db import publish_historical_city

    publish_historical_city(
        [{"date": "2026-09-07", "pm10": "", "pm2_5": "12.5", "us_aqi": ""}],
        "postgres://example",
    )
    insert_params = next(params for query, params in calls if "INSERT INTO historical" in query)
    assert insert_params["pm10"] is None
    assert insert_params["pm2_5"] == 12.5
    assert insert_params["us_aqi"] is None
