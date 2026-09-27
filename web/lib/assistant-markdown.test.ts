import { strictEqual } from "node:assert/strict";
import test from "node:test";
import { normalizeAssistantMarkdown } from "./assistant-markdown.ts";

test("normalizes common inline math into readable air-quality notation", () => {
  strictEqual(
    normalizeAssistantMarkdown(
      "Konsentrasi $\\text{PM}\\_{2.5}$ mencapai 50,4 $\\mu\\text{g/m}^3$; ISPU $\\le$ 50.",
    ),
    "Konsentrasi PM2.5 mencapai 50,4 µg/m³; ISPU ≤ 50.",
  );
});

test("removes empty source placeholders and normalizes prose spacing", () => {
  strictEqual(
    normalizeAssistantMarkdown(
      "Berdasarkan data resmi dari Dinas Lingkungan Hidup Provinsi DKI Jakarta (),  kondisi  bervariasi.\n\n*Catatan: bersumber dari portal .*",
    ),
    "Berdasarkan data resmi dari Dinas Lingkungan Hidup Provinsi DKI Jakarta, kondisi bervariasi.\n\n*Catatan: bersumber dari portal.*",
  );
});
