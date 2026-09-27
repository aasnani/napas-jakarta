import { createGoogleGenerativeAI } from "@ai-sdk/google";
import { emitServerException, emitServerLog } from "../lib/server-logger.ts";

export const DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite";
export const DEFAULT_GEMINI_REQUEST_TIMEOUT_MS = 120_000;

export function selectGeminiModel(configured: string | undefined): string {
  return configured?.trim() || DEFAULT_GEMINI_MODEL;
}

export function selectGeminiRequestTimeout(configured: string | undefined): number {
  const parsed = Number.parseInt(configured ?? "", 10);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : DEFAULT_GEMINI_REQUEST_TIMEOUT_MS;
}

export function classifyGeminiFailure(error: unknown, status?: number): string {
  if (status === 429) return "rate_limited";
  if (typeof status === "number" && status >= 500) return "upstream_5xx";
  if (typeof status === "number" && status >= 400) return "upstream_4xx";
  if (error instanceof DOMException && error.name === "TimeoutError") return "timeout";
  if (error instanceof Error && error.name === "AbortError") return "aborted";
  return "request_failed";
}

export function createNapasModel() {
  const apiKey = process.env.GEMINI_API_KEY?.trim() || undefined;
  const requestTimeoutMs = selectGeminiRequestTimeout(process.env.GEMINI_REQUEST_TIMEOUT_MS);
  const google = createGoogleGenerativeAI({
    apiKey: apiKey ?? "",
    fetch: async (input, init) => {
      if (apiKey === undefined) {
        emitServerLog("error", "provider_configuration_missing", {
          dependency: "gemini",
          critical: true,
          alertable: true,
        });
        throw new Error("GEMINI_API_KEY is not configured.");
      }

      const timeoutSignal = AbortSignal.timeout(requestTimeoutMs);
      const signal = init?.signal
        ? AbortSignal.any([init.signal, timeoutSignal])
        : timeoutSignal;

      try {
        const response = await fetch(input, { ...init, signal });
        if (!response.ok) {
          emitServerLog("error", "provider_failure", {
            dependency: "gemini",
            error_code: classifyGeminiFailure(undefined, response.status),
            http_status: response.status,
            critical: true,
            alertable: true,
          });
        }
        return response;
      } catch (error: unknown) {
        emitServerException("error", "provider_failure", error, {
          dependency: "gemini",
          error_code: classifyGeminiFailure(error),
          critical: true,
          alertable: true,
        });
        throw error;
      }
    },
  });

  return google(selectGeminiModel(process.env.GEMINI_MODEL));
}
