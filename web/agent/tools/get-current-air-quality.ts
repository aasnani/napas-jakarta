import { defineTool } from "eve/tools";
import { z } from "zod";

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
  }),
  async execute({ pollutant }) {
    const apiOrigin = process.env.NAPAS_API_ORIGIN ?? "http://127.0.0.1:8502";
    const response = await fetch(
      `${apiOrigin}/measurements/latest?pollutant=${encodeURIComponent(pollutant)}`,
      { headers: { accept: "application/json" }, cache: "no-store" },
    );

    if (!response.ok) {
      throw new Error(`The air-quality API returned HTTP ${response.status}.`);
    }

    const payload = latestResponseSchema.parse(await response.json());
    const stationIds = payload.measurements
      .map((measurement) => measurement.station_id ?? measurement.stationId)
      .filter((value): value is string => typeof value === "string" && value.length > 0);

    return {
      artifact: { stationIds, type: "map-focus" as const },
      measurements: payload.measurements,
      pollutant,
      sourceMode: payload.source_mode,
    };
  },
});
