from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from app.models import Measurement


def validate_measurements(measurements: list[Measurement], now: datetime | None = None) -> dict:
    """Validate normalized measurements before they are published."""
    now = now or datetime.now(UTC)
    duplicate_keys = [key for key, count in Counter(
        (item.station_id, item.observed_at, item.pollutant) for item in measurements
    ).items() if count > 1]
    invalid_units = [item.station_id for item in measurements
                     if item.concentration_unit not in {"ug/m3", "µg/m³", "ppm", "ppb"}]
    negative_values = [item.station_id for item in measurements
                     if (item.concentration is not None and item.concentration < 0)
                     or item.ispu_value < 0]
    future_values = [item.station_id for item in measurements
                     if item.observed_at > now]
    errors = {"duplicate_keys": len(duplicate_keys), "invalid_units": len(invalid_units),
              "negative_values": len(negative_values), "future_timestamps": len(future_values)}
    if any(errors.values()):
        raise ValueError(f"measurement validation failed: {errors}")
    return {"accepted": len(measurements), "rejected": 0, "errors": errors,
            "stations": len({item.station_id for item in measurements})}
