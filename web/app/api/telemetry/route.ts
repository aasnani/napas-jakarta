import { NextResponse } from "next/server";
import { requestClientKey, telemetryRateLimiter } from "@/lib/request-rate-limit";
import { internalApiHeaders, napasApiOrigin } from "@/lib/server-api";
import { emitServerLog } from "@/lib/server-logger";

const MAX_PAYLOAD_BYTES = 64_000;
const TARGETS = {
  feedback: "/feedback",
  turn: "/chat-telemetry",
} as const;

export async function POST(request: Request) {
  const rateLimit = telemetryRateLimiter.allow(requestClientKey(request));
  if (!rateLimit.allowed) {
    return NextResponse.json(
      { status: "ignored" },
      { headers: { "Retry-After": String(rateLimit.retryAfterSeconds) }, status: 429 },
    );
  }

  const contentLength = Number(request.headers.get("content-length") ?? 0);
  if (contentLength > MAX_PAYLOAD_BYTES) {
    return NextResponse.json({ status: "ignored" }, { status: 413 });
  }

  let body: unknown;
  try {
    const raw = await request.text();
    if (raw.length > MAX_PAYLOAD_BYTES) {
      return NextResponse.json({ status: "ignored" }, { status: 413 });
    }
    body = JSON.parse(raw);
  } catch {
    return NextResponse.json({ status: "ignored" }, { status: 400 });
  }

  if (!isTelemetryBody(body)) {
    return NextResponse.json({ status: "ignored" }, { status: 400 });
  }

  if (body.type === "failure") {
    if (!isChatFailurePayload(body.payload)) {
      return NextResponse.json({ status: "ignored" }, { status: 400 });
    }
    emitServerLog("error", "chat_failure", {
      alertable: true,
      context_messages: body.payload.context_messages,
      conversation_turn: body.payload.conversation_turn,
      critical: true,
      dependency: "eve_or_gemini",
      error_code: body.payload.error_code,
      input_chars: body.payload.input_chars,
      interaction_id: body.payload.interaction_id,
    });
    return NextResponse.json({ status: "recorded" });
  }

  const apiOrigin = napasApiOrigin();
  if (!apiOrigin) {
    return NextResponse.json({ status: "disabled" }, { status: 202 });
  }
  const internalToken = process.env.NAPAS_INTERNAL_TOKEN?.trim();
  if (!internalToken) {
    return NextResponse.json({ status: "disabled" }, { status: 202 });
  }

  try {
    const response = await fetch(`${apiOrigin}${TARGETS[body.type]}`, {
      body: JSON.stringify(body.payload),
      headers: {
        "content-type": "application/json",
        ...internalApiHeaders(),
      },
      method: "POST",
      signal: AbortSignal.timeout(8_000),
    });
    if (!response.ok) {
      emitServerLog("warn", "telemetry_forward_failed", {
        http_status: response.status,
        target: body.type,
      });
      return NextResponse.json({ status: "unavailable" }, { status: 202 });
    }
  } catch {
    emitServerLog("warn", "telemetry_forward_failed", { target: body.type });
    return NextResponse.json({ status: "unavailable" }, { status: 202 });
  }

  return NextResponse.json({ status: "recorded" });
}

function isTelemetryBody(value: unknown): value is {
  readonly payload: Record<string, unknown>;
  readonly type: keyof typeof TARGETS | "failure";
} {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    (record.type === "feedback" || record.type === "turn" || record.type === "failure") &&
    typeof record.payload === "object" &&
    record.payload !== null &&
    !Array.isArray(record.payload)
  );
}

function isChatFailurePayload(
  value: Record<string, unknown>,
): value is {
  readonly context_messages: number;
  readonly conversation_turn: number;
  readonly error_code: string;
  readonly input_chars: number;
  readonly interaction_id: string;
} {
  return (
    typeof value.error_code === "string" &&
    value.error_code.length > 0 &&
    value.error_code.length <= 80 &&
    typeof value.interaction_id === "string" &&
    value.interaction_id.length > 0 &&
    value.interaction_id.length <= 128 &&
    isBoundedInteger(value.input_chars, 0, 8_000) &&
    isBoundedInteger(value.context_messages, 0, 200) &&
    isBoundedInteger(value.conversation_turn, 1, 100)
  );
}

function isBoundedInteger(value: unknown, minimum: number, maximum: number): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= minimum && value <= maximum;
}
