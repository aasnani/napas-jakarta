# Architecture

> Direction update (2026-09-27): the accepted replacement experience is the
> single-workspace design in [product-design.md](product-design.md). The
> current product uses Next.js/React, Eve, and MapLibre; FastAPI and the
> verified Python data/domain layer remain authoritative.

The replacement product is a Next.js/React/Eve web service backed by a private
FastAPI data and telemetry service. The web surface provides the resident-facing
advisor, map, station detail, filters, source disclosure, feedback, and
language controls. The Python service remains authoritative for station data,
freshness, deterministic tools, and bounded anonymous telemetry.

The request router sends current readings, comparisons, history, policy
timelines, and index interpretation to deterministic Python tools. Questions
about documentary evidence, public-health guidance, regulations, and causes use
retrieval over the curated local corpus. The configured retrieval method is
read from `RETRIEVAL_MODE`; `hybrid` is the selected default. The API records
the actual method used with each answer event.

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
Next.js web service, a standalone API, and one-shot ingest/index services.
The replacement Railway shape deploys the Next/Eve web service, a private API,
and optionally PostgreSQL plus scheduled ingestion because in-process hybrid
retrieval is the configured production method and aggregate monitoring belongs
behind the service boundary. See
[deployment on Railway](deployment-railway.md) for the operational layout.

Interaction storage contains question text, answer text, a bounded anonymous
page-load grouping ID, response metadata, and usefulness feedback so the team
can diagnose product quality. The replacement workspace does not restore chat
history after refresh and does not send account, cookie, IP, device, or contact
identity fields in its application telemetry. These fields are never returned
by the aggregate Monitoring endpoint or rendered publicly. The scheduled
ingestion service deletes interaction and feedback rows older than the bounded
`INTERACTION_RETENTION_DAYS` setting (30 days by default). Access is limited to
the deployed service and its database operators; users should not enter
sensitive personal or health information.
