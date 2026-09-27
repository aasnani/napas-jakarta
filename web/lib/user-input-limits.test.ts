import assert from "node:assert/strict";
import test from "node:test";
import {
  countWords,
  extractEveMessageText,
  MAX_CHAT_CHARACTERS,
  MAX_CHAT_WORDS,
  validateChatInput,
  validateEveRequestPayload,
} from "./user-input-limits.ts";

test("counts multilingual words without treating punctuation as words", () => {
  assert.equal(countWords("PM2.5 di Jakarta, hari ini."), 5);
});

test("allows 500 words and rejects the next word", () => {
  const withinLimit = Array.from({ length: MAX_CHAT_WORDS }, (_, index) => `kata${index}`).join(" ");
  const overLimit = `${withinLimit} kata500`;

  assert.equal(validateChatInput(withinLimit), undefined);
  assert.equal(validateChatInput(overLimit), "word-limit");
});

test("rejects oversized characters even when word count is low", () => {
  assert.equal(validateChatInput("x".repeat(MAX_CHAT_CHARACTERS + 1)), "character-limit");
});

test("extracts only text parts from an Eve message payload", () => {
  assert.equal(
    extractEveMessageText([
      { type: "text", text: "first" },
      { type: "file", data: "ignored", mediaType: "text/plain" },
      { type: "text", text: "second" },
    ]),
    "first\nsecond",
  );
});

test("guards Eve message and client context payloads", () => {
  const withinLimit = Array.from({ length: MAX_CHAT_WORDS }, (_, index) => `kata${index}`).join(" ");

  assert.equal(validateEveRequestPayload({ message: withinLimit, clientContext: { napas: true } }), undefined);
  assert.equal(validateEveRequestPayload({ message: `${withinLimit} tambahan` }), "word-limit");
  assert.equal(
    validateEveRequestPayload({ message: "ok", clientContext: "x".repeat(8_001) }),
    "context-limit",
  );
});
