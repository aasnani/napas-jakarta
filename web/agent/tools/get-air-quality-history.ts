import { defineTool } from "eve/tools";
import { z } from "zod";
import { buildSourceCitations, fetchSourceManifest } from "@/lib/grounded-sources";
import { fetchNapasJson } from "@/lib/server-api";

const isoDate = z.string().regex(/^\d{4}-\d{2}-\d{2}$/u);
const historyResponseSchema = z
  .object({
    source_mode: z.string(),
    summary: z.record(z.string(), z.unknown()),
  })
  .passthrough();

export default defineTool({
  description:
    "Summarize historical Jakarta air-quality observations for a bounded location and date range. Use this for trend or past-period questions, and do not present the summary as a live reading.",
  inputSchema: z.object({
    end: isoDate,
    location: z.string().min(2).max(100),
    pollutant: z.enum(["PM2.5", "PM10"]).default("PM2.5"),
    start: isoDate,
  }),
  async execute({ end, location, pollutant, start }) {
    const [response, sourceRecords] = await Promise.all([
      fetchNapasJson<unknown>("/measurements/history", {
        body: JSON.stringify({ end, location, pollutant, start }),
        method: "POST",
      }),
      fetchSourceManifest(),
    ]);
    const payload = historyResponseSchema.parse(response);

    return {
      citations: buildSourceCitations([payload.summary], sourceRecords),
      dateRange: { end, start },
      location,
      pollutant,
      sourceMode: payload.source_mode,
      summary: payload.summary,
    };
  },
});
