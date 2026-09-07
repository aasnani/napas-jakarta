"""Validate a review export and write the approved 30-row JSONL.

The command is intentionally fail-closed: a packet with a pending or malformed
row cannot be presented as final.  The workbook is a review surface; export its
editable columns to CSV with the headers documented below before finalizing.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ALLOWED_STATUSES = {"Pending", "Approved", "Corrected", "Rejected"}
FINAL_STATUSES = {"Approved", "Corrected", "Rejected"}
REQUIRED_EXPORT_FIELDS = {
    "question_id", "status", "human_relevant_chunk_ids", "reviewer",
    "reviewed_at", "correction_notes",
}
ROOT = Path(__file__).resolve().parents[1]


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def _chunk_map(path: str | Path = ROOT / "data/index/chunks.jsonl") -> dict[str, dict[str, Any]]:
    return {row["chunk_id"]: row for row in load_jsonl(path)}


def validate_packet(rows: list[dict[str, Any]], chunks: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if len(rows) != 30:
        errors.append(f"candidate packet must contain exactly 30 rows, found {len(rows)}")
    seen: set[str] = set()
    for row in rows:
        question_id = str(row.get("question_id", "<missing>"))
        if question_id in seen:
            errors.append(f"duplicate question_id: {question_id}")
        seen.add(question_id)
        if not str(row.get("question", "")).strip():
            errors.append(f"{question_id}: question is blank")
        if row.get("review_status") != "pending_human":
            errors.append(f"{question_id}: packet review_status must be pending_human")
        for item in row.get("proposed_relevant_chunks", []):
            chunk = chunks.get(item.get("chunk_id"))
            if chunk is None:
                errors.append(f"{question_id}: unknown proposed chunk {item.get('chunk_id')}")
            elif item.get("locator") != chunk.get("locator"):
                errors.append(f"{question_id}: proposed locator does not match {item.get('chunk_id')}")
        for mode, evidence in row.get("retrieval_evidence", {}).items():
            for item in evidence:
                chunk_id = item.get("chunk_id")
                if chunk_id and chunk_id not in chunks:
                    errors.append(f"{question_id}/{mode}: unknown evidence chunk {chunk_id}")
                if chunk_id and item.get("locator") != chunks[chunk_id].get("locator"):
                    errors.append(f"{question_id}/{mode}: evidence locator does not match {chunk_id}")
    return errors


def read_review_export(path: str | Path) -> dict[str, dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = REQUIRED_EXPORT_FIELDS - fields
        if missing:
            raise ValueError(f"review export missing columns: {sorted(missing)}")
        result: dict[str, dict[str, str]] = {}
        for raw in reader:
            question_id = (raw.get("question_id") or "").strip()
            if not question_id:
                raise ValueError("review export contains a blank question_id")
            if question_id in result:
                raise ValueError(f"review export contains duplicate question_id: {question_id}")
            result[question_id] = {key: (raw.get(key) or "").strip() for key in REQUIRED_EXPORT_FIELDS}
    return result


def _split_ids(value: str) -> list[str]:
    return [item.strip() for item in value.replace(";", ",").split(",") if item.strip()]


def validate_review_export(
    candidates: list[dict[str, Any]],
    decisions: dict[str, dict[str, str]],
    chunks: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    candidate_ids = {row["question_id"] for row in candidates}
    missing = candidate_ids - decisions.keys()
    extra = decisions.keys() - candidate_ids
    if missing:
        errors.append(f"review export is missing rows: {sorted(missing)}")
    if extra:
        errors.append(f"review export has unknown rows: {sorted(extra)}")
    for question_id, decision in decisions.items():
        status = decision.get("status", "")
        ids = _split_ids(decision.get("human_relevant_chunk_ids", ""))
        if status not in ALLOWED_STATUSES:
            errors.append(f"{question_id}: invalid status {status!r}")
        if status == "Pending":
            errors.append(f"{question_id}: remains Pending; finalization refused")
        if status in {"Approved", "Corrected"} and not ids:
            errors.append(f"{question_id}: {status} requires human_relevant_chunk_ids")
        if status in FINAL_STATUSES and not decision.get("reviewer"):
            errors.append(f"{question_id}: {status} requires reviewer")
        if status in FINAL_STATUSES and not decision.get("reviewed_at"):
            errors.append(f"{question_id}: {status} requires reviewed_at")
        if status == "Rejected" and not decision.get("correction_notes"):
            errors.append(f"{question_id}: Rejected requires correction_notes")
        for chunk_id in ids:
            if chunk_id not in chunks:
                errors.append(f"{question_id}: unknown human chunk {chunk_id}")
    return errors


def finalize(
    candidate_path: str | Path,
    review_export_path: str | Path,
    output_path: str | Path,
) -> list[dict[str, Any]]:
    candidates = load_jsonl(candidate_path)
    chunks = _chunk_map()
    packet_errors = validate_packet(candidates, chunks)
    if packet_errors:
        raise ValueError("candidate packet failed validation:\n" + "\n".join(packet_errors))
    decisions = read_review_export(review_export_path)
    errors = validate_review_export(candidates, decisions, chunks)
    if errors:
        raise ValueError("review export failed validation:\n" + "\n".join(errors))
    output: list[dict[str, Any]] = []
    for candidate in candidates:
        decision = decisions[candidate["question_id"]]
        ids = _split_ids(decision["human_relevant_chunk_ids"])
        human_sources = sorted({chunks[chunk_id]["document_id"] for chunk_id in ids})
        output.append({
            **candidate,
            "proposed_relevant_source_ids": candidate["proposed_relevant_source_ids"],
            "human_relevant_chunk_ids": ids,
            "human_relevant_source_ids": human_sources,
            "review_status": "human_reviewed",
            "review_decision": decision["status"],
            "reviewer": decision["reviewer"],
            "reviewed_at": decision["reviewed_at"],
            "correction_notes": decision["correction_notes"],
        })
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in output), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", default="evaluation/gold_review_30_candidates.jsonl")
    parser.add_argument("--review-export", required=True, help="CSV with the six required editable review columns")
    parser.add_argument("--output", default="evaluation/gold_review_30_final.jsonl")
    args = parser.parse_args()
    rows = finalize(args.candidates, args.review_export, args.output)
    print(json.dumps({"status": "human_reviewed", "rows": len(rows), "output": args.output}, indent=2))


if __name__ == "__main__":
    main()
