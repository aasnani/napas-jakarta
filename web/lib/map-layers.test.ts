import assert from "node:assert/strict";
import { test } from "node:test";
import { mapLayerMatches } from "./map-layers.ts";

test("road network coalesces road geometry and labels without claiming transit layers", () => {
  assert.equal(mapLayerMatches("roads", "road_minor"), true);
  assert.equal(mapLayerMatches("roads", "highway-name-major"), true);
  assert.equal(mapLayerMatches("roads", "road_transit_rail"), false);
});

test("map feature groups stay distinct for transit, landmarks, and place labels", () => {
  assert.equal(mapLayerMatches("transit", "bridge_major_rail"), true);
  assert.equal(mapLayerMatches("transit", "road_transit_rail"), true);
  assert.equal(mapLayerMatches("landmarks", "poi_r20"), true);
  assert.equal(mapLayerMatches("landmarks", "poi_transit"), false);
  assert.equal(mapLayerMatches("placeLabels", "label_city"), true);
  assert.equal(mapLayerMatches("placeLabels", "poi_r20"), false);
});
