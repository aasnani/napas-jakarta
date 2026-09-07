"""Query-rewriting ablation over the committed ground-truth questions."""

from __future__ import annotations

import json
from pathlib import Path

from app.data import load_documents
from app.rag import rewrite_query
from app.retrieval import search


def evaluate() -> list[dict]:
    documents = load_documents("data/docs")
    questions = [json.loads(line) for line in Path("evaluation/ground_truth.jsonl").read_text().splitlines()]
    result = []
    for mode in ("off", "rules"):
        hits = 0
        for row in questions:
            query = rewrite_query(row["question"], mode)
            retrieved = search(query, documents, mode="dense", top_k=5)
            hits += int(any(x.document.document_id in row["relevant_document_ids"] for x in retrieved))
        result.append({"rewrite_mode": mode, "retrieval": "dense", "hit_rate_at_5": round(hits / len(questions), 4),
                       "questions": len(questions)})
    return result


if __name__ == "__main__":
    result = evaluate()
    Path("evaluation/results/rewrite_results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
