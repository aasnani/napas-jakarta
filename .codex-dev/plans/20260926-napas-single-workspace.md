# Napas single-workspace replacement and free-tier deployment

## Goal

Build the accepted Napas Jakarta end product as one conversational spatial
workspace: a Next.js/React frontend, Eve agent runtime, detailed MapLibre map,
and contextual result components backed by the existing verified FastAPI/data
layer. Move the active chat to Gemini Flash-Lite and shape deployment around a
free-tier Railway service plus durable low-volume anonymous telemetry.

## Non-goals

- Do not preserve the existing NiceGUI visual layout or page hierarchy.
- Do not build a public Monitoring page.
- Do not rewrite ingestion, PostgreSQL schemas, retrieval quality logic, or
  source validation in the first slice.
- Do not delete the legacy Python domain/API or its provider abstraction until
  the replacement passes browser acceptance and its deployment has been
  verified.
- Do not deploy or commit changes unless separately requested.
- Do not make Railway Cron a requirement for the zero-dollar deployment; the
  free plan is not the durable scheduled-job target.

## Verified baseline

- Repository: `/home/armand/Documents/Projects/napas-jakarta`, branch `main`,
  ahead of `origin/main` by five commits.
- Pre-existing dirty work is present in `.gitignore`, `app/citations.py`,
  `app/web.py`, `app/webui/state.py`, `app/webui/theme.py`, and untracked
  `app/i18n.py`; preserve it exactly.
- The current deployed presentation is NiceGUI/FastAPI, with Streamlit retained
  as a local compatibility UI.
- The FastAPI API already exposes `/health`, `/sources`, latest measurements,
  comparisons, history, standards, `/ask`, and feedback endpoints.
- `app/rag.answer` and deterministic tools have broad test/evaluation callers;
  keep them outside the first frontend replacement boundary.
- The product design brief is recorded in `docs/product-design.md`.
- The current Railway configuration still deploys `app.web:app`; the new
  `web/` Next/Eve workspace is not yet the Railway entrypoint.
- The current Railway baseline is a Python web service, PostgreSQL service, and
  scheduled ingestion service. The new free-tier target must account for the
  Railway Free service, volume, and scheduled-job limits documented at
  `https://docs.railway.com/pricing/plans`.
- The eventual public origin is the Cloudflare-managed hostname
  `napasjakarta.armasn.dev`; Railway's generated domain is an implementation
  detail and must not be the product URL.
- The active Eve web chat currently uses the Anthropic direct adapter in
  `web/agent/agent.ts`; the legacy FastAPI provider defaults to OpenAI in
  `app/provider.py`, while the deployed Compose/Railway examples select
  Anthropic. Provider selection is therefore split and must be made explicit.
- The current station-observation provenance is the Jakarta government portal
  at `https://udara.jakarta.go.id/`. Local runtime reads the retained
  `data/processed/measurements.csv` snapshot when `POSTGRES_DSN` is unset; it
  does not fetch the upstream portal per browser request. The ingestion
  boundary is configurable through `SOURCE_DATA_URL`, while the checked-in
  `data/ingestion_report.json` currently describes a committed demo snapshot
  and must be reconciled before the next source refresh or provider cutover.
- The current topic-grounding catalog is `data/sources.yaml`: 30 registered
  source records and 29 locally materialized documents under `data/docs/`.
  The Satu Data Jakarta ISPU 2023 record is retained for provenance but is
  explicitly unmirrored, so it must not be presented as a local ingested file.
- Refreshable articles and newsletters are an approved future source class,
  not yet a live ingestion path. Their transport, publisher allowlist,
  licensing, freshness policy, and revision handling must be designed before
  the latest content is pulled into retrieval.
- Node 24, npm 11, and pnpm 12 are available locally.
- Current registry versions checked on 2026-09-26: Eve `0.67.0`, Next `16.3.6`,
  MapLibre GL JS `6.11.2`.
- Surface targets are intentionally distinct: a 24-inch 1920 × 1080 desktop
  reference, a 14-inch 1920 × 1080 laptop reference represented by roughly
  1280–1599 CSS px under display scaling, plus a mobile composition that must
  provide the desktop feature set through a dedicated mobile navigation model;
  the exact navigation pattern remains a separate design decision.

## Constraints

- Use `apply_patch` for text-file edits.
- Preserve all existing dirty changes and generated `.codegraph/` data.
- Keep the new workspace additive during the first slice.
- Use Eve's typed tool boundary; do not expose arbitrary Python or SQL execution
  to the agent.
- Do not hard-code a production map tile provider before licensing,
  attribution, and availability are decided.
- The OpenFreeMap Liberty style is allowed as an explicitly labelled demo
  preview default only; keep the production style URL configurable.
- Do not treat demo station coordinates as official geospatial metadata.
- Do not let a generic mobile breakpoint decide the product composition. Mobile
  is a roadmap requirement with desktop feature parity, explicit mobile
  navigation, and a separately approved touch-first interaction model.
- The active web chat is page-local and must not expose or restore `/s` session
  routes, URL-backed chat history, or generated session navigation.
- Provider keys must remain server-only. `GEMINI_API_KEY` must never be exposed
  through a `NEXT_PUBLIC_*` variable, browser payload, build artifact, or log.
- The custom-domain cutover must use Railway's issued CNAME and TXT
  verification records, with Cloudflare DNS/proxy and TLS settings validated
  before the Railway hostname is removed from public documentation.
- Free Gemini usage is quota-limited and has different data-use terms from paid
  usage; the product must continue to discourage sensitive personal or health
  details in public prompts.
- The public chat is page-local: a full refresh starts with an empty transcript
  and restores no chat, account, or server session state. The EN/ID preference
  may be retained only as a non-identifying client setting so the deliberate
  language refresh opens in the selected language.
- Store completed answer turns and explicit usefulness feedback as anonymous
  telemetry. The browser may use one random in-memory page-load grouping ID,
  but application payloads must not contain account, IP, device, contact, or
  other identity fields. Telemetry failure must never block chat.

## Material-change boundary

The user authorized writing the durable product brief, beginning the new
workspace implementation, cleaning redundant paths from that first slice, and
setting up Google for the active chat. The current boundary includes the
roadmap, the redundant web-session/scaffold cleanup, and the direct Eve model
configuration. Existing Python UI/domain files, database schemas, Railway
deployment cutover, and user dirty changes remain outside the destructive
cleanup boundary until separately verified.

## Architecture / ADRs

### ADR-001: one workspace instead of peer-level pages

Accepted. Map, chat, station details, comparisons, trends, and sources are
contextual components of one route. Monitoring is excluded.

### ADR-002: Next.js + React + TypeScript for the replacement UI

Accepted. Eve's first-class Next integration gives the cleanest same-origin
agent session path. A standalone Vite client remains an alternative only if
Next integration creates a concrete constraint.

### ADR-003: Eve owns agent orchestration; FastAPI owns domain facts initially

Accepted. Eve defines the agent, skills, typed tools, sessions, streaming, and
evals. Eve tools call stable FastAPI data contracts until a later migration
proves that a domain capability should move to TypeScript.

### ADR-004: MapLibre replaces Leaflet and inline SVG

Accepted for the new UI. The preview uses a configurable OpenFreeMap Liberty
style with illustrative station coordinates; production provider, licensing,
attribution, and availability remain pending.

### ADR-005: Cloudflare owns the public hostname

Accepted for the eventual deployment. Railway remains the origin service, while
Cloudflare DNS routes `napasjakarta.armasn.dev` to the Railway custom-domain
target. The cutover must retain a reversible Railway hostname during
verification and must not expose database services publicly.

### ADR-006: public MCP is deferred

Accepted for the current slice. The Napas chatbot uses Eve's internal typed
tool boundary, backed by the FastAPI domain API, and does not expose a public
MCP endpoint. A future public MCP feature may reuse the same domain layer, but
it requires its own transport, discovery, rate-limit, authentication, and
public-schema review.

### ADR-007: refreshable editorial sources use controlled ingestion

Accepted as a roadmap direction. Approved articles and newsletters will enter
through the server-side ingestion/source registry, not through arbitrary URLs
provided in a chat prompt. Prefer publisher APIs or RSS/Atom/newsletter feeds;
HTML fetching is source-specific and must be explicitly allowlisted and
permitted. Each item retains publisher, canonical URL, published/updated time,
fetch time, language, content hash, license/attribution, topic tags, and
revision status. The retrieval layer may use only validated, cited material.

### ADR-008: the map reads a joined station catalog from the FastAPI boundary

Accepted for the current map slice. The Next workspace will not read CSV files
or duplicate station joins in the browser. FastAPI exposes a read-only
`GET /stations` contract that joins the retained station-coordinate catalog to
the latest requested-pollutant observation, normalizes public labels and
categories, and preserves source/freshness metadata. Next proxies that
contract same-origin at `/api/stations`; the browser keeps no provider or data
path knowledge. The existing 16-row fixture remains available only for local
component scaffolding and is not the displayed source once the contract
loads.

## Milestones

1. Durable brief and execution plan recorded (complete).
2. Scaffold the Next/Eve workspace and confirm the toolchain builds (complete).
3. Implement the first single-workspace shell with logo, chat dock, map canvas,
   and contextual surface slots (complete).
4. Add one typed Eve tool backed by a stable FastAPI read contract and a typed
   artifact rendered by the workspace (tool boundary complete; live integration
   pending).
5. Add real MapLibre station layers after tile/provider and coordinate
   contracts are verified (preview layer complete; production provider
   decision pending).
5a. Replace the static station fixture in the root map with the typed
    FastAPI `/stations` contract, including all retained station coordinates,
    latest-observation joins, dynamic KPIs/filters/list, and an honest loading
    or unavailable state (complete).
6. Add source rendering, trend/comparison artifacts, the distinct desktop and
   laptop responsive compositions, mobile feature parity with mobile
   navigation, accessibility, and browser acceptance.
7. Remove redundant first-slice web session routes, generated session
   navigation, Vercel-only proxy scaffolding, and unreferenced generated UI
   components; keep the root workspace build green (complete).
8. Configure the active Eve agent with a direct Google AI SDK adapter using a
   server-only `GEMINI_API_KEY` and configurable Flash-Lite model; verify
   streaming, tool calls, and recoverable missing-key behavior (adapter and
   missing-key behavior complete; live provider verification pending key).
9. Implement the free-tier deployment topology: Next/Eve web service, FastAPI
   data/telemetry service, and one durable state strategy (Railway Volume-backed
   SQLite first, Railway PostgreSQL if usage or concurrency justifies it).
   Replace the free-plan-incompatible scheduled-ingestion assumption with
   stale-while-refreshing or an explicitly external scheduler.
10. Attach the Railway web service to `napasjakarta.armasn.dev` through
    Cloudflare using Railway's CNAME/TXT verification flow; validate HTTPS,
    redirects, API routing, and health checks while retaining the origin domain
    as a rollback path.
11. Cut over deployment and remove the old UI only after parity, domain, and
    rollback evidence.
12. Deferred feature: evaluate a public remote MCP server only after the
    Napas domain/tool contracts are stable; do not add it to the current
    deployment.
13. Add a client-local EN / ID language dropdown that resets transient page
    state and refreshes the root workspace when changed; cover the same
    language behavior across desktop, laptop, and mobile navigation.
14. Make the air-quality provider boundary explicit and replaceable, including
    source provenance, freshness, station metadata, schema validation, and
    fallback behavior before changing the upstream feed.
15. Expand ingestion beyond the current station feed with isolated adapters for
    approved air-quality, contextual, article, and newsletter sources, while
    preserving the existing Eve tool and citation contracts.
16. Design and implement the source-grounded topic navigator beside the Napas
    assistant heading, with selected topic above selected location in the
    composer context rail and both values available to answer tailoring.
17. Complete the mobile parity pass: choose and validate a touch-first mobile
    navigation pattern that exposes every desktop capability without forcing a
    two-column layout onto a phone.
18. Refine the workspace hierarchy: enlarge the assistant logo, remove normal
    user-facing demo/scaffold language, expand the map legend horizontally,
    compact the selected-location view, and add terminology explanations.
19. Add controlled refresh ingestion for approved articles and newsletters,
    retaining the latest valid publication plus revision/provenance history,
    freshness status, deduplication, and source-linked citations.

## Roadmap additions

### EN / ID language selector

Outcome: a user can choose English or Indonesian from a dropdown in the root
workspace. English remains the current default unless a later product decision
changes it. The selection is client-local and must not affect another browser
or another user.

Constraints and acceptance:

- Changing language clears the transcript, selected station, map/filter state,
  feedback affordances, and other app state, then performs a full page refresh
  as the intentionally simple reset mechanism.
- Do not persist chat, transcript, map/filter, feedback, or other session state
  in cookies, local storage, URLs, or a server session. The language preference
  may use a non-identifying client-only mechanism such as `sessionStorage` (or
  an explicit language parameter) solely to survive the deliberate refresh;
  it must never include transcript or identity data and must not be sent as
  telemetry.
- Translate static chrome, map and filter labels, KPI/status text, loading and
  error states, stale-data warnings, feedback controls, suggested questions,
  source/attribution text, and any model instruction needed to keep generated
  answers in the selected language.
- Verify that switching one browser does not change a second browser, that a
  refresh starts empty, and that both languages preserve the same data meaning
  and safety/provenance behavior.

### Replaceable live station provider

Current finding: the recorded observation source is
`https://udara.jakarta.go.id/`. `ingestion/official.py` fetches the configured
`SOURCE_DATA_URL`, accepts the portal's published `__SPKU_DATA__` snapshot or a
CSV/JSON export URL, and normalizes rows into the shared `Measurement` model.
`ingestion/flow.py` writes the retained processed snapshot and can publish
validated rows to PostgreSQL. The Eve `get-current-air-quality` tool consumes
the stable API contract rather than knowing the upstream provider.

Before a source swap, document and verify the replacement's permitted/stable
interface, station identifiers and coordinates, observation timestamps,
pollutant/concentration units, ISPU or equivalent category semantics, quality
flags, update frequency, attribution, and failure behavior. Preserve source
URL, observed-at, fetched-at, freshness/stale status, and fallback provenance
through the swap so the UI and assistant do not silently relabel cached data
as live.

### Additional ingestion sources

Add a source registry and narrow adapters rather than embedding new provider
logic in the map or chat. Candidate classes are official alternative station
feeds, government/open datasets, weather or other environmental context, and
curated regulations, health guidance, or research documents. Specific sources
remain subject to a later license, authority, quality, and usefulness review.

Articles and newsletters are a specific refreshable source class within this
registry. For each approved publisher, prefer an RSS/Atom feed, newsletter
feed, or publisher API; use HTML page fetching only when the publisher permits
it and the source is explicitly allowlisted. Store the canonical URL, title,
publisher, publication/update time, fetch time, language, content hash,
license/attribution, topic tags, and revision/deletion status. Keep the latest
valid item and enough history to explain when content changed. Canonicalize and
deduplicate syndicated copies, isolate fetch/parser failures by source, and
mark stale or unavailable feeds rather than presenting old articles as current.
The chat request path must never fetch an arbitrary URL supplied by a user.

Each adapter must normalize into the existing measurement or document
contracts, retain publisher/source URL/effective date/language and attribution
metadata, support deduplication/versioning, and fail independently. Ingestion
reports should expose source health, validation results, and freshness; the
retrieval/citation layer should keep provenance visible in answers. The UI and
Eve tool schemas should remain unchanged when a source is added or removed.

### Mobile feature parity and navigation

Mobile is now an end-product roadmap requirement, not only a fallback. The
agreed mobile composition is assistant-first and already exposes chat, topic
selection, station selection and station-list access, feedback, contextual
suggestions, and the map through explicit mobile navigation.

The first mobile implementation is assistant-first: a centered Napas Advisor
identity row is followed by station and topic selectors on the left and a
top-right Map action. Map opens as a full-screen pannable overlay, and that
same action becomes an X in place to close it. Station/topic context remains
available and clearable without sending a message; suggestions remain derived
from the active intersection. The map view is intentionally accepted as-is on
mobile, and the mobile station list is already available through the station
selector. Landscape-specific validation is not a required milestone; keyboard
and touch validation will happen after deployment. The remaining shared
product gaps are the future EN/ID selector and full source/citation coverage for
non-station evidence. The first citation slice now presents the registered
station-data source directly below completed measurement-tool results.
The desktop legend remains inline, while mobile exposes the same legend and
terminology material through the Map-mode Legend action.

### Source-grounded topic navigator

Place a topic dropdown beside the larger Napas assistant heading. It opens a
grouped list of suggested questions and source-grounded topics. The selected
topic appears above the selected location in the composer context rail; either
context can be cleared independently, and both are passed as explicit typed
context for the next answer. Selecting a suggestion must remain visibly
user-driven and must not create an invisible turn.

Initial topic groups:

- Understand today's air: current conditions, map/stations, ISPU, PM2.5,
  PM10, units, categories, timestamps, stale readings, and station versus
  city-level data.
- Protect yourself now: bad-air-day actions, outdoor activity, respirators,
  ventilation, exposure reduction, and care escalation boundaries.
- Children, pregnancy, older adults, and health-sensitive people: cautious
  non-diagnostic guidance. Pregnancy-specific claims require a dedicated
  authoritative source review before the topic is treated as evidence-backed.
- Outdoor and professional workers: time outdoors, strenuous work, exposure
  reduction, scheduling, and public-health context.
- Improve home air: clean-air rooms, CADR, HVAC/MERV filtration, combustion
  sources, ventilation, and maintenance.
- Why Jakarta's air is unhealthy: transport, industry/power, regional
  transport, seasons, weather, source-apportionment limits, and high-rise or
  ground-level exposure.
- What can I do to help: transport, vehicle-emissions testing, household
  actions, public participation, and accountability.
- Policy, law, and implementation: ISPU methodology, ambient standards,
  regulations, ERP/policy history, SPPU, CEMS, court records, and the
  distinction between proposals, laws, programmes, and implementation evidence.
- Trends and comparisons: historical PM2.5/PM10 context, station comparisons,
  time trends, and modelled city series versus station observations.

The topics are grounded in the current catalog rather than a generic FAQ:

- Observations, stations, ISPU explanations, and recommendations: Udara Jakarta
  official monitoring portal.
- Historical and city-level context: Satu Data Jakarta ISPU 2023 (catalog-only,
  unmirrored) and the Zenodo/Open-Meteo CAMS historical series.
- Definitions and standards: Permen LHK No. 14/2020, PP No. 22/2021, Jakarta
  regulations, and WHO Global Air Quality Guidelines.
- Protection and home air: WHO exposure guidance, bad-air-day protection,
  WHO personal interventions, EPA clean-air guidance, and the local health
  communication boundary.
- Causes and exposure: Jakarta emissions inventory, seasonal exposure notice,
  and vertical/ground-level exposure evidence.
- Action and governance: Jakarta improvement strategies, individual emission
  actions, vehicle-emissions rules/testing, SPPU and CEMS material, policy
  implementation/status, policy-improvement evidence, and court records.

The implementation must keep topic labels and suggested questions available in
English and Indonesian while preserving the same source IDs, citation rules,
health boundaries, and freshness semantics.

Future article/newsletter ingestion can add a time-sensitive “Latest updates”
layer to these topics, such as new advisories, policy developments, research,
or local reporting. It must not silently replace the authoritative source
classes above: editorial material remains labelled with its publisher, date,
source type, and confidence/authority boundary.

### Map, legend, and assistant hierarchy

The next visual pass should remove implementation-scaffold language from the
normal product surface and improve the information balance:

- Make the Napas logo beside the assistant heading visibly larger.
- Remove “demo view,” “demo snapshot,” and equivalent copy from user-facing UI.
  Keep honest current/stale/fallback/source status, but phrase it as data
  status rather than an example implementation.
- Expand the map legend horizontally into the available right-side area and
  shrink the selected-location detail region without removing its core facts.
- Use the newly available legend area for concise terminology and explanations
  of ISPU, PM2.5, PM10, units, averaging periods, category colors, station
  observations, city-level model data, and freshness.
- On mobile, expose the same material from Map mode through a compact Legend
  action and a touch-friendly condensed modal; it may not disappear merely
  because the layout stacks.

## Task envelopes

- Documentation: add the product brief, update the architecture index so the
  old NiceGUI decision is explicitly historical, and record this plan.
- Toolchain: use the official Eve scaffold or equivalent Next/Eve setup; pin
  versions and keep the web app isolated under `web/`.
- Shell: create the single route and component boundaries without changing the
  current Python application.
- Agent: define instructions and one read-only tool with a Zod schema; keep the
  tool result typed and provenance-bearing.
- Localization: define the EN/ID dictionary and generated-language contract at
  the root workspace boundary; keep reset semantics client-only and explicit.
- Mobile: define the touch-first navigation model and prove desktop feature
  parity across portrait, landscape, keyboard, and long localized content.
- Topics: derive the initial topic/question registry from `data/sources.yaml`
  and `data/docs/`; keep topic, location, source, and answer context typed and
  independently clearable.
- Provider: add the Google AI SDK adapter at the Eve boundary; keep the key in
  runtime environment variables and expose the selected model as a safe,
  non-secret label only.
- Public MCP: explicitly out of scope for the current implementation slice;
  preserve the internal Eve-to-FastAPI tool path until a separate feature
  review authorizes a public endpoint.
- Cleanup: delete only paths proven unreachable from the `/` workspace or
  required runtime; verify the old Python API remains importable and tested.
- Deployment: record service count, storage ownership, retention, and refresh
  behavior before changing Railway configuration.
- Ingestion: define the provider adapter/source registry contract, reconcile
  the retained snapshot and ingestion report, and add fixture-based tests for
  provenance, freshness, schema drift, source failure fallback, and controlled
  article/newsletter refresh.
- Source security: keep publisher endpoints allowlisted, fetch outside the
  chat request path with bounded timeouts/size limits, validate content before
  indexing, and retain license/attribution and revision evidence.
- Workspace hierarchy: enlarge the assistant logo, remove demo/scaffold copy,
  rebalance the legend and selected-location regions, and add terminology
  explanations without weakening source or stale-data disclosure.
- Station map data: expose a read-only joined station contract from FastAPI,
  proxy it same-origin through Next, and keep station IDs, coordinates,
  observation timestamps, categories, source, and freshness aligned between
  the map, KPIs, station list, and selected-location card.
- Domain: configure the custom host only after the deployment is healthy, keep
  the Railway origin available during DNS propagation, and verify the expected
  Cloudflare SSL mode and Railway certificate status.
- Verification: run web typecheck/build plus a narrow Python API regression
  check; confirm no pre-existing dirty file changed. Add browser evidence for
  EN/ID reset/isolation and ingestion-contract evidence before either roadmap
  feature is considered complete.

## Test architecture and required evidence

- Configuration/scaffold: `npm`/`pnpm` install, TypeScript typecheck, and
  production build are the primary evidence.
- Agent tool: Eve mock/eval or a deterministic unit test proves the schema,
  tool selection, and structured result shape.
- FastAPI boundary: existing Python tests remain the authority for data
  semantics; every new read endpoint requires a contract test for response
  shape, station/observation joins, and unavailable-data behavior.
- Station map: a deterministic contract test proves the joined response
  includes the retained station catalog, preserves stale/missing stations,
  normalizes public labels/categories, and does not fall back to the 16-row
  browser fixture after a successful load.
- Workspace behavior: Playwright owns the real browser boundary once the shell
  is interactive—chat submission, tool activity, artifact rendering, map
  selection, topic/location context, desktop/laptop/mobile navigation, legend
  terminology, and recovery states.
- Corpus/topic contract: a deterministic test proves every topic maps to
  registered source IDs, distinguishes locally materialized versus
  provenance-only sources, and blocks unsupported pregnancy-specific claims.
- Editorial ingestion: fixture feeds prove canonicalization, deduplication,
  revision handling, publication/fetch freshness, attribution retention,
  bounded fetch behavior, and isolated failure for articles/newsletters.
- Accessibility: keyboard/focus, touch targets, virtual-keyboard overlap,
  long localized labels, zoom/reflow, and reduced-motion checks are required
  before the replacement is considered ready.

## Gates

- Design gate: `docs/product-design.md` remains the authoritative accepted
  direction.
- Scope gate: no Monitoring route or legacy page hierarchy is added to the new
  app.
- Data gate: no demo observation is presented as live or officially located.
- Mobile gate: every desktop capability has an intentional mobile navigation
  path; no feature is dropped as an accidental consequence of stacking.
- Topic gate: topic suggestions and context chips are source-grounded,
  bilingual, independently clearable, and do not overstate pregnancy or other
  health-sensitive evidence.
- Editorial-source gate: article/newsletter ingestion is allowlisted,
  permission-aware, bounded, deduplicated, revision-aware, and cited with
  publisher/date/source-type metadata; user prompts cannot trigger arbitrary
  network fetches.
- Presentation gate: ordinary user-facing surfaces contain no demo/scaffold
  wording while still disclosing freshness, fallback, source, and limitations.
- Agent gate: every model-facing capability has a narrow schema, explicit
  provenance, and a recoverable error path.
- Provider gate: no production or browser artifact contains a model key; the
  active web agent uses the configured Google model and reports provider
  failures without blocking telemetry or corrupting the UI.
- Persistence gate: telemetry remains durable only when its configured store
  is durable; ephemeral filesystem writes are treated as a development
  fallback, never as the Railway production guarantee.
- Verification gate: web build/typecheck pass; relevant Python tests pass; the
  dirty-file allowlist is unchanged.

## Risks and rollback

- Eve is beta and may change APIs. Pin the package and isolate calls behind
  Napas adapters. Rollback is to stop serving `web/` and keep the existing
  NiceGUI entry point.
- A Next/Eve service adds a Node runtime beside the Python service. Rollback is
  to keep the new app development-only until deployment topology is verified.
- Railway Free has a small resource credit, one volume, and no durable
  scheduled-job path after the trial. Rollback is to the existing Railway
  web/PostgreSQL/cron layout or to a paid/external scheduler if fresh data
  cannot be guaranteed by request-time refresh.
- A direct Google free-tier key changes provider data-use terms. Rollback is to
  disable the provider, return the deterministic answer path, and remove the
  key from the environment; never silently fall back to a different paid
  provider.
- DNS or certificate misconfiguration could make the public host unavailable
  while the Railway origin remains healthy. Rollback is to restore the
  Cloudflare record, keep the Railway origin live, and retry verification before
  changing application behavior.
- Tile providers introduce licensing, attribution, and availability constraints.
  Rollback is to use a local data-backed map shell while retaining the MapLibre
  layer contract.
- Article and newsletter sources can change format, disappear, republish
  content, or impose licensing limits. Rollback is to disable the affected
  adapter, retain the last validated snapshot with a stale label, and remove
  it from topic suggestions until the source contract is re-verified.
- Existing user changes are unrelated and may be incomplete. Rollback of this
  work must never use reset/checkout or overwrite those files.

## Attempt ledger

- Attempt 1: inspected repository status, current API/UI boundaries, existing
  plans, and local runtime versions; baseline captured.
- Attempt 2: created the durable product brief and this execution plan.
- Attempt 3: generated the official Eve/Next scaffold, added the first
  Napas workspace shell, real product logo, temporary detailed map fixture,
  Napas agent instructions, and one typed FastAPI-backed tool. Resolved a
  scaffold dependency-linking issue by using the generated lockfile with npm.
- Attempt 4: added the explicit desktop/laptop surface targets and parked
  mobile decision to both the product brief and this plan.
- Attempt 5: replaced the first shell with the OpenDesign-derived layout,
  added the three KPI cards before filters, wired a real MapLibre/OpenFreeMap
  preview basemap, and verified filters, station list, station selection, and
  context-panel updates in the browser.
- Attempt 6: removed the static example transcript, added an ephemeral
  multi-turn chat dock with thinking/streaming presentation, latest-answer
  feedback controls, and an anonymous telemetry relay to the existing
  interaction store.
- Attempt 7: audited the active `/` workspace against generated Eve session
  routes and provider/deployment entrypoints; confirmed the cleanup boundary
  and free-tier Railway/Gemini direction before mutation.
- Attempt 8: added the Cloudflare-owned `napasjakarta.armasn.dev` public-host
  requirement and reversible custom-domain cutover to the roadmap.
- Attempt 9: removed the redundant `/s` session routes, client-side session URL
  rewriting, Vercel dev/deploy scaffolding, unused chain-of-thought UI files,
  and generated Vercel auth policy; simplified the chat to the single root
  workspace and verified a clean production route list.
- Attempt 10: added the direct `@ai-sdk/google` adapter with the
  `gemini-3.5-flash-lite` default, server-only `GEMINI_API_KEY` handling, a
  configurable `GEMINI_MODEL`, explicit anonymous Eve auth, and a red/green
  model-selection test.
- Attempt 11: loaded the local Gemini key from ignored `web/.env.local`,
  verified a direct streamed answer, started the local FastAPI service on
  port 8502, and verified a tool-backed answer with the stale-data warning
  preserved. No Gemini authentication error occurred.
- Attempt 12: changed the chat presentation to buffer the completed provider
  turn behind Thinking, then reveal the final answer at a steady client-side
  pace with feedback held until presentation completes; added reduced-motion
  handling and deterministic pacing tests.
- Attempt 13: traced the current-air-quality tool error to a stopped local
  FastAPI process rather than a Gemini, Eve, or response-schema failure;
  restored the service, verified the tool-backed response, and documented the
  `npm run dev:api` local startup path.
- Attempt 14: reviewed the source catalog and local knowledge corpus, then
  recorded mobile feature parity/navigation, a source-grounded topic navigator,
  and the assistant/map/legend hierarchy refinement roadmap.
- Attempt 15: added refreshable article/newsletter ingestion as a controlled,
  allowlisted source class with freshness, revision, attribution, deduplication,
  and security requirements.
- Attempt 16: traced the map undercount to the client-only 16-station fixture;
  verified the retained processed catalog contains 105 station records and
  scoped the joined `/stations` contract that will replace it.
- Attempt 17: added the FastAPI `/stations` contract and same-origin Next
  proxy, replaced the map's 16-row fixture with the retained 105-station
  catalog, added loading/unavailable states and dynamic district filtering,
  and verified the full station list in the browser.
- Attempt 18: added the bilingual source-grounded topic registry and contract
  tests, placed the grouped topic navigator beside Napas Advisor, added an
  independently clearable topic chip above the selected station, and passed
  topic/source/location context through Eve's ephemeral `clientContext`; the
  desktop and mobile interactions were checked in the browser.
- Attempt 19: made the topic control right-aligned and bottom-aligned with the
  station-network status without an active-status dot, constrained the topic
  menu to an independently scrollable region, added a clearable station chip,
  and derived empty-state suggestions from the selected topic/location. Added
  red/green unit coverage for suggestion changes, then verified topic/station
  select and clear flows at desktop and 390px mobile widths.
- Attempt 20: changed the combined suggestion branch so every prompt is
  explicitly grounded in both selected pills, added container-based utility
  layout for narrow chat panes, and constrained long topic/location pills with
  internal ellipsis. Rebuilt the frontend bundle to avoid stale CSS evidence,
  then verified long station names at wide desktop, narrow desktop, and mobile
  widths.
- Attempt 21: diagnosed the chat turn that appeared stuck. The latest partial
  assistant message was being hidden while Eve remained in a busy state, and
  the Google request could keep its connection open without producing another
  chunk after a large tool result. Partial assistant text is now rendered as
  soon as it exists, while the initial thinking state remains available before
  the first token. Gemini requests also have a bounded 120-second deadline,
  with a positive `GEMINI_REQUEST_TIMEOUT_MS` override for local/deployment
  tuning. Added focused chat-state and timeout-selection tests; verified the
  production web build and reproduced the affected question to completion.
- Attempt 22: implemented the first mobile composition as a typed compact
  segmented switcher between full-screen Map and Assistant destinations. Added
  explicit tab/panel associations, icon-led touch targets, safe-area padding for
  the chat dock, keyboard scroll reservation, and a shorter landscape layout.
  Verified portrait at 390 × 844 and landscape at 844 × 390 with no horizontal
  overflow, corrected the map landmark and page-heading semantics found by
  accessibility lint, then ran the focused frontend tests, typecheck,
  production build, and two responsive lint-ui checks.
- Attempt 23: replaced the segmented mobile switcher with the accepted
  assistant-first composition: centered Napas Advisor identity, left-aligned
  station/topic selectors, and a top-right Map action that becomes an X while
  a pannable map overlays the assistant. Added a real station catalog menu with
  independent scrolling and clearing, removed the redundant mobile context
  pill, constrained both menus to the viewport, and verified the assistant,
  topic menu, station menu, deselection flow, and map overlay at 390 × 844.
- Attempt 24: traced the 7 September observation timestamp to the packaged
  `data/processed/measurements.csv` fallback rather than a browser formatting
  defect; verified the official `SOURCE_DATA_URL` does not itself refresh the
  runtime rows. The next polish slice is scoped to preserve that stale-data
  warning, label the map as the latest available snapshot, compact the
  desktop/mobile assistant header, add accessible About and Privacy dialogs,
  and restore contextual suggestions after each completed answer.
- Attempt 25: completed the data-trust and presentation polish slice. The map
  now labels the packaged observations as the latest available stale readings;
  the assistant uses the requested city-wide monitor tagline; the desktop
  header is compact with Topics right-aligned; the mobile header keeps the
  advisor identity on one row with the monitor tagline below; About and
  Privacy are accessible dialogs beside the product name; and contextual
  suggestions return after a completed answer while remaining hidden during a
  new turn. Corrected button cascade specificity for the compact controls,
  rebuilt the preview, and verified the final browser interaction.
- Attempt 26: revised the About and Privacy copy to remove em dashes and made
  About explain the operating-station data flow, stale-data handling,
  official-source grounding, and station/topic tailoring. Verified both dialog
  surfaces in the mobile browser.
- Attempt 27: moved About and Privacy from the left mobile group into the
  right-hand top-bar group, leaving Jakarta City Monitor on its own side so
  the compact monitor label no longer competes with navigation. Verified the
  desktop and 390px mobile layouts and reran responsive lint-ui.
- Attempt 28: renamed the product-side label to “Jakarta Air Monitor,” moved
  About and Privacy back beside it for desktop, removed the redundant right
  header label, and kept the links pinned to the right on mobile. Rebuilt the
  generated preview cache and verified both responsive surfaces.
- Attempt 29: reconciled the mobile parity status with the accepted product
  scope. Station-list access and the current map overlay are complete; the map
  will remain unchanged on mobile. Removed landscape validation from the
  roadmap, deferred keyboard/touch checks until deployment, and separated the
  remaining shared gaps of legend/terminology, EN/ID, and source/citations.
- Attempt 30: added the mobile Map-mode Legend action beside Napas Advisor,
  extracted the shared legend and terminology content for reuse, and added a
  condensed native dialog with a large close target. Verified the Map → Legend
  → close flow at 390 × 844, confirmed the modal fits without scrolling, and
  kept the control absent from the desktop header.

## Progress

- Product direction: accepted and persisted.
- Architecture: accepted and persisted.
- Implementation: OpenDesign-derived workspace, real MapLibre preview map, and
  initial Eve tool are in place; the public root chat is ephemeral, while
  completed answer and feedback telemetry use the existing interaction store.
  Redundant web-session scaffolding is removed. The active Eve provider now
  uses a direct Google adapter with a `gemini-3.5-flash-lite` default; the
  legacy Python provider remains separate until the later service cutover.
  Free-tier deployment and the Cloudflare custom-domain cutover remain next.
  The chat now keeps provider chunks out of the visible transcript until the
  response is complete, then presents the answer smoothly without delaying
  tool execution or telemetry.
- Current map-data slice: complete. The root map now uses the retained
  105-station catalog through the FastAPI/Next station contract rather than
  the static 16-station fixture. The joined payload drives markers, KPIs,
  filters, station list, selected-location details, and loading/unavailable
  states.
- Current topic-navigation slice: complete. The root assistant now exposes
  18 bilingual topic choices across 9 source-grounded groups, visibly places
  the selected topic above the selected station, keeps selection separate from
  sending, and sends the typed topic/source/location context ephemerally for
  the next model turn. Pregnancy remains explicitly clinical-review-gated.
- Current contextual-suggestion slice: complete. Suggested questions now
  update immediately when a topic or station is selected or cleared. The
  selected station can be removed without sending a message, both context
  chips are bounded by the chat pane, the Topics control is right/bottom
  aligned in the assistant header, and its long catalog scrolls inside the
  menu rather than extending the page. When both context pills are selected,
  every suggestion names both the topic and station rather than mixing generic
  topic prompts with location-only prompts. The utility row switches to a
  bounded stacked layout when the chat panel itself is narrow, independent of
  the overall viewport width.
- Current mobile navigation slice: complete for the agreed scope. Phones open
  on the assistant with a centered Napas Advisor header, scrollable station
  and topic selectors, station-list access, context-derived suggestions, and a
  top-right Map control. Map opens as a pannable overlay and the same control
  becomes an X to close it; station selection can be cleared without sending a
  message. The map is intentionally unchanged on mobile. While Map mode is
  open, a Legend button appears in the advisor header and opens the condensed
  shared legend/terminology modal; its close target returns to the map.
  Landscape testing is not planned, and keyboard/touch validation is deferred
  until deployment. The remaining cross-platform gaps are the future EN/ID and
  source/citation features.
- Current presentation/data-trust slice: complete. The map visibly distinguishes
  the latest available snapshot from a current reading, including the observed
  07 September timestamp and stale status. The requested
  “Live Data From City-Wide Jakarta Air Quality Monitors” tagline is shared by
  desktop and mobile, the assistant header is compact, and mobile keeps the
  advisor identity on one row with the tagline beneath it. About and Privacy
  dialogs are available beside Jakarta City Monitor on both surfaces; the
  privacy copy describes the actual anonymous question/answer/feedback
  telemetry without implying identity or account storage. Suggested questions
  reappear after each completed answer and are hidden while a new turn runs.
- Verification: web typecheck/build, the model-selection unit test, a missing
  key request-path check, direct Gemini chat, tool-backed Gemini chat through
  local FastAPI, focused Python regression checks, and a laptop-width browser
  visual/interaction pass are complete. The topic slice was additionally
  checked at the default desktop width and a 390px mobile width. The local
  tool result is intentionally stale and was labelled as such; production
  deployment evidence remains next. Mobile navigation is complete for the
  agreed scope; post-deployment keyboard and touch checks remain.
  Article and newsletter refresh ingestion is also only recorded, not
  connected. The final responsive lint-ui run passed at 390 × 844 and 844 ×
  390, and the focused frontend suite passed 11 tests.

## Change history

- 2026-09-26: recorded the single-workspace product direction, Eve agent
  boundary, Next.js frontend decision, MapLibre replacement, and staged
  migration boundary after explicit user approval.
- 2026-09-26: recorded separate 24-inch desktop and 14-inch laptop targets;
  explicitly deferred mobile-specific product design.
- 2026-09-26: replaced the first custom shell with the OpenDesign-derived
  composition, added KPI/filter hierarchy, and moved the preview map to
  MapLibre with an attributed OpenFreeMap vector style.
- 2026-09-26: made the root chat page-local, added latest-answer feedback, and
  documented anonymous answer/interaction telemetry with bounded retention.
- 2026-09-26: updated the roadmap for redundant first-slice cleanup, direct
  Gemini provider setup, and a Railway Free deployment/storage decision.
- 2026-09-26: recorded Cloudflare DNS ownership of
  `napasjakarta.armasn.dev` and a reversible Railway custom-domain cutover.
- 2026-09-26: removed redundant web session/Vercel scaffolding and replaced
  the active Eve model boundary with direct Google Flash-Lite configuration.
- 2026-09-26: explicitly deferred the public MCP feature; the current chatbot
  remains on the internal Eve-to-FastAPI typed tool path.
- 2026-09-26: added the client-local EN/ID reset-and-refresh language roadmap,
  documented the current Udara Jakarta station-source boundary, and added the
  provider-agnostic additional-ingestion roadmap.
- 2026-09-26: added mobile feature parity with open mobile navigation design,
  a source-grounded topic/question navigator, and the larger-logo,
  no-demo-copy, expanded-legend, and terminology hierarchy requirements.
- 2026-09-26: added controlled article/newsletter refresh ingestion with
  publisher allowlisting, provenance, revision, freshness, deduplication,
  attribution, and bounded-fetch requirements.
- 2026-09-26: replaced the root map's 16-station fixture with the joined
  105-station FastAPI/Next contract, including dynamic summary counts,
  district coverage, and honest loading/unavailable states.
- 2026-09-26: added the source-grounded bilingual topic navigator with
  clinical-review gating for pregnancy-specific topics, independently
  clearable topic/location context chips, and ephemeral Eve turn context.
- 2026-09-26: added contextual suggestion derivation, station deselection,
  right/bottom-aligned topic navigation, bounded context chips, and a
  scrollable topic menu with desktop/mobile interaction coverage.
- 2026-09-26: grounded combined suggestions in the topic/location intersection
  and added chat-panel container sizing to prevent long context pills from
  crossing into the map.
- 2026-09-26: made partial assistant output visible during active streaming and
  bounded Gemini requests so a stalled provider connection cannot leave the
  composer in an indefinite thinking state.
- 2026-09-26: replaced the segmented mobile navigation experiment with the
  assistant-first mobile composition: centered advisor header, station/topic
  selectors, scrollable menus, and an in-place Map/X control for a pannable
  map overlay.
- 2026-09-26: labelled the retained 7 September station snapshot honestly,
  added the city-wide monitor tagline, compacted the desktop/mobile assistant
  headers, added About and Privacy dialogs, restored post-answer suggestions,
  and passed the final typecheck, production build, focused tests, browser
  interaction check, and responsive lint-ui checks.
- 2026-09-26: expanded the About dialog with the station-data and
  official-source flow, removed em dashes from both informational dialogs, and
  verified their rendered copy on mobile.
- 2026-09-26: moved the informational navigation to the top-right group so
  the Jakarta City Monitor label remains readable on mobile, then passed both
  responsive lint-ui checks.
- 2026-09-26: renamed the header label to Jakarta Air Monitor, placed the
  desktop information links beside it, removed the redundant right-side
  label, and kept mobile navigation on the right.
- 2026-09-26: clarified that mobile station-list access and the agreed map
  overlay are complete, removed landscape validation from the plan, and
  deferred keyboard/touch checks to deployment.
- 2026-09-26: added the mobile Map-mode Legend action and condensed
  touch-friendly legend/terminology modal, reusing the desktop legend content
  and verifying the no-scroll close flow at 390 × 844.
- 2026-09-26: added source-grounded links to completed air-quality tool results
  by joining measurement provenance to the registered `/sources` manifest,
  validated clickable URLs in the chat, removed the implicit Kelapa Gading
  default so a fresh page starts unselected, stabilized desktop suggestions as
  one-per-row, and increased About/Privacy spacing across desktop and mobile.
- 2026-09-26: removed raw Eve tool panels from the user-facing conversation;
  source links now appear as a left-aligned, keyboard-accessible disclosure
  behind a compact caret.
- 2026-09-26: kept assistant prose, source disclosure, and feedback controls
  in the avatar-aligned message column; moved sources below the answer and
  added larger animated feedback buttons with checkmark and thank-you states.
- 2026-09-27: restored buffered answer pacing by keeping partial provider
  output behind the thinking state, made feedback wait for pacing completion,
  aligned the thank-you confirmation with the answer column, and removed the
  mouse-only focus ring from the source disclosure while preserving keyboard
  focus styling.
- 2026-09-27: made cited source hostnames render as trusted HTTPS anchors
  inside assistant prose, while leaving Streamdown link-safety handling intact
  for unrelated model-provided links.
- 2026-09-27: introduced the first elevation and spacing-rhythm pass for the
  desktop workspace: separated the assistant and map into rounded primary
  surfaces, inset the map canvas, and split the legend and station detail into
  quieter nested surfaces while preserving the mobile full-bleed composition.
- 2026-09-27: strengthened the shadow hierarchy for the desktop elevation pass
  across primary panels, nested map cards, and chat/map controls without
  changing layout geometry or the mobile composition.
- 2026-09-27: introduced a shared productive motion scale for popovers,
  disclosures, dialogs, feedback, chips, filters, and map controls, with a
  reduced-motion override; increased desktop panel/card radii and isolated
  overflow so elevated surfaces clip cleanly at their rounded corners.
- 2026-09-27: increased buffered assistant text pacing from 108 to 130
  characters per second while retaining the per-frame catch-up cap to prevent
  delayed frames from producing chunky bursts.
- 2026-09-27: reserved dynamic transcript space for the suggestion dock so
  completed-answer feedback remains visible and clickable when suggestions are
  shown on wide desktop layouts.
- 2026-09-27: completed a visual cohesion foundation pass: reduced the desktop
  assistant rail to roughly 32%, aligned desktop panel headers, flattened
  nested map cards, unified neutral controls, separated interaction teal/navy
  from air-quality status colors, and redesigned the empty station detail
  state.
- 2026-09-27: refined the desktop workspace hierarchy by moving air-quality
  level and district filters below the KPI strip, adding a radio-tower icon to
  Station list, and renaming the category filter to Air quality level. Recast
  the assistant and map as one shared shell with a single divider and softer
  outer elevation, aligned the three map toolbar rows, and nudged the empty
  assistant state toward the prompt dock without changing mobile composition.
- 2026-09-27: removed the inset margin, border, radius, and card shadow from
  the desktop map stage so the map canvas fills the map panel to its surrounding
  border while the outer shell and lower information surfaces retain their
  hierarchy.
- 2026-09-27: simplified the mobile header after testing the map-open state:
  shortened the monitor tagline to remove “Jakarta,” restored the stable flex
  row instead of wrapping the title around map controls, and removed the
  redundant north indicator from the map canvas.
- 2026-09-27: aligned the Topics trigger hover treatment with suggested
  question chips using the same soft surface, light border, subtle elevation,
  and lift response.
- 2026-09-27: increased the topbar typography for Jakarta Air Monitor and the
  About/Privacy controls, with smaller responsive values preserved for narrow
  mobile headers.
