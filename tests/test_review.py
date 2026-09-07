import csv
import json

from evaluation.review_ground_truth import apply_sheet, export_sheet, load_rows


def test_review_sheet_round_trip_preserves_pending_rows(tmp_path):
    source = tmp_path / "seed.jsonl"
    source.write_text(
        json.dumps(
            {
                "id": "a",
                "question": "q",
                "relevant_document_ids": ["doc"],
                "review_status": "seeded_pending_human_review",
            }
        )
        + "\n"
        + json.dumps(
            {
                "id": "b",
                "question": "q2",
                "relevant_document_ids": ["doc2"],
                "review_status": "seeded_pending_human_review",
            }
        )
        + "\n"
    )
    sheet = tmp_path / "review.csv"
    export_sheet(load_rows(source), sheet)
    with sheet.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows[0]["reviewed_relevant_document_ids"] = "doc,doc2"
    with sheet.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    updated, changed = apply_sheet(
        load_rows(source), sheet, "tester", now="2026-01-01T00:00:00+00:00"
    )
    assert changed == 1
    assert updated[0]["review_status"] == "human_reviewed"
    assert updated[0]["relevant_document_ids"] == ["doc", "doc2"]
    assert updated[1]["review_status"] == "seeded_pending_human_review"
