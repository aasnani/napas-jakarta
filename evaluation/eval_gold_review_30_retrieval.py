"""Evaluate document retrieval against the human-reviewed 30-question set.

The retrieval implementation returns documents, while the review packet labels
specific structure-aware chunks. Metrics rank a relevant chunk by the rank of
its parent document and report exactly which reviewed chunk IDs are covered.
"""

from __future__ import annotations

import csv
import json
import math
import time
from pathlib import Path
from typing import Any

from app.data import load_documents
from app.retrieval import search
from ingestion.chunking import structure_chunks

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "evaluation/gold_review_30_final.jsonl"
CHUNKS = ROOT / "data/index/chunks.jsonl"
OUT_JSON = ROOT / "evaluation/results/retrieval_gold_review_30.json"
OUT_CSV = ROOT / "evaluation/results/retrieval_gold_review_30.csv"
MODES = ("bm25", "dense", "hybrid", "hybrid_rerank")
TOP_K = 5


def load_rows(path: str | Path = PACKET) -> list[dict[str, Any]]:
    """Load the final packet and refuse provisional or incomplete labels."""
    rows = [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != 30:
        raise ValueError(f"human-reviewed packet must contain exactly 30 rows, found {len(rows)}")
    not_reviewed = [
        str(row.get("question_id", "<missing>"))
        for row in rows
        if row.get("review_status") != "human_reviewed"
    ]
    if not_reviewed:
        raise ValueError(
            "evaluation is fail-closed: rows are not human_reviewed: "
            + ", ".join(not_reviewed)
        )
    missing = [
        str(row.get("question_id", "<missing>"))
        for row in rows
        if not row.get("human_relevant_chunk_ids")
    ]
    if missing:
        raise ValueError(
            "evaluation is fail-closed: human_relevant_chunk_ids are missing for: "
            + ", ".join(missing)
        )
    return rows


def load_chunk_rows(path: str | Path = CHUNKS) -> dict[str, dict[str, Any]]:
    return {
        row["chunk_id"]: row
        for row in (
            json.loads(line)
            for line in Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }


def _parent_document_id(chunk_id: str, chunks: dict[str, dict[str, Any]]) -> str:
    chunk = chunks.get(chunk_id)
    if chunk is None:
        raise ValueError(f"human-reviewed chunk does not exist in the corpus: {chunk_id}")
    return str(chunk["document_id"])


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(percentile * len(ordered)) - 1))
    return ordered[index]


def _question_metrics(
    row: dict[str, Any],
    found_documents: list[str],
    chunks: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    relevant_chunks = list(dict.fromkeys(str(item) for item in row["human_relevant_chunk_ids"]))
    relevant_parents = {
        _parent_document_id(chunk_id, chunks) for chunk_id in relevant_chunks
    }
    parent_ranks = {
        document_id: rank
        for rank, document_id in enumerate(found_documents, start=1)
        if document_id in relevant_parents
    }
    covered_chunks = [
        chunk_id
        for chunk_id in relevant_chunks
        if _parent_document_id(chunk_id, chunks) in parent_ranks
    ]
    first_rank = min(parent_ranks.values(), default=None)
    gains = [
        sum(
            _parent_document_id(chunk_id, chunks) == document_id
            for chunk_id in relevant_chunks
        )
        for document_id in found_documents
    ]
    ideal_parent_gains = sorted(
        (
            sum(
                _parent_document_id(chunk_id, chunks) == parent_id
                for chunk_id in relevant_chunks
            )
            for parent_id in relevant_parents
        ),
        reverse=True,
    )
    ideal_gains = ideal_parent_gains[:TOP_K]
    dcg = sum(gain / math.log2(rank + 1) for rank, gain in enumerate(gains, start=1))
    ideal_dcg = sum(
        gain / math.log2(rank + 1)
        for rank, gain in enumerate(ideal_gains, start=1)
    )
    return {
        "question_id": row["question_id"],
        "language": row["language"],
        "topic": row["topic"],
        "human_relevant_chunk_ids": relevant_chunks,
        "human_relevant_parent_document_ids": sorted(relevant_parents),
        "retrieved_document_ids_at_5": found_documents,
        "covered_human_relevant_chunk_ids_at_5": covered_chunks,
        "covered_chunk_count_at_5": len(covered_chunks),
        "human_relevant_chunk_count": len(relevant_chunks),
        "question_hit_at_5": bool(covered_chunks),
        "chunk_recall_at_5": len(covered_chunks) / len(relevant_chunks),
        "first_relevant_rank_at_5": first_rank,
        "reciprocal_rank_at_5": 1 / first_rank if first_rank else 0.0,
        "ndcg_at_5": dcg / ideal_dcg if ideal_dcg else 0.0,
        "multi_source": len(relevant_parents) > 1,
        "multi_source_all_parents_at_5": relevant_parents.issubset(set(found_documents)),
    }


def _aggregate(
    mode: str,
    rows: list[dict[str, Any]],
    question_metrics: list[dict[str, Any]],
    latencies: list[float],
    scope: str = "overall",
    group: str = "all",
) -> dict[str, Any]:
    selected = [
        metrics
        for row, metrics in zip(rows, question_metrics)
        if scope == "overall"
        or (scope == "language" and row["language"] == group)
        or (scope == "topic" and row["topic"] == group)
    ]
    selected_latencies = latencies if scope == "overall" else [
        latency
        for row, latency in zip(rows, latencies)
        if (scope == "language" and row["language"] == group)
        or (scope == "topic" and row["topic"] == group)
    ]
    questions = len(selected)
    relevant_chunks = sum(item["human_relevant_chunk_count"] for item in selected)
    covered_chunks = sum(item["covered_chunk_count_at_5"] for item in selected)
    multi_source = [item for item in selected if item["multi_source"]]
    return {
        "mode": mode,
        "scope": scope,
        "group": group,
        "questions": questions,
        # A hit is over human-labelled chunks, ranked by parent-document rank.
        "hit_rate_at_5": round(
            sum(item["question_hit_at_5"] for item in selected) / questions, 4
        ) if questions else 0.0,
        "question_hit_rate_at_5": round(
            sum(item["question_hit_at_5"] for item in selected) / questions, 4
        ) if questions else 0.0,
        "chunk_recall_at_5": round(covered_chunks / relevant_chunks, 4) if relevant_chunks else 0.0,
        "mrr_at_5": round(sum(item["reciprocal_rank_at_5"] for item in selected) / questions, 4)
        if questions else 0.0,
        "ndcg_at_5": round(sum(item["ndcg_at_5"] for item in selected) / questions, 4)
        if questions else 0.0,
        "p50_latency_ms": round(_percentile(selected_latencies, 0.50), 4),
        "p95_latency_ms": round(_percentile(selected_latencies, 0.95), 4),
        "multi_source_questions": len(multi_source),
        "multi_source_recall_at_5": round(
            sum(item["multi_source_all_parents_at_5"] for item in multi_source) / len(multi_source), 4
        ) if multi_source else None,
        "multi_source_chunk_recall_at_5": round(
            sum(item["chunk_recall_at_5"] for item in multi_source) / len(multi_source), 4
        ) if multi_source else None,
    }


def evaluate() -> dict[str, Any]:
    rows = load_rows()
    chunks = load_chunk_rows()
    documents = load_documents(ROOT / "data/docs")
    for row in rows:
        for chunk_id in row["human_relevant_chunk_ids"]:
            _parent_document_id(str(chunk_id), chunks)
    current_chunk_ids = {
        chunk.chunk_id for document in documents for chunk in structure_chunks(document)
    }
    missing_from_loaded_corpus = sorted(
        {
            str(chunk_id)
            for row in rows
            for chunk_id in row["human_relevant_chunk_ids"]
            if str(chunk_id) not in current_chunk_ids
        }
    )
    if missing_from_loaded_corpus:
        raise ValueError(
            "human-reviewed chunks are absent from loaded corpus: "
            + ", ".join(missing_from_loaded_corpus)
        )

    by_mode: list[dict[str, Any]] = []
    all_details: dict[str, list[dict[str, Any]]] = {}
    all_latencies: dict[str, list[float]] = {}
    for mode in MODES:
        details = []
        latencies = []
        for row in rows:
            started = time.perf_counter()
            retrieved = search(row["question"], documents, mode=mode, top_k=TOP_K)
            latencies.append((time.perf_counter() - started) * 1000)
            details.append(
                _question_metrics(
                    row,
                    [item.document.document_id for item in retrieved],
                    chunks,
                )
            )
        all_details[mode] = details
        all_latencies[mode] = latencies
        overall = _aggregate(mode, rows, details, latencies)
        overall["language_hit_rate_at_5"] = {
            language: _aggregate(mode, rows, details, latencies, "language", language)["hit_rate_at_5"]
            for language in sorted({row["language"] for row in rows})
        }
        overall["topic_hit_rate_at_5"] = {
            topic: _aggregate(mode, rows, details, latencies, "topic", topic)["hit_rate_at_5"]
            for topic in sorted({row["topic"] for row in rows})
        }
        by_mode.append(overall)

    # Primary ranking is chunk recall, then question hit rate, MRR and nDCG;
    # latency is only a tie-break. This avoids overfitting one easy question.
    winner = max(
        by_mode,
        key=lambda item: (
            item["chunk_recall_at_5"],
            item["question_hit_rate_at_5"],
            item["mrr_at_5"],
            item["ndcg_at_5"],
            -item["p50_latency_ms"],
        ),
    )
    segments: list[dict[str, Any]] = []
    for mode in MODES:
        details = all_details[mode]
        for language in sorted({row["language"] for row in rows}):
            segments.append(_aggregate(mode, rows, details, all_latencies[mode], "language", language))
        for topic in sorted({row["topic"] for row in rows}):
            segments.append(_aggregate(mode, rows, details, all_latencies[mode], "topic", topic))

    return {
        "status": "human_reviewed",
        "review_status": "human_reviewed",
        "packet": "evaluation/gold_review_30_final.jsonl",
        "questions": len(rows),
        "human_reviewed_rows": len(rows),
        "relevance_unit": "human_relevant_chunk_ids; rank is parent document rank",
        "top_k": TOP_K,
        "ranking_criteria": [
            "chunk_recall_at_5",
            "question_hit_rate_at_5",
            "mrr_at_5",
            "ndcg_at_5",
            "lower_p50_latency_ms",
        ],
        "selected_mode": winner["mode"],
        "modes": by_mode,
        "segments": segments,
        "per_question": all_details,
    }


def _csv_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return list(payload["modes"]) + list(payload["segments"])


def main() -> None:
    payload = evaluate()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = (
        "mode", "scope", "group", "questions", "hit_rate_at_5",
        "question_hit_rate_at_5", "chunk_recall_at_5", "mrr_at_5", "ndcg_at_5",
        "p50_latency_ms", "p95_latency_ms", "multi_source_questions",
        "multi_source_recall_at_5", "multi_source_chunk_recall_at_5",
    )
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: row.get(key) for key in fields} for row in _csv_rows(payload))
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
