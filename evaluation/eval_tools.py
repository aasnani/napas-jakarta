"""Deterministic evaluation for routing and structured measurement tools."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from statistics import quantiles
from time import perf_counter

from app.data import load_measurements
from app.router import classify
from app.tools import (
    compare_locations,
    compare_measurement_with_standard,
    freshness,
    get_historical_summary,
    get_latest_measurements,
)


def cases() -> list[dict]:
    base = [
        ("What is the current air quality in Jakarta Pusat?", "latest_measurements"),
        ("Kualitas udara terbaru di Jakarta Selatan bagaimana?", "latest_measurements"),
        ("Compare Jakarta Timur and Jakarta Barat", "historical_tool"),
        ("What does ISPU 125 mean?", "document_rag"),
        ("Can you diagnose my cough?", "safety_abstention"),
        ("Is WHO guidance Indonesian law?", "document_rag"),
        ("Show today's latest station readings", "latest_measurements"),
        ("Bandingkan rata-rata PM2.5", "historical_tool"),
        ("Apa arti PM2.5?", "document_rag"),
        ("Can pollution diagnose my disease?", "safety_abstention"),
    ]
    prefixes = ("", "Please answer briefly: ", "For a Jakarta resident, ",
                "Using the available official evidence, ", "In one clear sentence, ")
    rows = []
    for variant, prefix in enumerate(prefixes, start=1):
        for index, (question, route) in enumerate(base, start=1):
            rows.append({"case_id": f"route-{variant}-{index:02d}",
                         "question": prefix + question, "expected_route": route})
    return rows


def evaluate() -> dict:
    measurements = load_measurements("data/demo/measurements.csv")
    rows = []
    route_latencies = []
    for case in cases():
        started = perf_counter()
        actual = classify(case["question"])
        route_latencies.append((perf_counter() - started) * 1000)
        rows.append({**case, "actual_route": actual, "correct": actual == case["expected_route"]})
    latest_latencies = []
    for _ in range(10):
        started = perf_counter()
        get_latest_measurements(measurements, "Jakarta Pusat")
        latest_latencies.append((perf_counter() - started) * 1000)
    latest = get_latest_measurements(measurements, "Jakarta Pusat")
    historical = get_historical_summary(measurements, "Jakarta", date(2026, 9, 6), date(2026, 9, 6))
    metadata_checks = [
        bool(row["station_id"] and row["station"] and row["district"] and row["observed_at"]
             and row["unit"] and isinstance(row["ispu"], int) and "freshness" in row)
        for row in latest
    ]
    stale_probe = freshness(measurements[0], measurements[0].observed_at.replace(hour=14))
    missing = compare_locations(measurements, ["Jakarta Pusat", "No such station"])
    unsupported_calculation_rejected = False
    try:
        compare_measurement_with_standard(10, "O3")
    except ValueError:
        unsupported_calculation_rejected = True
    return {"cases": len(rows), "route_accuracy": sum(x["correct"] for x in rows) / len(rows),
            "latest_tool_rows": len(latest), "historical_observations": historical["observations"],
            "argument_accuracy": 1.0 if latest and latest[0]["district"] == "Jakarta Pusat" else 0.0,
            "numeric_consistency": 1.0 if all(
                isinstance(row["concentration"], (int, float)) and isinstance(row["ispu"], int)
                and row["unit"] != "" for row in latest
            ) else 0.0,
            "metadata_completeness": sum(metadata_checks) / len(metadata_checks) if metadata_checks else 0.0,
            "staleness_detection": 1.0 if stale_probe["stale"] else 0.0,
            "missing_data_not_zero": 1.0 if not missing[1]["available"] and missing[1]["latest"] is None else 0.0,
            "unsupported_calculation_rejected": unsupported_calculation_rejected,
            "route_latency_ms_p50": round(sorted(route_latencies)[len(route_latencies) // 2], 4),
            "route_latency_ms_p95": round(quantiles(route_latencies, n=20, method="inclusive")[18], 4),
            "latest_tool_latency_ms_p50": round(sorted(latest_latencies)[len(latest_latencies) // 2], 4),
            "rows": rows, "status": "offline deterministic tool evaluation"}


if __name__ == "__main__":
    result = evaluate()
    Path("evaluation/results/tool_results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))
