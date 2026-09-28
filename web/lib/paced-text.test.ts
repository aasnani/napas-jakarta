import { strictEqual } from "node:assert/strict";
import { test } from "node:test";
import { revealPacedText } from "./paced-text.ts";

test("revealPacedText releases only the available character budget", () => {
  const step = revealPacedText({
    characterBudget: 0,
    elapsedMs: 100,
    targetText: "A buffered answer",
    visibleText: "",
  });

  strictEqual(step.text, "A buffered a");
  strictEqual(Number(step.characterBudget.toFixed(3)), 0);
});

test("revealPacedText carries fractional budget between frames", () => {
  const first = revealPacedText({
    characterBudget: 0,
    elapsedMs: 8,
    targetText: "abcdef",
    visibleText: "",
  });
  const second = revealPacedText({
    characterBudget: first.characterBudget,
    elapsedMs: 8,
    targetText: "abcdef",
    visibleText: first.text,
  });

  strictEqual(first.text, "a");
  strictEqual(second.text, "abc");
  strictEqual(Number(second.characterBudget.toFixed(3)), 0.2);
});

test("revealPacedText completes immediately when the stream target changes", () => {
  const step = revealPacedText({
    characterBudget: 0,
    elapsedMs: 16,
    targetText: "corrected answer",
    visibleText: "partial answer",
  });

  strictEqual(step.text, "corrected answer");
  strictEqual(step.characterBudget, 0);
});
