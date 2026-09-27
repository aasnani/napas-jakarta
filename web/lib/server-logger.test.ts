import assert from "node:assert/strict";
import { test } from "node:test";
import { emitServerLog } from "./server-logger.ts";
import { emitServerException } from "./server-logger.ts";

test("emitServerLog writes JSON without prompt or secret fields", () => {
  const originalLog = console.log;
  const lines: string[] = [];
  console.log = (line?: unknown) => lines.push(String(line));

  try {
    emitServerLog("error", "chat_failure", {
      alertable: true,
      api_key: "secret",
      input_chars: 42,
      question: "private user prompt",
    });
  } finally {
    console.log = originalLog;
  }

  assert.equal(lines.length, 1);
  const record = JSON.parse(lines[0]) as Record<string, unknown>;
  assert.equal(record.event, "chat_failure");
  assert.equal(record.level, "error");
  assert.equal(record.alertable, true);
  assert.equal(record.input_chars, 42);
  assert.equal("api_key" in record, false);
  assert.equal("question" in record, false);
});

test("emitServerException includes the stacktrace in the server event", () => {
  const originalLog = console.log;
  const lines: string[] = [];
  console.log = (line?: unknown) => lines.push(String(line));

  try {
    emitServerException("error", "provider_failure", new Error("provider detail"));
  } finally {
    console.log = originalLog;
  }

  const record = JSON.parse(lines[0]) as Record<string, unknown>;
  assert.equal(record.error_type, "Error");
  assert.equal(typeof record.stacktrace, "string");
  assert.match(String(record.stacktrace), /Error: provider detail/);
});
