# Architecture

The Streamlit UI and FastAPI API call the same service-layer function in
`app/rag.py`. A conservative router sends current, historical, comparison, and
unhealthy-day questions to deterministic measurement tools, while policy/health
questions use document retrieval. The
answer includes source IDs, exact chunk locators, structured claim citations,
timestamps, a rewritten query, route, and citation validation result.
`ingestion/flow.py` first runs the deterministic corpus inventory in
`ingestion/corpus.py`, then loads the official export adapter, normalizes
measurements, creates structure-aware chunks, and can be scheduled
as a Prefect flow. Validated measurements are upserted into PostgreSQL when a
DSN is configured, while offline runs use the committed CSV snapshot.
PostgreSQL also stores interaction events and Grafana reads the same schema with
live/evaluation traffic separated.

The dependency-light retrieval modes (sparse token, character-dense, hybrid
RRF, and rerank) are evaluated locally. `ingestion/indexing.py` is the optional
Qdrant/SentenceTransformers adapter for a production vector index; it is kept
behind the `retrieval` extra so evaluation never requires a paid or heavyweight
service. The pinned Qdrant server image and client range are compatible; a
local smoke test builds the collection and verifies its point count.
When the retrieval extra and model cache are available, `hybrid_rerank` uses a
multilingual CrossEncoder (`RERANKER_MODEL`); otherwise it falls back to the
measured lexical reranker without changing the API contract.
`make index` builds dense vectors; `make index ARGS="--hybrid"` builds parallel
dense and sparse collections and `qdrant_hybrid_search` fuses their candidates
with reciprocal rank fusion.
Set `QDRANT_URL` and choose `qdrant_hybrid` to make the service consume that
index; unavailable Qdrant falls back to the local evaluated hybrid path.

The API accepts bounded chat history and the UI stores session messages. The
provider sends up to three recent exchanges (the current turn is not duplicated)
to Claude or the OpenAI-compatible provider; retrieved evidence remains the
sole grounding source. Station coordinates are persisted by ingestion and are
loaded before any remote refresh attempt, so a Streamlit rerun does not need a
network call to build the map.

The UI is organized into Ask, Live map, Current overview, and Trends tabs. The
overview is appropriate for a one-snapshot feed; trend charts are shown only
when multiple observation timestamps exist. A selectable station filter links
the map to a station detail table while preserving the source and freshness
metadata.
