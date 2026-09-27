import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { chatGlobalRateLimiter, chatRateLimiter, requestClientKey } from "@/lib/request-rate-limit";

const MAX_CHAT_REQUEST_BYTES = 128_000;
const EVE_TURN_PATH = /^\/eve\/v1\/session(?:\/[^/]+)?$/u;

export function proxy(request: NextRequest) {
  const routerHost = process.env.VERCEL_URL;
  const forwardedHost = request.headers.get("x-forwarded-host");
  if (process.env.__VERCEL_DEV_RUNNING === "1" && routerHost && forwardedHost !== routerHost) {
    const target = request.nextUrl.clone();
    target.protocol = "http:";
    target.host = routerHost;
    return NextResponse.redirect(target);
  }

  if (request.method === "POST" && EVE_TURN_PATH.test(request.nextUrl.pathname)) {
    const contentLength = Number(request.headers.get("content-length") ?? 0);
    if (contentLength > MAX_CHAT_REQUEST_BYTES) {
      return NextResponse.json({ error: "Chat request is too large." }, { status: 413 });
    }
    const clientKey = requestClientKey(request);
    const clientDecision = chatRateLimiter.allow(clientKey);
    const globalDecision = clientDecision.allowed
      ? chatGlobalRateLimiter.allow("all-chat")
      : clientDecision;
    const decision = clientDecision.allowed ? globalDecision : clientDecision;
    if (!decision.allowed) {
      return NextResponse.json(
        { error: "Too many chat requests. Please try again shortly." },
        {
          headers: {
            "Cache-Control": "no-store",
            "Retry-After": String(decision.retryAfterSeconds),
          },
          status: 429,
        },
      );
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/eve/v1/:path*"],
};
