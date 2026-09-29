export function napasApiOrigin(): string {
  return (
    process.env.NAPAS_API_ORIGIN ??
    (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8502" : "")
  ).replace(/\/+$/, "");
}

export function internalApiHeaders(): Record<string, string> {
  const token = process.env.NAPAS_INTERNAL_TOKEN?.trim();
  return token ? { "X-Napas-Internal-Token": token } : {};
}

const WAKE_RETRY_DELAYS_MS = [1_000, 2_000, 3_000];
const WAKE_ATTEMPT_TIMEOUT_MS = 12_000;

function isWakeStatus(status: number): boolean {
  return status === 502 || status === 503 || status === 504;
}

/**
 * Fetch from the private API tolerating a cold start. Railway can put the API
 * (and its database) to sleep when idle; the first request wakes it and may
 * see a connection error or a 502/503/504 while it boots. Retry those briefly
 * instead of surfacing an error to the first visitor.
 */
export async function fetchApiWithWake(url: string, init: RequestInit = {}): Promise<Response> {
  let lastError: unknown;
  for (let attempt = 0; attempt <= WAKE_RETRY_DELAYS_MS.length; attempt += 1) {
    try {
      const response = await fetch(url, {
        ...init,
        signal: init.signal ?? AbortSignal.timeout(WAKE_ATTEMPT_TIMEOUT_MS),
      });
      if (!isWakeStatus(response.status) || attempt === WAKE_RETRY_DELAYS_MS.length) {
        return response;
      }
    } catch (error) {
      lastError = error;
      if (attempt === WAKE_RETRY_DELAYS_MS.length) throw error;
    }
    await new Promise((resolve) => setTimeout(resolve, WAKE_RETRY_DELAYS_MS[attempt]));
  }
  throw lastError;
}

export async function fetchNapasJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const origin = napasApiOrigin();
  if (!origin) throw new Error("Napas API origin is not configured.");

  const headers = new Headers(init.headers);
  headers.set("accept", "application/json");
  for (const [name, value] of Object.entries(internalApiHeaders())) {
    headers.set(name, value);
  }
  if (init.body !== undefined && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }

  const response = await fetchApiWithWake(`${origin}${path}`, {
    ...init,
    cache: "no-store",
    headers,
  });

  if (!response.ok) {
    throw new Error(`Napas API request failed with HTTP ${response.status}.`);
  }

  return (await response.json()) as T;
}
