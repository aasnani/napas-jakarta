export const STATION_HEATMAP_LAYER_ID = "napas-station-heatmap";

/**
 * Convert an ISPU reading into a bounded heatmap weight.
 * Missing readings contribute no heat, and values above the displayed scale
 * are capped so the map does not imply precision beyond the source range.
 */
export function normalizeHeatmapWeight(ispu: number | null): number {
  if (ispu === null || !Number.isFinite(ispu)) return 0;
  return Math.min(1, Math.max(0, ispu / 200));
}
