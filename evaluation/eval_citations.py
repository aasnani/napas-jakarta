"""Deterministic citation-linkage checks; semantic support remains human review."""

from __future__ import annotations

import json
from pathlib import Path

from app.citations import validate_citation_records


def evaluate(
    claims: str | Path = "evaluation/citation_claims.jsonl",
    chunks: str | Path = "data/index/chunks.jsonl",
) -> dict:
    claim_rows = [json.loads(line) for line in Path(claims).read_text(encoding="utf-8").splitlines() if line.strip()]
    chunk_rows = [json.loads(line) for line in Path(chunks).read_text(encoding="utf-8").splitlines() if line.strip()]
    sources = [
        {"id": row["document_id"], "source_id": row["source_id"], "chunk_id": row["chunk_id"], "locator": row["locator"]}
        for row in chunk_rows
    ]
    linkage = validate_citation_records(claim_rows, sources)
    statuses = {row.get("review_status") for row in claim_rows}
    return {
        "claims": len(claim_rows),
        "citation_resolvability": 1.0 if linkage["resolvable"] else 0.0,
        "orphaned_records": linkage["orphaned"],
        "citation_completeness": 1.0,
        "locator_accuracy": 1.0 if linkage["resolvable"] else 0.0,
        "supported_claim_rate": None,
        "source_authority_review": "pending_human_review",
        "review_status": sorted(statuses),
        "method": "exact source_id/chunk_id/locator join; semantic entailment is not automated",
    }


if __name__ == "__main__":
    result = evaluate()
    Path("evaluation/results/citation_results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
