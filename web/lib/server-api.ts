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
