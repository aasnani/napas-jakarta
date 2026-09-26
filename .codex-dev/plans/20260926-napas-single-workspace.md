# Napas single-workspace replacement

## Goal

Build the accepted Napas Jakarta end product as one conversational spatial
workspace: a Next.js/React frontend, Eve agent runtime, detailed MapLibre map,
and contextual result components backed by the existing verified FastAPI/data
layer.

## Non-goals

- Do not preserve the existing NiceGUI visual layout or page hierarchy.
- Do not build a public Monitoring page.
- Do not rewrite ingestion, PostgreSQL schemas, retrieval quality logic, or
  source validation in the first slice.
- Do not delete the existing UI until the replacement passes browser acceptance.
- Do not deploy or commit changes unless separately requested.

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
- Node 24, npm 11, and pnpm 12 are available locally.
- Current registry versions checked on 2026-09-26: Eve `0.67.0`, Next `16.3.6`,
  MapLibre GL JS `6.11.2`.
- Surface targets are intentionally distinct: a 24-inch 1920 × 1080 desktop
  reference, a 14-inch 1920 × 1080 laptop reference represented by roughly
  1280–1599 CSS px under display scaling, and a mobile composition that is
  explicitly parked pending a separate design decision.

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
- Do not let a generic mobile breakpoint decide the product composition; mobile
  must remain a basic fallback until its target and interaction model are
  approved.

## Material-change boundary

The user authorized writing the durable product brief and beginning the new
workspace implementation. The first implementation boundary is new repository
documentation plus a new `web/` application/agent workspace and its local
verification. Existing Python UI files, runtime data, deployment definitions,
and user dirty changes are not in scope for modification.

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
6. Add source rendering, trend/comparison artifacts, the distinct desktop and
   laptop responsive compositions, accessibility, and browser acceptance.
   Keep mobile as a separately scoped design milestone.
7. Cut over deployment and remove the old UI only after parity evidence.

## Task envelopes

- Documentation: add the product brief, update the architecture index so the
  old NiceGUI decision is explicitly historical, and record this plan.
- Toolchain: use the official Eve scaffold or equivalent Next/Eve setup; pin
  versions and keep the web app isolated under `web/`.
- Shell: create the single route and component boundaries without changing the
  current Python application.
- Agent: define instructions and one read-only tool with a Zod schema; keep the
  tool result typed and provenance-bearing.
- Verification: run web typecheck/build plus a narrow Python API regression
  check; confirm no pre-existing dirty file changed.

## Test architecture and required evidence

- Configuration/scaffold: `npm`/`pnpm` install, TypeScript typecheck, and
  production build are the primary evidence.
- Agent tool: Eve mock/eval or a deterministic unit test proves the schema,
  tool selection, and structured result shape.
- FastAPI boundary: existing Python tests remain the authority for data
  semantics; add an API contract test only if a new endpoint is introduced.
- Workspace behavior: Playwright owns the real browser boundary once the shell
  is interactive—chat submission, tool activity, artifact rendering, map
  selection, desktop/laptop responsive layout, and recovery states.
- Accessibility: keyboard/focus and reduced-motion checks are required before
  the replacement is considered ready.

## Gates

- Design gate: `docs/product-design.md` remains the authoritative accepted
  direction.
- Scope gate: no Monitoring route or legacy page hierarchy is added to the new
  app.
- Data gate: no demo observation is presented as live or officially located.
- Agent gate: every model-facing capability has a narrow schema, explicit
  provenance, and a recoverable error path.
- Verification gate: web build/typecheck pass; relevant Python tests pass; the
  dirty-file allowlist is unchanged.

## Risks and rollback

- Eve is beta and may change APIs. Pin the package and isolate calls behind
  Napas adapters. Rollback is to stop serving `web/` and keep the existing
  NiceGUI entry point.
- A Next/Eve service adds a Node runtime beside the Python service. Rollback is
  to keep the new app development-only until deployment topology is verified.
- Tile providers introduce licensing, attribution, and availability constraints.
  Rollback is to use a local data-backed map shell while retaining the MapLibre
  layer contract.
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

## Progress

- Product direction: accepted and persisted.
- Architecture: accepted and persisted.
- Implementation: OpenDesign-derived workspace, real MapLibre preview map, and
  initial Eve tool are in place; production provider selection and live artifact
  integration remain next.
- Verification: web typecheck/build, focused Python regression checks, and a
  laptop-width browser visual/interaction pass are complete. Desktop-width and
  live FastAPI/Eve integration evidence remain next.

## Change history

- 2026-09-26: recorded the single-workspace product direction, Eve agent
  boundary, Next.js frontend decision, MapLibre replacement, and staged
  migration boundary after explicit user approval.
- 2026-09-26: recorded separate 24-inch desktop and 14-inch laptop targets;
  explicitly deferred mobile-specific product design.
- 2026-09-26: replaced the first custom shell with the OpenDesign-derived
  composition, added KPI/filter hierarchy, and moved the preview map to
  MapLibre with an attributed OpenFreeMap vector style.
