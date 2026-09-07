"""Optional Qdrant dense/sparse index adapter.

The application remains dependency-light for evaluation. Installing the
`retrieval` extra enables this adapter for the Compose or cloud deployment.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence

from .chunking import Chunk


def build_qdrant_index(chunks: Sequence[Chunk], url: str = "http://localhost:6333",
                       collection: str = "napas_documents") -> int:
    try:
        from qdrant_client import QdrantClient, models
    except ImportError as exc:
        raise RuntimeError("Install `uv pip install qdrant-client` to build the Qdrant index") from exc
    if not chunks:
        return 0
    try:
        from sentence_transformers import SentenceTransformer
        encoder = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        vectors = [vector.tolist() for vector in encoder.encode(
            [chunk.text for chunk in chunks], normalize_embeddings=True)]
    except ImportError:
        # Keeps local Qdrant smoke tests lightweight; production uses the
        # multilingual encoder when the `retrieval` extra is installed.
        vectors = [_fallback_vector(chunk.text) for chunk in chunks]
    client = QdrantClient(url=url)
    client.recreate_collection(collection_name=collection, vectors_config=models.VectorParams(
        size=len(vectors[0]), distance=models.Distance.COSINE))
    client.upsert(collection_name=collection, points=[
        models.PointStruct(id=index, vector=vector, payload={
            "chunk_id": chunk.chunk_id, "document_id": chunk.document_id,
            "text": chunk.text, "variant": chunk.variant, "title": chunk.title,
            "publisher": chunk.publisher, "language": chunk.language,
            "document_type": chunk.document_type, "effective_date": chunk.effective_date,
            "article_or_clause": chunk.article_or_clause, "page": chunk.page,
            "source_url": chunk.source_url, "checksum": chunk.checksum,
            "source_id": chunk.source_id, "heading_path": chunk.heading_path,
            "paragraph": chunk.paragraph, "previous_chunk_id": chunk.previous_chunk_id,
            "next_chunk_id": chunk.next_chunk_id, "topics": list(chunk.topics),
            "jurisdiction": chunk.jurisdiction, "status": chunk.status,
        }) for index, (chunk, vector) in enumerate(zip(chunks, vectors))])
    return len(chunks)


def build_qdrant_hybrid_index(chunks: Sequence[Chunk], url: str = "http://localhost:6333",
                              dense_collection: str = "napas_documents",
                              sparse_collection: str = "napas_documents_sparse") -> int:
    """Build parallel dense and hashed-sparse collections for RRF fusion.

    Keeping sparse vectors in a separate collection works across Qdrant server
    versions and makes the two first-stage candidate lists independently
    inspectable before application-level reciprocal-rank fusion.
    """
    count = build_qdrant_index(chunks, url, dense_collection)
    from qdrant_client import QdrantClient, models
    client = QdrantClient(url=url)
    vectors = [_fallback_vector(chunk.text) for chunk in chunks]
    client.recreate_collection(collection_name=sparse_collection, vectors_config=models.VectorParams(
        size=len(vectors[0]), distance=models.Distance.DOT))
    client.upsert(collection_name=sparse_collection, points=[
        models.PointStruct(id=index, vector=vector, payload={"chunk_id": chunk.chunk_id,
                         "document_id": chunk.document_id, "text": chunk.text,
                         "variant": chunk.variant, "title": chunk.title,
                         "publisher": chunk.publisher, "language": chunk.language,
                         "document_type": chunk.document_type, "effective_date": chunk.effective_date,
                         "article_or_clause": chunk.article_or_clause, "page": chunk.page,
                         "source_url": chunk.source_url, "checksum": chunk.checksum,
                         "source_id": chunk.source_id, "heading_path": chunk.heading_path,
                         "paragraph": chunk.paragraph, "previous_chunk_id": chunk.previous_chunk_id,
                         "next_chunk_id": chunk.next_chunk_id, "topics": list(chunk.topics),
                         "jurisdiction": chunk.jurisdiction, "status": chunk.status})
        for index, (chunk, vector) in enumerate(zip(chunks, vectors))])
    return count


def qdrant_hybrid_search(query: str, url: str = "http://localhost:6333", top_k: int = 5,
                         dense_collection: str = "napas_documents",
                         sparse_collection: str = "napas_documents_sparse") -> list[dict]:
    """Return RRF-fused candidate payloads from the parallel collections."""
    from qdrant_client import QdrantClient
    client = QdrantClient(url=url)
    dense = client.query_points(dense_collection, query=_fallback_vector(query), limit=top_k).points
    sparse = client.query_points(sparse_collection, query=_fallback_vector(query), limit=top_k).points
    fused: dict[str, dict] = {}
    for rank, point in enumerate([*dense, *sparse], start=1):
        key = point.payload["chunk_id"]
        entry = fused.setdefault(key, {**point.payload, "score": 0.0})
        entry["score"] += 1 / (60 + rank)
    return sorted(fused.values(), key=lambda item: item["score"], reverse=True)[:top_k]


def _fallback_vector(text: str, dimensions: int = 64) -> list[float]:
    values = [0.0] * dimensions
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode()).digest()
        values[int.from_bytes(digest[:2], "big") % dimensions] += 1.0
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]
