import { strictEqual } from "node:assert/strict";
import { test } from "node:test";
import {
  DEFAULT_GEMINI_MODEL,
  DEFAULT_GEMINI_REQUEST_TIMEOUT_MS,
  classifyGeminiFailure,
  selectGeminiModel,
  selectGeminiRequestTimeout,
} from "./model.ts";

test("selectGeminiModel defaults to the supported Flash-Lite model", () => {
  strictEqual(selectGeminiModel(undefined), DEFAULT_GEMINI_MODEL);
});

test("selectGeminiModel trims a configured model name", () => {
  strictEqual(selectGeminiModel("  gemini-3.5-flash-lite  "), "gemini-3.5-flash-lite");
});

test("selectGeminiRequestTimeout defaults to a bounded request window", () => {
  strictEqual(selectGeminiRequestTimeout(undefined), DEFAULT_GEMINI_REQUEST_TIMEOUT_MS);
  strictEqual(selectGeminiRequestTimeout("not-a-duration"), DEFAULT_GEMINI_REQUEST_TIMEOUT_MS);
});

test("selectGeminiRequestTimeout accepts a positive millisecond override", () => {
  strictEqual(selectGeminiRequestTimeout("45000"), 45000);
});

test("classifyGeminiFailure keeps provider failures safe and queryable", () => {
  strictEqual(classifyGeminiFailure(undefined, 429), "rate_limited");
  strictEqual(classifyGeminiFailure(undefined, 503), "upstream_5xx");
  strictEqual(classifyGeminiFailure(new Error("provider detail")), "request_failed");
});
