import assert from "node:assert/strict";
import test from "node:test";
import { probeEveHealth } from "./eve-health.ts";

const originalOrigin = process.env.EVE_NEXT_PRODUCTION_ORIGIN;

test.afterEach(() => {
  if (originalOrigin === undefined) {
    delete process.env.EVE_NEXT_PRODUCTION_ORIGIN;
  } else {
    process.env.EVE_NEXT_PRODUCTION_ORIGIN = originalOrigin;
  }
});

test("Eve health probe accepts only the ready response", async () => {
  process.env.EVE_NEXT_PRODUCTION_ORIGIN = "http://127.0.0.1:4274/";
  const requests: string[] = [];

  const ready = await probeEveHealth(async (input) => {
    requests.push(String(input));
    return new Response(JSON.stringify({ ok: true, status: "ready" }), { status: 200 });
  });

  assert.equal(ready, true);
  assert.deepEqual(requests, ["http://127.0.0.1:4274/eve/v1/health"]);
});

test("Eve health probe fails closed for unavailable, non-ready, and malformed responses", async () => {
  process.env.EVE_NEXT_PRODUCTION_ORIGIN = "http://127.0.0.1:4274";

  assert.equal(
    await probeEveHealth(async () => new Response(JSON.stringify({ status: "starting" }), { status: 200 })),
    false,
  );
  assert.equal(await probeEveHealth(async () => new Response("", { status: 503 })), false);
  assert.equal(
    await probeEveHealth(async () => new Response("not json", { status: 200 })),
    false,
  );
  assert.equal(
    await probeEveHealth(async () => {
      throw new Error("connection refused");
    }),
    false,
  );
});
