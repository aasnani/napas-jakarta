"""Deterministic policy-status data used alongside policy-document retrieval."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


def load_policy_events(path: str | Path = "data/policy_events.json") -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def get_policy_timeline(instrument: str, path: str | Path = "data/policy_events.json") -> dict:
    """Return a policy record without inferring an unstated reason or status."""
    records = load_policy_events(path)
    needle = instrument.lower().strip()
    matches = [
        record
        for record in records
        if needle in (record["instrument_id"] + " " + record["title"]).lower()
    ]
    if not matches:
        raise ValueError(f"No policy record found for {instrument}")
    record = matches[0]
    events = sorted(record.get("events", []), key=lambda item: item["date"])
    return {
        **record,
        "events": events,
        "latest_event": events[-1] if events else None,
        "as_of": datetime.now(UTC).date().isoformat(),
    }


def get_policy_status(
    instrument: str, as_of_date: str | None = None, path: str | Path = "data/policy_events.json"
) -> dict:
    """Return recorded policy status and events known by an optional date."""
    record = get_policy_timeline(instrument, path)
    if as_of_date:
        record = {
            **record,
            "requested_as_of": as_of_date,
            "events": [event for event in record["events"] if event.get("date", "") <= as_of_date],
        }
    return record
