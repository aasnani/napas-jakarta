# Napas Jakarta application state

**Last verified:** 27 September 2026 (Asia/Jakarta)

This is the concise operational checkpoint for Napas Jakarta. It records the
broad product, data, deployment, security, and observability state so future
work can resume without relying on chat history or local scratch notes. Keep
this file current when any of those broad areas changes. Do not record secrets,
tokens, raw logs, or user-provided content here.

## Product

Napas Jakarta is a bilingual English and Indonesian air-quality assistant and
map for Jakarta. It combines current station observations with clear
terminology, citations, historical or city-level context, and practical
exposure guidance. The interface supports desktop and mobile layouts, station
selection, air-quality filtering, map exploration, a heatmap view, and a
grounded chat experience.

The product does not require an end-user account. Answers should distinguish a
station observation from citywide context, show the observation time and
source, and abstain when the required evidence is unavailable.

## Repository and release state

- The remote source of truth is `origin/main` at commit `0a13d1a`, which includes
  the merged Railway structured-logging work from [PR #3](https://github.com/aasnani/napas-jakarta/pull/3).
- The latest verified production web deployment was Railway deployment
  `e6e04dc5-ee10-47ee-a2df-668b5b37253d`, reported `SUCCESS`, and was built
  from that merged state.
- The local checkout used for this snapshot was stale and divergent from
  `origin/main`, with pre-existing local modifications and scratch files. Those
  changes were intentionally left untouched. Reconcile the checkout before a
  future release; do not discard local work without review.
- Detailed planning files under `.codex-dev/plans/` are historical working
  notes. This file is the high-level state reference.

## Production deployment

Production runs in Railway under one project and environment with these
responsibilities:

- **Web:** public Next.js and Eve application at
  [napasjakarta.armasn.dev](https://napasjakarta.armasn.dev).
- **API:** private server-side data boundary used by the web and ingestion
  services.
- **Ingestion:** scheduled refresh of official station data.
- **PostgreSQL:** shared runtime store for current observations and related
  operational data.

The web service is rooted at `/web`; the API service remains rooted at `/`.
The web readiness check includes Eve readiness. The last verified public health
check reported the web service as healthy and Eve as ready.

Cloudflare manages the custom-domain DNS path. The Railway web service is not
currently connected to GitHub for automatic deploys, so a repository merge does
not by itself prove that production changed. Verify the deployed commit,
Railway deployment status, and the public health endpoint after each release.

## Data and freshness

- The primary live source is the official Jakarta air-quality monitoring
  network, with source and station provenance retained for attribution.
- Ingestion writes the current catalog and observations to Railway PostgreSQL.
- Readings older than the 24-hour freshness window are stale and must not be
  presented as current air-quality conditions. Readings within that window may
  be presented as fresh, with their timestamp still visible.
- Historical or city-level context is labelled separately from official station
  observations. Packaged fallback data is clearly identified as fallback, not
  live data.
- Station-level source links should remain directly actionable so a user can
  open the underlying source for that observation.

## Security and privacy posture

- The API is intended to remain private to the Railway project. Server-to-server
  calls use the configured internal authentication boundary; the browser does
  not receive that credential.
- Secrets and provider credentials belong in Railway environment variables, not
  the repository or client bundles.
- Chat and telemetry requests have bounded input and request protection. User
  input is treated as untrusted content, not as an instruction to change system
  behavior or access secrets.
- The application does not require login and should avoid collecting identity
  data. Interaction telemetry is best-effort, bounded, and retention-controlled.
- The web code now supports opt-in Google Analytics 4 using Napas's own
  measurement ID. It loads only after explicit browser consent, tracks
  public-page views and aggregate map or assistant actions, and does not send
  chat text, station names, session IDs, or URL parameters. Ad storage, Google
  signals, and ads personalization are disabled. Production analytics still
  requires the web service to be redeployed and a visitor to opt in.

## Logging and retention

- The first monitoring slice uses Railway's built-in Logs and Log Explorer. No
  separate Loki, Grafana, or paid logging service is deployed.
- Application events are emitted as structured, one-line records with broad
  debug, info, warning, and error severity. Important events include request
  completion, rejected chat input, chat/provider failures, missing provider
  configuration, and telemetry-forwarding failures.
- Request IDs support correlation between a user-visible failure and its server
  logs.
- Diagnostic stack traces stay in Railway logs. Authorization headers, cookies,
  tokens, and provider secrets must never be logged or forwarded to clients.
- Railway Hobby Log Explorer retention is **7 days**. Export or introduce a
  dedicated backend only if longer retention, alerting, or historical analysis
  becomes necessary.
- Railway health checks establish process and dependency readiness. They do not
  prove that a semantic chat answer succeeded, so chat/provider failures must
  be diagnosed through structured application logs.

## Search discovery and analytics

- The web code defines canonical metadata, a bilingual English and Indonesian
  air-quality guide, `robots.txt`, and an XML sitemap. The sitemap lists the
  public homepage and both guide pages.
- Google Analytics support is opt-in and uses Napas's configured public
  measurement ID, with `NEXT_PUBLIC_GA_MEASUREMENT_ID` available as a build-time
  override. No analytics event contains a prompt, station name, session ID, or
  query string. See `web/SEO_AND_GOOGLE_SETUP.md` for the setup and content plan.
- The owner reports that the Napas Search Console Domain property is verified.
  Sitemap submission is pending. The dedicated GA4 property and linking the
  two Google properties also remain unconfirmed.
- The production homepage returned HTTP 200 during the 27 September 2026
  readiness check, while `/sitemap.xml` returned HTTP 404. The local search
  discovery changes have not been deployed. Reconcile the stale local checkout
  with `origin/main` before a release, then verify the deployed commit and live
  search files.

## Current operating boundaries

- Railway-native logs are the current operational monitoring solution. Email
  alerting and a Loki/Grafana stack are not currently deployed.
- Production verification should cover the public web surface, API readiness,
  ingestion freshness, station marker availability, chat success, and the
  deployed commit.
- The public app is intentionally evidence-grounded. Do not expand the visible
  topic surface without a corresponding typed retrieval path, source coverage,
  and an abstention or failure mode.

## Updating this file

Update the date and affected sections when any of the following changes:

1. production services, domains, deployment workflow, or health behavior;
2. official data sources, freshness rules, provenance, or fallback behavior;
3. logging, retention, alerting, or observability services;
4. authentication, secrets, input limits, privacy, or data handling; or
5. a major user-facing capability or known operational boundary.

After updating, verify that this file still describes the deployed state rather
than only the local working tree.
