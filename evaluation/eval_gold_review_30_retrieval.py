"""Run local retrieval modes over the pending 30-question packet.

All numbers are provisional machine-suggested measurements.  They must not be
reported as human-reviewed results until the finalizer has accepted an edited
review export.
"""

from __future__ import annotations

import csv
import json
import math
import time
from collections import Counter
from pathlib import Path

from app.data import load_documents
from app.retrieval import search

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "evaluation/gold_review_30_candidates.jsonl"
OUT_JSON = ROOT / "evaluation/results/retrieval_gold_review_30.json"
OUT_CSV = ROOT / "evaluation/results/retrieval_gold_review_30.csv"
MODES = ("bm25", "dense", "hybrid", "hybrid_rerank")


def load_rows() -> list[dict]:
    return [json.loads(line) for line in PACKET.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate() -> dict:
    rows = load_rows()
    documents = load_documents(ROOT / "data/docs")
    by_mode = []
    for mode in MODES:
        hits = 0
        reciprocal = 0.0
        ndcg = 0.0
        latencies = []
        language = Counter()
        language_hits = Counter()
        topic = Counter()
        topic_hits = Counter()
        multi_total = multi_hits = 0
        for row in rows:
            started = time.perf_counter()
            retrieved = search(row["question"], documents, mode=mode, top_k=5)
            latencies.append((time.perf_counter() - started) * 1000)
            expected = set(row["proposed_relevant_source_ids"])
            found = [item.document.document_id for item in retrieved]
            gains = [int(doc_id in expected) for doc_id in found]
            hit = bool(expected.intersection(found))
            hits += int(hit)
            if hit:
                first = next(index for index, doc_id in enumerate(found, 1) if doc_id in expected)
                reciprocal += 1 / first
            ideal_denominator = sum(1 / math.log2(index + 1) for index in range(1, min(len(expected), 5) + 1))
            dcg = sum(gain / math.log2(index + 1) for index, gain in enumerate(gains, 1))
            ndcg += dcg / ideal_denominator if ideal_denominator else 0.0
            language[row["language"]] += 1
            topic[row["topic"]] += 1
            if hit:
                language_hits[row["language"]] += 1
                topic_hits[row["topic"]] += 1
            if len(expected) > 1:
                multi_total += 1
                multi_hits += int(expected.issubset(set(found)))
        summary = {
            "mode": mode,
            "questions": len(rows),
            "hit_rate_at_5": round(hits / len(rows), 4),
            "mrr_at_5": round(reciprocal / len(rows), 4),
            "ndcg_at_5": round(ndcg / len(rows), 4),
            "p50_latency_ms": round(sorted(latencies)[len(latencies) // 2], 4),
            "language_hit_rate_at_5": {key: round(language_hits[key] / count, 4) for key, count in language.items()},
            "topic_hit_rate_at_5": {key: round(topic_hits[key] / count, 4) for key, count in topic.items()},
            "multi_source_recall_at_5": round(multi_hits / multi_total, 4) if multi_total else None,
        }
        by_mode.append(summary)
    return {
        "status": "provisional_machine_suggested",
        "review_status": "pending_human",
        "packet": "evaluation/gold_review_30_candidates.jsonl",
        "questions": len(rows),
        "modes": by_mode,
    }


def main() -> None:
    payload = evaluate()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        fields = ("mode", "questions", "hit_rate_at_5", "mrr_at_5", "ndcg_at_5", "p50_latency_ms", "multi_source_recall_at_5")
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: row.get(key) for key in fields} for row in payload["modes"])
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
