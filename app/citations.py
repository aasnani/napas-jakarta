"""Presentation helpers for turning grounded citation tokens into links.

The RAG answer string remains canonical and untouched.  This module only builds
the Markdown shown by a web client after generation has completed.
"""

from __future__ import annotations

import re
from html import escape
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


def normalize_answer_markdown(answer_text: str) -> str:
    """Repair safe, common paragraph-to-list mistakes in model output.

    Models occasionally emit ``Heading: - first item - second item`` as a
    single line.  This is presentation-only normalization: it never changes a
    citation token, URL, or ordinary hyphenated phrase.
    """
    text = answer_text.replace("\r\n", "\n").replace("\r", "\n")
    # A colon or a complete Markdown heading is a safe structural boundary
    # for a list marker.  Do not split arbitrary prose around every hyphen.
    text = re.sub(r"(?<=:)\s+-\s+(?=\S)", "\n- ", text)
    text = re.sub(r"(\*\*[^\n*]+\*\*)\s+-\s+(?=\S)", r"\1\n\n- ", text)
    # Consecutive inline bullets after the first are also list boundaries.
    text = re.sub(r"(?<=\])\s+-\s+(?=\S)", "\n- ", text)
    return text


def render_answer_html(answer_text: str, sources: Iterable[Mapping[str, object]]) -> str:
    """Render finalized answer prose with only retrieved citations as links.

    All provider text is escaped before minimal paragraph/list formatting is
    applied.  Therefore model-supplied HTML, Markdown destinations, and URLs
    cannot become active content.  Citation anchors are constructed solely
    from validated retrieved-source metadata and carry safe new-tab metadata.
    """
    by_id: dict[str, tuple[str, str]] = {}
    for source in sources:
        source_id = str(source.get("id", source.get("source_id", ""))).strip()
        url = str(source.get("url", "")).strip()
        title = str(source.get("title", source_id)).strip() or source_id
        if source_id and re.match(r"^https?://[^\s<>]+$", url, flags=re.IGNORECASE):
            by_id[source_id] = (title, url)

    def remove_model_destination(match: re.Match[str]) -> str:
        """Discard only an already-linked destination for a known citation."""
        return match.group(1) if match.group(2) in by_id else match.group(0)

    citation_with_destination = re.compile(
        r"(\[([A-Za-z0-9_-]+)(?:\s*§\s*[^\[\]]+?)?\])\s*\(<https?://[^>]+>\)",
        flags=re.IGNORECASE,
    )
    answer_text = citation_with_destination.sub(remove_model_destination, answer_text)

    def render_inline(value: str) -> str:
        escaped = escape(value, quote=False)

        def citation(match: re.Match[str]) -> str:
            source_id = match.group(1)
            metadata = by_id.get(source_id)
            if metadata is None:
                return match.group(0)
            title, url = metadata
            locator = match.group(2).strip() if match.group(2) else ""
            label = f"{title} § {locator}" if locator else title
            return (
                f'<a class="napas-inline-citation" href="{escape(url, quote=True)}" '
                f'target="_blank" rel="noopener noreferrer">{escape(label)}</a>'
            )

        rendered = _CITATION_RE.sub(citation, escaped)
        # Keep basic heading emphasis readable without admitting arbitrary HTML.
        return re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", rendered)

    lines = normalize_answer_markdown(answer_text).split("\n")
    output: list[str] = []
    list_open = False
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            if list_open:
                output.append("</ul>")
                list_open = False
            continue
        if line.startswith("- "):
            if not list_open:
                output.append('<ul class="napas-answer-list">')
                list_open = True
            output.append(f"<li>{render_inline(line[2:])}</li>")
            continue
        if list_open:
            output.append("</ul>")
            list_open = False
        # A standalone bold phrase is the familiar model heading pattern.
        heading = re.fullmatch(r"\*\*([^*\n]+)\*\*", line)
        if heading:
            output.append(f"<h3>{escape(heading.group(1))}</h3>")
        else:
            output.append(f"<p>{render_inline(line)}</p>")
    if list_open:
        output.append("</ul>")
    return "".join(output)


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
