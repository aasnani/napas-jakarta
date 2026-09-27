import { defineTool } from "eve/tools";
import { z } from "zod";
import { buildSourceCitations, fetchSourceManifest } from "@/lib/grounded-sources";
import { fetchNapasJson } from "@/lib/server-api";

const measurementSchema = z.record(z.string(), z.unknown());

const latestResponseSchema = z.object({
  measurements: z.array(measurementSchema),
  source_mode: z.string(),
});

export default defineTool({
  description:
    "Read the latest Jakarta station measurements. Use this for current air-quality questions; never answer current conditions from memory.",
  inputSchema: z.object({
    pollutant: z.enum(["PM2.5", "PM10"]).default("PM2.5"),
    location: z.string().min(2).max(100).optional(),
  }),
  async execute({ pollutant, location }) {
    const params = new URLSearchParams({ pollutant });
    if (location) params.set("location", location);
    const [measurementResult, sourceResult] = await Promise.allSettled([
      fetchNapasJson<unknown>(`/measurements/latest?${params.toString()}`),
      fetchSourceManifest(),
    ]);

    if (measurementResult.status === "rejected") {
      throw measurementResult.reason;
    }
    const payload = latestResponseSchema.parse(measurementResult.value);
    const sourceRecords = sourceResult.status === "fulfilled" ? sourceResult.value : [];
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
