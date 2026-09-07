"""Validate the retrieval benchmark shape before a human review pass."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def validate(path: str | Path = "evaluation/ground_truth.jsonl") -> dict:
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]
    required = {"id", "question", "relevant_document_ids", "intent", "language", "review_status"}
    errors = []
    seen = set()
    for row in rows:
        missing = required - row.keys()
        if missing:
            errors.append(f"{row.get('id', '<unknown>')}: missing {sorted(missing)}")
        if row.get("id") in seen:
            errors.append(f"duplicate id: {row['id']}")
        seen.add(row.get("id"))
        if not row.get("relevant_document_ids"):
            errors.append(f"{row.get('id', '<unknown>')}: no relevant documents")
    result = {"questions": len(rows), "languages": Counter(row.get("language") for row in rows),
              "intents": Counter(row.get("intent") for row in rows),
              "review_status": Counter(row.get("review_status") for row in rows), "errors": errors}
    if errors:
        raise ValueError(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate retrieval benchmark labels")
    parser.add_argument("--input", default="evaluation/ground_truth.jsonl")
    args = parser.parse_args()
    print(json.dumps(validate(args.input), indent=2, ensure_ascii=False, default=dict))
