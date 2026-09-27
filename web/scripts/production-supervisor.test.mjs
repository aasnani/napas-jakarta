import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import test from "node:test";
import { superviseProduction } from "./production-supervisor.mjs";

class FakeChild extends EventEmitter {
  exitCode = null;
  killed = false;

  kill(signal) {
    this.killed = true;
    this.emit("exit", null, signal);
  }
}

function createHarness() {
  const children = [];
  const signalSource = new EventEmitter();
  const spawnProcess = (command, args) => {
    const child = new FakeChild();
    children.push({ args, child, command });
    return child;
  };
  return { children, signalSource, spawnProcess };
}

test("supervisor stops Next when Eve exits unexpectedly", async () => {
  const harness = createHarness();
  const resultPromise = superviseProduction({
    env: { EVE_NEXT_PRODUCTION_PORT: "4274", PORT: "3000" },
    signalSource: harness.signalSource,
    spawnProcess: harness.spawnProcess,
  });

  assert.equal(harness.children.length, 2);
  harness.children[0].child.emit("exit", 1, null);

  assert.equal(await resultPromise, 1);
  assert.equal(harness.children[1].child.killed, true);
});

test("supervisor stops Eve when Next exits unexpectedly", async () => {
  const harness = createHarness();
  const resultPromise = superviseProduction({
    env: { EVE_NEXT_PRODUCTION_PORT: "4274", PORT: "3000" },
    signalSource: harness.signalSource,
    spawnProcess: harness.spawnProcess,
  });

  harness.children[1].child.emit("exit", 2, null);

  assert.equal(await resultPromise, 2);
  assert.equal(harness.children[0].child.killed, true);
});

test("supervisor terminates both children cleanly on service shutdown", async () => {
  const harness = createHarness();
  const resultPromise = superviseProduction({
    env: { EVE_NEXT_PRODUCTION_PORT: "4274", PORT: "3000" },
    signalSource: harness.signalSource,
    spawnProcess: harness.spawnProcess,
  });

  harness.signalSource.emit("SIGTERM");

  assert.equal(await resultPromise, 0);
  assert.equal(harness.children[0].child.killed, true);
  assert.equal(harness.children[1].child.killed, true);
});
