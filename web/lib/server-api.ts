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

  const response = await fetch(`${origin}${path}`, {
    ...init,
    cache: "no-store",
    headers,
    signal: init.signal ?? AbortSignal.timeout(10_000),
  });

  if (!response.ok) {
    throw new Error(`Napas API request failed with HTTP ${response.status}.`);
  }

  return (await response.json()) as T;
}
