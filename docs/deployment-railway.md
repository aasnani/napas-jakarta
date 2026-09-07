# Railway trial deployment

This runbook targets a short peer-review window using Railway's trial credit.
The application is one ASGI service: NiceGUI renders the browser UI and the
same process exposes FastAPI endpoints. A separate Postgres service stores
measurements, historical city data, feedback, and interaction events. A third
service runs the ingestion command on a schedule. Qdrant and Grafana are not
required for the deployed review path.

## Services

Create a Railway project with these services:

1. **Web** — deploy this repository with `railway.toml`.
   - Start command: `uvicorn app.web:app --host 0.0.0.0 --port $PORT`
   - Healthcheck path: `/health`
   - The service listens on Railway's injected `$PORT`; do not hard-code 8502.
2. **Postgres** — add Railway's PostgreSQL service. Copy its private
   `DATABASE_URL` into the web and cron services as `POSTGRES_DSN`.
3. **Ingestion** — create a second service from the same repository and apply
   `railway-cron.toml` (or set its start command to
   `python -m ingestion.railway_cron`). Set its cron schedule to `0 * * * *`.
   If the dashboard is used, configure this under Settings → Deploy → Cron
   Schedule; confirm the schedule there because it is a service setting.

The ingestion service is not an HTTP service. It runs station ingestion every
hour. At 17:00 UTC (00:00 Asia/Jakarta) it also refreshes the city historical
series. Railway cron expressions are UTC. The hour can be changed with
`HISTORICAL_REFRESH_UTC_HOUR`; a manual one-off run can set
`RUN_HISTORICAL=1`.

## Variables and secrets

Set these variables on the web service:

```text
DATA_DIR=/app/data
POSTGRES_DSN=${{Postgres.DATABASE_URL}}
SOURCE_DATA_URL=<the official Jakarta CSV/JSON export URL>
HISTORICAL_AIR_URL=https://air-quality-api.open-meteo.com/v1/air-quality
LLM_PROVIDER=anthropic
LLM_MODEL=claude-haiku-4-5-20251001
ANTHROPIC_API_KEY=<Railway secret>
ANTHROPIC_BASE_URL=https://api.anthropic.com
RUNTIME_REFRESH_TTL_SECONDS=60
NICEGUI_STORAGE_SECRET=<long random Railway secret>
PREFECT_SERVER_ANALYTICS_ENABLED=false
```

Set the same data, database, and historical variables on the ingestion
service, together with:

```text
DATA_DIR=/app/data
POSTGRES_DSN=${{Postgres.DATABASE_URL}}
SOURCE_DATA_URL=<the official Jakarta CSV/JSON export URL>
HISTORICAL_AIR_URL=https://air-quality-api.open-meteo.com/v1/air-quality
HISTORICAL_REFRESH_UTC_HOUR=17
HISTORICAL_REFRESH_DAYS=92
OFFICIAL_CONNECT_TIMEOUT_SECONDS=5
OFFICIAL_READ_TIMEOUT_SECONDS=15
OFFICIAL_FETCH_RETRIES=2
PREFECT_SERVER_ANALYTICS_ENABLED=false
```

Keep `ANTHROPIC_API_KEY` only on the web service if ingestion does not answer
questions. Never put it in source files, Docker build arguments, the browser,
or a generated data file. `SOURCE_DATA_URL` can use the supported official
portal landing page `https://udara.jakarta.go.id/` (the ingestion connector
reads its embedded SPKU data) or a permitted CSV/JSON export URL. Do not
substitute an arbitrary scrape endpoint.

Do not set `QDRANT_URL` for this deployment. The application retains its
dependency-light in-process hybrid retrieval path and falls back to the
packaged corpus.

The web image intentionally omits the optional OpenAI SDK and Prefect extras
to keep the trial container smaller. The Anthropic path used here is supported
by the existing `requests` dependency. If an OpenAI-compatible provider is
needed later, build a separately reviewed image with the `llm` extra enabled;
do not add that key to the browser or to the cron service.

## Deploy and verify

From a clean checkout, link the project and deploy the web service through the
Railway dashboard or CLI. The CLI is optional; the dashboard is sufficient:

```bash
railway login
railway link
railway up
```

Deploy the ingestion service from the same commit and set its start command to
`python -m ingestion.railway_cron`. Use the service's Variables tab to add the
database reference and source URL. Then run one manual ingestion execution
before waiting for the hourly schedule.

Verify, in order:

```bash
curl --fail https://<railway-domain>/health
curl --fail https://<railway-domain>/sources
```

The health response should report `measurement_store` as `postgres` after the
first successful ingestion. The sources response should show the live source,
runtime row count, and measurement source names. Ask a current station question
and confirm its timestamp changes after a later ingestion run. Submit one
feedback action and check the interaction/feedback tables in Postgres.

## Serverless behavior

Enable the web service's **Serverless** setting and use the smallest practical
replica count. The container may scale to zero while nobody is reviewing it;
the first request then pays a cold-start delay. This is expected for the trial
access pattern. Keep the healthcheck enabled, but do not add an external
uptime monitor because periodic probes would wake the service and consume
trial credit.

NiceGUI uses WebSockets for the live chat UI. Railway must route WebSocket
upgrades to the web service; test both an initial question and a follow-up
question after the service has slept. A browser refresh or reconnect should
retain no secret state; the bounded chat history remains client/session data.

## Domain and review access

Use Railway's generated public domain for the review. In the web service's
Settings → Networking panel, generate a domain and confirm that `/health` and
the root page are reachable without logging in. A custom domain is optional;
if used, add it only after the generated domain passes the health and WebSocket
checks.

## Data freshness and fallback

The web process checks Postgres at most once per
`RUNTIME_REFRESH_TTL_SECONDS` (60 seconds by default). It updates the shared
measurement and historical lists in place, so ingestion results appear
without a web redeploy. If Postgres is unavailable or empty, the packaged CSV
snapshot remains available and the answer must be read as fallback/demo data.

The hourly cron publishes normalized station observations to Postgres. The
daily branch publishes the city-level historical series to Postgres as a
separate table. The latter is explicitly city-model context, not an official
station reading. The CSV files are retained in the image as a fallback, but
Railway's container filesystem is ephemeral and must not be treated as the
durable database.

The official portal request uses bounded socket/read timeouts and retries
transient connection or read failures. If the portal remains unavailable, the
cron publishes the latest retained local snapshot (or the committed demo
snapshot only when no retained file exists) and records `source_status` and
`source_error` in `ingestion_report.json`; it never labels that fallback as a
new live observation. HTTP errors and schema changes still fail visibly so a
source contract problem is not silently hidden.

Railway may skip a scheduled run when the previous run is still active, so the
ingestion command is deliberately finite and idempotent. The schedule is an
hourly freshness target, not a guarantee that a run starts at the exact
minute. For current platform behavior, see Railway's official [cron job
documentation](https://docs.railway.com/cron-jobs), [serverless deployment
documentation](https://docs.railway.com/deployments/serverless), and
[healthcheck documentation](https://docs.railway.com/deployments/healthchecks).

## Trial end and teardown

Before the Railway trial expires, export any desired Postgres data and record
the public URL, deployed commit, source URL, and last successful ingestion.
Then remove the generated domain and delete the web, ingestion, and Postgres
services (or delete the entire Railway project). Also remove the Anthropic key
from Railway and rotate it if it was ever exposed outside Railway Variables.

Do not leave the cron service running after peer review: it is the component
most likely to continue consuming trial credit. Railway's trial/credit terms
can change, so check the current project usage and billing page before the
review and again during teardown.
