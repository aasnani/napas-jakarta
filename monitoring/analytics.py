"""Privacy-preserving aggregate telemetry for the in-app monitoring view.

This module deliberately never returns question text, rewritten queries, or
feedback comments.  PostgreSQL is preferred in deployment; local JSONL is a
small, dependency-free fallback for development and for a database outage.
"""

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def _empty(days: int) -> dict[str, Any]:
    return {
        "window_days": days,
        "source": "no data",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "requests": 0,
            "p50_latency_ms": None,
            "p95_latency_ms": None,
            "citation_rate": None,
            "feedback_total": 0,
            "feedback_positive": 0,
            "feedback_negative": 0,
            "error_count": 0,
            "abstention_count": 0,
            "tokens": 0,
            "estimated_cost_usd": 0.0,
        },
        "requests_by_day": [],
        "latency_by_day": [],
        "routes": [],
        "retrieval_modes": [],
        "feedback": [],
        "usage_by_day": [],
        "conversation_depth": [],
    }


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return round(ordered[index], 2)


def _number(value: object, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _day(value: object) -> str:
    if isinstance(value, datetime):
        return value.astimezone(UTC).date().isoformat() if value.tzinfo else value.date().isoformat()
    text = str(value or "")
    try:
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError:
        return text[:10] if len(text) >= 10 else "unknown"


def _dashboard_from_records(records: list[dict[str, Any]], days: int, source: str) -> dict[str, Any]:
    """Build an aggregate-only dashboard from records with no text access."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    answers: list[dict[str, Any]] = []
    feedback: list[dict[str, Any]] = []
    for record in records:
        event = str(record.get("event") or "answer")
        created = str(record.get("created_at") or "")
        try:
            parsed = datetime.fromisoformat(created)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            if parsed < cutoff:
                continue
        except ValueError:
            # Keep malformed timestamps out of time series and bounded windows.
            continue
        if event == "feedback":
            feedback.append(record)
        elif event == "answer":
            answers.append(record)

    result = _empty(days)
    result["source"] = source
    summary = result["summary"]
    latencies = [_number(row.get("latency_ms")) for row in answers if row.get("latency_ms") is not None]
    grounded = [row for row in answers if row.get("citation_grounded") is not None]
    summary.update(
        {
            "requests": len(answers),
            "p50_latency_ms": _percentile(latencies, 0.50),
            "p95_latency_ms": _percentile(latencies, 0.95),
            "citation_rate": round(sum(bool(row.get("citation_grounded")) for row in grounded) / len(grounded), 4)
            if grounded
            else None,
            "feedback_total": len(feedback),
            "feedback_positive": sum(row.get("feedback") == "positive" for row in feedback),
            "feedback_negative": sum(row.get("feedback") == "negative" for row in feedback),
            "error_count": sum(bool(row.get("error_type")) for row in answers),
            "abstention_count": sum(bool(row.get("abstention_type")) for row in answers),
            "tokens": int(sum(_number(row.get("token_usage")) for row in answers)),
            "estimated_cost_usd": round(sum(_number(row.get("estimated_cost")) for row in answers), 6),
        }
    )

    by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in answers:
        by_day[_day(row.get("created_at"))].append(row)
    for day in sorted(by_day):
        rows = by_day[day]
        day_latencies = [_number(row.get("latency_ms")) for row in rows if row.get("latency_ms") is not None]
        result["requests_by_day"].append({"date": day, "requests": len(rows)})
        result["latency_by_day"].append(
            {
                "date": day,
                "p50_ms": _percentile(day_latencies, 0.50),
                "p95_ms": _percentile(day_latencies, 0.95),
            }
        )
        result["usage_by_day"].append(
            {
                "date": day,
                "tokens": int(sum(_number(row.get("token_usage")) for row in rows)),
                "cost_usd": round(sum(_number(row.get("estimated_cost")) for row in rows), 6),
            }
        )

    routes = Counter(str(row.get("route") or "Unknown") for row in answers)
    retrieval = Counter(str(row.get("retrieval_mode") or "Unknown") for row in answers)
    result["routes"] = [{"name": key, "count": value} for key, value in routes.most_common()]
    result["retrieval_modes"] = [
        {"name": key, "count": value} for key, value in retrieval.most_common()
    ]
    feedback_by_day: dict[str, Counter[str]] = defaultdict(Counter)
    for row in feedback:
        feedback_by_day[_day(row.get("created_at"))][str(row.get("feedback") or "unknown")] += 1
    result["feedback"] = [
        {"date": day, **counts} for day, counts in sorted(feedback_by_day.items())
    ]
    depth: dict[str, list[float]] = defaultdict(list)
    for row in answers:
        if row.get("conversation_turn") is not None:
            depth[_day(row.get("created_at"))].append(_number(row.get("conversation_turn")))
    result["conversation_depth"] = [
        {"date": day, "average_turn": round(sum(values) / len(values), 2)}
        for day, values in sorted(depth.items())
    ]
    return result


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    try:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    records.append(value)
    except OSError:
        return []
    return records


def _from_postgres(dsn: str, days: int) -> dict[str, Any]:
    import psycopg

    # Deliberately select telemetry columns only; question and comment fields
    # never cross the database boundary into the dashboard process.
    with psycopg.connect(dsn) as connection:
        cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        rows = connection.execute(
            """SELECT created_at, event, route, retrieval_mode, citation_grounded,
                      latency_ms, token_usage, estimated_cost, error_type,
                      abstention_type, feedback
               FROM interactions
               WHERE created_at >= %s""",
            (cutoff,),
        ).fetchall()
    records = [
        {
            "created_at": row[0].isoformat() if isinstance(row[0], datetime) else row[0],
            "event": row[1],
            "route": row[2],
            "retrieval_mode": row[3],
            "citation_grounded": row[4],
            "latency_ms": row[5],
            "token_usage": row[6],
            "estimated_cost": row[7],
            "error_type": row[8],
            "abstention_type": row[9],
            "feedback": row[10],
        }
        for row in rows
    ]
    return _dashboard_from_records(records, days, "PostgreSQL aggregates")


def load_dashboard(days: int = 30, *, dsn: str | None = None, path: str | Path | None = None) -> dict[str, Any]:
    """Return a bounded, aggregate-only monitoring snapshot.

    PostgreSQL failures intentionally fall back to local JSONL so monitoring
    can never make the main application unavailable.
    """
    days = max(1, min(int(days), 365))
    configured_dsn = (dsn if dsn is not None else os.getenv("POSTGRES_DSN", "")).strip()
    if configured_dsn:
        try:
            return _from_postgres(configured_dsn, days)
        except Exception:  # noqa: BLE001 - monitoring must degrade gracefully
            fallback = Path(path or os.getenv("MONITORING_DB", "monitoring/interactions.jsonl"))
            return _dashboard_from_records(_read_jsonl(fallback), days, "Local JSONL fallback")
    fallback = Path(path or os.getenv("MONITORING_DB", "monitoring/interactions.jsonl"))
    records = _read_jsonl(fallback)
    return _dashboard_from_records(records, days, "Local JSONL fallback")
