export type RateLimitDecision = {
  readonly allowed: boolean;
  readonly retryAfterSeconds: number;
};

type WindowState = { startedAt: number; count: number };

export class FixedWindowRateLimiter {
  private readonly maxRequests: number;
  private readonly windowMs: number;
  private readonly maxKeys: number;
  private readonly windows = new Map<string, WindowState>();

  constructor(options: { readonly maxRequests: number; readonly windowMs: number; readonly maxKeys?: number }) {
    this.maxRequests = Math.max(1, Math.floor(options.maxRequests));
    this.windowMs = Math.max(1, options.windowMs);
    this.maxKeys = Math.max(1, Math.floor(options.maxKeys ?? 10_000));
  }

  allow(key: string, now = Date.now()): RateLimitDecision {
    for (const [candidate, state] of this.windows) {
      if (now - state.startedAt >= this.windowMs) this.windows.delete(candidate);
    }
    const current = this.windows.get(key) ?? { startedAt: now, count: 0 };
    if (now - current.startedAt >= this.windowMs) {
      current.startedAt = now;
      current.count = 0;
    }
    if (current.count >= this.maxRequests) {
      return {
        allowed: false,
        retryAfterSeconds: Math.max(1, Math.ceil((this.windowMs - (now - current.startedAt)) / 1000)),
      };
    }
    if (!this.windows.has(key) && this.windows.size >= this.maxKeys) {
      const oldestKey = [...this.windows.entries()].reduce((oldest, entry) =>
        entry[1].startedAt < oldest[1].startedAt ? entry : oldest,
      )[0];
      this.windows.delete(oldestKey);
    }
    current.count += 1;
    this.windows.set(key, current);
    return { allowed: true, retryAfterSeconds: 0 };
  }
}

export function requestClientKey(request: Request): string {
  const trustProxyHeaders = ["1", "true", "yes"].includes(
    (process.env.TRUST_PROXY_HEADERS ?? "").trim().toLowerCase(),
  );
  if (!trustProxyHeaders) return "unknown";
  const forwarded = request.headers.get("x-forwarded-for")?.split(",", 1)[0]?.trim();
  if (forwarded) return forwarded;
  return request.headers.get("x-real-ip")?.trim() || "unknown";
}

function configuredInteger(value: string | undefined, fallback: number): number {
  const parsed = Number.parseInt(value ?? "", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

export const chatRateLimiter = new FixedWindowRateLimiter({
  maxRequests: configuredInteger(process.env.CHAT_RATE_LIMIT_MAX, 12),
  windowMs: configuredInteger(process.env.CHAT_RATE_LIMIT_WINDOW_MS, 60000),
});

export const telemetryRateLimiter = new FixedWindowRateLimiter({
  maxRequests: configuredInteger(process.env.TELEMETRY_RATE_LIMIT_MAX, 60),
  windowMs: configuredInteger(process.env.TELEMETRY_RATE_LIMIT_WINDOW_MS, 60000),
});

export const chatGlobalRateLimiter = new FixedWindowRateLimiter({
  maxRequests: configuredInteger(process.env.CHAT_GLOBAL_RATE_LIMIT_MAX, 60),
  windowMs: configuredInteger(process.env.CHAT_GLOBAL_RATE_LIMIT_WINDOW_MS, 60000),
});
