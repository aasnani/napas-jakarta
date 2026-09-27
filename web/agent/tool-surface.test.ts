import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("the public Napas agent disables Eve's optional default tools", async () => {
  const source = await readFile(new URL("./agent.ts", import.meta.url), "utf8");

  assert.match(source, /defaultTools:\s*false/);
});
