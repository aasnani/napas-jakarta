"""Auditable CSV workflow for promoting seeded retrieval labels to reviewed labels."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SEED_STATUS = "seeded_pending_human_review"
REVIEWED_STATUS = "human_reviewed"
FIELDS = ("id", "question", "language", "intent", "proposed_relevant_document_ids",
          "reviewed_relevant_document_ids", "review_status", "reviewer", "reviewed_at", "notes")


def load_rows(path: str | Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def export_sheet(rows: list[dict[str, Any]], path: str | Path) -> None:
    """Write a spreadsheet-friendly sheet without changing the seed JSONL."""
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "id": row.get("id", ""), "question": row.get("question", ""),
                "language": row.get("language", ""), "intent": row.get("intent", ""),
                "proposed_relevant_document_ids": ",".join(row.get("relevant_document_ids", [])),
                "reviewed_relevant_document_ids": "", "review_status": row.get("review_status", SEED_STATUS),
                "reviewer": "", "reviewed_at": "", "notes": "",
            })


def apply_sheet(rows: list[dict[str, Any]], sheet_path: str | Path,
                reviewer: str, now: str | None = None) -> tuple[list[dict[str, Any]], int]:
    """Apply only non-blank CSV decisions; unanswered rows remain pending."""
    by_id = {row["id"]: row for row in rows}
    changed = 0
    reviewed_at = now or datetime.now(UTC).isoformat()
    with Path(sheet_path).open(newline="", encoding="utf-8") as handle:
        for decision in csv.DictReader(handle):
            row = by_id.get(decision.get("id", ""))
            ids = [item.strip() for item in decision.get("reviewed_relevant_document_ids", "").split(",") if item.strip()]
            if row is None or not ids:
                continue
            row["relevant_document_ids"] = ids
            row["review_status"] = REVIEWED_STATUS
            row["reviewer"] = decision.get("reviewer") or reviewer
            row["reviewed_at"] = decision.get("reviewed_at") or reviewed_at
            if decision.get("notes"):
                row["review_notes"] = decision["notes"]
            changed += 1
    return rows, changed


def write_jsonl(rows: list[dict[str, Any]], path: str | Path) -> None:
    with Path(path).open("w", encoding="utf-8") as handle:
        handle.writelines(
            json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
            for row in rows
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="evaluation/ground_truth.jsonl")
    parser.add_argument("--export", metavar="CSV", help="export a review sheet")
    parser.add_argument("--apply", metavar="CSV", help="apply completed review decisions")
    parser.add_argument("--output", default="evaluation/ground_truth_reviewed.jsonl")
    parser.add_argument("--reviewer", default="", help="reviewer name recorded in applied rows")
    args = parser.parse_args()
    rows = load_rows(args.input)
    if args.export:
        export_sheet(rows, args.export)
        print(f"exported {len(rows)} rows to {args.export}")
    if args.apply:
        if not args.reviewer:
            parser.error("--reviewer is required with --apply")
        rows, changed = apply_sheet(rows, args.apply, args.reviewer)
        write_jsonl(rows, args.output)
        print(f"applied {changed} reviewed rows; wrote {args.output}")
    if not args.export and not args.apply:
        parser.error("choose --export or --apply")


if __name__ == "__main__":
    main()
