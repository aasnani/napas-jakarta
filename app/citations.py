"""Presentation helpers for turning grounded citation tokens into links.

The RAG answer string remains canonical and untouched.  This module only builds
the Markdown shown by a web client after generation has completed.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

_CITATION_RE = re.compile(r"\[([A-Za-z0-9_-]+)(?:\s*§\s*([^\[\]]+?))?\]")


def parse_citations(answer_text: str) -> list[dict[str, str | None]]:
    """Parse legacy ``[source]`` and exact ``[source § locator]`` markers."""
    return [
        {"source_id": match.group(1), "locator": match.group(2).strip() if match.group(2) else None}
        for match in _CITATION_RE.finditer(answer_text)
    ]


def linkify_citations(answer_text: str, sources: Iterable[Mapping[str, object]]) -> str:
    """Replace known ``[source-id]`` tokens with safe Markdown links.

    Only absolute HTTP(S) URLs from retrieved source metadata are accepted.
    Unknown IDs and malformed URLs stay as visible plain tokens, preserving the
    grounding signal rather than silently inventing a link.
    """
    by_id: dict[str, tuple[str, str]] = {}
    for source in sources:
        source_id = str(source.get("id", source.get("source_id", ""))).strip()
        url = str(source.get("url", "")).strip()
        title = str(source.get("title", source_id)).strip() or source_id
        if source_id and re.match(r"^https?://[^\s<>]+$", url, flags=re.IGNORECASE):
            by_id[source_id] = (title.replace("[", "(").replace("]", ")"), url.replace(")", "%29"))

    def replace(match: re.Match[str]) -> str:
        source_id = match.group(1)
        metadata = by_id.get(source_id)
        if metadata is None:
            return match.group(0)
        title, url = metadata
        locator = match.group(2).strip() if match.group(2) else ""
        label = f"{title} § {locator}" if locator else title
        return f"[{label}](<{url}>)"

    return _CITATION_RE.sub(replace, answer_text)


def citation_ids(answer_text: str) -> list[str]:
    """Return citation tokens in first-seen order for UI source summaries."""
    return list(dict.fromkeys(match.group(1) for match in _CITATION_RE.finditer(answer_text)))


def citation_token(source_id: str, locator: str | None = None) -> str:
    """Build a readable, parseable exact-locator token."""
    clean_id = re.sub(r"[^A-Za-z0-9_-]", "", str(source_id))
    clean_locator = re.sub(r"[\[\]]", "", str(locator or "")).strip()
    return f"[{clean_id} § {clean_locator}]" if clean_locator else f"[{clean_id}]"


def validate_citation_records(
    records: Iterable[Mapping[str, object]], sources: Iterable[Mapping[str, object]]
) -> dict[str, object]:
    """Check structured claim records against retrieved source metadata.

    This is intentionally deterministic: a record is resolvable only when its
    source, chunk and locator exactly match a source returned for that answer.
    """
    by_key = set()
    for source in sources:
        chunk = str(source.get("chunk_id", ""))
        locator = str(source.get("locator", ""))
        for identifier in (source.get("id", ""), source.get("source_id", "")):
            if identifier:
                by_key.add((str(identifier), chunk, locator))
    orphaned = []
    total = 0
    for record in records:
        total += 1
        key = (str(record.get("source_id", "")), str(record.get("chunk_id", "")), str(record.get("locator", "")))
        if key not in by_key:
            orphaned.append(key)
    return {"total": total, "resolvable": not orphaned, "orphaned": orphaned}
