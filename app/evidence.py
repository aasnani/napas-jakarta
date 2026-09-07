"""Deterministic access to structured scientific-evidence metadata."""

from __future__ import annotations

import json
from pathlib import Path


def load_study_findings(path: str | Path = "data/study_findings.json") -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def get_source_apportionment(
    pollutant: str = "PM2.5",
    season: str | None = None,
    location: str | None = None,
    path: str | Path = "data/study_findings.json",
) -> list[dict]:
    """Filter study findings without converting study estimates into facts."""
    results = []
    for finding in load_study_findings(path):
        if pollutant.lower() not in finding.get("pollutant", "").lower():
            continue
        if season and season.lower() not in finding.get("season", "").lower():
            continue
        if (
            location
            and location.lower()
            not in (finding.get("location", "") + " " + finding.get("geographic_scope", "")).lower()
        ):
            continue
        results.append(finding)
    return results


def compare_study_findings(
    source_ids: list[str] | None = None, path: str | Path = "data/study_findings.json"
) -> dict:
    findings = load_study_findings(path)
    if source_ids:
        findings = [item for item in findings if item.get("source_id") in source_ids]
    return {
        "findings": findings,
        "comparison_note": "Methods, locations, periods, and limitations differ; no cross-study causal ranking is inferred.",
        "count": len(findings),
    }
