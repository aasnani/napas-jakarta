export const MAX_CHAT_WORDS = 500;
export const MAX_CHAT_CHARACTERS = 8_000;
export const MAX_CLIENT_CONTEXT_CHARACTERS = 8_000;

const WORD_RE = /[\p{L}\p{N}]+(?:[.'’\-][\p{L}\p{N}]+)*/gu;

export type ChatInputViolation = "character-limit" | "word-limit";

export function countWords(value: string): number {
  return value.match(WORD_RE)?.length ?? 0;
}

export function validateChatInput(value: string): ChatInputViolation | undefined {
  if (value.length > MAX_CHAT_CHARACTERS) return "character-limit";
  if (countWords(value) > MAX_CHAT_WORDS) return "word-limit";
  return undefined;
}

export function extractEveMessageText(message: unknown): string {
  if (typeof message === "string") return message;
  if (!Array.isArray(message)) return "";

  return message
    .filter(
      (part): part is { readonly text: string; readonly type: "text" } =>
        typeof part === "object" &&
        part !== null &&
        (part as { readonly type?: unknown }).type === "text" &&
        typeof (part as { readonly text?: unknown }).text === "string",
    )
    .map((part) => part.text)
    .join("\n");
}

export function validateEveRequestPayload(payload: unknown): ChatInputViolation | "context-limit" | undefined {
  if (typeof payload !== "object" || payload === null || Array.isArray(payload)) return undefined;

  const record = payload as { readonly message?: unknown; readonly clientContext?: unknown };
  const messageViolation = validateChatInput(extractEveMessageText(record.message));
  if (messageViolation) return messageViolation;

  if (record.clientContext !== undefined) {
    let serializedContext: string | undefined;
    try {
      serializedContext = JSON.stringify(record.clientContext);
    } catch {
      return "context-limit";
    }
    if (typeof serializedContext !== "string" || serializedContext.length > MAX_CLIENT_CONTEXT_CHARACTERS) {
      return "context-limit";
    }
  }

  return undefined;
}
