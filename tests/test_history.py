from datetime import date

from app.history import historical_series_metadata, load_historical_city


def test_historical_city_series_has_year_window():
    rows = load_historical_city()
    assert len(rows) > 300
    assert max(row["date"] for row in rows) > date(2026, 1, 1)
    assert min(row["date"] for row in rows) < date(2023, 1, 1)
    assert {row["source"] for row in rows} <= {
        "Zenodo/Open-Meteo CAMS city series",
        "Open-Meteo CAMS recent refresh",
    }
    assert any(row["source"] == "Open-Meteo CAMS recent refresh" for row in rows)


def test_historical_pollutant_metadata_does_not_fabricate_pm10():
    metadata = historical_series_metadata(
        [
            {"date": date(2026, 1, 1), "pm2_5": 20.0, "pm10": None, "source": "test"},
            {"date": date(2026, 1, 2), "pm2_5": 21.0, "pm10": 44.0, "source": "test"},
        ]
    )
    assert metadata["pm25_available"] is True
    assert metadata["pm10_available"] is True
    assert metadata["paired_rows"] == 1
    assert metadata["identical_paired_rows"] == 0
