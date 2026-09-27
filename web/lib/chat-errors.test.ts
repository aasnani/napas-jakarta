import assert from "node:assert/strict";
import test from "node:test";
import { localizeChatError } from "./chat-errors.ts";

test("chat errors never expose provider or runtime details", () => {
  assert.equal(
    localizeChatError("Gemini returned an internal stack trace", "en"),
    "The model is temporarily unavailable. Please try again.",
  );
  assert.equal(
    localizeChatError("TypeError: fetch failed at provider.ts:44", "en"),
    "The model is temporarily unavailable. Please try again.",
  );
  assert.equal(
    localizeChatError("unexpected secret-bearing runtime message", "en"),
    "We could not complete that request. Please try again.",
  );
});

test("chat cancellation errors remain localized", () => {
  assert.equal(
    localizeChatError("AbortError: operation aborted", "id"),
    "Respons tidak dapat dihentikan.",
  );
});
