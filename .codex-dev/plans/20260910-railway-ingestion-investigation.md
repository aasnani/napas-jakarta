# Railway ingestion investigation — napas-jakarta

## Goal
Identify and safely contain the Railway `ingestion` cron failure, preserving
the last good snapshot and allowing the existing hourly schedule to retry on
the next run; keep the repository in `~/Documents/Projects` without losing
pre-existing working changes.

## Non-goals
- Do not restart, replay, or backfill data in this change.
- Do not change Railway variables, services, schedules, or persistent data.
- Do not expose secret values or sensitive payloads.

## Verified baseline
- Repository: `/home/armand/napas-jakarta`, branch `main`, aligned with
  `origin/main` before investigation; pre-existing dirty changes are present
  in `app/citations.py`, `app/web.py`, `app/webui/state.py`,
  `app/webui/theme.py`, and untracked `app/i18n.py`.
- Railway project: `napas-jakarta`, production environment, cron service
  `ingestion`, schedule `0 * * * *`; service is currently crashed.
- Latest successful runs completed through `2026-09-10T11:01:04Z`.
- Failed run at `2026-09-10T12:03:02Z` raised `UnicodeDecodeError` in
  `ingestion/official.py:188` while decoding the configured source response
  as `utf-8-sig`; the response began with bytes `ff d8 ff e0`, i.e. JPEG data.
- A direct read-only request to `https://udara.jakarta.go.id/` returned HTTP
  200 with a 146633-byte body beginning with the same JPEG signature.
- The deployed flow calls `fetch_measurements()` before the fallback branch can
  handle the error; `UnicodeDecodeError` is not a `requests.RequestException`.

## Constraints
- Preserve all pre-existing dirty work; no reset, checkout, or cleanup of user
  files.
- Railway deployment is authorized only for the committed ingestion fix; do
  not deploy unrelated dirty work.
- The move is explicitly authorized by the user after investigation.
- Do not commit or push without a separate verified implementation request.

## Material-change boundary
The repository relocation was authorized. The user has now authorized a
behavior change limited to treating unexpected source responses as a failed
refresh, retaining the last good data, and relying on the existing hourly cron
schedule for the next attempt. No source URL or Railway configuration change
is in scope.

## Architecture / ADRs
- Current production ingestion is a Railway cron container running
  `python -m ingestion.railway_cron` from `railway-cron.toml`.
- It fetches official measurements, validates them, publishes to PostgreSQL,
  refreshes historical data at the configured UTC hour, and records provenance.
- Current source-format handling is selected by URL suffix; the bare portal URL
  is parsed as HTML containing `window.__SPKU_DATA__`.

## Milestones
1. Capture repository and Railway baseline (complete).
2. Correlate Railway logs to the deployed ingestion code and reproduce the
   response-format boundary (complete).
3. Relocate the repository, verify git identity/status and working tree
   preservation (complete).
4. Implement and test safe source-failure fallback (complete).
5. Report root cause, behavior, operational impact, and safe deployment next
   action (complete).
6. Deploy the exact committed fix to the production ingestion service and
   verify the deployment (complete).
7. Reduce station-ingestion cadence to every six hours while aligning the
   daily historical refresh to a scheduled UTC hour, then deploy and verify
   (complete).

## Task envelopes
- Investigation: read-only repository inspection, CodeGraph mapping, Railway
  status/log/deployment queries, and one bounded source request.
- Relocation: filesystem move only; no edits to tracked application files
  (complete).
- Implementation: tests first, then minimal handling for decode/format failures
  at the source boundary; no in-job sleep or retry schedule change (complete).
- Verification: confirm new path, git branch, diff summary, remote, and no
  unexpected tracked-file changes.
- Deployment: create a clean archive from commit `b4180b1`, preserve the cron
  service command/config, deploy only to Railway service `ingestion`, and
  inspect deployment status and logs (passed).
- Cadence change: use `0 */6 * * *`; align
  `HISTORICAL_REFRESH_UTC_HOUR` from 17 to 18 UTC so the daily historical job
  remains reachable (passed).

## Required evidence and gates
- Reliability gate: identify failure layer, impact window, retry behavior, and
  why no rerun/backfill is safe to claim yet.
- Debugging gate: connect exact runtime exception to the source response bytes
  and the responsible code path; distinguish root cause from symptom.
- Test-architecture gate: unit/integration evidence proves a malformed source
  retains the prior local snapshot and records the failure for the next cron
  run (passed).
- Relocation gate: new path exists and old path is absent; dirty diff and
  untracked user file remain present (passed).

## Risks and rollback
- Risk: moving a dirty repository can break active shells or tooling that still
  references the old absolute path. Rollback is to move the directory back to
  `/home/armand/napas-jakarta` before any code changes.
- Risk: untracked generated `.codegraph/` is present from the investigation;
  preserve it rather than deleting user-visible files.
- Risk: retrying the cron could duplicate or alter persisted state; preserve the
  existing upsert/idempotency behavior and do not trigger a production replay.
- Risk: six-hour cadence increases maximum freshness delay and reduces the
  frequency of retention cleanup; verify the new operational bound.

## Attempt ledger
- Attempt 1: local and Railway evidence collection; succeeded in isolating the
  response-format failure.
- Attempt 2: implement only after a failing regression test; use the existing
  hourly Railway schedule rather than sleeping in the cron process.

## Progress
- Baseline, failure diagnosis, repository relocation, safe fallback
  implementation, and verification complete.

## Change history
- 2026-09-10: created after runtime evidence confirmed the Railway failure
  boundary; no application code changed.
- 2026-09-10: moved repository to `/home/armand/Documents/Projects/napas-jakarta`
  and verified branch, remote, dirty paths, and old-path absence.
- 2026-09-10: user authorized safe fallback behavior; bounded research confirms
  the existing hourly cron is the appropriate 30–60 minute retry mechanism.
- 2026-09-10: added regression coverage and caught `UnicodeError`/`ValueError`
  source-format failures so the prior local snapshot is retained and the error
  is recorded for the next scheduled run.
- 2026-09-10: targeted tests (14) and Ruff passed; full suite reached 130
  passing but has 4 unrelated pre-existing UI contract failures in the user's
  dirty `app/web.py`/i18n work.
- 2026-09-10: user authorized production deployment of the committed fix;
  deployment must use a clean commit archive rather than the dirty checkout.
- 2026-09-10: deployed clean commit `b4180b1` to production Railway service
  `ingestion` as deployment `0bbf3075-d056-49a5-ae66-59d4c2b42881`; Railway
  reports the cron online with the next scheduled run pending.
- 2026-09-10: verified the first scheduled post-deploy run completed at
  `2026-09-10T15:01:18Z`; logs reported 296 measurements and no unhandled
  exception.
- 2026-09-10: user requested six-hour cadence; identified that the prior 17 UTC
  historical refresh hour would be skipped, so the safe change aligns it to
  18 UTC.
- 2026-09-10: applied the schedule-only Railway IaC change; deployment
  `f03fe09b-16ef-4277-a4be-349a50692d4a` succeeded and Railway reports
  `0 */6 * * *` with the ingestion service online. Production variable
  `HISTORICAL_REFRESH_UTC_HOUR=18` is aligned.
