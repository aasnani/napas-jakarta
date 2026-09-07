# Corpus depth and exact citations

The committed corpus is a reproducible, bilingual document layer separate from
typed measurements. `ingestion.corpus.build_corpus()` reads `data/docs` and
`data/sources.yaml`, writes deterministic JSONL documents/chunks under
`data/index/`, and emits `data/index/corpus_report.json`. `ingestion.flow` runs
the same builder before measurement validation, publication or optional Qdrant
indexing.

## Current freeze

The pre-expansion baseline is preserved at
`data/baseline/corpus_baseline_2026-09-07.json`: 20 Markdown documents, 3,966
words and 31 old heading chunks (document fingerprint
`e1fb4f72b72185bc81189a38d10cd9391dde349105a08f34b85a0f6eac27391a`). The
stale report at that point said 10 documents/10 chunks; the new report records
the actual identity rather than inheriting that stale count.

The current freeze has 29 local documents, 6,534 words and 113 structure-aware
chunks. Three local document IDs are intentional aliases (`ispu`,
`who-guidance`, and `jakarta-monitoring`) for authoritative source records;
`health-disclaimer` is an explicit local safety contract derived from linked
WHO guidance, not a verbatim external mirror. `satu-data-ispu-2023` remains a
catalog-only record: it is marked `unmirrored_external` and is not used to
claim that the application has downloaded or indexed that dataset. The corpus
report separates this intentional exception from a broken manifest/local
mismatch. Manifest checksums for local snapshots have distinct values and are
never interpreted as proof that two external publications are identical.

Nine authoritative records were added across BPK national/provincial law,
WHO health guidance, US EPA indoor-air engineering guidance, an official
Mahkamah Agung locator, CEMS monitoring, and a dated DKI SPPU status statement.
Where a PDF or case document could not be fetched, the local file is explicitly
an official metadata/abstract or locator extract. No full text, page number or
legal conclusion is fabricated. `data/raw/authoritative/fetch-manifest.json`
records each URL, outcome and the network/content-type blockers so a permitted
fetch can replace the extract.

## Chunk contract

Chunks use stable IDs of the form
`{source_id}:structure:{zero_based_index}` and contain text, heading path,
paragraph locator, previous/next IDs, SHA-256 content hash, language,
jurisdiction, legal/status metadata, publisher and URL. Boundaries are
Markdown headings and blank-line paragraphs; long paragraphs are split at
sentence boundaries with a 520-word upper bound. Re-running the builder is
idempotent and its fingerprint covers document and chunk identity/checksums.

## Citation contract

The canonical answer remains plain text, but document answers upgrade compact
legacy markers to `[source-id § locator]`. The response additionally exposes a
`citations` list mapping `claim_id` to `source_id`, `chunk_id`, locator, title,
URL, supporting excerpt and retrieval score. `citation_validation` reports
orphaned or legacy-without-locator markers. `app.citations` accepts both old
and exact syntax, validates only retrieved source metadata, and linkifies exact
markers only for safe HTTP(S) URLs. Tool-backed measurement answers preserve
the compact token for existing clients while their structured citation records
carry the exact observation provenance/chunk locator.

Human claim labels and provider-backed citation scores remain pending. The
current 150-question retrieval artifact is still a seeded, pending-human-review
benchmark; its after-expansion metrics are descriptive and must not be reported
as human-validated relevance or groundedness.
