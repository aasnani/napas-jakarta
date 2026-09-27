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
- Left chat dock with a larger Napas product logo beside the “Napas assistant”
  label, a concise welcome, suggested prompts, and a composer.
- A topic dropdown sits to the right of the assistant heading. It opens the
  source-grounded topic list without leaving the chat window.
- Above the composer, the selected topic is shown above the selected location
  context. Both are removable context chips and are used to tailor the next
  answer without becoming hidden conversation state.
- Main map canvas centered on Jakarta with detailed streets, waterways,
  boundaries, labels, landmarks, and air-quality station markers.
- A quiet source/freshness strip that makes current, stale, and limited-data
  states explicit without presenting the product as a “demo view.”

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
- The map legend expands horizontally into the available right-side space while
  the selected-location detail becomes more compact. The expanded area also
  contains short explanations of ISPU, PM2.5, PM10, units, categories, and
  observation freshness.

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
- Choosing a topic or location updates the next-turn context visibly. The
  assistant must distinguish a user-selected context from a model inference
  and must retain source, freshness, and health-safety boundaries.

### Topic navigation and answer context

The topic menu is a compact discovery layer beside the assistant heading. It
should open a grouped list of suggested questions, then place the chosen topic
above the chosen location in the composer context rail. Selecting a suggested
question fills or submits a clearly visible prompt; it must not silently send a
question without an obvious user action.

The first topic groups are grounded in the current source catalog and local
knowledge corpus:

- Understand today's air: current station conditions, Jakarta map, ISPU,
  PM2.5, PM10, categories, units, timestamps, stale readings, and station
  versus city-level data.
- Protect yourself now: bad-air-day actions, outdoor exertion, respirators,
  ventilation, exposure reduction, and when to seek qualified care.
- Children, pregnancy, older adults, and health-sensitive people: cautious,
  non-diagnostic guidance tailored to vulnerability and exposure. Pregnancy-
  specific evidence must be reviewed and cited before dedicated advice is
  presented as authoritative.
- Outdoor and professional workers: time outdoors, strenuous work, exposure
  reduction, scheduling, and employer/public-health context.
- Improve home air: clean-air rooms, portable cleaners, CADR, HVAC/MERV
  filtration, cooking or combustion sources, ventilation, and maintenance.
- Why Jakarta's air is unhealthy: transport, industry and power, regional
  transport, seasonal accumulation, weather, source-apportionment limits, and
  high-rise versus ground-level exposure.
- What can I do to help: transport choices, vehicle-emissions testing,
  household actions, public participation, and accountability.
- Policy, law, and implementation: ISPU methodology, ambient standards,
  Jakarta regulations, ERP/policy history, SPPU, CEMS, court records, and the
  difference between a proposal, a legal instrument, an official programme,
  and evidence of implementation.
- Trends and comparisons: historical PM2.5/PM10 context, station comparisons,
  time trends, and the distinction between modelled city series and station
  observations.

The current grounding inventory is recorded in `data/sources.yaml`: 30 source
records are registered and 29 documents are locally materialized under
`data/docs/`. The Satu Data Jakarta ISPU 2023 record is currently provenance-
only and explicitly not claimed as a downloaded local dataset. Topic labels
and suggested questions must be available in both English and Indonesian and
must map to the same source IDs and safety boundaries.

The roadmap also includes a refreshable editorial layer for approved articles
and newsletters. It should prefer publisher APIs, RSS/Atom, or newsletter feeds
and use explicitly allowlisted page fetches only where permitted. Each item
needs publisher, canonical URL, publication/update time, fetch time, language,
content hash, license/attribution, topic tags, and revision status. Editorial
updates can supply “latest” context, but must remain visibly distinct from
official measurements, laws, guidance, and research evidence.

### Anonymous interaction telemetry

- The public `/` workspace starts empty after a full page refresh. It does not
  restore chat history from a cookie, local storage, URL session, or account.
- Completed assistant turns and usefulness feedback are product telemetry, not
  user profiles. The browser creates one random in-memory grouping ID per page
  load; it is not persisted and the application payload contains no account,
  IP, device, or contact fields.
- A completed turn stores the question, answer text, interaction ID, turn
  number, and transcript message count. A positive or negative feedback event
  links to that answer and the same anonymous grouping ID.
- Feedback is exposed only for the latest completed answer and disappears when
  the next turn begins. Telemetry delivery is best-effort and never blocks the
  chat experience.
- Interaction and feedback rows remain private to the service and database
  operators, with the bounded `INTERACTION_RETENTION_DAYS` cleanup window (30
  days by default).

## Visual direction

Use one coherent language: calm civic utility with a light, editorial surface
and a dark teal brand anchor. The map is the visual center; the assistant is a
quiet analytical companion rather than a decorative mascot.

The initial implementation stays close to the OpenDesign composition: an
editorial assistant transcript on the left; a structured map header with title,
three KPI cards, and filters; then a detailed map canvas, legend, and selected
station detail dock.

The next hierarchy pass should make the product feel finished rather than like
an example view:

- Remove “demo view,” “demo snapshot,” and similar implementation language from
  normal user-facing UI. Keep necessary source, freshness, and limitation
  messaging, but phrase it as trustworthy data status rather than scaffolding.
- Increase the Napas logo beside the assistant heading so the product identity
  is legible at a glance.
- Give the legend a wider horizontal region to the right of the map while
  reducing, but not hiding, the selected-location detail region.
- Use the added region for concise terminology cards: ISPU is an index, PM2.5
  and PM10 are concentrations with units and averaging periods, and station
  observations are not interchangeable with city-level model series.
- On mobile, make the same terminology and legend content available through a
  collapsible panel or mobile navigation destination rather than deleting it.

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

### Mobile: full feature parity with mobile navigation

Mobile is now a roadmap requirement. The mobile experience must retain the
desktop feature set: chat, topic selection, EN/ID selection, map and station
context, selected location, current/stale/source status, terminology,
citations, feedback, and contextual answer artifacts.

The two-column desktop relationship transforms into an assistant-first mobile
surface rather than simply shrinking both panes. The global navigation remains
at the top, followed by a centered Napas Advisor identity row. Beneath it,
station and topic selectors sit on the left while a Map action is anchored on
the right. Assistant chat, source-grounded topics, suggestions, and the
composer are the default view. Map opens as a full-screen pannable overlay;
the same top-right action becomes an X in place and closes the overlay. The
conversation and selection context remain mounted while the map is open.

The mobile milestone must validate portrait and landscape layouts, long
localized labels, touch targets, keyboard/panel overlap, map gestures, topic
and station menu scrolling, selection clearing, and access to every desktop
capability. It should avoid horizontal overflow and use progressive disclosure
for the legend, terminology, citations, and selected-location details.

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
- Refreshable articles and newsletters are ingested server-side through an
  allowlisted source registry; the chat does not fetch arbitrary URLs from
  user prompts. Failed or stale feeds remain labelled and do not silently
  replace validated source material.

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
- Current, stale, fallback, and source limitations are explicit without
  exposing “demo view” or implementation-scaffold language in normal UI copy.
- Citations are structured, linked, and source details are inspectable.
- The 24-inch desktop and 14-inch laptop compositions are covered by automated
  browser evidence at their agreed viewport bands.
- The default composition follows the OpenDesign assistant/map relationship,
  with the three KPI cards between the map title and filters.
- The assistant heading uses a prominent Napas logo, with a topic dropdown and
  selected-topic/selected-location context above the composer.
- Topic suggestions cover personal protection, home air, vulnerable people,
  outdoor workers, causes, individual action, policy, health, and trends, and
  are grounded in the registered source catalog.
- The topic navigator can surface dated, cited article/newsletter updates
  without confusing them with station observations or authoritative legal and
  health sources.
- The map uses a real interactive basemap with visible roads, waterways,
  labels, attribution, station markers, filtering, and station detail.
- The desktop legend expands horizontally into terminology and brief
  explanations while selected-location detail remains available in a compact
  region.
- A full refresh clears the public chat transcript; completed answer telemetry
  and explicit usefulness feedback remain anonymously persisted.
- Keyboard, reduced-motion, and error states are covered before release.
- Mobile has the desktop feature set behind an assistant-first layout with a
  full-screen Map overlay, station/topic selectors, and an in-place Map/X
  control. Portrait/landscape, keyboard, touch, localization, and
  progressive-disclosure evidence remain required before release.
- The old UI can be removed only after the new workspace passes the above
  checks.
