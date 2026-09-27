import { defineTool } from "eve/tools";
import { z } from "zod";
import type { SourceCitation } from "@/lib/source-citations";

const measurementSchema = z.record(z.string(), z.unknown());
const sourceRecordSchema = z
  .object({
    author: z.string().optional(),
    id: z.string(),
    role: z.string().optional(),
    retrieved_at: z.string().optional(),
    title: z.string(),
    url: z.string(),
  })
  .passthrough();
const sourceManifestSchema = z.object({ sources: z.array(sourceRecordSchema) }).passthrough();

const latestResponseSchema = z.object({
  measurements: z.array(measurementSchema),
  source_mode: z.string(),
});

function asHttpUrl(value: unknown): string | undefined {
  if (typeof value !== "string" || value.trim().length === 0) return undefined;
  try {
    const parsed = new URL(value);
    return parsed.protocol === "http:" || parsed.protocol === "https:" ? parsed.toString() : undefined;
  } catch {
    return undefined;
  }
}

function buildSourceCitations(
  measurements: readonly Record<string, unknown>[],
  sourceRecords: readonly z.infer<typeof sourceRecordSchema>[],
): SourceCitation[] {
  const sourceByUrl = new Map(sourceRecords.map((source) => [asHttpUrl(source.url), source]));
  const urls = new Set(
    measurements
      .map((measurement) => asHttpUrl(measurement.source_url ?? measurement.source))
      .filter((value): value is string => value !== undefined),
  );

  return [...urls].map((url) => {
    const source = sourceByUrl.get(url);
    if (source) {
      return {
        ...(source.author ? { author: source.author } : {}),
        id: source.id,
        ...(source.retrieved_at ? { retrievedAt: source.retrieved_at } : {}),
        ...(source.role ? { role: source.role } : {}),
        title: source.title,
        url,
      };
    }

    return {
      id: url,
      role: "Station measurement source",
      title: new URL(url).hostname,
      url,
    };
  });
}

export default defineTool({
  description:
    "Read the latest Jakarta station measurements. Use this for current air-quality questions; never answer current conditions from memory.",
  inputSchema: z.object({
    pollutant: z.enum(["PM2.5", "PM10"]).default("PM2.5"),
  }),
  async execute({ pollutant }) {
    const apiOrigin = process.env.NAPAS_API_ORIGIN ?? "http://127.0.0.1:8502";
    const [measurementResult, sourceResult] = await Promise.allSettled([
      fetch(
        `${apiOrigin}/measurements/latest?pollutant=${encodeURIComponent(pollutant)}`,
        { headers: { accept: "application/json" }, cache: "no-store" },
      ),
      fetch(`${apiOrigin}/sources`, { headers: { accept: "application/json" }, cache: "no-store" }),
    ]);

    if (measurementResult.status === "rejected") {
      throw measurementResult.reason;
    }
    if (!measurementResult.value.ok) {
      throw new Error(`The air-quality API returned HTTP ${measurementResult.value.status}.`);
    }

    const payload = latestResponseSchema.parse(await measurementResult.value.json());
    let sourceRecords: z.infer<typeof sourceRecordSchema>[] = [];
    if (sourceResult.status === "fulfilled" && sourceResult.value.ok) {
      try {
        const parsed = sourceManifestSchema.safeParse(await sourceResult.value.json());
        if (parsed.success) sourceRecords = parsed.data.sources;
      } catch {
        // Source presentation is additive; a source-catalog outage must not
        // make the current-measurement tool fail.
      }
    }
    const stationIds = payload.measurements
      .map((measurement) => measurement.station_id ?? measurement.stationId)
      .filter((value): value is string => typeof value === "string" && value.length > 0);
    const citations = buildSourceCitations(payload.measurements, sourceRecords);

    return {
      artifact: { stationIds, type: "map-focus" as const },
      citations,
      measurements: payload.measurements,
      pollutant,
      sourceMode: payload.source_mode,
    };
  },
});
