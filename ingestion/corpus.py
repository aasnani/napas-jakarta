"""Reproducible document inventory and structure-aware corpus artifacts.

The application can still run directly from Markdown, but this module is the
single deterministic path used to freeze source identity, chunk IDs, and
provenance diagnostics.  It deliberately reports manifest/local mismatches;
it never silently treats a source summary as a full primary document.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.data import load_documents

from .chunking import Chunk, structure_chunks


def load_sources(path: str | Path) -> list[dict[str, Any]]:
    try:
        import yaml

        value = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []
    except (ImportError, OSError, ValueError):
        return []
    return value if isinstance(value, list) else value.get("sources", [])


def _jsonl_write(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _chunk_row(chunk: Chunk) -> dict[str, Any]:
    row = asdict(chunk)
    row["topics"] = list(chunk.topics)
    row["locator"] = chunk.locator
    return row


def corpus_fingerprint(documents: list, chunks: list[Chunk]) -> str:
    payload = {
        "documents": [
            {"id": doc.document_id, "checksum": doc.checksum, "url": doc.source_url}
            for doc in documents
        ],
        "chunks": [{"id": chunk.chunk_id, "checksum": chunk.checksum} for chunk in chunks],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def build_corpus(data_dir: str | Path = "data") -> dict[str, Any]:
    root = Path(data_dir)
    documents = load_documents(root / "docs")
    chunks = [chunk for document in documents for chunk in structure_chunks(document)]
    manifest = load_sources(root / "sources.yaml")
    manifest_by_id = {str(item.get("id")): item for item in manifest if item.get("id")}
    local_ids = {doc.source_id or doc.document_id for doc in documents}
    manifest_ids = set(manifest_by_id)
    checksums: dict[str, list[str]] = {}
    for item in manifest:
        checksum = str(item.get("checksum", ""))
        if checksum:
            checksums.setdefault(checksum, []).append(str(item.get("id", "")))
    duplicate_manifest_checksums = {
        checksum: ids for checksum, ids in checksums.items() if len(ids) > 1
    }
    rows = []
    for doc in documents:
        source = manifest_by_id.get(doc.source_id or doc.document_id, {})
        rows.append({
            "source_id": doc.source_id or doc.document_id,
            "document_id": doc.document_id,
            "title": doc.title,
            "publisher": doc.publisher,
            "url": doc.source_url,
            "local_path": str((root / "docs" / f"{doc.section}.md").as_posix()),
            "words": len(doc.text.split()),
            "checksum": doc.checksum,
            "manifest_checksum": source.get("checksum", ""),
            "manifest_present": bool(source),
            "status": doc.status,
            "language": doc.language,
            "jurisdiction": doc.jurisdiction,
        })
    _jsonl_write(root / "index" / "documents.jsonl", rows)
    _jsonl_write(root / "index" / "chunks.jsonl", [_chunk_row(chunk) for chunk in chunks])
    report = {
        "schema_version": "corpus-v2",
        "generated_at": datetime.now(UTC).isoformat(),
        "manifest_sources": len(manifest),
        "local_documents": len(documents),
        "local_words": sum(len(doc.text.split()) for doc in documents),
        "chunks": len(chunks),
        "missing_local_documents_for_manifest": sorted(manifest_ids - local_ids),
        "local_documents_not_in_manifest": sorted(local_ids - manifest_ids),
        "duplicate_manifest_checksums": duplicate_manifest_checksums,
        "documents_without_url": sorted(doc.document_id for doc in documents if not doc.source_url),
        "chunk_rejections": [],
        "fingerprint": corpus_fingerprint(documents, chunks),
        "document_sha256": hashlib.sha256("".join(doc.text for doc in documents).encode()).hexdigest(),
        "word_count_method": "Python str.split over normalized UTF-8 Markdown",
        "chunking": {
            "variant": "structure",
            "boundary": "Markdown heading and blank-line paragraph boundaries",
            "max_words": 520,
            "stable_id": "{source_id}:structure:{zero_based_index}",
        },
    }
    (root / "index" / "corpus_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report
