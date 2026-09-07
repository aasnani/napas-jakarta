"""Deterministic chunking variants used in the retrieval experiment."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.models import Document


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_id: str
    text: str
    section_path: str
    variant: str
    title: str = ""
    publisher: str = ""
    language: str = "en"
    document_type: str = "guidance"
    effective_date: str | None = None
    article_or_clause: str | None = None
    page: int | None = None
    source_url: str = ""
    checksum: str = ""
    source_id: str = ""
    heading_path: str = ""
    paragraph: str | None = None
    previous_chunk_id: str | None = None
    next_chunk_id: str | None = None
    topics: tuple[str, ...] = ()
    jurisdiction: str = ""
    status: str = ""

    @property
    def locator(self) -> str:
        return self.article_or_clause or self.paragraph or self.section_path or f"chunk {self.chunk_id}"


def _make(document: Document, text: str, index: int, variant: str, section: str = "") -> Chunk:
    normalized = text.strip()
    declared_type = str(document.metadata.get("document_type", "")).strip()
    document_type = declared_type or ("regulation" if any(token in document.document_id for token in ("ispu", "regul", "permen", "pergub", "pp-")) else "guidance")
    heading = section or document.heading_path or document.section
    return Chunk(
        f"{document.document_id}:{variant}:{index}", document.document_id, normalized, heading, variant,
        title=document.title, publisher=document.publisher, document_type=document_type,
        source_url=document.source_url, checksum=hashlib.sha256(normalized.encode()).hexdigest(),
        source_id=document.source_id or document.document_id, heading_path=heading,
        language=document.language, jurisdiction=document.jurisdiction, status=document.status,
        effective_date=document.effective_date,
    )


def fixed_chunks(document: Document, words: int = 450, overlap: int = 60) -> list[Chunk]:
    tokens = document.text.split()
    if not tokens:
        return []
    step = max(1, words - overlap)
    return [_make(document, " ".join(tokens[i:i + words]), n, "fixed")
            for n, i in enumerate(range(0, len(tokens), step)) if tokens[i:i + words]]


def structure_chunks(document: Document) -> list[Chunk]:
    """Split Markdown into stable heading/paragraph units.

    A long section is split only at blank-line boundaries.  This preserves
    legal/article and research-section context while bounding retrieval text.
    """
    lines = document.text.splitlines()
    heading: list[str] = []
    blocks: list[tuple[str, str]] = []
    current: list[str] = []
    current_heading = document.heading_path or document.section
    def flush() -> None:
        nonlocal current
        body = "\n".join(current).strip()
        if body:
            blocks.append((current_heading, body))
        current = []
    for line_number, line in enumerate(lines):
        if line_number < 12 and re.match(
            r"^(?:source_id|jurisdiction|language|status|effective_date|publisher|source|access_note|publication_date|document_type|legal_status):\s*",
            line,
            flags=re.IGNORECASE,
        ):
            continue
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            flush()
            level = len(match.group(1))
            heading[:] = heading[: level - 1]
            heading.append(match.group(2).strip())
            current_heading = " > ".join(heading)
        elif not line.strip():
            flush()
        else:
            current.append(line)
    flush()
    chunks: list[Chunk] = []
    for heading_path, body in blocks:
        words = body.split()
        # Keep short clauses together; split long text at sentence/line
        # boundaries rather than arbitrary character offsets.
        pieces: list[str] = []
        if len(words) <= 520:
            pieces = [body]
        else:
            current_words: list[str] = []
            for sentence in re.split(r"(?<=[.!?])\s+|\n", body):
                sentence_words = sentence.split()
                if current_words and len(current_words) + len(sentence_words) > 520:
                    pieces.append(" ".join(current_words))
                    current_words = []
                current_words.extend(sentence_words)
            if current_words:
                pieces.append(" ".join(current_words))
        for piece in pieces:
            chunks.append(_make(document, piece, len(chunks), "structure", heading_path))
    linked: list[Chunk] = []
    for index, chunk in enumerate(chunks):
        linked.append(Chunk(**{**chunk.__dict__,
            "previous_chunk_id": chunks[index - 1].chunk_id if index else None,
            "next_chunk_id": chunks[index + 1].chunk_id if index + 1 < len(chunks) else None,
            "paragraph": f"p.{index + 1}"}))
    return linked


def semantic_chunks(document: Document, min_words: int = 80, max_words: int = 450) -> list[Chunk]:
    """A dependency-free semantic proxy: split at paragraph/topic boundaries.

    Production runs can replace the boundary scorer with embedding similarity;
    the stable IDs and output contract remain unchanged.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", document.text) if p.strip()]
    chunks: list[Chunk] = []
    current: list[str] = []
    count = 0
    for paragraph in paragraphs:
        words = paragraph.split()
        if current and count + len(words) > max_words:
            chunks.append(_make(document, "\n\n".join(current), len(chunks), "semantic"))
            current, count = [], 0
        current.append(paragraph)
        count += len(words)
        if count >= min_words:
            chunks.append(_make(document, "\n\n".join(current), len(chunks), "semantic"))
            current, count = [], 0
    if current:
        chunks.append(_make(document, "\n\n".join(current), len(chunks), "semantic"))
    return chunks
