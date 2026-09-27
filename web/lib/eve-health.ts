const DEFAULT_EVE_PORT = "4274";

export function eveHealthUrl(env: NodeJS.ProcessEnv = process.env): string {
  const origin = (
    env.EVE_NEXT_PRODUCTION_ORIGIN ??
    `http://127.0.0.1:${env.EVE_NEXT_PRODUCTION_PORT ?? DEFAULT_EVE_PORT}`
  ).replace(/\/+$/, "");
  return `${origin}/eve/v1/health`;
}

export async function probeEveHealth(
  fetcher: typeof fetch = globalThis.fetch,
  env: NodeJS.ProcessEnv = process.env,
): Promise<boolean> {
  try {
    const response = await fetcher(eveHealthUrl(env), {
      cache: "no-store",
      signal: AbortSignal.timeout(1_500),
    });
    if (!response.ok) return false;
    const payload = (await response.json()) as { status?: unknown };
    return payload.status === "ready";
  } catch {
    return false;
  }
}
