import assert from "node:assert/strict";
import { test } from "node:test";
import { FixedWindowRateLimiter, requestClientKey } from "./request-rate-limit.ts";

test("fixed window limiter returns a retry interval after the budget is spent", () => {
  const limiter = new FixedWindowRateLimiter({ maxRequests: 2, windowMs: 1000 });

  assert.equal(limiter.allow("client", 1000).allowed, true);
  assert.equal(limiter.allow("client", 1100).allowed, true);
  const rejected = limiter.allow("client", 1200);

  assert.equal(rejected.allowed, false);
  assert.equal(rejected.retryAfterSeconds, 1);
  assert.equal(limiter.allow("client", 2000).allowed, true);
});

test("proxy headers are ignored unless the deployment opts in", () => {
  const previous = process.env.TRUST_PROXY_HEADERS;
  delete process.env.TRUST_PROXY_HEADERS;
  try {
    const request = new Request("https://napas.example/eve/v1/session", {
      headers: { "x-forwarded-for": "198.51.100.10", "x-real-ip": "198.51.100.10" },
    });
    assert.equal(requestClientKey(request), "unknown");
  } finally {
    if (previous === undefined) delete process.env.TRUST_PROXY_HEADERS;
    else process.env.TRUST_PROXY_HEADERS = previous;
  }
});

test("proxy headers use the first forwarded address when explicitly trusted", () => {
  const previous = process.env.TRUST_PROXY_HEADERS;
  process.env.TRUST_PROXY_HEADERS = "true";
  try {
    const request = new Request("https://napas.example/eve/v1/session", {
      headers: { "x-forwarded-for": "198.51.100.10, 203.0.113.20" },
    });
    assert.equal(requestClientKey(request), "198.51.100.10");
  } finally {
    if (previous === undefined) delete process.env.TRUST_PROXY_HEADERS;
    else process.env.TRUST_PROXY_HEADERS = previous;
  }
});
