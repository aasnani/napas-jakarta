# Napas Jakarta deployment plan

Status: implementation complete locally; deployment not started
Owner: project owner with Codex support
Target hostname: `napasjakarta.armasn.dev`
Prepared: 2026-09-27

## Goal

Deploy the current Next.js/Eve workspace as the public Napas Jakarta surface,
with Gemini 3.5 Flash-Lite on the server, the existing FastAPI data and
telemetry boundary behind it, durable runtime data, and the Cloudflare-managed
custom hostname. Keep the legacy Railway deployment available until the new
surface has passed smoke, privacy, data-freshness, and rollback checks.

## Non-goals

- Do not add the deferred public MCP feature.
- Do not change the UI design or add new ingestion classes as part of this
  deployment.
- Do not deploy the current dirty working tree as-is.
- Do not expose the FastAPI or database services publicly after verification.
- Do not claim live data while the runtime is serving the packaged snapshot.
- Do not put the Gemini key, database URL, or telemetry contents in the
  browser, source tree, screenshots, or logs.

## Verified baseline

- Current branch is `main` at `2ca779d`; the worktree contains intentional
  uncommitted feature changes and generated `.codegraph/` data.
- The checked-in [`railway.toml`](../../railway.toml) builds the root
  [`Dockerfile`](../../Dockerfile) as the private API service and starts
  `uvicorn app.api:app`.
- The intended public replacement lives under [`web/`](../../web/), uses
  Next.js, Eve, Node 24, `@ai-sdk/google`, and a checked-in
  [`web/Dockerfile`](../../web/Dockerfile). Its `/api/health` route is the web
  health check and its entrypoint starts both Next and the loopback Eve server.
- The replacement web server expects `GEMINI_API_KEY`,
  `GEMINI_MODEL`, `GEMINI_REQUEST_TIMEOUT_MS`, and `NAPAS_API_ORIGIN`.
- The web server proxies station data and telemetry to FastAPI. FastAPI owns
  `/health`, `/version`, `/sources`, `/stations`, chat-domain routes, and
  feedback/telemetry persistence.
- The FastAPI runtime can read packaged fallback files or Railway PostgreSQL.
  The ingestion job can validate the official Jakarta source and publish
  normalized observations to PostgreSQL.
- The configured live-source boundary is `https://udara.jakarta.go.id/`.
- `npm run build` explicitly runs `eve build` before `next build`; the web
  image includes Eve's `just-bash` peer so a clean container build does not
  depend on a host-level Docker daemon.
- Local verification passed TypeScript typecheck, 31 TypeScript tests,
  production build, Docker image build, web `/api/health`, public `/eve/v1/info`,
  and a container Eve session/turn smoke test. These do not prove a deployed
  service or a production quota decision.

## Constraints

- Railway Free is `$0/month` with `$1` of monthly resource credit; it is not
  unlimited free production hosting. A continuously running web service,
  API, database, and cron service may exceed that allowance.
- Gemini's free tier has quota limits and states that content may be used to
  improve Google products. The product privacy copy must not imply that the
  provider receives or retains nothing. Avoid sensitive personal or health
  details in public prompts.
- The page-local transcript must disappear on refresh. Only the non-identifying
  EN/ID preference may survive a deliberate language refresh.
- Telemetry must remain anonymous, best effort, and bounded by retention. It
  may record interaction and usefulness information, but not account, IP,
  device, contact, or other identity fields.
- Railway private networking is scoped to one project and environment. The
  web service can call the API over its private hostname; browsers cannot.
- Cloudflare must remain authoritative for `armasn.dev`. Railway supplies the
  exact CNAME and TXT values for custom-domain verification.

## Architecture decision

### Recommended production-shaped pilot

Use one Railway project and one environment with these services:

| Service | Exposure | Responsibility |
| --- | --- | --- |
| `web` | Public, custom domain | Next.js/Eve UI, Gemini calls, same-origin route handlers |
| `api` | Private after smoke testing | FastAPI station/data/tool contracts and anonymous telemetry |
| `Postgres` | Private | Measurements, ingestion provenance, chat turns, feedback |
| `ingestion` | No public domain, scheduled | Official station refresh and retention cleanup |

The web service uses an internal URL such as
`http://${{api.RAILWAY_PRIVATE_DOMAIN}}:${{api.PORT}}`. The browser only talks
to the web service. Qdrant and Grafana remain out of the first hosted shape.

PostgreSQL is the recommended path if the product is going to describe station
readings as live and store telemetry across deployments. The current code
already publishes measurements and provenance there. A Railway Volume-only
design is not a drop-in replacement for this code: the ingestion service and
API would need a shared-storage contract, and the JSONL fallback currently
needs explicit retention cleanup.

### Strict-$0 fallback

If the Railway Free credit cannot support the four-service shape, deploy only
`web` and `api`, keep the packaged snapshot, and use a small API Volume only
for bounded fallback telemetry. Refresh data manually or through an external
scheduler after that path is implemented. Label the UI as snapshot/fallback
when the API is not serving a validated live runtime. Do not present this as
the final live-data deployment.

## Material-change boundary

The user has explicitly authorized implementation of the security and data
hardening slice below. No provider account, DNS, secret value, database
provisioning, or external deployment state is changed by this plan. Repository
changes remain limited to the application contracts, tests, and deployment
instructions described here.

Before a deployment attempt, the following repository changes require explicit
implementation approval:

1. Add a reproducible Next/Eve production image or an equivalent Railway
   service configuration.
2. Give the API service an explicit `uvicorn app.api:app` entrypoint so it is
   not accidentally serving the legacy NiceGUI UI.
3. Add a web health route if `/` is not accepted as the health check.
4. Resolve the audited stale-reading presentation, JSONL retention fallback,
   source-link exposure, and telemetry abuse-control gaps.
5. Reconcile deployment documentation and environment examples so they no
   longer advertise the old Anthropic/NiceGUI path for the replacement service.

## Security and data-hardening slice

### Goal

Make stale data visibly stale, keep anonymous telemetry bounded on the strict
`$0` JSONL path, preserve actionable station attribution, and put a server-only
shared token plus process-local abuse controls between the browser and the API
without introducing Redis, a paid database, or a new hosted service.

### Non-goals

- No user accounts, identity tracking, CAPTCHA, or IP persistence in telemetry.
- No browser-visible API token and no token embedded in client bundles.
- No claim that process-local limits replace provider quotas, a WAF, or a
  distributed limiter when the app is later scaled horizontally.
- No new public MCP feature or new ingestion source in this slice.

### Verified baseline and constraints

- FastAPI already has a `NAPAS_INTERNAL_TOKEN` dependency on chat/telemetry
  writes and process-local fixed-window limiters, but the Next station proxy
  does not yet forward the token.
- Next chat and telemetry routes already have first-line request limits, but
  their client-key helper trusts proxy headers unconditionally and limiter maps
  do not prune inactive keys.
- `monitoring/logging.py` has JSONL cleanup on writes, but
  `ingestion/railway_cron.py` only invokes retention for PostgreSQL.
- `get_latest_measurements()` marks observations stale at six hours; the API
  catalog must preserve that freshness contract and never derive a current
  category from a stale row.
- Station source URLs are already carried in the API shape, but the web proxy
  and UI must preserve and render them as validated direct `http(s)` links.

### Architecture decisions

1. **Server boundary token.** The browser calls same-origin Next routes. Those
   routes attach `X-Napas-Internal-Token` from the server-only
   `NAPAS_INTERNAL_TOKEN` variable when calling FastAPI. In production the API
   rejects protected writes and chat requests when the token is absent or
   invalid. Local development may omit it for convenience.
2. **Strict-$0 storage.** JSONL remains the fallback store on a dedicated
   Railway Volume. Retention is enforced on writes and by the scheduled cron,
   with malformed records preserved for recovery. PostgreSQL remains optional,
   not a prerequisite for this slice.
3. **Abuse controls.** Keep bounded request bodies, provider timeouts, and
   process-local limits at both the Next chat boundary and FastAPI telemetry
   boundary. Trust forwarded client-IP headers only when the deployment
   explicitly sets `TRUST_PROXY_HEADERS=true`. Treat these as first-line
   controls and pair them with Gemini key quotas before public launch.
4. **Freshness and attribution.** Freshness is computed from observation time
   at the data boundary. A stale or missing observation maps only to
   `Stale / missing`; its numeric value may remain visible as historical context
   but cannot count as current reporting. Direct station URLs are limited to
   `http` and `https` and are rendered with an explicit external-link contract.

### Task envelopes and gates

- **H1 Freshness:** add a regression test at the API catalog boundary for an
  old row with a valid ISPU category; implement the smallest fix and verify
  reporting/moderate/unhealthy counts exclude it.
- **M1 Retention:** make the cron invoke the same cleanup for JSONL and add an
  integration test proving an expired record is removed from the fallback path.
- **M2 Attribution:** test API-to-web source URL preservation and render the
  direct source hyperlink without accepting non-HTTP schemes.
- **M3 Boundary token:** test protected FastAPI routes and the Next station and
  telemetry proxies with missing and valid tokens. Keep the token out of
  response bodies and browser-facing code.
- **M4 Abuse controls:** add limiter key-pruning and proxy-header tests, retain
  request-size and rate-limit tests, and document the production quota/WAF
  boundary.

Gate: focused Python and TypeScript tests pass, full test suites pass, typecheck
passes, `git diff --check` passes, and the deployment plan contains the exact
secret/rate-limit/retention variables the owner must set.

## Milestones and action envelopes

### M0. Choose the cost and privacy posture

Owner: project owner.

1. Decide between the recommended PostgreSQL pilot and the strict-$0 snapshot
   fallback.
2. In Google AI Studio, confirm the API key belongs to the intended project,
   check that `gemini-3.5-flash-lite` is available, and record the active
   quota limits.
3. Decide whether the free-tier provider data-use terms are acceptable for
   anonymous public prompts. If not, use a paid Google tier or revise the
   privacy notice and consent language before launch.
4. Confirm that `napasjakarta.armasn.dev` is not already used by another DNS
   record or service.

Gate: written choice of storage path and provider privacy posture.

### M1. Prepare a deployable repository candidate

Owner: Codex after approval, then project owner reviews the diff.

1. Create a `web` production image with Node 24, `npm ci`, `eve build`,
   `next build`, and the two-process entrypoint bound to Railway's `$PORT`.
2. Add a separate API service configuration using the existing Python image
   and `uvicorn app.api:app --host 0.0.0.0 --port $PORT`.
3. Use `/api/health` for the web health check and `/health` for the API.
4. Add tests or smoke scripts for private API routing, missing Gemini key,
   provider timeout, tool failure, station-source failure, and refresh reset.
5. Fix or explicitly gate the five audit findings before calling the service
   production-ready:
   - legacy Railway entrypoint,
   - stale station freshness semantics,
   - JSONL fallback retention,
   - non-clickable station source URLs,
   - public telemetry abuse control.
6. Update deployment docs and `.env.example` to show Gemini and the actual
   two-service topology. Keep secrets as placeholders only.

Gate: clean candidate commit, typecheck, production build, Docker image build,
tests, and local two-service smoke test all pass. Keep the existing legacy
commit available for rollback.

### M2. Create the Railway project

Owner: project owner in Railway.

1. Create a new Railway project and a `production` environment. Do not
   repoint the existing legacy service yet.
2. Add PostgreSQL if M0 selected the live-data path. Keep it private and use
   Railway reference variables rather than copying credentials manually.
3. Create the `api` service from the repository root and set its explicit API
   start command and health check.
4. Create the `web` service from the `web` directory or the approved web
   Dockerfile. Set its explicit build/start behavior and health check.
5. Create the `ingestion` cron service for the PostgreSQL path or whenever the
   strict-$0 JSONL fallback volume is retained. Use the existing short-lived
   command `python -m ingestion.railway_cron` and the desired UTC schedule.
   Confirm every run exits; Railway skips a later run if the previous cron
   execution remains active.
6. Attach a small API Volume only if the fallback JSONL path is retained;
   mount it to a dedicated runtime path rather than shadowing packaged seed
   data.

### M3. Set variables and secrets

Owner: project owner in Railway. Seal secrets where Railway supports it.

API service:

```text
ENVIRONMENT=production
DATA_DIR=/app/data
POSTGRES_DSN=${{Postgres.DATABASE_URL}}
SOURCE_DATA_URL=https://udara.jakarta.go.id/
RETRIEVAL_MODE=hybrid
PROMPT_VARIANT=strict
INTERACTION_RETENTION_DAYS=30
INTERACTION_CLEANUP_INTERVAL_SECONDS=3600
MONITORING_DB=/app/runtime/interactions.jsonl   # only with the fallback volume
APP_VERSION=<release version>
GIT_COMMIT=<candidate commit>
BUILD_TIME=<UTC build time>
RUNTIME_REFRESH_TTL_SECONDS=60
NAPAS_INTERNAL_TOKEN=<same long random value in web and api>
TRUST_PROXY_HEADERS=true
CHAT_RATE_LIMIT_MAX=12
CHAT_RATE_LIMIT_WINDOW_SECONDS=60
CHAT_GLOBAL_RATE_LIMIT_MAX=60
CHAT_GLOBAL_RATE_LIMIT_WINDOW_SECONDS=60
TELEMETRY_RATE_LIMIT_MAX=120
TELEMETRY_RATE_LIMIT_WINDOW_SECONDS=60
```

Web service:

```text
GEMINI_API_KEY=<sealed Google key>
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_REQUEST_TIMEOUT_MS=120000
NAPAS_API_ORIGIN=http://${{api.RAILWAY_PRIVATE_DOMAIN}}:${{api.PORT}}
NAPAS_INTERNAL_TOKEN=<same long random value in web and api>
TRUST_PROXY_HEADERS=true
CHAT_RATE_LIMIT_MAX=12
CHAT_RATE_LIMIT_WINDOW_MS=60000
CHAT_GLOBAL_RATE_LIMIT_MAX=60
CHAT_GLOBAL_RATE_LIMIT_WINDOW_MS=60000
TELEMETRY_RATE_LIMIT_MAX=120
TELEMETRY_RATE_LIMIT_WINDOW_MS=60000
NEXT_PUBLIC_MAP_STYLE_URL=<approved production map style, if not the preview>
```

Do not copy `GEMINI_API_KEY` into a `NEXT_PUBLIC_*` variable. Do not add the
old Anthropic variables to the new web service. Do not expose `POSTGRES_DSN`
or the API public URL to browser code.

### M4. Initialize and smoke-test the origin

Owner: project owner, with Codex reviewing results.

1. Deploy API and confirm `/health`, `/version`, `/sources`, and `/stations`
   return expected JSON. Confirm `source_mode`, `measurement_store`, and
   `data_age_seconds` are honest.
2. Run one ingestion execution manually or wait for the first cron run. Check
   the source status, row count, validation result, and `ingestion_runs` record.
3. Deploy web and open its Railway-generated domain. Confirm the page loads,
   the map calls `/api/stations`, and the server can reach the private API.
4. Submit English and Indonesian questions. Exercise a current-air-quality
   tool call, a source-grounded answer, a provider failure, and a timeout.
5. Confirm the UI shows thinking, smooth answer delivery, citations, feedback,
   and suggestions returning after a completed turn.
6. Refresh the browser and confirm the transcript, selected station, topic,
   and feedback state are gone. Confirm only the intended language preference
   survives.
7. Submit one feedback event and verify it is linked to the anonymous answer
   turn without identity fields.
8. Inspect logs for secrets, raw API keys, unexpected personal data, and
   misleading demo/live labels.
9. Check Railway usage after the first day and again after one week. Treat the
   Free plan's `$1` credit as a budget ceiling, not an availability promise.

Gate: all origin checks pass and the runtime data is either validated live or
clearly labelled fallback. Keep the generated Railway domains available.

### M5. Attach `napasjakarta.armasn.dev`

Owner: project owner in Railway and Cloudflare.

1. In the Railway `web` service, add the custom domain
   `napasjakarta.armasn.dev`.
2. Copy the exact Railway CNAME target and TXT verification name/value.
3. In Cloudflare DNS, add the CNAME for `napasjakarta` and the TXT record
   exactly as Railway shows. Keep the TXT record DNS-only. Start the CNAME
   DNS-only if verification or certificate issuance is unclear.
4. Wait for Railway to show the DNS record as valid and the certificate as
   issued. Then enable Cloudflare proxying for the web CNAME if desired and
   set SSL/TLS to Full (strict). Do not proxy a verification record.
5. Validate from a clean network:

```bash
dig +short CNAME napasjakarta.armasn.dev
dig +short TXT <Railway-verification-name>
curl --fail --location https://napasjakarta.armasn.dev/
```

6. Repeat the full browser smoke suite against the custom hostname. Confirm
   no browser request attempts to reach the private API hostname.
7. Update README and deployment links only after this gate passes. Keep the
   Railway-generated web domain as the rollback origin.

### M6. Cut over and operate

Owner: project owner.

1. Announce the custom hostname as the canonical URL only after M5.
2. Leave the legacy Railway service intact for the agreed rollback window.
3. Review daily for the first week: Railway usage, Gemini quota, API health,
   source freshness, ingestion status, telemetry retention, and error rate.
4. Re-run the adversarial audit after the first hosted smoke pass.
5. Only after a stable rollback window, decide whether to retire the legacy
   service. Do not delete it as part of the first cutover.

## Required evidence

- Candidate commit SHA and clean working-tree check.
- Local `npm run typecheck`, `npm run build`, TypeScript tests, Python tests,
  and `git diff --check` output.
- Railway deployment IDs for `web`, `api`, and optional `ingestion`.
- API responses from `/health`, `/version`, `/sources`, and `/stations` with
  secrets and private URLs redacted.
- One successful and one failed ingestion result.
- Browser evidence for English, Indonesian, mobile layout, tool call, source
  disclosure, feedback, refresh reset, and provider failure.
- Railway private-domain routing evidence and absence of an unnecessary public
  API domain.
- Cloudflare DNS/TXT verification and HTTPS certificate status.
- First-day and first-week Railway/Gemini usage snapshots.

## Gates and stop conditions

Stop before DNS if any of these is true:

- Railway is still starting `app.web:app` for the public surface.
- The web cannot reach the API over the private network.
- `/sources` or UI labels imply live data while the API reports fallback.
- The Gemini key appears in a client bundle, response, or log.
- A refresh restores chat content or feedback.
- Telemetry accepts identity fields or has no bounded retention path.
- The selected free-tier Google data-use posture has not been accepted.
- Railway usage indicates the chosen shape cannot stay within the agreed
  budget.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Free Railway credit is exhausted | Start with a small pilot, monitor usage, and use the strict-$0 snapshot path if needed. |
| Gemini free quota is exhausted | Set request timeouts, rate-limit public chat, show recoverable errors, and monitor quota. |
| Source feed is stale or unavailable | Preserve last validated snapshot, show freshness/source mode, and never relabel fallback as live. |
| API is accidentally public | Use a private Railway domain after smoke testing and remove the public API domain. |
| Cloudflare verification fails | Keep TXT DNS-only, follow Railway's exact records, and retain the Railway origin. |
| Telemetry fallback grows without bound | Fix JSONL retention before enabling it in production; prefer PostgreSQL cleanup. |
| Data schema or app rollback is incompatible | Avoid destructive migrations, keep the legacy service, and test rollback before cutover. |
| Free-tier provider data terms conflict with privacy promise | Use paid Gemini tier or revise the product notice before public launch. |

## Rollback

1. Keep the old Railway service and generated domain running until the rollback
   window closes.
2. For an application regression, redeploy the last known-good web/API commit
   and leave PostgreSQL data intact.
3. For a domain regression, remove or reassign the custom domain in Railway
   and restore the last verified Cloudflare CNAME target. Keep the old DNS/TXT
   values recorded before changing them.
4. For a Gemini failure, temporarily disable chat generation or use the
   approved deterministic fallback; do not expose the key or silently switch
   to an unapproved provider.
5. For a data-source failure, retain the last validated observations and make
   the stale state visible. Do not wipe the database or publish a demo snapshot
   as current data.

## Attempt ledger

| Date | Action | Result | Evidence / next action |
| --- | --- | --- | --- |
| 2026-09-27 | Audited deployment baseline and provider docs | Complete | Current Railway entrypoint mismatch recorded; plan prepared. |
| 2026-09-27 | Deployment execution | Not started | Await M0 storage/privacy decision; repository hardening is now locally implemented but no external deployment has been performed. |
| 2026-09-27 | Security/data hardening implementation | Complete locally | Freshness fail-closed, JSONL retention on write and cron, direct source URL preservation/linking, server-only API token, and chat/telemetry limits implemented. Focused Python tests: 44 passed; TypeScript tests: 31 passed; web typecheck/build passed. Full Python suite is 143 passed with 4 pre-existing legacy NiceGUI contract failures. |
| 2026-09-27 | Chat and deployment packaging | Complete locally | Eve stream responses are marked `no-store, no-transform`; clean local suggested chat completed with an answer; the web image builds from a clean Docker context and its container passed `/api/health`, `/eve/v1/info`, and a session/turn smoke test. Deployment remains unstarted. |

## Progress

- M0: not started
- M1: complete locally; awaiting repository review and merge
- M2: not started
- M3: not started
- M4: not started
- M5: not started
- M6: not started
- Security/data hardening slice: complete locally; awaiting clean-candidate review and deployment smoke evidence.

## Change history

- 2026-09-27: initial deployment plan created from the whole-app audit and
  current Railway, Google, and Cloudflare documentation.
- 2026-09-27: added the strict-$0 security/data-hardening architecture,
  implementation boundary, environment contract, evidence, and rollback notes.

## External references

- [Railway pricing plans](https://docs.railway.com/pricing/plans)
- [Railway custom domains](https://docs.railway.com/networking/domains/working-with-domains)
- [Railway private networking](https://docs.railway.com/guides/lock-down-production-project)
- [Railway volumes](https://docs.railway.com/volumes)
- [Railway cron jobs](https://docs.railway.com/cron-jobs)
- [Gemini API models](https://ai.google.dev/gemini-api/docs/models)
- [Gemini API keys](https://ai.google.dev/gemini-api/docs/api-key)
- [Gemini API pricing and data-use terms](https://ai.google.dev/gemini-api/docs/pricing)
- [Cloudflare proxy status](https://developers.cloudflare.com/dns/proxy-status/)
