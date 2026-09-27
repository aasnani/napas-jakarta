import assert from "node:assert/strict";
import { test } from "node:test";
import { buildSourceCitations } from "./grounded-sources.ts";

test("source citations resolve source IDs and direct URLs without duplicates", () => {
  const citations = buildSourceCitations(
    [
      { source_id: "official", source_url: "https://example.test/official" },
      { source_id: "official" },
      { source_url: "https://example.test/direct" },
    ],
    [
      {
        author: "Official publisher",
        id: "official",
        role: "primary source",
        retrieved_at: "2026-09-07",
        title: "Official source",
        url: "https://example.test/official",
      },
    ],
  );

  assert.deepEqual(citations, [
    {
      author: "Official publisher",
      id: "official",
      retrievedAt: "2026-09-07",
      role: "primary source",
      title: "Official source",
      url: "https://example.test/official",
    },
    {
      id: "https://example.test/direct",
      role: "Retrieved source",
      title: "example.test",
      url: "https://example.test/direct",
    },
  ]);
});
