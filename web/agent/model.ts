import { createGoogleGenerativeAI } from "@ai-sdk/google";

export const DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite";
export const DEFAULT_GEMINI_REQUEST_TIMEOUT_MS = 120_000;

export function selectGeminiModel(configured: string | undefined): string {
  return configured?.trim() || DEFAULT_GEMINI_MODEL;
}

export function selectGeminiRequestTimeout(configured: string | undefined): number {
  const parsed = Number.parseInt(configured ?? "", 10);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : DEFAULT_GEMINI_REQUEST_TIMEOUT_MS;
}

export function createNapasModel() {
  const apiKey = process.env.GEMINI_API_KEY?.trim();
  const requestTimeoutMs = selectGeminiRequestTimeout(process.env.GEMINI_REQUEST_TIMEOUT_MS);
  const google = createGoogleGenerativeAI({
    apiKey: apiKey ?? "",
    fetch: async (input, init) => {
      if (apiKey === undefined) {
        throw new Error("GEMINI_API_KEY is not configured.");
      }

      const timeoutSignal = AbortSignal.timeout(requestTimeoutMs);
      const signal = init?.signal
        ? AbortSignal.any([init.signal, timeoutSignal])
        : timeoutSignal;

      return fetch(input, { ...init, signal });
    },
  });

  return google(selectGeminiModel(process.env.GEMINI_MODEL));
}
