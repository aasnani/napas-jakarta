# Napas Jakarta single-workspace product design

## Status

Accepted direction, 2026-09-26.

This document is the authoritative product and architecture brief for the
replacement web experience. It supersedes the presentation-layer decision in
`docs/professional-ui-redesign-plan.md`, which describes the earlier NiceGUI
multi-page direction. The existing OpenDesign artifact is the visual reference
for the first workspace pass. Its chat/map composition is the accepted
presentation baseline; production implementation is React/Eve rather than a
direct HTML export.

## Product intent

Napas Jakarta is a spatial, conversational air-quality workspace for residents
and curious observers of Jakarta. The primary job is to let someone ask a
plain-language question, understand the current condition of the city, and
immediately see the relevant place, station, trend, or source without leaving
the workspace.

The product is one view. It is not a dashboard with peer-level pages, and it
does not include a public Monitoring surface. Map, overview, trends, station
detail, comparison, source evidence, and health guidance are contextual
components that appear inside the workspace in response to the conversation or
map selection.

## End-product experience

The home route is a single responsive workspace:

```text
┌─────────────────────────────────────────────────────────────┐
│ Napas logo / wordmark              freshness · language     │
├───────────────────┬─────────────────────────────────────────┤
│                   │                                         │
│ Conversational    │                                         │
│ assistant         │              Jakarta map                 │
│                   │                                         │
│                   │                                         │
│                   ├─────────────────────────────────────────┤
│                   │ Contextual result / station / trend     │
└───────────────────┴─────────────────────────────────────────┘
```

### Default state

- Top app bar with the real Napas logo and wordmark, freshness/source status,
  language control, and a compact help/terminology affordance.
- Left chat dock with a concise welcome, four starter prompts, and a composer.
- Main map canvas centered on Jakarta with detailed streets, waterways,
  boundaries, labels, landmarks, and air-quality station markers.
- A quiet source/freshness strip that makes demo, stale, and live states
  explicit.

### Contextual composition

- Asking for current conditions updates the answer and highlights relevant
  stations on the map.
- Selecting a station opens a station card without navigating away.
- Asking for a comparison opens a compact comparison table and adjusts map
  emphasis.
- Asking about change over time opens a trend chart below the answer or in a
  contextual panel.
- Source evidence is available as expandable cards and linked citations.
- Health guidance is a sourced, bounded response, not a medical diagnosis.

## Interaction rules

Every interaction follows intent → action → response → recoverable next step.

- Chat submits on explicit send; Enter inserts a newline unless the composer
  is configured for submit-on-enter.
- Streaming updates one stable assistant message instead of appending a new
  message for every token.
- The transcript follows the bottom only while the reader is already near the
  bottom. Scrolling upward pauses following and exposes a return-to-latest
  control.
- Tool activity is visible as short, human-readable steps such as “Checking
  current stations” rather than raw tool-call JSON.
- Map focus requested by the assistant is reversible and never prevents manual
  pan, zoom, filtering, or station selection.
- Every loading, empty, stale, error, and offline state has a useful next
  action. No blank panel is an acceptable state.
- The interface honors reduced-motion preferences and never uses motion to
  conceal latency or state changes.

## Visual direction

Use one coherent language: calm civic utility with a light, editorial surface
and a dark teal brand anchor. The map is the visual center; the assistant is a
quiet analytical companion rather than a decorative mascot.

The initial implementation stays close to the OpenDesign composition: an
editorial assistant transcript on the left; a structured map header with title,
three KPI cards, and filters; then a detailed map canvas, legend, and selected
station detail dock.

### Tokens

- Brand teal: `#086B68`; primary container: `#BDECE6`.
- Background: `#F7FAF9`; surface: `#FFFFFF`; elevated surface: `#EDF3F1`.
- Text: `#172B2B`; muted text: `#5E706E`; outline: `#B8C9C5`.
- Air-quality category colors are semantic data colors only:
  - Good `#2E7D32`
  - Moderate `#D6A700`
  - Unhealthy `#E45D20`
  - Very unhealthy `#C62828`
  - Hazardous `#6A1B9A`
  - Missing/stale `#78909C`
- Use 4 px spacing increments, 12 px card radii, restrained borders, and
  minimal elevation.
- Use a readable system/Roboto stack and keep prose around 70–80 characters per
  line.
- Status is never conveyed by color alone; every category has text and/or an
  icon.

## Target surfaces and responsive behavior

The physical device labels are design references; CSS responds to the available
browser viewport and cannot reliably detect whether a 1920 px display is a
24-inch monitor or a 14-inch laptop. We therefore define separate composition
modes and test the laptop mode at widths commonly produced by display scaling.

### Desktop reference: 24-inch, 1920 × 1080

- Wide mode begins at roughly 1600 CSS px.
- Keep the chat dock visually quiet at about 380–400 px while the map owns most
  of the horizontal field.
- Keep the contextual result surface visible below the map in the first frame.
- Use the full top-bar status treatment and the most generous workspace
  padding.

### Laptop reference: 14-inch, 1920 × 1080

- Compact mode is the 1280–1599 CSS px band; a 14-inch 1080p laptop at display
  scaling often presents a viewport in this range.
- Narrow the chat dock to about 320–350 px, reduce outer padding, and preserve
  the map/chat split rather than stacking the product by default.
- Keep the contextual result card compact so the map and composer remain
  usable within a shorter vertical viewport.
- Validate at a representative 1536 × 864 CSS viewport and at the smallest
  supported laptop width before treating the layout as ready.

### Mobile: intentionally parked

There is no agreed mobile target device or composition yet. Mobile-specific
decisions are intentionally deferred rather than inferred from the desktop
layout. The implementation should still avoid horizontal overflow and remain
usable as a basic stacked fallback, but mobile is not an end-product
acceptance target until a separate mobile design pass is approved.

The same workspace state can eventually be deep-linked through URL parameters
for selected station, map layer, date range, or conversation focus.

## Technology decisions

### Browser application

- Next.js + React + TypeScript.
- Next.js is selected over Vite because Eve has first-class Next.js mounting
  and same-origin routing through `withEve`, while still allowing a custom
  React interface.
- shadcn/Radix-style primitives for dialogs, popovers, tooltips, sheets,
  command surfaces, and accessible controls.
- Tailwind for layout utilities plus a small Napas CSS-variable token layer.
- Streamdown or an equivalent streaming-safe Markdown renderer for assistant
  content and citations.

### Agent runtime

- Vercel `eve` owns agent sessions, streaming, typed tools, skills, evals, and
  durable workflow state.
- `eve/react` powers the browser session hook; `eve/client` is available for
  custom UI, tests, or server-to-server calls.
- Pin Eve because the framework is still beta. Keep an adapter around its
  event stream so UI components depend on Napas events, not framework internals.

### Data and visualization

- MapLibre GL JS for the production map, with vector tiles for the basemap and
  GeoJSON sources/layers for stations, boundaries, selection, and overlays.
- The current preview uses the OpenFreeMap Liberty style through MapLibre so
  the map is a real, labelled Jakarta basemap rather than a CSS illustration.
  Keep the style URL replaceable until production licensing, attribution,
  availability, and rate limits are accepted.
- Apache ECharts for trend and comparison charts.
- Existing FastAPI/Pydantic service remains the authoritative air-quality data
  API during the first migration slice.
- PostgreSQL remains the runtime store. Qdrant remains optional for retrieval.

### Quality

- Keep Python Pytest/Ruff for the data and domain layer.
- Add Vitest/Testing Library for frontend units and components.
- Add Playwright for one-workspace browser flows at desktop, tablet, and mobile
  widths.
- Add Eve evals for grounding, correct tool choice, abstention, freshness, and
  citation completeness.

## Eve agent organization

```text
agent/
  agent.ts
  instructions.md
  skills/
    air-quality-interpretation.md
    source-grounding.md
    health-guidance.md
    map-context.md
  tools/
    get-current-air-quality.ts
    get-station-details.ts
    compare-areas.ts
    get-trend.ts
    find-source-evidence.ts
  evals/
    air-quality-answering.eval.ts
```

Initial tools are intentionally narrow:

- `get_current_air_quality`
- `get_station_details`
- `compare_areas`
- `get_trend`
- `find_source_evidence`
- `get_health_guidance`

No unrestricted SQL, arbitrary browser control, or broad web-search tool is
part of the first product boundary.

## Agent-to-UI contract

The agent returns structured data and provenance. It never returns arbitrary
HTML or directly mutates browser state. The frontend renders a typed artifact
union such as:

```ts
type NapasArtifact =
  | { type: "map-focus"; stationIds: string[]; bounds?: Bounds }
  | { type: "station-card"; stationId: string }
  | { type: "trend-chart"; metric: "pm25" | "pm10"; points: Point[] }
  | { type: "comparison-table"; rows: ComparisonRow[] }
  | { type: "source-list"; sources: Source[] };
```

The frontend owns presentation and interaction. Tool responses include source
IDs, observed-at timestamps, freshness, and any limitations needed to keep a
response honest. Demo station coordinates remain explicitly approximate until
official geospatial metadata is available.

## Repository boundary

### Retain initially

- FastAPI/Pydantic data contracts.
- PostgreSQL runtime data and packaged fallback data.
- Existing ingestion, provenance, source validation, retrieval, and evaluation
  logic.
- Deterministic air-quality calculations from `app/tools.py`.
- Docker/Railway operational infrastructure while the new web service is
  introduced.

### Retire after parity

- NiceGUI and Quasar as the primary web UI.
- Streamlit compatibility UI.
- NiceGUI page routes and client-state implementation.
- `ui.leaflet` and the prototype's inline SVG map implementation.
- Public Monitoring page and peer-level Overview/Trends/Map/Ask navigation.

The first implementation does not delete the old UI. It adds the new web/agent
workspace beside it so rollback remains possible until browser acceptance is
complete.

## Deployment direction

The target topology is:

```text
Browser → Next.js + Eve → FastAPI data API → PostgreSQL / optional Qdrant
                                      ↑
                              ingestion jobs
```

Eve can be hosted as a Node service on the existing infrastructure or deployed
with Vercel. A self-hosted deployment must provide persistent workflow state,
production route authentication, and the Eve workflow callback routes. The
existing PostgreSQL service is a candidate for Eve's workflow world, but that
choice is a deployment milestone, not a reason to couple the first UI slice to
it.

## Acceptance criteria for the intended end product

- One primary workspace route with no Monitoring page.
- Chat and map remain visible as the default desktop composition.
- The assistant can invoke a typed air-quality tool and render a contextual
  result component.
- A map selection can provide context to the next assistant turn.
- Current data, demo data, stale data, and source limitations are explicit.
- Citations are structured, linked, and source details are inspectable.
- The 24-inch desktop and 14-inch laptop compositions are covered by automated
  browser evidence at their agreed viewport bands.
- The default composition follows the OpenDesign assistant/map relationship,
  with the three KPI cards between the map title and filters.
- The map uses a real interactive basemap with visible roads, waterways,
  labels, attribution, station markers, filtering, and station detail.
- Keyboard, reduced-motion, and error states are covered before release.
- Mobile remains a separately approved design milestone, not an implicit
  acceptance target.
- The old UI can be removed only after the new workspace passes the above
  checks.
