// Keep the buffered answer reveal smooth while making it faster than the
// original 72-character-per-second presentation rate.
export const PACED_TEXT_RATE = 130;

const MAX_ELAPSED_MS = 100;
const MAX_CHARACTER_BUDGET = 12;

export type PacedTextStep = {
  readonly characterBudget: number;
  readonly text: string;
};

export function revealPacedText({
  characterBudget,
  elapsedMs,
  rate = PACED_TEXT_RATE,
  targetText,
  visibleText,
}: {
  readonly characterBudget: number;
  readonly elapsedMs: number;
  readonly rate?: number;
  readonly targetText: string;
  readonly visibleText: string;
}): PacedTextStep {
  if (visibleText === targetText) {
    return { characterBudget: 0, text: targetText };
  }

  // A provider can revise a partial part while it is streaming. Showing the
  // replacement in full is safer than mixing the old and new prefixes.
  if (!targetText.startsWith(visibleText)) {
    return { characterBudget: 0, text: targetText };
  }

  const safeElapsedMs = Math.min(Math.max(elapsedMs, 0), MAX_ELAPSED_MS);
  const availableBudget = Math.min(
    Math.max(characterBudget, 0) + (safeElapsedMs * Math.max(rate, 0)) / 1000,
    MAX_CHARACTER_BUDGET,
  );
  const charactersToReveal = Math.min(
    targetText.length - visibleText.length,
    Math.floor(availableBudget),
  );

  return {
    characterBudget: availableBudget - charactersToReveal,
    text:
      charactersToReveal === 0
        ? visibleText
        : targetText.slice(0, visibleText.length + charactersToReveal),
  };
}
