"""Refresh the recent city-level history without mixing it with SPKU rows."""

from __future__ import annotations

import csv
import os
from collections import defaultdict
from pathlib import Path

import requests

DEFAULT_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


def refresh_city_history(output: str | Path = "data/processed/historical_city_air_quality.csv",
                         past_days: int = 92) -> dict[str, int | str]:
    """Merge a recent Open-Meteo CAMS window into the committed long history."""
    if not 1 <= past_days <= 92:
        raise ValueError("past_days must be between 1 and 92")
    response = requests.get(
        os.getenv("HISTORICAL_AIR_URL", DEFAULT_URL),
        params={"latitude": -6.2088, "longitude": 106.8456,
                "hourly": "pm2_5,pm10", "past_days": past_days,
                "forecast_days": 0, "timezone": "Asia/Jakarta"},
        timeout=(10, 45),
        headers={"User-Agent": "napas-jakarta/0.1"},
    )
    response.raise_for_status()
    hourly = response.json().get("hourly", {})
    grouped: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for timestamp, pm25, pm10 in zip(hourly.get("time", []), hourly.get("pm2_5", []), hourly.get("pm10", [])):
        day = timestamp[:10]
        if pm25 is not None:
            grouped[day]["pm2_5"].append(float(pm25))
        if pm10 is not None:
            grouped[day]["pm10"].append(float(pm10))
    path = Path(output)
    existing = {}
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            existing = {row["date"]: row for row in csv.DictReader(handle)}
    for day, values in grouped.items():
        row = existing.get(day, {"date": day, "us_aqi": "", "european_aqi": "", "carbon_monoxide": "",
                                 "nitrogen_dioxide": "", "sulphur_dioxide": "", "ozone": "",
                                 "aerosol_optical_depth": "", "dust": "", "uv_index": ""})
        row["pm2_5"] = f"{sum(values['pm2_5']) / len(values['pm2_5']):.6f}" if values["pm2_5"] else row.get("pm2_5", "")
        row["pm10"] = f"{sum(values['pm10']) / len(values['pm10']):.6f}" if values["pm10"] else row.get("pm10", "")
        row["source"] = "Open-Meteo CAMS recent refresh"
        existing[day] = row
    fields = ["date", "pm10", "pm2_5", "carbon_monoxide", "nitrogen_dioxide", "sulphur_dioxide",
              "ozone", "aerosol_optical_depth", "dust", "uv_index", "us_aqi", "european_aqi", "source"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for _, row in sorted(existing.items()))
    return {"days_fetched": len(grouped), "days_total": len(existing), "latest": max(existing) if existing else ""}


if __name__ == "__main__":
    print(refresh_city_history())
