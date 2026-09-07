"""Historical city-level series used for honest long-range trend context."""

from __future__ import annotations

import csv
from datetime import date, timedelta
from itertools import pairwise
from math import sqrt
from pathlib import Path
from statistics import median


def load_historical_city(
    path: str | Path = "data/processed/historical_city_air_quality.csv",
) -> list[dict]:
    """Load the public Zenodo/Open-Meteo-derived Jakarta city series.

    This is deliberately separate from station observations: it is a city
    aggregate, not an official SPKU reading, and must be labelled accordingly.
    """
    file_path = Path(path)
    if not file_path.exists():
        return []
    rows = []
    with file_path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if not row.get("date") or (
                row.get("pm2_5") in (None, "") and row.get("pm10") in (None, "")
            ):
                continue
            try:
                rows.append(
                    {
                        "date": date.fromisoformat(row["date"]),
                        "pm2_5": float(row["pm2_5"])
                        if row.get("pm2_5") not in (None, "")
                        else None,
                        "pm10": float(row["pm10"]) if row.get("pm10") not in (None, "") else None,
                        "pm25_available": row.get("pm2_5") not in (None, ""),
                        "pm10_available": row.get("pm10") not in (None, ""),
                        "us_aqi": float(row["us_aqi"]) if row.get("us_aqi") else None,
                        "source": row.get("source") or "Zenodo/Open-Meteo CAMS city series",
                    }
                )
            except ValueError:
                continue
    return rows


def historical_series_metadata(rows: list[dict]) -> dict[str, object]:
    """Describe pollutant availability without deriving one series from another.

    The quality flags are deliberately conservative diagnostics for this
    city-model series.  They catch an accidental shared-column/alias mapping
    and material violations of the expected PM10 >= PM2.5 relationship without
    treating a high correlation alone as proof of a mapping error.
    """
    paired = [row for row in rows if row.get("pm2_5") is not None and row.get("pm10") is not None]
    pairs = [(float(row["pm2_5"]), float(row["pm10"])) for row in paired]
    identical = sum(pm25 == pm10 for pm25, pm10 in pairs)
    below = sum(pm10 < pm25 for pm25, pm10 in pairs)
    pearson = _pearson([pm25 for pm25, _ in pairs], [pm10 for _, pm10 in pairs])
    identical_fraction = identical / len(paired) if paired else 0.0
    below_fraction = below / len(paired) if paired else 0.0
    mean_abs_diff = (
        sum(abs(pm10 - pm25) for pm25, pm10 in pairs) / len(pairs) if pairs else None
    )
    quality_flags: list[str] = []
    if paired and identical_fraction >= 0.99:
        quality_flags.append("near_identity")
    if paired and below_fraction > 0.05:
        quality_flags.append("pm10_below_pm25_rate")
    # A near-perfect correlation is normal for co-varying pollutants; only
    # pair it with a near-zero absolute difference to flag likely aliasing.
    if pearson is not None and pearson >= 0.99999 and (mean_abs_diff or 0.0) < 0.01:
        quality_flags.append("near_perfect_shared_series")
    return {
        "rows": len(rows),
        "pm25_available": any(row.get("pm2_5") is not None for row in rows),
        "pm10_available": any(row.get("pm10") is not None for row in rows),
        "paired_rows": len(paired),
        "identical_paired_rows": identical,
        "identical_paired_fraction": identical_fraction,
        "pm10_below_pm25_rows": below,
        "pm10_below_pm25_fraction": below_fraction,
        "pearson_correlation": pearson,
        "mean_absolute_difference": mean_abs_diff,
        "quality_flags": quality_flags,
        "sources": sorted({str(row.get("source", "")) for row in rows if row.get("source")}),
    }


def historical_series_diagnostics(rows: list[dict], recent_days: int = 92) -> dict[str, object]:
    """Return human-facing quality and provenance diagnostics for the series.

    ``recent_days`` is a calendar window ending on the newest available date;
    it is intentionally independent of row count so missing dates do not get
    presented as observations.  The continuity diagnostic reports the largest
    date gap and the source at either side of it, when available.
    """
    valid_rows = [row for row in rows if isinstance(row.get("date"), date)]
    if not valid_rows:
        return {
            "whole": _paired_diagnostics([]),
            "recent": _paired_diagnostics([]),
            "recent_start": None,
            "recent_end": None,
            "continuity_gap": None,
        }

    latest = max(row["date"] for row in valid_rows)
    recent_start = latest - timedelta(days=max(1, recent_days) - 1)
    recent_rows = [row for row in valid_rows if recent_start <= row["date"] <= latest]

    dates = sorted({row["date"] for row in valid_rows})
    largest_gap: dict[str, object] | None = None
    for before, after in pairwise(dates):
        missing_days = (after - before).days - 1
        if missing_days <= 0:
            continue
        candidate = {
            "missing_days": missing_days,
            "start": before + timedelta(days=1),
            "end": after - timedelta(days=1),
            "before": before,
            "after": after,
            "before_source": _source_for_date(valid_rows, before),
            "after_source": _source_for_date(valid_rows, after),
        }
        if largest_gap is None or missing_days > int(largest_gap["missing_days"]):
            largest_gap = candidate

    return {
        "whole": _paired_diagnostics(valid_rows),
        "recent": _paired_diagnostics(recent_rows),
        "recent_start": recent_start,
        "recent_end": latest,
        "recent_days": max(1, recent_days),
        "continuity_gap": largest_gap,
    }


def _paired_diagnostics(rows: list[dict]) -> dict[str, object]:
    """Compute diagnostics for rows where both pollutant values are present."""
    paired = [row for row in rows if row.get("pm2_5") is not None and row.get("pm10") is not None]
    pairs = [(float(row["pm2_5"]), float(row["pm10"])) for row in paired]
    identical = sum(pm25 == pm10 for pm25, pm10 in pairs)
    gaps = [abs(pm10 - pm25) for pm25, pm10 in pairs]
    return {
        "rows": len(rows),
        "paired_rows": len(pairs),
        "identical_paired_rows": identical,
        "pearson_correlation": _pearson(
            [pm25 for pm25, _ in pairs], [pm10 for _, pm10 in pairs]
        ),
        "median_absolute_difference": median(gaps) if gaps else None,
    }


def _source_for_date(rows: list[dict], target: date) -> str | None:
    sources = sorted({str(row.get("source")) for row in rows if row["date"] == target and row.get("source")})
    return ", ".join(sources) if sources else None


def _pearson(left: list[float], right: list[float]) -> float | None:
    """Return Pearson correlation without adding a scientific dependency."""
    if len(left) < 2 or len(left) != len(right):
        return None
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right))
    denominator = sqrt(
        sum((a - left_mean) ** 2 for a in left) * sum((b - right_mean) ** 2 for b in right)
    )
    return numerator / denominator if denominator else None
