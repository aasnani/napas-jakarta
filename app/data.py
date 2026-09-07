from __future__ import annotations

import csv
import hashlib
import re
from datetime import datetime
from pathlib import Path

from .models import Document, Measurement


def district_matches(value: str, requested: str) -> bool:
    """Match portal-prefixed district names to their user-facing Jakarta names."""
    left = " ".join(value.lower().replace("kota adm.", "").split())
    right = " ".join(requested.lower().replace("kota adm.", "").split())
    return left == right or right in left or left in right


def load_measurements(path: str | Path) -> list[Measurement]:
    records: list[Measurement] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            records.append(
                Measurement(
                    station_id=row["station_id"],
                    station_name=row["station_name"],
                    district=row["district"],
                    observed_at=datetime.fromisoformat(row["observed_at"]),
                    pollutant=row["pollutant"],
                    concentration=(
                        float(row["concentration"]) if row["concentration"].strip() else None
                    ),
                    concentration_unit=row["concentration_unit"],
                    ispu_value=int(row["ispu_value"]),
                    ispu_category=row["ispu_category"],
                    source=row["source"],
                    # Preserve an explicit value when supplied; never leave
                    # the tool metadata ambiguous for legacy demo snapshots.
                    averaging_period=row.get("averaging_period") or "unknown",
                    quality_flag=row.get("quality_flag") or None,
                    fetched_at=datetime.fromisoformat(row["fetched_at"])
                    if row.get("fetched_at")
                    else None,
                )
            )
    return records


def load_documents(directory: str | Path) -> list[Document]:
    source_aliases = {
        "ispu": "permen-lhk-14-2020",
        "who-guidance": "who-aqg-2021",
        "jakarta-monitoring": "udara-jakarta",
    }
    manifest_by_id: dict[str, dict] = {}
    manifest_path = Path(directory).parent / "sources.yaml"
    if manifest_path.exists():
        try:
            import yaml

            loaded = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or []
            manifest_by_id = {
                str(item.get("id")): item for item in loaded if isinstance(item, dict) and item.get("id")
            }
        except (ImportError, OSError, ValueError):
            manifest_by_id = {}
    documents: list[Document] = []
    for path in sorted(Path(directory).glob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        title = path.stem.replace("-", " ").title()
        publisher = "Napas Jakarta demo corpus"
        source_url = ""
        metadata: dict[str, str] = {}
        for line in lines[:12]:
            if line.startswith("# "):
                title = line[2:].strip()
            if line.lower().startswith("source:"):
                source_url = line.split(":", 1)[1].strip()
            if line.lower().startswith("publisher:"):
                publisher = line.split(":", 1)[1].strip()
            match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
            if match and match.group(1).lower() not in {"source", "publisher"}:
                metadata[match.group(1).lower()] = match.group(2).strip()
        source_id = metadata.get("source_id", source_aliases.get(path.stem, path.stem))
        manifest_source = manifest_by_id.get(source_id, {})
        language = metadata.get("language", manifest_source.get("language", "id" if "indonesia" in metadata.get("jurisdiction", "").lower() else "en"))
        text = "\n".join(lines)
        documents.append(
            Document(
                document_id=path.stem,
                title=title,
                publisher=publisher,
                source_url=source_url or str(manifest_source.get("url", "")),
                section=path.stem,
                text=text,
                source_id=source_id,
                heading_path=path.stem,
                language=language,
                jurisdiction=metadata.get("jurisdiction", str(manifest_source.get("jurisdiction", ""))),
                status=metadata.get("status", metadata.get("legal_status", str(manifest_source.get("legal_status", "")))),
                effective_date=(
                    str(metadata.get("effective_date", manifest_source.get("effective_date")))
                    if metadata.get("effective_date", manifest_source.get("effective_date")) is not None
                    else None
                ),
                checksum=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                metadata=metadata,
            )
        )
    return documents


def latest_by_station(
    measurements: list[Measurement], pollutant: str = "PM2.5"
) -> list[Measurement]:
    latest: dict[str, Measurement] = {}
    for measurement in measurements:
        if measurement.pollutant != pollutant:
            continue
        previous = latest.get(measurement.station_id)
        if previous is None or measurement.observed_at > previous.observed_at:
            latest[measurement.station_id] = measurement
    return sorted(latest.values(), key=lambda item: item.ispu_value, reverse=True)


def summarize_district(
    measurements: list[Measurement], district: str, pollutant: str = "PM2.5"
) -> dict[str, float | int | str | None]:
    matching = [
        item
        for item in measurements
        if district_matches(item.district, district) and item.pollutant == pollutant
    ]
    selected = [item for item in matching if item.concentration is not None]
    if not matching:
        raise ValueError(f"No {pollutant} observations found for {district}")
    latest = max(matching, key=lambda item: item.observed_at)
    return {
        "district": district,
        "pollutant": pollutant,
        "mean_concentration": (
            round(sum(x.concentration for x in selected) / len(selected), 2) if selected else None
        ),
        # ISPU is independent from raw concentration and remains reportable
        # when every concentration value is missing.
        "max_ispu": max(x.ispu_value for x in matching),
        "latest_ispu": latest.ispu_value,
        "latest_category": latest.ispu_category,
        "latest_observed_at": latest.observed_at.isoformat(),
        "observations": len(matching),
        "missing_concentration_observations": len(matching) - len(selected),
    }
