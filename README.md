<p align="center">
  <img src="assets/napas-jakarta-air-icon.png" width="104" alt="Napas Jakarta air-quality mark">
</p>

<h1 align="center">Napas Jakarta</h1>

<p align="center"><strong>Understand Jakarta’s air, why it changes, and what you can do next.</strong></p>

<p align="center">
  A bilingual, citation-grounded companion for current station observations,
  city-level air-quality context, policy, and practical exposure reduction.
</p>

<p align="center">
  <a href="https://web-production-e07b9.up.railway.app"><strong>Open the live app →</strong></a>
  · <a href="https://web-production-e07b9.up.railway.app/docs">API</a>
</p>

[![Tests](https://github.com/aasnani/napas-jakarta/actions/workflows/test.yml/badge.svg)](https://github.com/aasnani/napas-jakarta/actions/workflows/test.yml)

Napas Jakarta brings station observations, an interactive map, and a bilingual conversational advisor together in one calm, understandable workspace. It helps residents and organizations turn air-quality data into practical next steps.

## What it offers

- **Current local visibility.** Explore available Jakarta monitoring stations with ISPU, PM2.5, observation times, freshness status, district filters, and direct source links.
- **A useful conversation layer.** Ask questions in English or Bahasa Indonesia about current conditions, comparisons, historical context, standards, policy, health guidance, and exposure reduction.
- **Map-based understanding.** Use station markers, filters, station detail, and heatmap views to see how conditions vary across the city.
- **Evidence you can inspect.** Answers are designed around official monitoring sources, curated institutional evidence, structured retrieval, and citations rather than unsupported guesses.
- **Responsible communication.** The product distinguishes station readings, city-level context, historical data, stale readings, and fallback data so one number is not mistaken for the whole city.

## Useful for

Napas can support public-information services, workplace and campus wellbeing, community programs, environmental education, civic engagement, and early-stage city or NGO pilots. It is designed to make technical air-quality information easier to understand without replacing official authorities, medical advice, or regulatory guidance.

## Privacy and security

- No account or login is required, and browser conversation state is not restored as persistent chat history.
- Model credentials remain server-side. The public web app communicates with a private API through an internal service token.
- Chat input is bounded, attachments are disabled, and chat, telemetry, and feedback endpoints have rate limits and payload validation.
- The product is not built for data harvesting or advertising profiles. Limited anonymous product telemetry may include questions, answers, turn metadata, and explicit feedback for quality improvement. It does not include account, cookie, IP, device, or contact identity fields. Users should not enter sensitive personal or health details.

## Cost and deployment

The initial deployment is designed around a strict $0 starting point: Railway free allocation, a lightweight web service, a private API service, and a bounded JSONL telemetry fallback without requiring a paid database. PostgreSQL and scheduled ingestion can be added when a live-data operation needs them. Hosting, model, or data-provider charges may apply if usage exceeds free quotas or a paid capacity is selected.

The architecture can run as a standalone public service or as part of a broader city, workplace, education, or community information program. It supports bilingual presentation, official source configuration, scheduled data refresh, aggregate operational monitoring, and a clear fallback when live feeds are unavailable.

## Important boundaries

- A station reading is local and time-stamped, not a citywide or indoor average.
- Historical context is labelled separately and should not be read as official station history.
- Health content is educational, not a diagnosis or emergency triage service.
- Policy information is date- and source-bounded; users should verify obligations with the responsible authority.

For the technical history, architecture notes, evaluation record, and deployment details, see the [archived project README](README.historical.md).
