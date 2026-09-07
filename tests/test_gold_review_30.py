import csv
import json
from collections import Counter
from pathlib import Path

import pytest

from evaluation.finalize_gold_review import (
    _chunk_map,
    finalize,
    load_jsonl,
    validate_packet,
    validate_review_export,
)

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "evaluation/gold_review_30_candidates.jsonl"
MANIFEST = ROOT / "evaluation/gold_review_30_manifest.json"


def _rows():
    return load_jsonl(PACKET)


def test_exact_shape_quotas_and_unique_ids():
    rows = _rows()
    assert len(rows) == 30
    assert len({row["question_id"] for row in rows}) == 30
    assert all(row["question"].strip() for row in rows)
    assert Counter(row["language"] for row in rows) == {"English": 15, "Bahasa Indonesia": 15}
    assert Counter(row["topic"] for row in rows) == {
        "current_measurements": 4,
        "historical_category_threshold": 5,
        "causes": 4,
        "regulations_implementation": 5,
        "protection_individual_action": 5,
        "multi_turn_followups": 4,
        "missing_data_safety_abstention": 3,
    }
    assert Counter(row["difficulty"] for row in rows) == {"easy": 10, "medium": 12, "hard": 8}


def test_packet_has_resolvable_locators_and_pending_honesty():
    rows = _rows()
    errors = validate_packet(rows, _chunk_map())
    assert errors == []
    for row in rows:
        assert row["review_status"] == "pending_human"
        assert row["human_relevant_chunk_ids"] == []
        assert row["reviewer"] == ""
        assert row["reviewed_at"] == ""
        assert row["correction_notes"] == ""


def test_multi_turn_context_and_separation_from_120():
    rows = _rows()
    multi = [row for row in rows if row["topic"] == "multi_turn_followups"]
    assert len(multi) == 4
    assert all(row["parent_conversation_id"] and row["parent_question"] for row in multi)
    assert len({row["parent_conversation_id"] for row in multi}) == 4
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["candidate_count"] == 30
    assert manifest["development_count"] == 120
    assert not set(manifest["candidate_seed_ids"]).intersection(manifest["development_seed_ids"])
    assert len(set(manifest["candidate_seed_ids"])) == 30
    assert len(set(manifest["development_seed_ids"])) == 120


def _write_export(path: Path, rows, status="Approved", chunk_ids=None):
    fields = ["question_id", "status", "human_relevant_chunk_ids", "reviewer", "reviewed_at", "correction_notes"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "question_id": row["question_id"],
                "status": status,
                "human_relevant_chunk_ids": chunk_ids or row["proposed_relevant_chunks"][0]["chunk_id"],
                "reviewer": "tester",
                "reviewed_at": "2026-09-07",
                "correction_notes": "accepted" if status != "Rejected" else "not supported",
            })


def test_finalizer_refuses_pending_and_accepts_complete_export(tmp_path):
    rows = _rows()
    pending = tmp_path / "pending.csv"
    _write_export(pending, rows[:2], status="Pending")
    decisions = {}
    with pending.open(newline="", encoding="utf-8") as handle:
        decisions = {row["question_id"]: row for row in csv.DictReader(handle)}
    errors = validate_review_export(rows, decisions, _chunk_map())
    assert any("missing rows" in error for error in errors)
    assert any("Pending" in error for error in errors)
    complete = tmp_path / "complete.csv"
    _write_export(complete, rows)
    output = tmp_path / "final.jsonl"
    finalized = finalize(PACKET, complete, output)
    assert len(finalized) == 30
    assert all(row["review_status"] == "human_reviewed" for row in finalized)
    assert output.exists()


def test_finalizer_rejects_unknown_chunk(tmp_path):
    rows = _rows()
    export = tmp_path / "bad.csv"
    _write_export(export, rows, chunk_ids="does-not-exist:structure:99")
    with pytest.raises(ValueError, match="unknown human chunk"):
        finalize(PACKET, export, tmp_path / "final.jsonl")
