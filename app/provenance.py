from __future__ import annotations

import os
from pathlib import Path


def source_manifest(data_dir: str | Path = "data") -> dict:
    root = Path(data_dir)
    sources_path = root / "sources.yaml"
    sources: list[dict] = []
    if sources_path.exists():
        try:
            import yaml

            loaded = yaml.safe_load(sources_path.read_text(encoding="utf-8")) or {}
            sources = loaded if isinstance(loaded, list) else loaded.get("sources", [])
        except (ImportError, OSError, ValueError):
            sources = []
    report_path = root / "ingestion_report.json"
    report = {}
    if report_path.exists():
        import json

        report = json.loads(report_path.read_text(encoding="utf-8"))
    configured = bool(os.getenv("SOURCE_DATA_URL", "").strip())
    structured = {}
    for name in ("policy_instruments.json", "policy_events.json", "study_findings.json"):
        path = root / name
        if path.exists():
            try:
                import json

                structured[name] = len(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError, TypeError):
                structured[name] = 0
    persisted_live = bool(report.get("source") and report["source"] != "committed-demo-snapshot")
    return {
        "mode": "live" if configured or persisted_live else "demo",
        "source_data_url_configured": configured,
        "sources": sources,
        "ingestion_report": report,
        "structured_evidence": structured,
    }


REQUIRED_SOURCE_FIELDS = (
    "id",
    "title",
    "author",
    "jurisdiction",
    "document_type",
    "language",
    "status_as_of",
    "legal_status",
    "retrieved_at",
    "url",
    "checksum",
    "geographic_scope",
    "evidence_strength",
)


def validate_source_manifest(data_dir: str | Path = "data") -> dict:
    """Report missing provenance fields without rejecting useful local data."""
    manifest = source_manifest(data_dir)
    missing = {
        item.get("id", f"row-{index}"): [
            field for field in REQUIRED_SOURCE_FIELDS if not item.get(field)
        ]
        for index, item in enumerate(manifest["sources"], 1)
    }
    missing = {key: fields for key, fields in missing.items() if fields}
    return {"sources": len(manifest["sources"]), "valid": not missing, "missing": missing}
