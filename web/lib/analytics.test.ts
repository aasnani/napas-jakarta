import assert from "node:assert/strict";
import test from "node:test";
import { sanitizeAnalyticsUrl, trackNapasEvent } from "./analytics.ts";

test("sanitizes analytics page locations by removing query strings and fragments", () => {
  assert.equal(
    sanitizeAnalyticsUrl("https://napasjakarta.armasn.dev/about?email=person@example.com#team", true),
    "https://napasjakarta.armasn.dev/about",
  );
});

test("reduces analytics referrers to their origin", () => {
  assert.equal(
    sanitizeAnalyticsUrl("https://search.example/results?q=private#top"),
    "https://search.example",
  );
});

test("rejects malformed and non-web analytics URLs", () => {
  assert.equal(sanitizeAnalyticsUrl("not a URL", true), "");
  assert.equal(sanitizeAnalyticsUrl("javascript:alert(1)", true), "");
});

test("sets sanitized page context before sending an opted-in interaction event", () => {
  const previousWindow = Object.getOwnPropertyDescriptor(globalThis, "window");
  const previousDocument = Object.getOwnPropertyDescriptor(globalThis, "document");
  const calls: unknown[][] = [];
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: {
      location: {
        href: "https://napasjakarta.armasn.dev/?email=person@example.com#contact",
        pathname: "/",
      },
      napasAnalyticsConsent: "granted",
      gtag: (...args: unknown[]) => calls.push(args),
    },
  });
  Object.defineProperty(globalThis, "document", {
    configurable: true,
    value: { referrer: "https://search.example/results?q=private#top" },
  });

  try {
    trackNapasEvent("map_zoom_control_clicked", { direction: "in" });
    assert.deepEqual(calls, [
      ["set", "page_location", "https://napasjakarta.armasn.dev/"],
      ["set", "page_referrer", "https://search.example"],
      ["event", "map_zoom_control_clicked", { direction: "in" }],
    ]);
  } finally {
    if (previousWindow) Object.defineProperty(globalThis, "window", previousWindow);
    else Reflect.deleteProperty(globalThis, "window");
    if (previousDocument) Object.defineProperty(globalThis, "document", previousDocument);
    else Reflect.deleteProperty(globalThis, "document");
  }
});
