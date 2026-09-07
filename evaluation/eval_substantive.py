"""Offline checks for substantive routes, evidence diversity, and fallback contracts."""

from __future__ import annotations

import json
from pathlib import Path

from app.data import load_documents, load_measurements
from app.rag import answer
from app.router import classify


def evaluate(
    dataset: str | Path = "evaluation/substantive_ground_truth.jsonl",
    data_dir: str | Path = "data",
) -> dict:
    root = Path(data_dir)
    documents = load_documents(root / "docs")
    measurement_path = root / "processed" / "measurements.csv"
    if not measurement_path.exists():
        measurement_path = root / "demo" / "measurements.csv"
    measurements = load_measurements(measurement_path)
    rows = [json.loads(line) for line in Path(dataset).read_text(encoding="utf-8").splitlines()]
    route_hits = 0
    source_hits = 0
    structure_hits = 0
    outputs = []
    for row in rows:
        actual_route = classify(row["question"])
        result = answer(
            row["question"], documents, measurements, language=row.get("language", "English")
        )
        source_ids = {source["id"] for source in result["sources"]}
        source_ok = all(document_id in source_ids for document_id in row["relevant_document_ids"])
        text = result["answer"]
        structure_ok = all(term.lower() in text.lower() for term in row["required_terms"])
        route_hits += int(actual_route == row["route"] == result["route"])
        source_hits += int(source_ok)
        structure_hits += int(structure_ok)
        outputs.append(
            {
                "id": row["id"],
                "route": actual_route,
                "source_ids": sorted(source_ids),
                "route_ok": actual_route == row["route"],
                "sources_ok": source_ok,
                "structure_ok": structure_ok,
                "citation_complete": result["citation_complete"],
                "citation_grounded": result["citation_grounded"],
            }
        )
    total = len(rows) or 1
    return {
        "questions": len(rows),
        "route_accuracy": round(route_hits / total, 4),
        "preferred_source_recall": round(source_hits / total, 4),
        "fallback_structure_rate": round(structure_hits / total, 4),
        "results": outputs,
        "provider": "offline deterministic fallback; no paid API calls",
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, ensure_ascii=False))
