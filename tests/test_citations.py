from app.citations import citation_ids, linkify_citations


def test_linkify_citations_uses_retrieved_metadata_only():
    sources = [{"id": "ispu", "title": "ISPU guidance", "url": "https://example.org/ispu"}]
    rendered = linkify_citations("ISPU is unitless [ispu]. Unknown [missing].", sources)
    assert (
        rendered
        == "ISPU is unitless [ISPU guidance](<https://example.org/ispu>). Unknown [missing]."
    )


def test_linkify_citations_rejects_non_http_urls_and_preserves_answer():
    sources = [{"id": "bad", "title": "Bad", "url": "javascript:alert(1)"}]
    assert linkify_citations("Claim [bad]", sources) == "Claim [bad]"
    assert citation_ids("A [one] then [two] then [one]") == ["one", "two"]
