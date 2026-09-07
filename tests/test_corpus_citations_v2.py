import json
from pathlib import Path

from app.citations import citation_token, parse_citations, validate_citation_records
from ingestion.corpus import build_corpus

ROOT = Path(__file__).parents[1]


def test_corpus_artifacts_are_reproducible_and_structure_aware(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "sources.yaml").write_text("[]\n")
    (tmp_path / "docs" / "x.md").write_text(
        "# Title\nPublisher: Test\nSource: https://example.test/x\n\n## Article 1\n\nFirst clause.\n\nSecond clause.\n"
    )
    first = build_corpus(tmp_path)
    first_chunks = (tmp_path / "index" / "chunks.jsonl").read_text()
    second = build_corpus(tmp_path)
    assert first["fingerprint"] == second["fingerprint"]
    assert first_chunks == (tmp_path / "index" / "chunks.jsonl").read_text()
    rows = [json.loads(line) for line in first_chunks.splitlines()]
    assert rows[0]["heading_path"] == "Title > Article 1"
    assert rows[0]["next_chunk_id"] == rows[1]["chunk_id"]
    assert rows[1]["previous_chunk_id"] == rows[0]["chunk_id"]


def test_exact_locator_parser_and_structured_claim_validation():
    token = citation_token("law-1", "Pasal 8, ayat (2)")
    assert parse_citations(f"Claim {token}") == [
        {"source_id": "law-1", "locator": "Pasal 8, ayat (2)"}
    ]
    source = {"id": "law-1", "source_id": "law-1", "chunk_id": "law-1:structure:0", "locator": "Pasal 8, ayat (2)"}
    record = {"source_id": "law-1", "chunk_id": "law-1:structure:0", "locator": "Pasal 8, ayat (2)"}
    assert validate_citation_records([record], [source])["resolvable"] is True
    assert validate_citation_records([{**record, "locator": "Pasal 99"}], [source])["resolvable"] is False
