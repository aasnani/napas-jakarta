"use client";

import { useState } from "react";
import { AgentChat } from "./agent-chat";
import { WorkspaceMap } from "./workspace-map";
import { DEMO_STATIONS, type DemoStation } from "@/lib/napas";

export function Workspace() {
  const defaultStation = DEMO_STATIONS.find((station) => station.id === "kelapa-gading") ?? DEMO_STATIONS[0];
  const [selectedStation, setSelectedStation] = useState<DemoStation>(defaultStation);
  const [mobileView, setMobileView] = useState<"map" | "chat">("map");

  return (
    <main className="napas-od-app" id="main">
      <header className="topbar" data-od-id="top-navbar">
        <div className="topbar-side">Jakarta city monitor</div>
        <a aria-label="Napas Jakarta home" className="brand" href="#main" data-od-id="napas-logo">
          <img alt="" height={1254} src="/napas-jakarta-air-icon.png" width={1254} />
          <span>Napas <small>Jakarta</small></span>
        </a>
        <div className="topbar-side">Air quality · demo view</div>
      </header>

      <div className="mobile-switch" role="tablist" aria-label="Screen view">
        <button aria-controls="map-panel" aria-selected={mobileView === "map"} onClick={() => setMobileView("map")} role="tab" type="button">Map</button>
        <button aria-controls="chat-panel" aria-selected={mobileView === "chat"} onClick={() => setMobileView("chat")} role="tab" type="button">Assistant</button>
      </div>

      <div className="workspace" data-mobile-tab={mobileView} data-od-id="dashboard-workspace">
        <section aria-labelledby="chat-heading" className="chat-panel" id="chat-panel" role="tabpanel" data-od-id="assistant-panel">
          <AgentChat embedded selectedStation={selectedStation.name} />
        </section>
        <WorkspaceMap onStationSelect={setSelectedStation} selectedStationId={selectedStation.id} />
      </div>
    </main>
  );
}
