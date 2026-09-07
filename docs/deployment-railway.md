# Railway deployment

Railway runs three components from this repository:

1. **Web** uses `railway.toml` and starts the combined NiceGUI/FastAPI ASGI
   process.
2. **PostgreSQL** stores runtime observations, historical context, private
   interaction events, feedback, and completed ingestion facts.
3. **Ingestion** uses `railway-cron.toml` and runs hourly. It refreshes station
   observations each run, runs the city-history branch at the configured UTC
   hour, and applies interaction retention cleanup.

Qdrant and Grafana are deliberately local-Compose services. Production uses the
configured in-process `hybrid` retrieval method and the built-in aggregate
Monitoring page, so they are not required by the Railway deployment.

## Web variables

```text
DATA_DIR=/app/data
POSTGRES_DSN=${{Postgres.DATABASE_URL}}
SOURCE_DATA_URL=https://udara.jakarta.go.id/
LLM_PROVIDER=anthropic
LLM_MODEL=claude-haiku-4-5-20251001
ANTHROPIC_API_KEY=<secret>
ANTHROPIC_BASE_URL=https://api.anthropic.com
RETRIEVAL_MODE=hybrid
PROMPT_VARIANT=strict
NICEGUI_STORAGE_SECRET=<long random secret>
APP_VERSION=<release version>
GIT_COMMIT=<deployed commit>
BUILD_TIME=<UTC build timestamp>
RUNTIME_REFRESH_TTL_SECONDS=60
INTERACTION_RETENTION_DAYS=30
```

`NICEGUI_STORAGE_SECRET` is required in production. The application refuses to
start in a production environment without it; the built-in local value is only
for local development. Never place `ANTHROPIC_API_KEY` or a database URL in a
source file, build argument, browser response, or screenshot.

## Ingestion variables

```text
DATA_DIR=/app/data
POSTGRES_DSN=${{Postgres.DATABASE_URL}}
SOURCE_DATA_URL=https://udara.jakarta.go.id/
HISTORICAL_AIR_URL=https://air-quality-api.open-meteo.com/v1/air-quality
HISTORICAL_REFRESH_UTC_HOUR=17
HISTORICAL_REFRESH_DAYS=92
INTERACTION_RETENTION_DAYS=30
OFFICIAL_CONNECT_TIMEOUT_SECONDS=5
OFFICIAL_READ_TIMEOUT_SECONDS=15
OFFICIAL_FETCH_RETRIES=2
```

The ingestion service must use the same `POSTGRES_DSN` as the web service. A
successful PostgreSQL publication writes an `ingestion_runs` row containing only
the completion time, source status, source URL, row count, and non-sensitive
failure detail. The web service uses that row as runtime provenance.

## Verify a deployment

After Railway reports a healthy deployment, make non-sensitive public requests:

```bash
curl --fail https://<domain>/health
curl --fail https://<domain>/version
curl --fail https://<domain>/sources
curl --fail https://<domain>/monitoring/summary?days=30
curl --fail https://<domain>/docs
```

`/sources` has separate `runtime` and `packaged_fallback` objects. A live
runtime uses `store: postgres` and includes loaded row count, newest observation,
and the latest completed ingestion record. If PostgreSQL is empty or unavailable,
the response names the fallback reason rather than presenting packaged data as a
fresh run.

Then submit one synthetic current-station question, verify the cited answer and
selected retrieval/prompt fields, and submit one synthetic feedback event. Keep
only aggregate results and screenshots; do not use personal or health details.

Railway can scale the web process to zero. A first request may therefore have a
cold-start delay. The scheduled ingestion process is finite and idempotent;
inspect its deployment log after source failures rather than assuming the hourly
target guarantees a successful refresh.
