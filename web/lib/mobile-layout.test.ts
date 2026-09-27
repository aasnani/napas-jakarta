import assert from "node:assert/strict";
import test from "node:test";
import { MOBILE_DEFAULT_SURFACE, toggleMobileMapOverlay } from "./mobile-layout.ts";

test("mobile opens on the assistant surface", () => {
  assert.equal(MOBILE_DEFAULT_SURFACE, "assistant");
});

test("mobile map control toggles the overlay state", () => {
  assert.equal(toggleMobileMapOverlay(false), true);
  assert.equal(toggleMobileMapOverlay(true), false);
});
