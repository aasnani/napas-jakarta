import { z } from "zod";
import { fetchNapasJson } from "./server-api.ts";
import type { SourceCitation } from "./source-citations.ts";

export const sourceRecordSchema = z
  .object({
    author: z.string().optional(),
    id: z.string(),
    role: z.string().optional(),
    retrieved_at: z.string().optional(),
    title: z.string(),
    url: z.string(),
  })
  .passthrough();

export const sourceManifestSchema = z.object({ sources: z.array(sourceRecordSchema) }).passthrough();

export type SourceRecord = z.infer<typeof sourceRecordSchema>;

export async function fetchSourceManifest(): Promise<SourceRecord[]> {
  const payload = await fetchNapasJson<unknown>("/sources");
  return sourceManifestSchema.parse(payload).sources;
}

function asHttpUrl(value: unknown): string | undefined {
  if (typeof value !== "string" || value.trim().length === 0) return undefined;
  try {
    const parsed = new URL(value);
    return parsed.protocol === "http:" || parsed.protocol === "https:" ? parsed.toString() : undefined;
  } catch {
    return undefined;
  }
}

function collectSourceReferences(
  value: unknown,
  references: { ids: Set<string>; urls: Set<string> },
): void {
  if (Array.isArray(value)) {
    for (const item of value) collectSourceReferences(item, references);
    return;
  }
  if (typeof value !== "object" || value === null) return;

  for (const [key, nested] of Object.entries(value)) {
    if (["source_id", "sourceId", "source_ids", "sourceIds"].includes(key)) {
      if (typeof nested === "string" && nested.trim()) references.ids.add(nested.trim());
      if (Array.isArray(nested)) {
        for (const item of nested) {
          if (typeof item === "string" && item.trim()) references.ids.add(item.trim());
        }
      }
    }
    if (["source_url", "sourceUrl", "source"].includes(key)) {
      const url = asHttpUrl(nested);
      if (url) references.urls.add(url);
    }
    if (key === "url" && asHttpUrl(nested)) {
      references.urls.add(asHttpUrl(nested)!);
    }
    if (typeof nested === "object" && nested !== null) {
      collectSourceReferences(nested, references);
    }
  }
}

export function buildSourceCitations(
  payloads: readonly unknown[],
  sourceRecords: readonly SourceRecord[],
  fallbackSourceIds: readonly string[] = [],
): SourceCitation[] {
  const references = { ids: new Set(fallbackSourceIds), urls: new Set<string>() };
  for (const payload of payloads) collectSourceReferences(payload, references);

  const sourceById = new Map(sourceRecords.map((source) => [source.id, source]));
  const sourceByUrl = new Map(
    sourceRecords
      .map((source) => [asHttpUrl(source.url), source] as const)
      .filter(([url]) => url !== undefined),
  );
  const citations: SourceCitation[] = [];
  const seenUrls = new Set<string>();

  for (const id of references.ids) {
    const source = sourceById.get(id);
    if (!source) continue;
    const url = asHttpUrl(source.url);
    if (!url || seenUrls.has(url)) continue;
    seenUrls.add(url);
    citations.push({
      ...(source.author ? { author: source.author } : {}),
      id: source.id,
      ...(source.retrieved_at ? { retrievedAt: source.retrieved_at } : {}),
      ...(source.role ? { role: source.role } : {}),
      title: source.title,
      url,
    });
  }

  for (const url of references.urls) {
    if (seenUrls.has(url)) continue;
    const source = sourceByUrl.get(url);
    if (source) {
      seenUrls.add(url);
      citations.push({
        ...(source.author ? { author: source.author } : {}),
        id: source.id,
        ...(source.retrieved_at ? { retrievedAt: source.retrieved_at } : {}),
        ...(source.role ? { role: source.role } : {}),
        title: source.title,
        url,
      });
      continue;
    }

    seenUrls.add(url);
    citations.push({
      id: url,
      role: "Retrieved source",
      title: new URL(url).hostname,
      url,
    });
  }

  return citations;
}
