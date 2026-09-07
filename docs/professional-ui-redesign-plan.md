# Napas Jakarta professional UI redesign

## Decision

Replace Streamlit as the primary presentation layer with **NiceGUI 3.16 and its Quasar frontend**, while retaining the existing Python RAG, retrieval, ingestion, evaluation, monitoring, and FastAPI domain logic.

NiceGUI is the best fit because its official architecture is Python/FastAPI → WebSocket → Vue/Quasar, it provides real layout primitives instead of rerun-positioned script output, and it includes the components this product already needs: headers/drawers, rows/columns/cards, chat messages, QTable, ECharts, Leaflet, Material icons, per-client state, and pytest-based UI testing. It can also mount into an existing FastAPI application. [NiceGUI documentation](https://nicegui.io/documentation), [NiceGUI repository](https://github.com/zauberzeug/nicegui)

The visual system will be **Quasar Material with a restrained Material 3-inspired token layer**. Carbon AI Chat is the interaction reference for message width, starter prompts, streaming updates, sources, feedback, and reader-controlled auto-scroll; it is not the runtime dependency because its React/web-component package would introduce a second frontend toolchain. [Carbon AI Chat overview](https://chat.carbondesignsystem.com/tag/latest/docs/documents/Overview.html), [Carbon chat layout](https://chat.carbondesignsystem.com/tag/latest/docs/documents/UI_customization.Layout.html)

## Research findings translated into product rules

- Material Design treats layout as an adaptive scaffold rather than a collection of independently placed widgets. Napas Jakarta will have one app shell, one spacing scale, explicit breakpoints, and repeatable page templates. [Material adaptive layout](https://m3.material.io/foundations/layout/layout-overview/adaptive-design), [Material spacing](https://m3.material.io/foundations/layout/grids-spacing/spacing)
- Material color roles separate primary brand actions from surfaces, outlines, errors, and status. The air-quality category scale must remain a semantic data palette and must not double as the brand/action palette. [Material color roles](https://m3.material.io/styles/color/roles)
- Carbon recommends a bounded message column (its default is 672 px), an optional home screen with starter prompts, stable component identity during streamed updates, and explicit auto-scroll controls. Napas Jakarta will use an approximately 760 px reading column, an empty-state starter grid, one message component per turn, and near-bottom-only follow behavior. [Carbon chat layout](https://chat.carbondesignsystem.com/tag/latest/docs/documents/UI_customization.Layout.html), [Carbon home screen](https://chat.carbondesignsystem.com/tag/latest/docs/documents/UI_customization.Home_screen.html), [Carbon response customization](https://chat.carbondesignsystem.com/tag/latest/docs/documents/UI_customization.Customizing_responses.html), [Carbon auto-scroll options](https://chat.carbondesignsystem.com/tag/latest/docs/interfaces/Type_reference.AutoScrollOptions.html)
- Quasar's layout system provides real header, aside, main, and footer landmarks. Use those semantic regions and keep one main landmark so keyboard and screen-reader navigation follow the product hierarchy. [Quasar QLayout](https://quasar.dev/layout/layout/)
- NiceGUI recommends framework-native `ui.*` elements before raw CSS/JavaScript, background I/O through its managed async helpers, and per-client rather than process-global state. The implementation should follow those constraints. [NiceGUI concise reference](https://nicegui.io/llms.txt)

## Product information architecture

Use one responsive application shell instead of four peer-level radio buttons floating under introductory copy.

### Global shell

- **Top app bar:** 40 px brand mark, “Napas Jakarta”, compact `Official snapshot` badge, newest-observation time, language switcher, terminology/help button, and theme control if it can be supported without compromising category colors.
- **Desktop navigation rail/drawer:** Ask, Map, Overview, Trends. Each item has one Material icon, one label, and an active indicator. The drawer contains navigation only—not map controls, definitions, or dense status copy.
- **Mobile navigation:** compact bottom navigation or horizontal tab bar with the same four destinations; no permanently open drawer.
- **Main page region:** centered responsive container, maximum width approximately 1440 px, 12-column grid on expanded screens, 8 columns on medium, and 4 columns on compact.
- **Help surface:** PM2.5, PM10, ISPU, concentration units, freshness, median, and source caveats live in one accessible dialog or right drawer opened from the app bar. Contextual one-line help remains beside complex controls.

### Stable page template

Every destination uses the same vertical rhythm:

1. page title and one-sentence purpose;
2. freshness/source strip;
3. optional filter/action toolbar;
4. primary content surface;
5. secondary analysis/detail surface;
6. page-specific limitations or methodology note.

## Design tokens

Create a single `theme.py` and CSS variable layer; pages must not invent local colors, shadows, radii, or spacing.

### Brand and surfaces

- Primary: `#086B68`; on-primary: `#FFFFFF`.
- Primary container: `#BDECE6`; on-primary-container: `#073B39`.
- Background: `#F7FAF9`; surface: `#FFFFFF`.
- Surface container: `#EDF3F1`; surface container high: `#E3ECE9`.
- Text: `#172B2B`; muted text: `#5E706E`; outline: `#B8C9C5`.
- Error: `#BA1A1A`; warning: `#8A4F00`; information: `#205C8A`.

### Air-quality data palette

Keep this palette exclusive to measurement categories and legends:

- Good `#2E7D32`
- Moderate `#D6A700`
- Unhealthy `#E45D20`
- Very unhealthy `#C62828`
- Hazardous `#6A1B9A`
- Missing/stale `#78909C`

Never color a button, link, or success toast with the air-quality scale merely for decoration. Include text labels/icons so status is not color-only.

### Shape, spacing, and type

- Base spacing unit: 4 px; normal gaps: 8, 12, 16, 24, 32, 48 px.
- Content padding: 16 px compact, 24 px medium, 32 px expanded.
- Cards: 12 px radius; prominent panels: 16 px; pills/chips: full radius.
- One subtle border and, at most, low elevation for cards; no arbitrary gradients or stacked shadows.
- Typography: system/Roboto stack; display 32/40, page title 24/32, section title 18/26, body 15/24, label 13/18. Limit long-form chat text to roughly 70–80 characters per line.
- Motion: 120–220 ms for navigation/filter state, no decorative looping motion, and honor `prefers-reduced-motion`.

## Page specifications

### Ask

- Use a dedicated centered conversation column (`max-width: 760px`) within the wider shell.
- Empty state: concise capability statement, current-data caveat, and a 2×2 starter-card grid for current conditions, causes, policy, and protection.
- Completed user turns use a compact tinted bubble aligned right; assistant responses use a clean left-aligned content block rather than a large decorated card.
- Keep the project logo in the global header/favicon only. Do not brand every assistant message.
- The composer is inline after the transcript, with multiline input, send icon, keyboard hint, and concise “educational, not medical advice” helper text. It is not fixed to the viewport.
- During generation, update one persistent Markdown element from native Claude deltas. Show a small source-search state only until the first delta.
- Maintain near-bottom-only following: continue following if the reader is at the end; stop immediately when they scroll upward; never jump on response completion.
- Put answer actions in a quiet footer: helpful/not helpful, copy, and “Sources (n)”. Technical retrieval metadata belongs in a developer/details dialog, not inline with every answer.

### Live map

- Primary surface: interactive `ui.leaflet` map spanning 8–9 columns on desktop and full width on compact screens.
- Secondary surface: filter panel or collapsible filter sheet, not a narrow information sidebar. Controls: district, category, freshness, color meaning, and reset.
- Use category-colored markers with clear selection/hover states. Popup content follows a fixed hierarchy: station name, category + ISPU, PM2.5 concentration, observed time, district, source.
- Place a compact legend on the map at expanded widths and immediately below it on mobile.
- Add snapshot summary cards above the map: stations reporting, highest ISPU, median ISPU, and newest time.
- Selecting a marker may highlight the corresponding station row, but do not restore the removed “investigate station” panel.

### Current overview

- First row: four equal KPI cards with icon, label, value, and contextual subtitle—not raw framework metrics.
- Second row: responsive two-card chart grid using `ui.echart`: category distribution and district median. Provide tooltips, axes/labels where relevant, and accessible text summaries.
- Third row: one Quasar `ui.table` for all stations with client-side search, category/district filters, sorting, explicit row numbers, sticky header, and 20-row pagination.
- “20 highest readings” becomes a sortable preset or clearly separated ranked panel; avoid showing two nearly identical full tables without purpose.
- Use human-readable station/district names and formatted WIB timestamps throughout.

### Trends

- Put date range, pollutant series, aggregation, and reset controls in one toolbar.
- Use ECharts with PM2.5 and PM10 as separately toggleable series, human tooltips, data zoom, and visible units.
- Add summary cards for selected-period average, peak, available-day count, and missingness.
- Keep the historical-source caveat adjacent to the chart and visually separate city-model history from official station snapshots.
- The raw historical table should be collapsible/downloadable, not the dominant page element.

## Citation and source interaction

Plain `[source-id]` tokens are not an acceptable final state.

- Add one shared, tested `linkify_citations(answer_text, sources)` renderer.
- During streaming, show the raw accumulated Markdown so incomplete citation syntax cannot create flickering links.
- When the response finishes and citation validation succeeds, update the **same message component in place** so every recognized `[source-id]` becomes a descriptive Markdown hyperlink to that source URL.
- Open external sources in a new tab and use `rel="noopener noreferrer"` where the renderer permits.
- Preserve the original unmodified answer string for evaluation, logs, and conversation history. Store/render linked Markdown separately so presentation never alters evaluation evidence.
- Beneath the answer, show a collapsed “Sources (n)” section containing title, publisher, domain, and a short retrieved excerpt. Unsupported/ungrounded citation IDs remain visually flagged rather than linked.
- Apply the same shared renderer to the current Streamlit compatibility UI immediately, so links work before the NiceGUI cutover is complete.

## Application architecture

### Preserve

- `app/rag.py`, `app/provider.py`, `app/tools.py`, retrieval, ingestion, policy, provenance, monitoring, and evaluation remain the domain layer.
- The existing FastAPI endpoints and contracts remain available.
- Native Anthropic streaming and bounded conversation context remain provider behavior.

### Add

Suggested structure:

```text
app/
  web.py                     # NiceGUI/FastAPI entry point
  citations.py               # canonical-to-linked presentation helper
  webui/
    theme.py                 # tokens and global CSS
    state.py                 # per-client conversation/navigation/filter state
    shell.py                 # header, navigation, responsive page container
    components/
      chat.py
      source_list.py
      metric_card.py
      filter_bar.py
      station_table.py
    pages/
      ask.py
      map.py
      overview.py
      trends.py
```

- Add `nicegui>=3.16,<4` as the UI dependency.
- Register the existing icon through NiceGUI's favicon support and serve it through the framework's static-file helper.
- Mount NiceGUI into the existing FastAPI application or expose a combined `app.web:app` ASGI entry point so UI and API share one deployable process.
- Run blocking provider/network work with NiceGUI's managed I/O worker. Forward provider deltas to an `asyncio.Queue`, then update the client-owned Markdown element from the async UI task. Never mutate another client's elements.
- Keep conversation/navigation/filter state per browser client or tab, not in module globals.
- Change local, Docker, Render, Makefile, and README launch commands from Streamlit to the combined ASGI/NiceGUI entry point after parity tests pass.
- Retain `app/ui.py` as a temporary compatibility/rollback surface until the new shell passes all acceptance checks; it should not remain the documented default.

## Accessibility and responsive requirements

- Use semantic Quasar/NiceGUI landmarks, one `main`, ordered headings, labeled navigation, and keyboard-operable controls.
- Visible focus rings must meet the design token system; do not remove outlines.
- Category status always includes text, not color alone.
- Target WCAG 2.2 AA contrast for text and interactive states.
- Provide accessible chart summaries and table alternatives.
- At compact widths, cards stack, map filters collapse into a sheet, tables scroll horizontally, and primary actions stay reachable without overlaying content.
- Test English and Bahasa Indonesia strings for overflow and control width.

## Implementation workstreams (no calendar schedule)

1. **Immediate correctness:** retain the positive iframe-height fix; add citation linkification to the existing Streamlit UI with regression tests.
2. **Foundation:** add NiceGUI, theme tokens, combined FastAPI entry point, static favicon, and responsive application shell.
3. **Ask parity:** per-client state, full history, native streaming bridge, linked citations, feedback, copy/source actions, and reader-controlled scrolling.
4. **Data pages:** Leaflet map, ECharts overview/trends, and Quasar station table using existing normalized data helpers.
5. **Runtime cutover:** update run/deployment documentation and health checks, keeping Streamlit as an explicitly labeled fallback.
6. **Polish and audit:** responsive states, loading/empty/error/stale states, bilingual layout, keyboard/focus/contrast, reduced motion, and visual regression screenshots.

## Verification and acceptance

- Ruff, full pytest, and Python compilation pass.
- Unit tests cover citation linking, unsafe/unknown source IDs, design token uniqueness, filters, pagination, and state isolation.
- Provider tests continue proving ordered Anthropic deltas, exact final accumulation, interruption safety, and usage accounting.
- NiceGUI screen tests cover every route/page, navigation state, responsive breakpoints, table controls, empty/error states, and a two-turn conversation.
- A real configured Haiku smoke test proves the first visible delta arrives before completion and that final links replace citation tokens in the same message component.
- Browser QA checks 1440 px desktop, 1024 px tablet, and 390 px mobile widths; keyboard navigation; scroll interruption/resumption; map popup/legend; table sorting/pagination; chart tooltips; header logo; and favicon.
- The default local command serves the combined NiceGUI application on port 8502 and its health endpoint returns 200.

## Definition of done

Napas Jakarta has a coherent Quasar Material application shell, consistent tokens and responsive grids, a professional bounded chat experience, real streaming with reader-respecting scroll behavior, clickable in-place citations plus source details, a rich interactive map, purposeful charts, one capable station table, accessible terminology/help, and a single documented NiceGUI/FastAPI runtime whose automated and browser checks pass.
