"use client";

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import { AgentChat } from "./agent-chat";
import { SiteHeader } from "./site-header";
import { WorkspaceMap } from "./workspace-map";
import { trackNapasEvent } from "@/lib/analytics";
import {
  DEFAULT_LANGUAGE,
  getUiCopy,
  LANGUAGE_CHANGE_EVENT,
  LANGUAGE_STORAGE_KEY,
  syncDocumentLanguage,
  type Language,
} from "@/lib/i18n";
import { type DemoStation } from "@/lib/napas";
import { toggleMobileMapOverlay } from "@/lib/mobile-layout";
import { reconcileStationId, resolveStation } from "@/lib/station-selection";

export function Workspace() {
  const [selectedStationId, setSelectedStationId] = useState<string>();
  const [stationOptions, setStationOptions] = useState<readonly DemoStation[]>([]);
  const [mapOverlayOpen, setMapOverlayOpen] = useState(false);
  const [mobileLegendOpen, setMobileLegendOpen] = useState(false);
  const language = useSyncExternalStore(subscribeToLanguageChanges, getStoredLanguage, () => DEFAULT_LANGUAGE);
  const copy = getUiCopy(language);
  const selectedStation = resolveStation(stationOptions, selectedStationId);

  useEffect(() => {
    syncDocumentLanguage(language);
  }, [language]);

  const changeLanguage = (nextLanguage: Language) => {
    if (nextLanguage === language) return;
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, nextLanguage);
    window.dispatchEvent(new Event(LANGUAGE_CHANGE_EVENT));
  };

  const handleStationClear = useCallback((source: "map_detail" | "chat_context") => {
    setSelectedStationId(undefined);
    trackNapasEvent("station_selection_cleared", { source });
  }, []);

  const handleStationSelect = useCallback((station: DemoStation, source: "map_marker" | "station_list" | "chat_picker") => {
    setSelectedStationId(station.id);
    trackNapasEvent("station_selected", { source });
  }, []);

  const handleStationsChange = useCallback((stations: readonly DemoStation[]) => {
    setStationOptions(stations);
    setSelectedStationId((currentId) => reconcileStationId(stations, currentId));
  }, []);

  useEffect(() => {
    if (!mapOverlayOpen) {
      setMobileLegendOpen(false);
    }
  }, [mapOverlayOpen]);

  return (
    <main className="napas-od-app" id="main">
      <SiteHeader language={language} onLanguageChange={changeLanguage} />

      <div className="workspace" data-mobile-map-open={mapOverlayOpen} data-od-id="dashboard-workspace">
        <section aria-labelledby="chat-heading" className="chat-panel" id="chat-panel" data-od-id="assistant-panel">
          <AgentChat
            language={language}
            isLegendOpen={mobileLegendOpen}
            isMapOpen={mapOverlayOpen}
            onMapToggle={() => setMapOverlayOpen((open) => toggleMobileMapOverlay(open))}
            onLegendOpen={() => setMobileLegendOpen(true)}
            onStationClear={handleStationClear}
            onStationSelect={handleStationSelect}
            selectedStation={selectedStation?.name}
            selectedStationId={selectedStationId}
            stationOptions={stationOptions}
          />
        </section>
        <WorkspaceMap
          id="map-panel"
          language={language}
          isMobileOverlayOpen={mapOverlayOpen}
          mobileLegendOpen={mobileLegendOpen}
          onMobileLegendClose={() => setMobileLegendOpen(false)}
          onStationClear={handleStationClear}
          onStationSelect={handleStationSelect}
          onStationsChange={handleStationsChange}
          selectedStationId={selectedStationId}
        />
      </div>

    </main>
  );
}

function getStoredLanguage(): Language {
  try {
    return window.localStorage.getItem(LANGUAGE_STORAGE_KEY) === "id" ? "id" : DEFAULT_LANGUAGE;
  } catch {
    return DEFAULT_LANGUAGE;
  }
}

function subscribeToLanguageChanges(onStoreChange: () => void): () => void {
  window.addEventListener("storage", onStoreChange);
  window.addEventListener(LANGUAGE_CHANGE_EVENT, onStoreChange);
  return () => {
    window.removeEventListener("storage", onStoreChange);
    window.removeEventListener(LANGUAGE_CHANGE_EVENT, onStoreChange);
  };
}
