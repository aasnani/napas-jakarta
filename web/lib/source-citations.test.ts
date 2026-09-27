import assert from "node:assert/strict";
import test from "node:test";
import { extractSourceCitations } from "./source-citations.ts";

test("extractSourceCitations keeps only deduplicated HTTP source records", () => {
  const citations = extractSourceCitations({
    citations: [
      { id: "official", title: "Official portal", url: "https://example.com/source" },
      { id: "duplicate", title: "Duplicate", url: "https://example.com/source" },
      { id: "unsafe", title: "Unsafe", url: "javascript:alert(1)" },
    ],
  });

  assert.deepEqual(citations, [
    { id: "official", title: "Official portal", url: "https://example.com/source" },
  ]);
});

test("extractSourceCitations supports a source-list artifact", () => {
  const citations = extractSourceCitations({
    artifact: {
      type: "source-list",
      sources: [{ id: "who", title: "WHO", url: "https://who.int/guidance" }],
    },
  });

  assert.equal(citations[0]?.id, "who");
  assert.equal(citations[0]?.title, "WHO");
});
