export type SourceCitation = {
  readonly id: string;
  readonly title: string;
  readonly url: string;
  readonly role?: string;
  readonly author?: string;
  readonly retrievedAt?: string;
};

type UnknownRecord = Record<string, unknown>;

function asRecord(value: unknown): UnknownRecord | undefined {
  return typeof value === "object" && value !== null ? (value as UnknownRecord) : undefined;
}

function asNonEmptyString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : undefined;
}

function asHttpUrl(value: unknown): string | undefined {
  const candidate = asNonEmptyString(value);
  if (!candidate) return undefined;

  try {
    const parsed = new URL(candidate);
    return parsed.protocol === "http:" || parsed.protocol === "https:" ? parsed.toString() : undefined;
  } catch {
    return undefined;
  }
}

/**
 * Extract only source records returned by a trusted tool/API contract.
 * Provider text cannot turn arbitrary strings into clickable links here.
 */
export function extractSourceCitations(output: unknown): SourceCitation[] {
  const record = asRecord(output);
  if (!record) return [];

  const artifact = asRecord(record.artifact);
  const rawSources = Array.isArray(record.citations)
    ? record.citations
    : Array.isArray(record.sources)
      ? record.sources
      : artifact?.type === "source-list" && Array.isArray(artifact.sources)
        ? artifact.sources
        : [];

  const citations: SourceCitation[] = [];
  const seenUrls = new Set<string>();
  for (const rawSource of rawSources) {
    const source = asRecord(rawSource);
    if (!source) continue;

    const url = asHttpUrl(source.url);
    if (!url || seenUrls.has(url)) continue;
    const id = asNonEmptyString(source.id) ?? asNonEmptyString(source.source_id) ?? url;
    const title = asNonEmptyString(source.title) ?? id;
    const role = asNonEmptyString(source.role);
    const author = asNonEmptyString(source.author);
    const retrievedAt = asNonEmptyString(source.retrievedAt) ?? asNonEmptyString(source.retrieved_at);

    seenUrls.add(url);
    citations.push({
      ...(author ? { author } : {}),
      id,
      ...(retrievedAt ? { retrievedAt } : {}),
      ...(role ? { role } : {}),
      title,
      url,
    });
  }

  return citations;
}
