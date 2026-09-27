import test from "node:test";
import assert from "node:assert/strict";
import { shouldShowPendingThinking, shouldShowSuggestedQuestions } from "./chat-state.ts";

test("shows thinking before an assistant response has text", () => {
  assert.equal(
    shouldShowPendingThinking({ isBusy: true, isResuming: false }),
    true,
  );
});

test("keeps thinking visible while a full assistant response is being buffered", () => {
  assert.equal(
    shouldShowPendingThinking({ isBusy: true, isResuming: false }),
    true,
  );
});

test("does not show thinking after the turn is no longer active", () => {
  assert.equal(
    shouldShowPendingThinking({ isBusy: false, isResuming: false }),
    false,
  );
});

test("shows suggested questions on an empty conversation", () => {
  assert.equal(
    shouldShowSuggestedQuestions({
      hasAssistantAnswer: false,
      isBusy: false,
      isEmpty: true,
      isResuming: false,
    }),
    true,
  );
});

test("restores suggested questions after a completed assistant answer", () => {
  assert.equal(
    shouldShowSuggestedQuestions({
      hasAssistantAnswer: true,
      isBusy: false,
      isEmpty: false,
      isResuming: false,
    }),
    true,
  );
});

test("hides suggested questions while a new turn is active", () => {
  assert.equal(
    shouldShowSuggestedQuestions({
      hasAssistantAnswer: true,
      isBusy: true,
      isEmpty: false,
      isResuming: false,
    }),
    false,
  );
});
