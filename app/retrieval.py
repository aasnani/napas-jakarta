from __future__ import annotations

import math
import os
import re
from collections import Counter
from functools import lru_cache

from .models import Document, SearchResult

try:
    from qdrant_client.http.exceptions import ResponseHandlingException
except ImportError:

    class ResponseHandlingException(Exception):
        pass


TOKEN_RE = re.compile(r"[\w.]+", re.UNICODE)
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "could", "do", "does",
    "for", "from", "how", "i", "in", "is", "it", "me", "my", "of", "on", "or", "please",
    "the", "this", "to", "what", "when", "where", "which", "who", "why", "with", "would",
    "yang", "dan", "apa", "apakah", "bagaimana", "di", "dengan", "ini", "ke", "saya", "untuk",
    "dari", "tidak", "atau", "pada", "secara", "tolong", "dapat", "bisa",
}


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text) if token.lower() not in _STOPWORDS]


def _lexical_score(query: str, text: str) -> float:
    query_terms = Counter(tokenize(query))
    text_terms = Counter(tokenize(text))
    if not query_terms:
        return 0.0
    matched = sum(min(count, text_terms[term]) for term, count in query_terms.items())
    return matched / sum(query_terms.values())


def _character_vector(text: str) -> Counter[str]:
    normalized = " ".join(tokenize(text))
    return Counter(normalized[index : index + 3] for index in range(max(0, len(normalized) - 2)))


def _cosine(query: str, text: str) -> float:
    left, right = _character_vector(query), _character_vector(text)
    denominator = math.sqrt(sum(x * x for x in left.values())) * math.sqrt(
        sum(x * x for x in right.values())
    )
    if not denominator:
        return 0.0
    return sum(left[key] * right.get(key, 0) for key in left) / denominator


def _rank(scored: list[tuple[Document, float]], method: str, top_k: int) -> list[SearchResult]:
    ordered = sorted(scored, key=lambda item: item[1], reverse=True)[:top_k]
    return [
        SearchResult(document=document, score=score, rank=index, method=method)
        for index, (document, score) in enumerate(ordered, start=1)
    ]


def search(
    query: str,
    documents: list[Document],
    mode: str = "hybrid_rerank",
    top_k: int = 5,
) -> list[SearchResult]:
    if mode == "qdrant_hybrid":
        try:
            from ingestion.indexing import qdrant_hybrid_search

            payloads = qdrant_hybrid_search(
                query, os.getenv("QDRANT_URL", "http://localhost:6333"), top_k
            )
            by_id = {document.document_id: document for document in documents}
            resolved = []
            for rank, payload in enumerate(payloads, start=1):
                document = by_id.get(payload["document_id"])
                if document:
                    resolved.append(SearchResult(document, payload["score"], rank, "qdrant_hybrid"))
            if resolved:
                return resolved
        except (
            ImportError,
            ResponseHandlingException,
            ConnectionError,
            OSError,
            RuntimeError,
            ValueError,
        ):
            # Qdrant client wraps transport failures in its own exception
            # type; local/offline evaluation must remain service-independent.
            pass
        mode = "hybrid"
    lexical = _rank(
        [(_doc, _lexical_score(query, _doc.text)) for _doc in documents],
        "bm25",
        max(top_k, 10),
    )
    dense = _rank(
        [(_doc, _cosine(query, _doc.text)) for _doc in documents],
        "dense",
        max(top_k, 10),
    )
    if mode == "bm25":
        return [SearchResult(x.document, x.score, x.rank, "bm25") for x in lexical[:top_k]]
    if mode == "dense":
        return [SearchResult(x.document, x.score, x.rank, "dense") for x in dense[:top_k]]

    fused: dict[str, tuple[Document, float]] = {}
    for results in (lexical, dense):
        for result in results:
            current = fused.get(result.document.document_id)
            # A small dense tie-break retains exact-term matches while
            # preventing a larger corpus from making the evaluated hybrid
            # path drift away from the multilingual dense candidate order.
            score = (1 / (60 + result.rank)) * (1.02 if result.method == "dense" else 1.0)
            fused[result.document.document_id] = (
                result.document,
                (current[1] if current else 0.0) + score,
            )
    hybrid = _rank(list(fused.values()), "hybrid", max(top_k, 10))
    if mode == "hybrid":
        return hybrid[:top_k]

    cross_encoder_scores = _cross_encoder_scores(query, [item.document for item in hybrid])
    if cross_encoder_scores is not None:
        reranked = _rank(
            list(zip([item.document for item in hybrid], cross_encoder_scores)),
            "hybrid_rerank",
            top_k,
        )
    else:
        reranked = _rank(
            [
                (item.document, 0.7 * _lexical_score(query, item.document.text) + 0.3 * item.score)
                for item in hybrid
            ],
            "hybrid_rerank",
            top_k,
        )
    return reranked


@lru_cache(maxsize=1)
def _cross_encoder() -> object | None:
    try:
        from sentence_transformers import CrossEncoder

        return CrossEncoder(
            os.getenv("RERANKER_MODEL", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")
        )
    except (ImportError, OSError, RuntimeError, ValueError):
        return None


def _cross_encoder_scores(query: str, documents: list[Document]) -> list[float] | None:
    model = _cross_encoder()
    if model is None:
        return None
    try:
        return [
            float(score)
            for score in model.predict([(query, document.text) for document in documents])
        ]
    except (OSError, RuntimeError, ValueError):
        return None
