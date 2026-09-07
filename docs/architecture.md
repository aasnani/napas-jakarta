# Architecture

The deployed product is a combined NiceGUI and FastAPI ASGI service. NiceGUI
provides the resident-facing Ask, map, overview, trends, and Monitoring pages;
FastAPI exposes the same domain functions at HTTP endpoints. `app/ui.py` is a
legacy Streamlit compatibility UI for local experiments only and is not the
deployed surface.

The request router sends current readings, comparisons, history, policy
timelines, and index interpretation to deterministic Python tools. Questions
about documentary evidence, public-health guidance, regulations, and causes use
retrieval over the curated local corpus. The configured retrieval method is
read from `RETRIEVAL_MODE`; `hybrid` is the selected default. Both the NiceGUI
and API paths record the actual method used with each answer event.

Answer generation reads a named prompt from `app.provider.PROMPTS`. The selected
value is `PROMPT_VARIANT=strict` by default, and the same prompt dictionary is
used by the bounded provider check. Answer telemetry records its prompt version
without storing a provider key. If no provider is configured or a provider is
unavailable, the app returns a cited deterministic response.

Runtime observations prefer PostgreSQL. Packaged CSV and ingestion artifacts
remain a transparent fallback when PostgreSQL is missing, empty, or unavailable.
`GET /sources` deliberately separates current loaded-store facts from the
packaged fallback summary; it does not relabel an image-local report as a live
run. Successful PostgreSQL ingestion writes a minimal `ingestion_runs` record,
which gives the runtime block its most recent completed ingestion time and row
count. `GET /version` returns only safe build metadata, plus the selected
retrieval and prompt variants.

The full local Compose environment includes PostgreSQL, Qdrant, Grafana, the
combined web service, a standalone API, and one-shot ingest/index services.
Railway intentionally deploys only the web service, PostgreSQL, and scheduled
ingestion because in-process hybrid retrieval is the configured production
method and the Monitoring page renders aggregate data directly. See
[deployment on Railway](deployment-railway.md) for the operational layout.

Interaction storage contains question text, rewritten queries, a bounded
anonymous session ID, response metadata, and optional feedback comments so the
team can diagnose product quality. These fields are never returned by the
aggregate Monitoring endpoint or rendered publicly. The scheduled ingestion
service deletes interaction and feedback rows older than the bounded
`INTERACTION_RETENTION_DAYS` setting (30 days by default). Access is limited to
the deployed service and its database operators; users should not enter
sensitive personal or health information.
