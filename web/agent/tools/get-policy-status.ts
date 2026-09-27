import { defineTool } from "eve/tools";
import { z } from "zod";
import { buildSourceCitations, fetchSourceManifest } from "@/lib/grounded-sources";
import { fetchNapasJson } from "@/lib/server-api";

const policyResponseSchema = z.record(z.string(), z.unknown());
const isoDate = z.string().regex(/^\d{4}-\d{2}-\d{2}$/u);

export default defineTool({
  description:
    "Retrieve a recorded Jakarta or Indonesian air-quality policy timeline or status. Distinguish enacted rules, pilots, drafts, and proposals; never infer implementation beyond returned events.",
  inputSchema: z.object({
    asOf: isoDate.optional(),
    instrument: z.string().min(2).max(120),
    view: z.enum(["status", "timeline"]).default("status"),
  }),
  async execute({ asOf, instrument, view }) {
    const params = new URLSearchParams({ instrument });
    if (view === "status" && asOf) params.set("as_of", asOf);
    const [response, sourceRecords] = await Promise.all([
      fetchNapasJson<unknown>(`/policies/${view}?${params.toString()}`),
      fetchSourceManifest(),
    ]);
    const payload = policyResponseSchema.parse(response);
    const record = payload[view];

    return {
      asOf,
      citations: buildSourceCitations([record], sourceRecords),
      instrument,
      record,
      view,
    };
  },
});
