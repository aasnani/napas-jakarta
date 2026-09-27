import assert from "node:assert/strict";
import test from "node:test";
import { getUiCopy, localizedCategory, localizedDistrict, replaceCopy, syncDocumentLanguage } from "./i18n.ts";

test("English is the default UI language and Indonesian copy is available", () => {
  assert.equal(getUiCopy("en").chat.heading, "Napas Advisor");
  assert.equal(getUiCopy("id").chat.heading, "Penasihat Napas");
  assert.equal(getUiCopy("en").chat.capabilityStationAware, "Station-aware");
  assert.equal(getUiCopy("id").chat.capabilityStationAware, "Berbasis stasiun");
  assert.equal(getUiCopy("en").chat.capabilityTopicAware, "Topic-aware");
  assert.equal(getUiCopy("id").chat.capabilityTopicAware, "Berbasis topik");
  assert.notEqual(getUiCopy("en").map.heading, getUiCopy("id").map.heading);
});

test("dynamic air-quality labels and placeholders localize without changing filter values", () => {
  assert.equal(localizedCategory("Moderate", "id"), "Sedang");
  assert.equal(localizedDistrict("North Jakarta", "id"), "Jakarta Utara");
  assert.equal(replaceCopy("Sertakan {station} dalam pertanyaan berikutnya", { station: "Kelapa Gading" }), "Sertakan Kelapa Gading dalam pertanyaan berikutnya");
});

test("document language follows the selected UI language", () => {
  const documentRef = { documentElement: { lang: "en" } };

  syncDocumentLanguage("id", documentRef);
  assert.equal(documentRef.documentElement.lang, "id");

  syncDocumentLanguage("en", documentRef);
  assert.equal(documentRef.documentElement.lang, "en");
});
