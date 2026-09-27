const SUPERSCRIPT_DIGITS: Record<string, string> = {
  "0": "⁰",
  "1": "¹",
  "2": "²",
  "3": "³",
  "4": "⁴",
  "5": "⁵",
  "6": "⁶",
  "7": "⁷",
  "8": "⁸",
  "9": "⁹",
};

function superscript(value: string): string {
  return [...value].map((character) => SUPERSCRIPT_DIGITS[character] ?? character).join("");
}

function normalizeMathExpression(expression: string): string {
  let value = expression
    .replace(/\\mu/g, "µ")
    .replace(/\\(?:text|mathrm|operatorname)\s*\{([^{}]*)\}/g, "$1")
    .replace(/\\(?:leq?|le)\b/g, "≤")
    .replace(/\\(?:geq?|ge)\b/g, "≥")
    .replace(/\\times\b/g, "×")
    .replace(/\\cdot\b/g, "·")
    .replace(/\\%/g, "%")
    .replace(/\\([_{}])/g, "$1")
    .replace(/\\(?:left|right)\b/g, "")
    .replace(/\s+/g, " ")
    .trim();

  value = value.replace(/PM\s*_\s*\{?2\.5\}?/gi, "PM2.5");
  value = value.replace(/\^\s*\{?([0-9]+)\}?/g, (_match, digits: string) => superscript(digits));
  value = value.replace(/([A-Za-zµ]+)\s*_\s*\{?([^{}]+)\}?/g, "$1$2");
  value = value.replace(/\{([^{}]*)\}/g, "$1");
  value = value.replace(/\\([A-Za-z]+)/g, "$1");
  value = value.replace(/\s+([,.;:!?])/g, "$1");

  return value;
}

function normalizeMath(text: string): string {
  return text
    .replace(/\$\$([\s\S]*?)\$\$/g, (_match, expression: string) => normalizeMathExpression(expression))
    .replace(/\$([^$\n]+)\$/g, (_match, expression: string) => normalizeMathExpression(expression))
    .replace(/\\\(([\s\S]*?)\\\)/g, (_match, expression: string) => normalizeMathExpression(expression))
    .replace(/\\\[([\s\S]*?)\\\]/g, (_match, expression: string) => normalizeMathExpression(expression));
}

function normalizeLine(line: string): string {
  const leadingWhitespace = line.match(/^\s*/)?.[0] ?? "";
  const content = line
    .slice(leadingWhitespace.length)
    .replace(/[ \t]+/g, " ")
    .replace(/\(\s*\)/g, "")
    .replace(/\[\s*\]\(\s*\)/g, "")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/\s+([,.;:!?%)\]}])/g, "$1")
    .replace(/([([{])\s+/g, "$1")
    .replace(/\bportal\s+\./gi, "portal.")
    .replace(/\bportal\.(?!\s*resmi\b)/gi, "portal.")
    .trimEnd();

  return leadingWhitespace + content;
}

/**
 * Keep provider prose readable when a model emits lightweight TeX or empty
 * citation placeholders instead of the plain Markdown contract.
 */
export function normalizeAssistantMarkdown(text: string): string {
  return normalizeMath(text.replace(/\r\n?/g, "\n"))
    .split("\n")
    .map(normalizeLine)
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}
