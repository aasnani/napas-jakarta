# Data contract

## Current status

The repository contains a clearly labeled demo snapshot. It is not a live feed.
The production connector accepts an official Jakarta CSV/JSON export through
`SOURCE_DATA_URL` and writes `data/processed/measurements.csv` after schema
validation. It also supports an explicit opt-in snapshot from
`https://udara.jakarta.go.id/`, whose published `__SPKU_DATA__` server-rendered
station block currently provides station IDs, district, timestamp, ISPU, and
PM2.5 values. That page format is checked and fails closed if it changes; it is
not treated as a guaranteed API. The Satu Data Jakarta search route is
`https://satudata.jakarta.go.id/backend/api/v2/satudata/search-v2`; use its
dataset metadata to select a stable export URL rather than scraping HTML.
Each run writes an ignored `data/ingestion_report.json` containing fetch time,
row/chunk counts, source, SHA-256 fingerprints, station coverage, and
validation counts for duplicates, units, negatives, and future timestamps. A
live fetch also stores a content-addressed raw snapshot under `data/raw/`.
The normalized measurement fingerprint excludes per-fetch `fetched_at`, so an
unchanged upstream snapshot retains the same checksum across refreshes.
When the processed file exists, both the API and Streamlit application consume
it automatically; otherwise they fall back to the committed demo snapshot.
`GET /sources` derives the displayed mode from both configuration and the
persisted report, preventing a live snapshot from being mislabeled after a
restart.
When `POSTGRES_DSN` is configured, validated rows are also upserted into the
typed PostgreSQL `measurements` table, using
`(station_id, observed_at, pollutant)` as the idempotency key.
URL-backed observations preserve their source URL and expose it as
`source_url` in structured tool responses; the committed demo source is
explicitly non-live.

## Required connector decision

Before connecting live data, verify that the official Jakarta source provides a
stable permitted interface with station identifiers, timestamps, units, quality
flags, and update frequency. Do not depend on an undocumented browser endpoint.

The committed demo snapshot remains the reliable scored core. For current
conditions, set `SOURCE_DATA_URL=https://udara.jakarta.go.id/` only after
reviewing the portal's current terms and attribution; otherwise link users to
the official portal.

## Invariants

- All timestamps are stored in UTC and displayed in Asia/Jakarta.
- ISPU is an index without a physical concentration unit.
- Concentration and ISPU are stored in separate fields.
- Missing values remain missing.
- Station observations are not automatically generalized to all Jakarta.
- Every displayed observation includes source and observed-at timestamp.
- Current answers include an explicit age/stale flag; stale observations are
  not presented as live conditions.
- Demo station coordinates are approximate and are never presented as official
  geospatial metadata. When `SOURCE_DATA_URL` is set to the official portal,
  the UI uses the portal's station IDs and coordinates instead.
