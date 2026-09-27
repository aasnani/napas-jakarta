import { defineTool } from "eve/tools";
import { z } from "zod";
import { buildSourceCitations, fetchSourceManifest } from "@/lib/grounded-sources";
import { fetchNapasJson } from "@/lib/server-api";

const standardResponseSchema = z
  .object({
    comparison: z.record(z.string(), z.unknown()),
  })
  .passthrough();

export default defineTool({
  description:
    "Compare a PM2.5 or PM10 concentration with the configured WHO annual guideline. Clearly state that this is health-guideline context, not an Indonesian legal threshold.",
  inputSchema: z.object({
    pollutant: z.enum(["PM2.5", "PM10"]).default("PM2.5"),
    value: z.number().finite().nonnegative().max(100_000),
  }),
  async execute({ pollutant, value }) {
    const [response, sourceRecords] = await Promise.all([
      fetchNapasJson<unknown>("/measurements/standard", {
        body: JSON.stringify({ pollutant, value }),
        method: "POST",
      }),
      fetchSourceManifest(),
    ]);
    const payload = standardResponseSchema.parse(response);

    return {
      citations: buildSourceCitations([payload.comparison], sourceRecords, ["who-aqg-2021"]),
      comparison: payload.comparison,
      pollutant,
      value,
    };
  },
});
