"use client";

import {
  Layers2Icon,
  LocateFixedIcon,
  MinusIcon,
  PlusIcon,
  RotateCcwIcon,
  XIcon,
} from "lucide-react";
import {
  Map as MapLibreMap,
  NavigationControl,
  setWorkerUrl,
  type GeoJSONSource,
  type MapLayerMouseEvent,
} from "maplibre-gl";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import {
  categoryKey,
  DEMO_STATIONS,
  type AirQualityCategory,
  type DemoStation,
} from "@/lib/napas";

const MAP_STYLE_URL =
  process.env.NEXT_PUBLIC_MAP_STYLE_URL ?? "https://tiles.openfreemap.org/styles/liberty";
setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");
const JAKARTA_CENTER: [number, number] = [106.84, -6.2];
const JAKARTA_BOUNDS: [[number, number], [number, number]] = [
  [106.7, -6.36],
  [106.96, -6.05],
];

type FilterCategory = "all" | "good" | "moderate" | "unhealthy" | "stale";
type LayerKey = "primaryRoads" | "localRoads" | "boundaries" | "waterways" | "transit" | "landmarks" | "roads" | "districts" | "places";

const LAYER_DEFAULTS: Record<LayerKey, boolean> = {
  primaryRoads: true,
  localRoads: true,
  boundaries: true,
  waterways: true,
  transit: true,
  landmarks: true,
  roads: true,
  districts: true,
  places: true,
};

const CATEGORY_COLOR: Record<AirQualityCategory, string> = {
  Good: "#2E9B78",
  Moderate: "#E2A900",
  Unhealthy: "#D94E3E",
  "Stale / missing": "#7B8790",
};

function stationCollection(stations: readonly DemoStation[], selectedId: string) {
  return {
    type: "FeatureCollection" as const,
    features: stations.map((station) => ({
      type: "Feature" as const,
      geometry: {
        type: "Point" as const,
        coordinates: [station.longitude, station.latitude] as [number, number],
      },
      properties: {
        category: station.category,
        color: CATEGORY_COLOR[station.category],
        id: station.id,
        selected: station.id === selectedId,
        value: station.ispu === null ? "—" : String(station.ispu),
      },
    })),
  };
}

export function WorkspaceMap({
  onStationSelect,
  selectedStationId = "kelapa-gading",
}: {
  readonly onStationSelect: (station: DemoStation) => void;
  readonly selectedStationId?: string;
}) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [selectedId, setSelectedId] = useState(selectedStationId);
  const [categoryFilter, setCategoryFilter] = useState<FilterCategory>("all");
  const [districtFilter, setDistrictFilter] = useState("all");
  const [layersOpen, setLayersOpen] = useState(false);
  const [stationListOpen, setStationListOpen] = useState(false);
  const [layers, setLayers] = useState(LAYER_DEFAULTS);

  useEffect(() => {
    setSelectedId(selectedStationId);
  }, [selectedStationId]);

  const visibleStations = useMemo(
    () =>
      DEMO_STATIONS.filter(
        (station) =>
          (categoryFilter === "all" || categoryKey[station.category] === categoryFilter) &&
          (districtFilter === "all" || station.district === districtFilter),
      ),
    [categoryFilter, districtFilter],
  );
  const selectedStation = DEMO_STATIONS.find((station) => station.id === selectedId) ?? DEMO_STATIONS[0];
  const reportingCount = DEMO_STATIONS.filter((station) => station.ispu !== null).length;
  const moderateCount = DEMO_STATIONS.filter((station) => station.category === "Moderate").length;
  const unhealthyCount = DEMO_STATIONS.filter((station) => station.category === "Unhealthy").length;

  const selectStation = useCallback(
    (station: DemoStation) => {
      setSelectedId(station.id);
      onStationSelect(station);
    },
    [onStationSelect],
  );

  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;

    const map = new MapLibreMap({
      attributionControl: { compact: true },
      center: JAKARTA_CENTER,
      container: mapContainer.current,
      maxBounds: JAKARTA_BOUNDS,
      maxZoom: 15,
      minZoom: 9.7,
      style: MAP_STYLE_URL,
      zoom: 10.7,
    });
    mapRef.current = map;
    map.addControl(new NavigationControl({ showCompass: false, showZoom: false }), "top-right");

    map.on("load", () => {
      map.addSource("napas-stations", {
        data: stationCollection(DEMO_STATIONS, selectedStationId),
        type: "geojson",
      });
      map.addLayer({
        id: "napas-station-halo",
        paint: {
          "circle-color": "#6DB6B0",
          "circle-opacity": ["case", ["boolean", ["get", "selected"], false], 0.24, 0],
          "circle-radius": ["case", ["boolean", ["get", "selected"], false], 34, 0],
          "circle-stroke-color": "#086B68",
          "circle-stroke-opacity": ["case", ["boolean", ["get", "selected"], false], 0.75, 0],
          "circle-stroke-width": 2,
        },
        source: "napas-stations",
        type: "circle",
      });
      map.addLayer({
        id: "napas-stations",
        paint: {
          "circle-color": ["get", "color"],
          "circle-radius": 10,
          "circle-stroke-color": "#FFFFFF",
          "circle-stroke-width": 2.5,
        },
        source: "napas-stations",
        type: "circle",
      });
      map.addLayer({
        id: "napas-station-values",
        layout: {
          "text-allow-overlap": true,
          "text-field": ["get", "value"],
          "text-size": 10,
        },
        paint: {
          "text-color": ["case", ["==", ["get", "category"], "Moderate"], "#172B2B", "#FFFFFF"],
        },
        source: "napas-stations",
        type: "symbol",
      });
      setMapReady(true);
    });

    const handleStationClick = (event: MapLayerMouseEvent) => {
      const id = event.features?.[0]?.properties?.id;
      const station = DEMO_STATIONS.find((item) => item.id === id);
      if (station) selectStation(station);
    };
    const setPointer = () => {
      map.getCanvas().style.cursor = "pointer";
    };
    const clearPointer = () => {
      map.getCanvas().style.cursor = "";
    };
    map.on("click", "napas-stations", handleStationClick);
    map.on("mouseenter", "napas-stations", setPointer);
    map.on("mouseleave", "napas-stations", clearPointer);

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [selectStation]);

  useEffect(() => {
    const source = mapRef.current?.getSource("napas-stations") as GeoJSONSource | undefined;
    if (!source || !mapReady) return;
    source.setData(stationCollection(visibleStations, selectedId));
  }, [mapReady, selectedId, visibleStations]);

  const setMapLayerVisibility = useCallback((key: LayerKey, visible: boolean) => {
    const map = mapRef.current;
    if (!map?.isStyleLoaded()) return;
    const style = map.getStyle();
    const tokens: Record<LayerKey, string[]> = {
      primaryRoads: ["road", "transportation"],
      localRoads: ["road", "transportation"],
      boundaries: ["boundary", "admin"],
      waterways: ["water", "river", "canal"],
      transit: ["rail", "transit"],
      landmarks: ["poi", "landmark"],
      roads: ["road", "transportation"],
      districts: ["place", "settlement", "admin"],
      places: ["place", "poi", "settlement"],
    };
    for (const layer of style.layers ?? []) {
      if (tokens[key].some((token) => layer.id.toLowerCase().includes(token))) {
        try {
          map.setLayoutProperty(layer.id, "visibility", visible ? "visible" : "none");
        } catch {
          // Some provider layers do not expose a layout visibility property.
        }
      }
    }
  }, []);

  const toggleLayer = (key: LayerKey) => {
    setLayers((current) => {
      const next = { ...current, [key]: !current[key] };
      setMapLayerVisibility(key, next[key]);
      return next;
    });
  };

  const recenter = () => {
    mapRef.current?.fitBounds(JAKARTA_BOUNDS, { duration: 550, padding: 36 });
  };

  return (
    <section className="map-panel" aria-label="Jakarta monitoring map">
      <header className="map-head">
        <div className="map-head-title">
          <h2>Jakarta monitoring map</h2>
          <p className="map-subtitle">Demo snapshot · illustrative readings · 26 Sep 2026, 09:20 WIB</p>
        </div>

        <div className="map-kpis" aria-label="Jakarta air quality summary">
          <KpiCard detail="stations" label="Reporting" value={`${reportingCount}/${DEMO_STATIONS.length}`} />
          <KpiCard detail="stations" label="Moderate" value={String(moderateCount)} tone="moderate" />
          <KpiCard detail="stations" label="Unhealthy" value={String(unhealthyCount)} tone="unhealthy" />
        </div>

        <div className="filters" data-od-id="map-filters">
          <label className="filter-label" htmlFor="category-filter">
            CATEGORY
            <select id="category-filter" value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value as FilterCategory)}>
              <option value="all">All categories</option>
              <option value="good">Good</option>
              <option value="moderate">Moderate</option>
              <option value="unhealthy">Unhealthy</option>
              <option value="stale">Stale / missing</option>
            </select>
          </label>
          <label className="filter-label" htmlFor="district-filter">
            DISTRICT
            <select id="district-filter" value={districtFilter} onChange={(event) => setDistrictFilter(event.target.value)}>
              <option value="all">All districts</option>
              <option value="North Jakarta">North Jakarta</option>
              <option value="Central Jakarta">Central Jakarta</option>
              <option value="East Jakarta">East Jakarta</option>
              <option value="West Jakarta">West Jakarta</option>
              <option value="South Jakarta">South Jakarta</option>
            </select>
          </label>
          <button className="station-list-button" onClick={() => setStationListOpen(true)} type="button">
            Station list
          </button>
        </div>
      </header>

      <div className="map-stage" id="map-stage">
        <div ref={mapContainer} className="napas-real-map" role="img" aria-label="Interactive MapLibre map of Jakarta with air-quality stations" />

        <div className="map-aids" aria-hidden="true">
          <div className="scale-aid"><div className="scale-rule" /><div className="scale-caption"><span>0</span><span>≈ 5 km</span></div></div>
          <div className="map-note">OpenStreetMap-derived vector base · provider attribution below</div>
        </div>
        <div className="north-aid" aria-label="North is up"><span>N</span><RotateCcwIcon className="size-4" /></div>

        <div className="live-card">
          <div className="live-kicker"><i aria-hidden="true" />Live air quality</div>
          <div className="live-main"><strong>Moderate</strong><span>Demo snapshot</span></div>
          <p className="network">{reportingCount} of {DEMO_STATIONS.length} reporting</p>
        </div>

        <div className="map-controls" aria-label="Map controls">
          <button aria-label="Zoom in" className="map-control" onClick={() => mapRef.current?.zoomIn()} type="button"><PlusIcon /></button>
          <button aria-label="Zoom out" className="map-control" onClick={() => mapRef.current?.zoomOut()} type="button"><MinusIcon /></button>
          <button aria-label="Recenter map" className="map-control" onClick={recenter} type="button"><LocateFixedIcon /></button>
          <button aria-controls="layers-menu" aria-expanded={layersOpen} aria-label="Map layers" className="map-control" onClick={() => setLayersOpen((open) => !open)} type="button"><Layers2Icon /></button>
        </div>

        {layersOpen ? (
          <div className="layers-menu" id="layers-menu" role="dialog" aria-label="Map layers">
            <div className="layer-heading">Geography</div>
            <LayerToggle checked={layers.primaryRoads} label="Primary roads & toll" onChange={() => toggleLayer("primaryRoads")} />
            <LayerToggle checked={layers.localRoads} label="Local roads" onChange={() => toggleLayer("localRoads")} />
            <LayerToggle checked={layers.boundaries} label="Municipality boundaries" onChange={() => toggleLayer("boundaries")} />
            <LayerToggle checked={layers.waterways} label="Waterways" onChange={() => toggleLayer("waterways")} />
            <LayerToggle checked={layers.transit} label="Transit corridors" onChange={() => toggleLayer("transit")} />
            <LayerToggle checked={layers.landmarks} label="Landmarks" onChange={() => toggleLayer("landmarks")} />
            <div className="layer-heading">Labels</div>
            <LayerToggle checked={layers.roads} label="Road labels" onChange={() => toggleLayer("roads")} />
            <LayerToggle checked={layers.districts} label="Municipality labels" onChange={() => toggleLayer("districts")} />
            <LayerToggle checked={layers.places} label="Place labels" onChange={() => toggleLayer("places")} />
          </div>
        ) : null}

        {visibleStations.length === 0 ? (
          <div className="map-empty">
            <strong>No stations match</strong>
            <p>Try a different category or district to see monitoring locations.</p>
            <button onClick={() => { setCategoryFilter("all"); setDistrictFilter("all"); }} type="button">Clear filters</button>
          </div>
        ) : null}
      </div>

      <div className="map-dock">
        <aside className="legend" aria-label="Air quality legend">
          <h3>ISPU categories</h3>
          <div className="legend-grid">
            <LegendItem color="good" label="Good" range="0–50" />
            <LegendItem color="moderate" label="Moderate" range="51–100" />
            <LegendItem color="unhealthy" label="Unhealthy" range="101–200" />
            <LegendItem color="stale" label="Stale / missing" />
          </div>
          <div className="legend-key" aria-label="Geographic line key">
            <span><i className="key-water" />Waterway</span>
            <span><i className="key-road" />Primary road</span>
            <span><i className="key-transit" />Transit</span>
            <span><i className="key-landmark" />Landmark</span>
          </div>
          <p className="legend-note">Marker values are ISPU. All readings on this screen are illustrative.</p>
        </aside>
        <article className="station-detail" aria-live="polite">
          <div className="station-detail-top">
            <div><h3>{selectedStation.name}</h3><p className="station-district">{selectedStation.district}</p></div>
            <span className={cn("category-pill", categoryKey[selectedStation.category])}>{selectedStation.category}</span>
          </div>
          <div className="detail-lower">
            <div className="detail-metrics">
              <div className="detail-metric"><span>ISPU</span><strong>{selectedStation.ispu ?? "—"}</strong></div>
              <div className="detail-metric"><span>PM2.5</span><strong>{selectedStation.pm25 ?? "—"} <small>{selectedStation.pm25 === null ? "" : "µg/m³"}</small></strong></div>
            </div>
            <button className="ask-station" onClick={() => onStationSelect(selectedStation)} type="button">Ask assistant ↗</button>
          </div>
          <div className="detail-meta"><span>Observed <strong>{selectedStation.observedAt}</strong></span><span>Source <strong>{selectedStation.source}</strong></span></div>
        </article>
      </div>

      {stationListOpen ? (
        <dialog className="station-dialog" open aria-labelledby="station-dialog-title">
          <div className="dialog-head">
            <div><h2 id="station-dialog-title">Monitoring stations</h2><p>Demo snapshot · select a station to locate it on the map</p></div>
            <button aria-label="Close station list" className="dialog-close" onClick={() => setStationListOpen(false)} type="button"><XIcon /></button>
          </div>
          <div className="station-table-wrap">
            <table>
              <thead><tr><th scope="col">Station</th><th scope="col">District</th><th scope="col">ISPU</th><th scope="col">PM2.5</th><th scope="col">Status</th></tr></thead>
              <tbody>{visibleStations.map((station) => <tr key={station.id}><td><button className="table-station" onClick={() => { selectStation(station); setStationListOpen(false); }} type="button">{station.name}</button></td><td>{station.district}</td><td>{station.ispu ?? "—"}</td><td>{station.pm25 === null ? "—" : `${station.pm25} µg/m³`}</td><td className={cn("table-status", categoryKey[station.category])}>{station.category}</td></tr>)}</tbody>
            </table>
          </div>
        </dialog>
      ) : null}
    </section>
  );
}

function KpiCard({ detail, label, tone = "good", value }: { readonly detail: string; readonly label: string; readonly tone?: "good" | "moderate" | "unhealthy"; readonly value: string }) {
  return (
    <div className={cn("map-kpi", tone)}>
      <span className={cn("kpi-dot", tone)} />
      <div className="kpi-copy">
        <strong>{value}</strong>
        <span className="kpi-meta"><span className="kpi-label">{label}</span><small>{detail}</small></span>
      </div>
    </div>
  );
}

function LegendItem({ color, label, range }: { readonly color: string; readonly label: string; readonly range?: string }) {
  return <div className="legend-item"><i className={`legend-dot ${color}`} /><span>{label} {range ? <small>{range}</small> : null}</span></div>;
}

function LayerToggle({ checked, label, onChange }: { readonly checked: boolean; readonly label: string; readonly onChange: () => void }) {
  return <label className="layer-toggle"><input checked={checked} onChange={onChange} type="checkbox" />{label}</label>;
}
