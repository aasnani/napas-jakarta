export type MapLayerKey = "roads" | "boundaries" | "waterways" | "transit" | "landmarks" | "placeLabels";

export const MAP_LAYER_DEFAULTS: Record<MapLayerKey, boolean> = {
  boundaries: true,
  landmarks: true,
  placeLabels: true,
  roads: true,
  transit: true,
  waterways: true,
};

function isRoadLayer(id: string): boolean {
  return (
    id.startsWith("road_") ||
    id.startsWith("bridge_") ||
    id.startsWith("tunnel_") ||
    id.startsWith("highway-")
  );
}

export function mapLayerMatches(key: MapLayerKey, layerId: string): boolean {
  const id = layerId.trim().toLowerCase();

  switch (key) {
    case "roads":
      return isRoadLayer(id) && !id.includes("rail") && !id.includes("transit");
    case "boundaries":
      return id.startsWith("boundary_");
    case "waterways":
      return id === "water" || id.startsWith("waterway_") || id.startsWith("water_name_");
    case "transit":
      return id.includes("rail") || id.includes("transit");
    case "landmarks":
      return id.startsWith("poi_") && !id.includes("transit");
    case "placeLabels":
      return id.startsWith("label_");
  }
}
