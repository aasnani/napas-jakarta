import test from "node:test";
import assert from "node:assert/strict";
import { normalizeHeatmapWeight } from "./map-heatmap.ts";

test("heatmap weight is normalized from ISPU without inventing missing readings", () => {
  assert.equal(normalizeHeatmapWeight(null), 0);
  assert.equal(normalizeHeatmapWeight(0), 0);
  assert.equal(normalizeHeatmapWeight(100), 0.5);
  assert.equal(normalizeHeatmapWeight(200), 1);
  assert.equal(normalizeHeatmapWeight(260), 1);
});
