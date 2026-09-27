type ServerLogLevel = "debug" | "info" | "warn" | "error";

const SENSITIVE_KEY = /(?:api[_-]?key|authorization|cookie|password|prompt|question|answer|content|history|secret|token|credential|body)/i;
const CONTROL_CHARACTER = /[\u0000-\u001f\u007f]/g;
const MAX_STRING_LENGTH = 2_000;
const MAX_STACKTRACE_LENGTH = 12_000;

export function emitServerLog(
  level: ServerLogLevel,
  event: string,
  fields: Record<string, unknown> = {},
): Readonly<Record<string, unknown>> {
  const record: Record<string, unknown> = {
    timestamp: new Date().toISOString(),
    level,
    message: safeText(event, 240),
    service: process.env.RAILWAY_SERVICE_NAME?.trim() || "napas-web",
    environment:
      process.env.RAILWAY_ENVIRONMENT_NAME?.trim() ||
      process.env.RAILWAY_ENVIRONMENT?.trim() ||
      process.env.NODE_ENV ||
      "unknown",
    event: safeText(event, 120),
  };

  for (const [key, value] of Object.entries(fields)) {
    if (SENSITIVE_KEY.test(key)) continue;
    const safeValue = safeFieldValue(key, value);
    if (safeValue !== undefined) record[key] = safeValue;
  }

  console.log(JSON.stringify(record));
  return record;
}

export function emitServerException(
  level: ServerLogLevel,
  event: string,
  error: unknown,
  fields: Record<string, unknown> = {},
): Readonly<Record<string, unknown>> {
  return emitServerLog(level, event, {
    ...fields,
    error_type: error instanceof Error ? error.name : typeof error,
    ...(error instanceof Error && error.stack ? { stacktrace: error.stack } : {}),
  });
}

function safeFieldValue(
  key: string,
  value: unknown,
): string | number | boolean | null | undefined {
  if (value === null || typeof value === "number" || typeof value === "boolean") {
    return value;
  }
  if (typeof value === "string") {
    return safeText(value, key === "stacktrace" ? MAX_STACKTRACE_LENGTH : MAX_STRING_LENGTH);
  }
  return undefined;
}

function safeText(value: string, maxLength: number): string {
  return value.replace(CONTROL_CHARACTER, " ").slice(0, maxLength);
}
