import { defineTool } from "eve/tools";
import { z } from "zod";
import { buildSourceCitations, fetchSourceManifest } from "@/lib/grounded-sources";
import { fetchNapasJson } from "@/lib/server-api";

const comparisonResponseSchema = z
  .object({
    comparisons: z.array(z.record(z.string(), z.unknown())),
    source_mode: z.string(),
  })
  .passthrough();

export default defineTool({
  description:
    "Compare the latest available air-quality observations across two to ten Jakarta locations. Preserve unavailable locations as unavailable; never fill missing values from memory.",
  inputSchema: z.object({
    locations: z.array(z.string().min(2).max(100)).min(2).max(10),
    pollutant: z.enum(["PM2.5", "PM10"]).default("PM2.5"),
  }),
  async execute({ locations, pollutant }) {
    const [response, sourceRecords] = await Promise.all([
      fetchNapasJson<unknown>("/measurements/compare", {
        body: JSON.stringify({ locations, pollutant }),
        method: "POST",
      }),
      fetchSourceManifest(),
    ]);
    const payload = comparisonResponseSchema.parse(response);

    return {
      citations: buildSourceCitations(payload.comparisons, sourceRecords),
      comparisons: payload.comparisons,
      locations,
      pollutant,
      sourceMode: payload.source_mode,
    };
  },
});
