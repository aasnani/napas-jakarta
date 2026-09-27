import assert from "node:assert/strict";
import { test } from "node:test";
import { fetchNapasJson } from "./server-api.ts";

test("fetchNapasJson forwards the internal API token server-side", async () => {
  const previousOrigin = process.env.NAPAS_API_ORIGIN;
  const previousToken = process.env.NAPAS_INTERNAL_TOKEN;
  const previousFetch = globalThis.fetch;
  let capturedRequest: unknown;
  let capturedInit: RequestInit | undefined;

  process.env.NAPAS_API_ORIGIN = "http://api.internal";
  process.env.NAPAS_INTERNAL_TOKEN = "test-secret";
  globalThis.fetch = async (input, init) => {
    capturedRequest = input;
    capturedInit = init;
    return new Response(JSON.stringify({ ok: true }), {
      headers: { "content-type": "application/json" },
      status: 200,
    });
  };

  try {
    const result = await fetchNapasJson<{ ok: boolean }>("/sources");

    assert.deepEqual(result, { ok: true });
    assert.equal(String(capturedRequest), "http://api.internal/sources");
    assert.equal(
      new Headers(capturedInit?.headers).get("X-Napas-Internal-Token"),
      "test-secret",
    );
  } finally {
    globalThis.fetch = previousFetch;
    if (previousOrigin === undefined) delete process.env.NAPAS_API_ORIGIN;
    else process.env.NAPAS_API_ORIGIN = previousOrigin;
    if (previousToken === undefined) delete process.env.NAPAS_INTERNAL_TOKEN;
    else process.env.NAPAS_INTERNAL_TOKEN = previousToken;
  }
});
