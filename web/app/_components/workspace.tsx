"use client";

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { AgentChat } from "./agent-chat";
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

type InfoDialog = "about" | "privacy" | null;
type AssistantPrefill = { id: number; text: string };

export function Workspace() {
  const [selectedStationId, setSelectedStationId] = useState<string>();
  const [stationOptions, setStationOptions] = useState<readonly DemoStation[]>([]);
  const [mapOverlayOpen, setMapOverlayOpen] = useState(false);
  const [mobileLegendOpen, setMobileLegendOpen] = useState(false);
  const [infoDialog, setInfoDialog] = useState<InfoDialog>(null);
  const [assistantPrefill, setAssistantPrefill] = useState<AssistantPrefill>();
  const language = useSyncExternalStore(subscribeToLanguageChanges, getStoredLanguage, () => DEFAULT_LANGUAGE);
  const assistantPrefillId = useRef(0);
  const infoDialogRef = useRef<HTMLDialogElement>(null);
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

  const handleAskAssistant = (station: DemoStation) => {
    assistantPrefillId.current += 1;
    const ispu = station.ispu == null ? (language === "id" ? "tidak tersedia" : "unavailable") : `ISPU ${station.ispu}`;
    const pm25 = station.pm25 == null ? (language === "id" ? "tidak tersedia" : "unavailable") : `PM2.5 ${station.pm25} µg/m³`;

    setAssistantPrefill({
      id: assistantPrefillId.current,
      text: language === "id"
        ? `Jelaskan mengapa pembacaan ${station.name} adalah ${ispu} dan ${pm25}.`
        : `Explain why ${station.name} readings are ${ispu} and ${pm25}.`,
    });
  };

  const handleStationClear = useCallback(() => {
    setSelectedStationId(undefined);
  }, []);

  const handleStationSelect = useCallback((station: DemoStation) => {
    setSelectedStationId(station.id);
    trackNapasEvent("station_selected");
  }, []);

  const handleStationsChange = useCallback((stations: readonly DemoStation[]) => {
    setStationOptions(stations);
    setSelectedStationId((currentId) => reconcileStationId(stations, currentId));
  }, []);

  useEffect(() => {
    const dialog = infoDialogRef.current;
    if (!dialog) return;

    if (infoDialog && !dialog.open) {
      dialog.showModal();
    } else if (!infoDialog && dialog.open) {
      dialog.close();
    }
  }, [infoDialog]);

  useEffect(() => {
    if (!mapOverlayOpen) {
      setMobileLegendOpen(false);
    }
  }, [mapOverlayOpen]);

  return (
    <main className="napas-od-app" id="main">
      <header className="topbar" data-od-id="top-navbar">
        <div className="topbar-left">
          <div aria-label={copy.navbar.monitor} className="topbar-side">
            <span className="topbar-label-full">{copy.navbar.monitor}</span>
            <span className="topbar-label-mobile">{copy.navbar.mobileMonitor}</span>
          </div>
          <nav aria-label={copy.navbar.productInformation} className="topbar-actions">
            <button aria-haspopup="dialog" className="topbar-link" onClick={() => setInfoDialog("about")} type="button">{copy.navbar.about}</button>
            <button aria-haspopup="dialog" className="topbar-link" onClick={() => setInfoDialog("privacy")} type="button">{copy.navbar.privacy}</button>
          </nav>
        </div>
        <a aria-label={copy.navbar.brandHome} className="brand" href="#main" data-od-id="napas-logo">
          <img alt="" height={1254} src="/napas-jakarta-air-icon.png" width={1254} />
          <h1 className="brand-title">Napas <small>Jakarta</small></h1>
        </a>
        <div className="topbar-right">
          <LanguageToggle language={language} onChange={changeLanguage} />
        </div>
      </header>

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
            prefillPrompt={assistantPrefill}
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
          onAskAssistant={handleAskAssistant}
          onStationClear={handleStationClear}
          onStationSelect={handleStationSelect}
          onStationsChange={handleStationsChange}
          selectedStationId={selectedStationId}
        />
      </div>

      <dialog
        aria-describedby="info-dialog-description"
        aria-labelledby="info-dialog-title"
        className="info-dialog"
        onClose={() => setInfoDialog(null)}
        ref={infoDialogRef}
      >
        <div className="info-dialog-head">
          <div>
            <p className="info-dialog-kicker">{copy.about.kicker}</p>
            <h2 id="info-dialog-title">{infoDialog === "privacy" ? copy.about.privacyTitle : copy.about.aboutTitle}</h2>
          </div>
          <button aria-label={copy.about.close} className="dialog-close" onClick={() => setInfoDialog(null)} type="button">×</button>
        </div>
        <div className="info-dialog-body" id="info-dialog-description">
          {infoDialog === "privacy" ? (
            <>
              <p>{copy.about.privacyBody[0]}</p>
              <p>{copy.about.privacyBody[1]}</p>
              <ul>
                {copy.about.privacyBody.slice(2, 5).map((paragraph) => <li key={paragraph}>{paragraph}</li>)}
              </ul>
              <p>{copy.about.privacyBody[5]}</p>
            </>
          ) : (
            <>{copy.about.aboutBody.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}</>
          )}
        </div>
      </dialog>
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

function LanguageToggle({ language, onChange }: { readonly language: Language; readonly onChange: (language: Language) => void }) {
  const copy = getUiCopy(language);

  return (
    <div aria-label={copy.navbar.language} className="language-toggle" role="group">
      <button
        aria-label={copy.navbar.switchEnglish}
        aria-pressed={language === "en"}
        className={language === "en" ? "is-active" : undefined}
        onClick={() => onChange("en")}
        type="button"
      >
        EN
      </button>
      <button
        aria-label={copy.navbar.switchIndonesian}
        aria-pressed={language === "id"}
        className={language === "id" ? "is-active" : undefined}
        onClick={() => onChange("id")}
        type="button"
      >
        ID
      </button>
    </div>
  );
}
