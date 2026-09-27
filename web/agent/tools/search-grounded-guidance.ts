import { defineTool } from "eve/tools";
import { z } from "zod";
import { buildSourceCitations, fetchSourceManifest } from "@/lib/grounded-sources";
import { fetchNapasJson } from "@/lib/server-api";

const retrievalModes = ["bm25", "dense", "hybrid", "hybrid_rerank", "qdrant_hybrid"] as const;
const guidanceResponseSchema = z
  .object({
    results: z.array(z.record(z.string(), z.unknown())),
    retrieval_mode: z.string(),
    source_mode: z.string(),
  })
  .passthrough();

export default defineTool({
  description:
    "Retrieve source-grounded excerpts for health, protection, standards, policy, pollution causes, and other documentary questions. Use selected topic source IDs when available, and abstain if no relevant evidence is returned.",
  inputSchema: z.object({
    language: z.enum(["English", "Bahasa Indonesia"]).default("English"),
    query: z.string().min(3).max(500),
    retrievalMode: z.enum(retrievalModes).default("hybrid"),
    sourceIds: z.array(z.string().min(1).max(120)).max(12).default([]),
    topK: z.number().int().min(1).max(8).default(5),
  }),
  async execute({ language, query, retrievalMode, sourceIds, topK }) {
    const [response, sourceRecords] = await Promise.all([
      fetchNapasJson<unknown>("/guidance/search", {
        body: JSON.stringify({
          language,
          query,
          retrieval_mode: retrievalMode,
          source_ids: sourceIds,
          top_k: topK,
        }),
        method: "POST",
      }),
      fetchSourceManifest(),
    ]);
    const payload = guidanceResponseSchema.parse(response);

    return {
      citations: buildSourceCitations(payload.results, sourceRecords),
      language,
      query,
      results: payload.results,
      retrievalMode: payload.retrieval_mode,
      sourceMode: payload.source_mode,
    };
  },
});
