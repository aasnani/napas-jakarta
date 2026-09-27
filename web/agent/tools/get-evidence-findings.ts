import { defineTool } from "eve/tools";
import { z } from "zod";
import { buildSourceCitations, fetchSourceManifest } from "@/lib/grounded-sources";
import { fetchNapasJson } from "@/lib/server-api";

const evidenceResponseSchema = z
  .object({
    findings: z.array(z.record(z.string(), z.unknown())),
  })
  .passthrough();

export default defineTool({
  description:
    "Retrieve structured study findings about Jakarta pollution sources or compare selected studies. Preserve study scope, uncertainty, and limitations; do not turn study estimates into universal causal rankings.",
  inputSchema: z.object({
    location: z.string().min(2).max(120).optional(),
    mode: z.enum(["source-apportionment", "compare-studies"]).default("source-apportionment"),
    pollutant: z.string().min(2).max(40).default("PM2.5"),
    season: z.string().min(2).max(80).optional(),
    sourceIds: z.array(z.string().min(1).max(120)).max(10).default([]),
  }),
  async execute({ location, mode, pollutant, season, sourceIds }) {
    const request =
      mode === "source-apportionment"
        ? fetchNapasJson<unknown>(
            `/evidence/source-apportionment?${new URLSearchParams({
              ...(location ? { location } : {}),
              pollutant,
              ...(season ? { season } : {}),
            }).toString()}`,
          )
        : fetchNapasJson<unknown>("/evidence/compare", {
            body: JSON.stringify({ source_ids: sourceIds }),
            method: "POST",
          });
    const [response, sourceRecords] = await Promise.all([request, fetchSourceManifest()]);
    const payload = evidenceResponseSchema.parse(response);

    return {
      citations: buildSourceCitations(payload.findings, sourceRecords),
      comparisonNote: payload.comparison_note,
      findings: payload.findings,
      location,
      mode,
      pollutant,
      season,
      sourceIds,
    };
  },
});
