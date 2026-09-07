"""Compare chunking variants with the same retrieval evaluation protocol."""

from __future__ import annotations

import json
from pathlib import Path

from app.data import load_documents
from app.models import Document
from app.retrieval import search
from ingestion.chunking import fixed_chunks, semantic_chunks, structure_chunks


def _chunk_documents(documents: list[Document], variant: str) -> list[Document]:
    builders = {"fixed": fixed_chunks, "structure": structure_chunks, "semantic": semantic_chunks}
    chunks = [chunk for document in documents for chunk in builders[variant](document)]
    return [Document(document_id=chunk.chunk_id, title=chunk.document_id, publisher="chunked",
                     source_url="", section=chunk.section_path, text=chunk.text) for chunk in chunks]


def evaluate() -> list[dict]:
    documents = load_documents("data/docs")
    questions = [json.loads(line) for line in Path("evaluation/ground_truth.jsonl").read_text().splitlines()]
    results = []
    for variant in ("fixed", "structure", "semantic"):
        chunked = _chunk_documents(documents, variant)
        hits, reciprocal_rank = 0, 0.0
        for row in questions:
            retrieved = search(row["question"], chunked, mode="dense", top_k=5)
            for result in retrieved:
                original_id = result.document.document_id.split(":", 1)[0]
                if original_id in row["relevant_document_ids"]:
                    hits += 1
                    reciprocal_rank += 1 / result.rank
                    break
        results.append({"chunker": variant, "retrieval": "dense", "hit_rate_at_5": round(hits / len(questions), 4),
                        "mrr_at_5": round(reciprocal_rank / len(questions), 4), "chunks": len(chunked)})
    return results


if __name__ == "__main__":
    result = evaluate()
    Path("evaluation/results/chunking_results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
