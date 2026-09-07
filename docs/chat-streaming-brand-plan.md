# Chat streaming, scroll, and branding revision

## Outcome

Revise the Ask experience so it behaves like a conventional document-flow chat: the composer appears inline after the conversation, Claude's actual response text arrives progressively, and the page follows generation only when the reader is already near the bottom. Replace the lungs artwork with a simpler Jakarta air-quality mark used only in the page header and browser favicon.

## 1. Brand placement and replacement mark

- Replace the lungs asset with a new original mark based on Jakarta and moving air, with no lungs, nose, face, text, or medical imagery.
- Use the raster mark in exactly two product locations:
  - the visible page header beside “Napas Jakarta”;
  - the browser-tab favicon through `st.set_page_config(page_icon=...)`.
- Do not pass the project logo as a `st.chat_message` avatar. Use Streamlit's normal user/assistant presentation or restrained role-specific non-brand icons.
- Keep an emoji fallback only for the page/favicon if the raster asset is absent.

Acceptance criteria:

- The project mark is visibly present in the main header and browser tab.
- No chat response header/avatar contains the project logo.
- The old lungs artwork is no longer referenced by the application.

## 2. Inline composer, not viewport attachment

- Place `st.chat_input` inside an ordinary Streamlit container rendered after the transcript, which makes it part of document flow rather than the viewport-fixed global chat bar.
- Ensure the complete sequence is always: existing transcript, any currently generated assistant message, disclaimer/controls as appropriate, then composer.
- Use a pending-prompt state transition: submission records the user turn and reruns once so that the user message is rendered in transcript order; the pending assistant response is then streamed above the inline composer.
- Never render a submitted user/assistant pair after the composer.

Acceptance criteria:

- Scrolling away from the bottom also scrolls the composer out of view.
- After several turns, there is only one composer and it remains after the latest response.
- Navigation away from and back to Ask preserves the transcript.

## 3. Real provider streaming

- Extend the provider boundary with an optional text-delta callback (or equivalent iterator) rather than faking word-by-word playback after a buffered answer.
- For Anthropic, request native Messages API streaming and consume `content_block_delta` text deltas as they arrive. Accumulate the exact same final answer for citation validation, logging, feedback, and conversation history.
- Preserve usage accounting from streaming events and retain the configured `claude-haiku-4-5-20251001` model.
- Keep non-streaming call sites and tests backward compatible. Deterministic/no-key fallback may be chunked for display, but it must be clearly an offline fallback rather than described as provider streaming.
- Handle failure safely:
  - before any provider text arrives, use the existing deterministic fallback;
  - after partial provider text arrives, do not append a second contradictory fallback answer; retain the partial response and expose a concise interruption notice.

Acceptance criteria:

- With Claude configured, visible answer text updates from real API deltas before the full response is complete.
- The stored assistant message exactly matches the final visible streamed text.
- Citations, usage, cost, route, source details, and feedback still work after streaming.

## 4. Reading-position and follow behavior

- Remove unconditional end-of-answer `st.rerun()` and any unconditional `scrollIntoView`/scroll-to-bottom behavior.
- On prompt submission, keep the new user turn and assistant stream in the current reading area instead of jumping straight to the document bottom after completion.
- Add near-bottom following behavior with a small, isolated scroll controller only if native Streamlit behavior is insufficient:
  - consider the reader “following” only when they are within a small threshold of the page bottom;
  - while following, advance the viewport as new deltas grow the answer;
  - once the reader scrolls upward beyond the threshold, stop automatic movement;
  - resume following only after they return near the bottom;
  - never force a jump on initial page load, view switching, or response completion.
- Prefer browser-native scroll anchoring and minimal JavaScript; do not create a full custom chat component merely for scrolling.

Acceptance criteria:

- Submitting a question does not immediately teleport the page to the final bottom position.
- While the growing response reaches the viewport edge and the user remains near the bottom, new content stays visible.
- Manually scrolling upward during generation is respected.
- Completion does not trigger a second jump.

## 5. Chat rendering lifecycle

- Render previously completed messages normally without replaying their animation.
- For the pending assistant turn, open one assistant message and progressively update one placeholder/stream target.
- Display a compact initial state such as “Searching observations and sources…” until the first provider delta, then let the streamed answer become the primary activity.
- After completion, render source/provenance expanders and feedback controls without reordering the page.
- Preserve full bounded conversation history for follow-up questions and keep the current-turn de-duplication fix.

## 6. Automated and live verification

- Add provider tests using representative Anthropic SSE events to prove ordered delta delivery, final text accumulation, and usage capture.
- Add UI contract tests for:
  - no logo avatar in chat messages;
  - page header plus favicon use the new asset;
  - chat input is container-scoped and rendered after pending/completed messages;
  - no completion-time rerun or unconditional forced scrolling;
  - two turns remain ordered and only one composer exists.
- Run Ruff, the complete pytest suite, and Python compilation.
- Restart port 8502 with the project `.env` and verify a real Claude response streams. Avoid logging or exposing the API key.
- Use connected browser testing for favicon/header placement and scroll behavior when available; otherwise report the limitation and use Streamlit AppTest for the executable contract.

## Definition of done

The new non-medical Jakarta-air mark appears only in the header and favicon, chat avatars are unbranded, the composer is inline after the transcript, Claude text visibly arrives from native streaming deltas, the viewport follows only while the reader is already near the bottom, response completion causes no jump, and all automated checks pass on the running port-8502 app.
