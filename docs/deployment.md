# Deployment runbook

## Local Compose

```bash
cp .env.example .env
# put ANTHROPIC_API_KEY in .env for Claude Haiku (or use the OpenAI variables)
make up
```

After the services report healthy, `make smoke` checks the API, NiceGUI,
Grafana, and Qdrant HTTP health endpoints. Stop the local stack with `make down`.
Compose forwards `SOURCE_DATA_URL` to ingestion, the API, and the UI; set it in
`.env` to opt into the official portal snapshot for a refresh.

Check `http://localhost:8502`, `http://localhost:8000/health`, and
`http://localhost:3000`. The `ingest` service is idempotent and completes before
the app and API start. PostgreSQL and Qdrant have health checks; monitoring
falls back to JSONL if PostgreSQL is temporarily unavailable.
The API's `/sources` endpoint exposes source attribution and ingestion mode for
reviewer verification.
The Trends tab also includes the committed Zenodo/Open-Meteo CAMS-derived
city-level historical series (`data/processed/historical_city_air_quality.csv`)
as separately labelled context; it is not presented as official SPKU station
data.
Run `make refresh-history` to merge the public Open-Meteo CAMS trailing
92-day window into that series. The refresh is city context, not a replacement
for official station observations.
It also includes runtime measurement row counts and distinct runtime source
names, which may differ from the committed demo ingestion report when a
PostgreSQL live refresh has been loaded.
`/health` reports the loaded store (`local` or `postgres`), demo/live source
mode, row counts, and the age in seconds of the newest observation.
`/measurements/latest`, `/measurements/compare`, `/measurements/history`,
`/measurements/standard`, and `/measurements/unhealthy-days` expose the deterministic
structured-data tools for direct review; the LLM never receives permission to
generate SQL or perform those calculations.
The `/evidence/source-apportionment` and `/evidence/compare` endpoints expose
structured study findings and retain each study's method and limitation fields;
they do not infer a cross-study causal ranking.
Grafana panel 13 reports newest observation age by measurement source and
station, independently of interaction traffic.
Interaction logs include only a bounded anonymous session ID (no IP address or
personal identifier), and feedback events retain their parent interaction ID so
session-level feedback and answer-level analysis are joinable.
Answer events also record carried-forward conversation entities (as JSON),
source count, token usage, estimated cost, and freshness context for route-level
analysis without persisting personal health details.
With Prefect installed, ingestion executes a retryable `validate-and-publish`
task (two retries with a five-second delay). Without the optional dependency,
the same function remains directly executable for local evaluation.
Run `make prefect-run` to install the locked orchestration extra and execute the
Prefect-decorated flow locally.
`prefect.yaml` defines the production `daily-official-refresh` deployment on an
Asia/Jakarta hourly schedule. Register it with `prefect deploy` after creating
the `napas-jakarta-processes` work pool and inject `SOURCE_DATA_URL` and
`POSTGRES_DSN` through the worker's secret environment. Set `QDRANT_URL` as
well to make the flow build the hybrid index after validation/publication; no
credentials are committed to this repository.

## Cloud checklist

- Build from a clean clone and configure secrets in the host secret manager.
- Set request and token limits at the application gateway.
- Configure `OPENAI_BASE_URL` when using an OpenAI-compatible hosted endpoint;
  the provider uses a 30-second timeout, retries twice, and caps output at 700
  tokens.
- Use a managed PostgreSQL, Qdrant, Grafana, and LLM provider endpoint.
- Verify `/health` and an unauthenticated question from a logged-out browser.
- Record the public URL, deployment date, data snapshot, and model in README.
- Roll back by redeploying the previous immutable image tag.

No public URL is claimed until that logged-out verification has been completed.

## Temporary review URL

The local Compose stack was exposed through a Cloudflare Quick Tunnel and
verified from an unauthenticated client:
<https://dicke-completion-comic-principles.trycloudflare.com>

This is an ephemeral tunnel with no uptime guarantee. Replace it with a named
cloud deployment before submission; never put secrets in the tunnel command.

The image has been locally verified with Podman: the API `/health` and `/ask`
endpoints return successfully, and `python -m ingestion.flow` completes as a
Prefect flow inside the image. Docker and Podman use the same Compose file.
The current source tree was rebuilt and ran the same checks on 2026-09-07;
the container returned demo-mode `/health`, a cited `/ask` response, a
successful `/measurements/standard` comparison, and the peak-station `/ask`
route before being removed.
The verified image includes Prefect 3.8.5; a demo run completed the
`validate-and-publish` task and returned the original demo corpus's four
documents, four chunks, and five measurements. The current expanded local
source is ten documents/chunks plus the official snapshot; the rebuilt image
was rerun against the current source and
completed the same Prefect flow successfully before cleanup.
The pinned Qdrant 1.12.4 service was also exercised locally: the index command
created `napas_documents` with four points using the lightweight fallback
encoder. Installing the `retrieval` extra switches that encoder to the
multilingual SentenceTransformers model.
The hybrid mode was also exercised: both dense and sparse collections contained
four points and the RRF helper returned fused candidates.

Prefect analytics are disabled in the image and one-shot ingest service so the
temporary local server does not create telemetry writes or require an external
analytics service.

`render.yaml` is a durable deployment blueprint for the NiceGUI/FastAPI service. It
keeps `OPENAI_API_KEY`, `POSTGRES_DSN`, and `QDRANT_URL` as unsynced secrets;
create those managed/external services in Render (or substitute compatible
providers) before deploying. The blueprint is intentionally not presented as a
live URL until an account-backed deployment is verified.

The Compose reviewer path deliberately uses the immutable demo corpus copied
into the image; it does not bind-mount host `data/`, which keeps rootless Docker
and Podman runs portable. For a live source, run `python -m ingestion.flow` on
the host (with `SOURCE_DATA_URL` configured), inspect the validation report, and
restart the application so it consumes `data/processed/measurements.csv`.

For a clean Python checkout, run `make setup` (or `uv sync --frozen --extra
dev`) before `make test`; the dev extra supplies pytest and Ruff while the
runtime image installs only production dependencies.
