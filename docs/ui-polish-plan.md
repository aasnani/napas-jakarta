# Napas Jakarta UI polish and data-readability plan

## Objective

Make the application feel like a coherent air-quality product rather than a set of Streamlit demos, while preserving the existing citation-grounded RAG behavior, official-source provenance, monitoring, and evaluation work.

## 1. Verify what the map is actually claiming

- Audit the latest PM2.5 observation selected for every station and report the category distribution, timestamp range, and ISPU range.
- Treat the official category in the ingested feed as the health-category source of truth; do not recalculate or silently relabel it.
- Make the UI explicit that the map shows the latest *loaded* observation, not a guarantee of minute-by-minute conditions.
- Show the newest-observation time and category counts near the map so an all-green/yellow map is interpretable rather than suspicious.
- Retain the relative-to-network-median color mode, but label it as a comparison view rather than a health rating.

Acceptance criteria:

- A user can tell which timestamp/window the map represents.
- The map legend distinguishes official health categories from relative comparison colors.
- Missing/stale observations remain visibly distinct from healthy readings.

## 2. Normalize station and district display names without changing identifiers

- Add one shared display-name helper that removes machine/source prefixes while leaving the underlying station ID and raw source value untouched.
- Examples: `DKI_PM25_64 SMPN 88 Jakarta (ROOFTOP)` becomes `SMPN 88 Jakarta (Rooftop)`; `LCS-09 PT. JIEP` becomes `PT. JIEP`; `DKI1 Bundaran HI` becomes `Bundaran HI`.
- Use the display name consistently in map tooltips, overview metrics/tables, search results, and chat-facing measurement summaries where practical.
- Humanize district labels such as `Kota Adm. Jakarta Pusat` to `Jakarta Pusat` for display only.
- Keep raw IDs available in data/tooling for joins, provenance, debugging, and tests.

Acceptance criteria:

- No visible station name begins with a DKI/DKJ/LCS source code when a readable suffix exists.
- Search accepts both the raw and display forms where possible.

## 3. Give the chat a true bottom composer

- Replace tab-contained navigation with a stateful top-level page selector so the chat composer can be rendered at the root of the active chat page.
- Render the complete message history first and `st.chat_input` last, then process a submitted prompt and rerun. This prevents the composer from being stranded between the old history and the newest turn.
- Preserve the existing conversation history passed to RAG and the new-conversation behavior.
- Keep all non-chat views free of the chat composer.

Acceptance criteria:

- After multiple turns, the composer remains below the latest assistant message.
- Message order is user, assistant, user, assistant with no input field inserted between turns.
- Switching views and returning to Ask preserves the conversation.

## 4. Make the assistant feel alive without exposing chain-of-thought

- Add a restrained branded header, message-card styling, assistant/user avatars, and subtle entrance/pulse animation that does not interfere with accessibility.
- Add useful starter-question buttons when the conversation is empty.
- During generation, show honest progress stages such as “Checking current observations”, “Searching Jakarta evidence”, and “Preparing a cited answer”. Do not display hidden chain-of-thought or fabricate reasoning text.
- Keep sources, retrieval route, carried conversation context, and citations in inspectable expanders after the answer.
- Retain feedback controls and the educational/medical disclaimer.

Acceptance criteria:

- The wait state visibly changes while an answer is being prepared.
- Users can inspect evidence and process metadata without seeing private model reasoning.
- The design remains usable on narrow screens and respects reduced-motion preferences.

## 5. Put terminology help everywhere it is needed

- Add a compact, reusable “Air-quality terms” explainer visible from every page.
- Define PM2.5 (particles no wider than 2.5 micrometres), PM10 (no wider than 10 micrometres), ISPU (Indonesia's unitless air-pollution index), concentration (`µg/m³`), station, stale/missing data, network median, and the distinction between ISPU and pollutant concentration.
- Add concise contextual captions near maps, charts, and tables rather than forcing users to leave the current view.

Acceptance criteria:

- PM2.5 and PM10 are explained from Ask, Live map, Current overview, and Trends.
- ISPU is never presented as if it were a concentration in `µg/m³`.

## 6. Improve overview tables

- Rename the highest-readings table to “20 highest current readings” and show up to 20 rows, rather than an unlabeled top 10.
- Add an explicit `No.` column to both the highest-readings and all-stations tables.
- Keep all-stations filtering and pagination; number paginated rows according to their position in the filtered result.
- Use display station/district names and friendly column headings in both tables.
- Retain the raw observation time and source meaning while formatting timestamps for humans.

Acceptance criteria:

- The first table contains at most 20 rows and both tables visibly start with `No.`.
- Page two numbering continues after page one instead of restarting at 1.

## 7. New project icon

- Generate an original, compact lungs-and-clean-air mark with a strong silhouette, transparent background, no text, and no third-party marks.
- Save the final raster asset under `assets/` and use it for the Streamlit page icon and assistant avatar, with a safe emoji fallback if the asset cannot be loaded.
- Keep sufficient padding and contrast for 32–64 px display.

Acceptance criteria:

- The generated asset is stored inside the project and referenced by the running app.
- It remains recognizable at favicon/avatar size.

## 8. Verification

- Add unit/contract coverage for display-name normalization, top-20/table numbering helpers, navigation/chat ordering where testable, and category display mapping.
- Run Ruff and the full pytest suite.
- Start or reuse the app on port 8502 and visually verify navigation, multi-turn chat order, map tooltip/legend, both tables, terminology help, responsive width, and the generated icon.
- Recheck the loaded map snapshot after implementation and document what is verified from local data versus what would require independent live-source comparison.

## Definition of done

The work is complete when the chat composer is consistently last, station labels are readable everywhere, the map's category claim is transparent, terminology is accessible on every view, both overview tables are numbered and the highest table uses 20 rows, the chat has polished progress/visual states without chain-of-thought, the generated icon is wired into the app, and automated plus browser-level checks pass.
