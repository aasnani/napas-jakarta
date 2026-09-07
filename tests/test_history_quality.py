import csv

import pytest

from app.history import (
    historical_series_diagnostics,
    historical_series_metadata,
    load_historical_city,
)


def test_retained_pm_series_have_independent_non_identity_quality() -> None:
    metadata = historical_series_metadata(load_historical_city())

    assert metadata["paired_rows"] == 1387
    assert metadata["identical_paired_rows"] == 1
    assert metadata["identical_paired_fraction"] < 0.01
    assert metadata["pm10_below_pm25_fraction"] < 0.05
    assert metadata["pearson_correlation"] < 0.99999
    assert metadata["quality_flags"] == []


def test_quality_diagnostics_flag_shared_mapping_and_pm10_inversion() -> None:
    rows = [
        {"pm2_5": 10.0, "pm10": 10.0},
        {"pm2_5": 20.0, "pm10": 20.0},
        {"pm2_5": 30.0, "pm10": 30.0},
    ]
    assert "near_identity" in historical_series_metadata(rows)["quality_flags"]
    rows[0]["pm10"] = 9.0
    rows[1]["pm10"] = 19.0
    rows[2]["pm10"] = 29.0
    assert "pm10_below_pm25_rate" in historical_series_metadata(rows)["quality_flags"]


def test_refresh_keeps_upstream_pm_variables_independent(monkeypatch, tmp_path) -> None:
    from ingestion import historical

    captured = {}

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "hourly": {
                    "time": ["2026-09-07T00:00", "2026-09-07T03:00"],
                    "pm2_5": [2.0, 4.0],
                    "pm10": [10.0, 30.0],
                }
            }

    def fake_get(url, **kwargs):
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr(historical.requests, "get", fake_get)
    output = tmp_path / "history.csv"
    historical.refresh_city_history(output, past_days=1)
    with output.open(encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    assert captured["params"]["hourly"] == "pm2_5,pm10"
    assert row["pm2_5"] == "3.000000"
    assert row["pm10"] == "20.000000"


def test_city_series_diagnostics_explain_recent_overlap_and_source_gap() -> None:
    diagnostics = historical_series_diagnostics(load_historical_city())

    whole = diagnostics["whole"]
    recent = diagnostics["recent"]
    assert whole["paired_rows"] == 1387
    assert whole["identical_paired_rows"] == 1
    assert whole["pearson_correlation"] == pytest.approx(0.8833077, abs=1e-6)
    assert whole["median_absolute_difference"] == pytest.approx(16.8, abs=1e-6)
    assert recent["rows"] == 92
    assert recent["pearson_correlation"] == pytest.approx(0.9971980, abs=1e-6)
    assert recent["median_absolute_difference"] == pytest.approx(1.8875, abs=1e-6)

    gap = diagnostics["continuity_gap"]
    assert gap["missing_days"] == 108
    assert gap["start"].isoformat() == "2026-02-19"
    assert gap["end"].isoformat() == "2026-06-06"
