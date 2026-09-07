from ingestion.indexing import _fallback_vector


def test_fallback_embedding_is_normalized_and_stable():
    first = _fallback_vector("PM2.5 Jakarta")
    assert first == _fallback_vector("PM2.5 Jakarta")
    assert len(first) == 64
    assert round(sum(value * value for value in first), 6) == 1.0
