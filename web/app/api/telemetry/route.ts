import { NextResponse } from "next/server";
import { requestClientKey, telemetryRateLimiter } from "@/lib/request-rate-limit";
import { internalApiHeaders, napasApiOrigin } from "@/lib/server-api";

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
      return NextResponse.json({ status: "unavailable" }, { status: 202 });
    }
  } catch {
    return NextResponse.json({ status: "unavailable" }, { status: 202 });
  }

  return NextResponse.json({ status: "recorded" });
}

function isTelemetryBody(value: unknown): value is {
  readonly payload: Record<string, unknown>;
  readonly type: keyof typeof TARGETS;
} {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    (record.type === "feedback" || record.type === "turn") &&
    typeof record.payload === "object" &&
    record.payload !== null &&
    !Array.isArray(record.payload)
  );
}
