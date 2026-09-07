"""Napas Jakarta's responsive NiceGUI application.

The FastAPI object remains the source of truth for API contracts; NiceGUI is
mounted into that same ASGI process so local and deployed clients share one
health endpoint and one domain layer.
"""

from __future__ import annotations

import asyncio
import base64
import html
import json
import os
import queue
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from app.api import (
    DOCUMENTS,
    MEASUREMENTS,
    refresh_runtime_historical,
    refresh_runtime_measurements,
)
from app.api import app as api_app
from app.citations import linkify_citations
from app.history import (
    historical_series_diagnostics,
    historical_series_metadata,
    load_historical_city,
)
from app.rag import answer
from app.stations import display_district_name, display_station_name, load_runtime_stations
from app.tools import get_latest_measurements, latest_data_age_seconds
from monitoring.analytics import load_dashboard

ROOT = Path(__file__).resolve().parents[1]
ICON_PATH = ROOT / "assets" / "napas-jakarta-air-icon.png"
HISTORICAL = load_historical_city(ROOT / "data" / "processed" / "historical_city_air_quality.csv")
HISTORICAL_META = historical_series_metadata(HISTORICAL)
HISTORICAL_DIAGNOSTICS = historical_series_diagnostics(HISTORICAL)
STATIONS = load_runtime_stations(source_url=os.getenv("SOURCE_DATA_URL", ""))
LATEST = get_latest_measurements(MEASUREMENTS)

try:
    from nicegui import app, ui

    from app.webui.state import (
        CHAT_STORAGE_KEY,
        ChatTurnLifecycle,
        chat_payload,
        clear_conversation,
        client_state,
        restore_chat_payload,
    )
    from app.webui.theme import TOKENS, install_theme
except ImportError:  # Keep API imports/test collection useful before optional UI install.
    app = None  # type: ignore[assignment]
    ui = None  # type: ignore[assignment]


def _category(value: object) -> str:
    labels = {
        "BAIK": "Good",
        "GOOD": "Good",
        "SEDANG": "Moderate",
        "MODERATE": "Moderate",
        "TIDAK SEHAT": "Unhealthy",
        "UNHEALTHY": "Unhealthy",
        "SANGAT TIDAK SEHAT": "Very unhealthy",
        "VERY UNHEALTHY": "Very unhealthy",
        "BERBAHAYA": "Hazardous",
        "HAZARDOUS": "Hazardous",
    }
    text = str(value or "").strip()
    return labels.get(text.upper(), text.title() if text else "No observation")


def _time(value: object) -> str:
    if value is None or str(value) in {"", "None", "NaT"}:
        return "No observation"
    try:
        parsed = datetime.fromisoformat(str(value))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
        return parsed.astimezone().strftime("%d %b %Y, %H:%M WIB")
    except (TypeError, ValueError):
        return str(value)


def _source_mode() -> str:
    return (
        "live"
        if os.getenv("SOURCE_DATA_URL", "").strip()
        or any(not row.source.startswith("Udara Jakarta demo") for row in MEASUREMENTS)
        else "demo"
    )


def _source_label(source: object) -> str:
    text = str(source or "").strip()
    if not text:
        return "No source recorded"
    if text.startswith(("http://", "https://")):
        return (
            "Official Jakarta monitoring"
            if "udara.jakarta.go.id" in text
            else text.split("//", 1)[-1].split("/", 1)[0]
        )
    return "Demo snapshot" if text.lower().startswith("udara jakarta demo") else text


def _rows() -> list[dict[str, Any]]:
    latest = {row["station_id"]: row for row in LATEST}
    result = []
    for station in STATIONS:
        row = latest.get(station.get("station_id"), {})
        result.append(
            {
                **station,
                "station": display_station_name(station.get("station") or row.get("station")),
                "district": display_district_name(station.get("district") or row.get("district")),
                "ispu": row.get("ispu"),
                "category": _category(row.get("category")),
                "concentration": row.get("concentration"),
                "observed_at": row.get("observed_at"),
                "source": row.get("source", ""),
            }
        )
    return result


ROWS = _rows()


def _refresh_runtime_ui() -> None:
    """Refresh DB-backed UI globals before each page is built."""
    refresh_runtime_measurements()
    global HISTORICAL, HISTORICAL_META, HISTORICAL_DIAGNOSTICS, LATEST, STATIONS, ROWS
    HISTORICAL = refresh_runtime_historical()
    HISTORICAL_META = historical_series_metadata(HISTORICAL)
    HISTORICAL_DIAGNOSTICS = historical_series_diagnostics(HISTORICAL)
    LATEST = get_latest_measurements(MEASUREMENTS)
    STATIONS = load_runtime_stations(source_url=os.getenv("SOURCE_DATA_URL", ""))
    ROWS = _rows()


def _status_color(category: str) -> str:
    return {
        "Good": TOKENS["good"],
        "Moderate": TOKENS["moderate"],
        "Unhealthy": TOKENS["unhealthy"],
        "Very unhealthy": TOKENS["very_unhealthy"],
        "Hazardous": TOKENS["hazardous"],
    }.get(category, TOKENS["missing"])


def filter_station_rows(
    rows: list[dict],
    district: str | list[str] = "All districts",
    category: str | list[str] = "All categories",
    freshness: str = "All data",
    now: datetime | None = None,
    search: str = "",
    ispu_min: float | None = None,
    ispu_max: float | None = None,
) -> list[dict]:
    """Apply shared station-table and marker filters without coercing missing ISPU."""
    now = now or datetime.now().astimezone()
    district_values = {district} if isinstance(district, str) else set(district)
    category_values = {category} if isinstance(category, str) else set(category)
    district_values.discard("All districts")
    category_values.discard("All categories")
    term = search.strip().lower()
    selected = []
    for row in rows:
        if district_values and row.get("district") not in district_values:
            continue
        if category_values and row.get("category") not in category_values:
            continue
        if term and term not in f"{row.get('station', '')} {row.get('district', '')}".lower():
            continue
        value = row.get("ispu")
        if ispu_min is not None and (value is None or value < ispu_min):
            continue
        if ispu_max is not None and (value is None or value > ispu_max):
            continue
        is_fresh = False
        try:
            observed = datetime.fromisoformat(str(row.get("observed_at")))
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=now.tzinfo)
            is_fresh = (now - observed).total_seconds() <= 3 * 3600
        except (TypeError, ValueError):
            pass
        if freshness == "Fresh only" and not is_fresh:
            continue
        if freshness == "Stale or missing" and is_fresh:
            continue
        if freshness == "Missing only" and value is not None:
            continue
        selected.append(row)
    return selected


def _station_filter_summary(
    rows: list[dict],
    filtered: list[dict],
    district: object,
    category: object,
    freshness: object,
    search: object,
    ispu_min: object,
    ispu_max: object,
) -> str:
    active = []
    if district and district != "All districts":
        district_text = (
            ", ".join(district) if isinstance(district, (list, tuple, set)) else district
        )
        active.append(f"district: {district_text}")
    if category:
        values = category if isinstance(category, (list, tuple, set)) else [category]
        if values:
            active.append(f"category: {', '.join(values)}")
    if freshness and freshness != "All data":
        active.append(f"freshness: {freshness}")
    if search:
        active.append(f"search: {search}")
    if ispu_min is not None or ispu_max is not None:
        min_text = ispu_min if ispu_min is not None else "—"
        max_text = ispu_max if ispu_max is not None else "—"
        active.append(f"ISPU: {min_text}–{max_text}")
    suffix = f" · {', '.join(active)}" if active else " · no filters"
    return f"Showing {len(filtered)} of {len(rows)} stations{suffix}"


def _station_filter_toolbar(rows: list[dict], scope: str):
    """Build the reusable filter model and controls shared by map and tables."""
    districts = sorted({row.get("district") for row in rows if row.get("district")})
    categories = sorted({row.get("category") for row in rows if row.get("category")})
    values = [row["ispu"] for row in rows if row.get("ispu") is not None]
    value_min, value_max = (min(values), max(values)) if values else (0, 500)
    with ui.card().classes("napas-card napas-filter-surface w-full p-4"):
        ui.label(scope).classes("text-sm font-semibold")
        ui.label(
            "Filters apply to the station table and, on Live map, its visible markers."
        ).classes("text-xs napas-muted")
        with ui.row().classes("items-end gap-3 w-full flex-wrap mt-2"):
            search = (
                ui.input("Station search", placeholder="Search station or district…")
                .props("outlined clearable")
                .classes("w-64")
            )
            district = (
                ui.select(["All districts", *districts], value="All districts", label="District")
                .props("outlined dense")
                .classes("w-52")
            )
            category = (
                ui.select(categories, multiple=True, value=[], label="Categories")
                .props("outlined dense use-chips clearable")
                .classes("w-64")
            )
            freshness = (
                ui.select(
                    ["All data", "Fresh only", "Stale or missing", "Missing only"],
                    value="All data",
                    label="Freshness",
                )
                .props("outlined dense")
                .classes("w-52")
            )
            ispu_min = (
                ui.number("Min ISPU", min=value_min, max=value_max, step=1)
                .props("outlined dense clearable")
                .classes("w-32")
            )
            ispu_max = (
                ui.number("Max ISPU", min=value_min, max=value_max, step=1)
                .props("outlined dense clearable")
                .classes("w-32")
            )
            reset = ui.button("Clear filters", icon="filter_alt_off").props("flat")
        summary = ui.label().classes("text-xs napas-muted mt-2")

    def selected_rows() -> list[dict]:
        return filter_station_rows(
            rows,
            district.value,
            category.value,
            freshness.value,
            search=search.value or "",
            ispu_min=ispu_min.value,
            ispu_max=ispu_max.value,
        )

    def update_summary() -> None:
        summary.text = _station_filter_summary(
            rows,
            selected_rows(),
            district.value,
            category.value,
            freshness.value,
            search.value,
            ispu_min.value,
            ispu_max.value,
        )

    def clear() -> None:
        search.set_value("")
        district.set_value("All districts")
        category.set_value([])
        freshness.set_value("All data")
        ispu_min.set_value(None)
        ispu_max.set_value(None)
        update_summary()

    reset.on_click(clear)
    update_summary()
    return (
        selected_rows,
        (search, district, category, freshness, ispu_min, ispu_max),
        update_summary,
    )


def _surface(title: str | None = None):
    card = ui.card().classes("napas-card w-full p-5")
    if title:
        with card:
            ui.label(title).classes("text-lg font-semibold")
    return card


def _metric(label: str, value: str, subtitle: str, icon: str = "analytics") -> None:
    with ui.card().classes("napas-card napas-metric p-4 flex-1 min-w-[180px]"):
        with ui.row().classes("items-center gap-3"):
            ui.icon(icon).classes("text-2xl text-primary")
            ui.label(label).classes("text-sm napas-muted")
        ui.label(value).classes("text-2xl font-semibold mt-2")
        ui.label(subtitle).classes("text-xs napas-muted")


def _freshness_strip() -> None:
    age = latest_data_age_seconds(MEASUREMENTS)
    age_text = (
        "No observations"
        if age is None
        else f"newest observation {_time(max(MEASUREMENTS, key=lambda x: x.observed_at).observed_at.isoformat())}"
    )
    with (
        ui.row()
        .classes("items-center gap-2 w-full rounded-lg px-4 py-3")
        .style("background:#EDF3F1")
    ):
        ui.icon("schedule").classes("text-primary")
        ui.label(f"{_source_mode().title()} snapshot · {age_text}").classes("text-sm")
        ui.space()
        source_dialog = _source_details_dialog()
        ui.button("Source details", icon="open_in_new", on_click=source_dialog.open).props(
            "flat dense color=primary"
        ).classes("text-sm")


def _help_dialog() -> None:
    with ui.dialog() as dialog, ui.card().classes("w-[min(620px,92vw)] p-6"):
        ui.label("Air-quality terms").classes("text-xl font-semibold")
        ui.markdown("""**PM2.5** — fine particles up to 2.5 micrometres that can travel deep into the lungs.

**PM10** — particles up to 10 micrometres; PM2.5 is the smaller subset.

**ISPU** — Indonesia's unitless air-pollution index, not a concentration.

**µg/m³** — micrograms per cubic metre, the concentration unit.

**Freshness** — how long ago a station observation was recorded. A stale or missing value is never silently treated as current.

The app is educational and does not provide medical diagnosis.""").classes("text-sm leading-7")
        ui.button("Close", on_click=dialog.close).props("flat color=primary")
    return dialog


def _source_details_dialog():
    """Show the provenance and freshness context behind the current snapshot."""
    newest = max(MEASUREMENTS, key=lambda item: item.observed_at) if MEASUREMENTS else None
    source_names = sorted({str(item.source) for item in MEASUREMENTS if item.source})
    station_count = len({item.station_id for item in MEASUREMENTS})
    with ui.dialog() as dialog, ui.card().classes("w-[min(720px,94vw)] p-6"):
        ui.label("Source details").classes("text-xl font-semibold")
        ui.label(
            "Use this panel to distinguish the loaded snapshot from historical context."
        ).classes("text-sm napas-muted")
        with ui.grid(columns=2).classes("w-full gap-x-6 gap-y-3 mt-4"):
            ui.label("Snapshot mode").classes("text-sm font-medium")
            ui.label(_source_mode().title()).classes("text-sm")
            ui.label("Measurement count").classes("text-sm font-medium")
            ui.label(str(len(MEASUREMENTS))).classes("text-sm")
            ui.label("Stations represented").classes("text-sm font-medium")
            ui.label(str(station_count)).classes("text-sm")
            ui.label("Newest observation").classes("text-sm font-medium")
            ui.label(_time(newest.observed_at.isoformat()) if newest else "No observation").classes(
                "text-sm"
            )
            ui.label("Freshness").classes("text-sm font-medium")
            ui.label(
                "No observations available"
                if newest is None
                else f"{latest_data_age_seconds(MEASUREMENTS):.0f} seconds old"
            ).classes("text-sm")
        ui.separator().classes("my-4")
        ui.label("Measurement sources").classes("font-medium")
        if source_names:
            for source in source_names:
                publisher = (
                    "Dinas Lingkungan Hidup Provinsi DKI Jakarta"
                    if "udara.jakarta.go.id" in source
                    else "Loaded measurement feed"
                )
                ui.label(f"{_source_label(source)} · {publisher}").classes("text-sm font-medium")
                if source.startswith(("http://", "https://")):
                    ui.link(source, source, new_tab=True).classes("text-sm break-all")
                else:
                    ui.label(source).classes("text-sm")
        else:
            ui.label("No source recorded").classes("text-sm napas-muted")
        ui.label("Historical series").classes("font-medium mt-3")
        ui.label(
            "The Trends page uses a city-level Zenodo/Open-Meteo CAMS series. It is model context, not an official SPKU station observation."
        ).classes("text-sm napas-muted")
        ui.link(
            "Open-Meteo air-quality API documentation",
            "https://open-meteo.com/en/docs/air-quality-api",
            new_tab=True,
        ).classes("text-sm")
        ui.button("Close", on_click=dialog.close).props("flat color=primary").classes("mt-4")
    return dialog


def _understand_numbers() -> None:
    """Visible, reusable education surface present on every destination."""
    with ui.expansion("Understand the numbers", icon="menu_book", value=False).classes(
        "w-full napas-card"
    ):
        ui.label(
            "These values answer two different questions: how much pollutant is in the air, and how Indonesia classifies the health concern."
        ).classes("text-sm leading-6")
        with ui.element("div").classes("grid grid-cols-1 md:grid-cols-2 w-full gap-4 mt-3"):
            for title, body in (
                (
                    "PM2.5 · concentration",
                    "Fine particles up to 2.5 µm. Reported in µg/m³ (micrograms per cubic metre). Higher means more particle mass in the sampled air; lower means less. It is a physical concentration, not an index.",
                ),
                (
                    "PM10 · concentration",
                    "Particles up to 10 µm, including the smaller PM2.5 fraction. Also reported in µg/m³. PM10 and PM2.5 should not be assumed identical; missing PM10 is shown as unavailable rather than invented.",
                ),
                (
                    "ISPU · Indonesian category",
                    "A unitless Indonesian air-pollution index. Higher values indicate a more concerning category: Good (1–50), Moderate (51–100), Unhealthy (101–200), Very unhealthy (201–300), Hazardous (301+). ISPU is not a PM2.5 concentration.",
                ),
                (
                    "Freshness · data age",
                    "How long ago the station observation was recorded. Freshness is about recency, not safety. Stale or missing values are not treated as current.",
                ),
                (
                    "Network median · comparison",
                    "The middle ISPU value across loaded stations. It is a relative snapshot baseline: below the median means lower than other loaded stations, not automatically safe; above means higher than the network at that moment.",
                ),
            ):
                with ui.card().classes("p-3 bg-[#F7FAF9] border"):
                    ui.label(title).classes("font-medium text-sm")
                    ui.label(body).classes("text-sm leading-6 napas-muted")
        with ui.row().classes("gap-4 mt-3 text-sm flex-wrap"):
            ui.link(
                "WHO air-quality guidelines",
                "https://www.who.int/publications/i/item/9789240034228",
                new_tab=True,
            )
            ui.link(
                "Indonesian ISPU method (Permen LHK No. 14/2020)",
                "https://peraturan.bpk.go.id/Details/163466/permen-lhk-no-14-tahun-2020",
                new_tab=True,
            )
        ui.label(
            "Educational context only; it is not a diagnosis or personalized medical advice."
        ).classes("text-xs napas-muted mt-2")


def _navigation_link(path: str, label: str, icon: str, active: str) -> None:
    classes = "napas-nav-active" if path == active else ""
    with ui.link(target=path).classes(
        f"w-full items-center rounded-lg px-4 py-3 no-underline napas-nav-link napas-rounded-control {classes}"
    ):
        ui.icon(icon).classes("mr-3 text-[23px]")
        ui.label(label).classes("text-base")


def _shell2(active: str, content) -> None:
    """Shell kept separate to make navigation children explicit and testable."""
    install_theme()
    if ICON_PATH.exists():
        encoded = base64.b64encode(ICON_PATH.read_bytes()).decode("ascii")
        ui.add_head_html(
            f'<link rel="icon" type="image/png" href="data:image/png;base64,{encoded}">'
        )
    # sessionStorage is tab-scoped and survives internal route navigation. A
    # real document reload clears it synchronously before the new client
    # handshakes, without a fragile beforeunload handler.
    ui.add_head_html(
        f"""<script>(function() {{
            const nav = window.performance?.getEntriesByType('navigation')?.[0]?.type;
            if (nav === 'reload') sessionStorage.removeItem({json.dumps(CHAT_STORAGE_KEY)});
        }})();</script>"""
    )
    # Quasar's responsive breakpoint closes the drawer on compact screens; the
    # header toggle keeps navigation reachable without covering content.
    drawer = ui.left_drawer(value=True).classes("napas-drawer bg-white border-r p-4")
    drawer.props("behavior=desktop breakpoint=800")
    with ui.header().classes("items-center px-4 h-16 bg-white text-[#172B2B] border-b"):
        ui.button(icon="menu", on_click=lambda: drawer.toggle()).props("flat round").classes(
            "md:hidden"
        )
        ui.icon("air").classes("text-3xl text-primary")
        ui.label("Napas Jakarta").classes("text-xl font-semibold")
        ui.badge(f"{_source_mode().title()} snapshot").props("outline color=primary")
        ui.space()
        help_dialog = _help_dialog()
        ui.button(icon="help_outline", on_click=help_dialog.open).props("flat round").tooltip(
            "Terms and methodology"
        )
        ui.select(
            ["English", "Bahasa Indonesia"],
            value=client_state()["language"],
            on_change=lambda e: client_state().__setitem__("language", e.value),
        ).props("dense borderless")
    with drawer:
        ui.label("Explore").classes("text-xs uppercase tracking-wider napas-muted px-3 py-3")
        _navigation_link("/", "Ask", "chat", active)
        _navigation_link("/map", "Live map", "map", active)
        _navigation_link("/overview", "Overview", "dashboard", active)
        _navigation_link("/trends", "Trends", "show_chart", active)
        _navigation_link("/monitoring", "Monitoring", "monitoring", active)
        ui.separator().classes("my-4")
        ui.label("One clear view of Jakarta's air, its causes, and what people can do.").classes(
            "text-sm napas-muted px-3"
        )
    content_width = "napas-analytics-content" if active != "/" else "napas-chat-content"
    with (
        ui.element("main").classes("napas-main"),
        ui.column().classes(f"napas-content {content_width} gap-6"),
    ):
        content()


def _page_header(title: str, subtitle: str) -> None:
    ui.label(title).classes("text-3xl font-semibold")
    ui.label(subtitle).classes("text-base napas-muted")
    _freshness_strip()
    _understand_numbers()


def _render_sources(sources: list[dict], parent=None) -> None:
    if not sources:
        return
    target = parent or ui.column().classes("w-full")
    with (
        target,
        ui.expansion(f"Sources ({len(sources)})", icon="library_books").classes(
            "w-full napas-rounded-control"
        ),
    ):
        for source in sources:
            title = source.get("title", source.get("id", "Source"))
            url = source.get("url")
            with ui.row().classes("items-start gap-2 py-2 w-full"):
                ui.icon("link").classes("text-primary mt-1")
                if url and str(url).startswith(("http://", "https://")):
                    ui.link(str(title), str(url), new_tab=True).classes("font-medium")
                else:
                    ui.label(str(title)).classes("font-medium")
                publisher = str(source.get("publisher", "")).strip()
                if publisher:
                    ui.label(publisher).classes("text-xs napas-muted")
                locator = str(source.get("locator", "")).strip()
                effective_date = str(source.get("effective_date", "")).strip()
                if locator or effective_date:
                    ui.label(" · ".join(item for item in (locator, effective_date) if item)).classes(
                        "text-xs napas-muted"
                    )
            if source.get("excerpt"):
                ui.label(str(source["excerpt"])[:220]).classes("text-xs napas-muted pl-7")


def station_marker_options(row: dict[str, Any]) -> dict[str, Any]:
    """Return explicit Leaflet hit-target and category styling for a station."""
    color = _status_color(str(row.get("category", "No observation")))
    return {
        "radius": 11,
        "color": "#FFFFFF",
        "weight": 2,
        "opacity": 1,
        "fillColor": color,
        "fillOpacity": 0.95,
        "interactive": True,
        "bubblingMouseEvents": True,
        "pane": "markerPane",
        "title": str(row.get("station", "Station")),
    }


def station_tooltip_html(row: dict[str, Any]) -> str:
    """Create concise, human-readable hover content for one station marker."""
    station = html.escape(str(row.get("station", "Station")))
    district = html.escape(str(row.get("district", "District unknown")))
    category = html.escape(str(row.get("category", "No observation")))
    ispu = row.get("ispu") if row.get("ispu") is not None else "—"
    concentration = row.get("concentration")
    pm25 = "—" if concentration is None else f"{concentration:.1f} µg/m³"
    observed = html.escape(_time(row.get("observed_at")))
    return (
        f"<b>{station}</b><br>"
        f"{district}<br>"
        f"{category} · ISPU {ispu}<br>"
        f"PM2.5: {pm25}<br>"
        f"Observed: {observed}"
    )


def station_marker_interaction_config(row: dict[str, Any]) -> dict[str, Any]:
    """Return the Leaflet commands needed for hover and click interactions."""
    tooltip = station_tooltip_html(row)
    return {
        "tooltip": tooltip,
        "tooltip_options": {"sticky": True, "direction": "top", "opacity": 0.96},
        "popup": f"{tooltip}<br>Source: {html.escape(_source_label(row.get('source')))}",
    }


def bind_station_marker_interactions(map_view, marker, row: dict[str, Any]) -> None:
    """Bind interactions after a marker exists on the initialized Leaflet map."""
    config = station_marker_interaction_config(row)
    map_view.run_layer_method(
        marker.id,
        "bindTooltip",
        config["tooltip"],
        config["tooltip_options"],
    )
    map_view.run_layer_method(marker.id, "bindPopup", config["popup"])


def _render_chat_turn(parent, message: dict[str, Any]):
    """Render one complete chat turn with one shared history/live structure.

    The returned markdown and source slot are deliberately kept in the same
    assistant group so streaming and completed citation links cannot drift to
    a different part of the page.
    """
    role = message.get("role")
    with parent:
        if role == "user":
            with (
                ui.row().classes("justify-end w-full napas-fade"),
                ui.row().classes("items-end gap-2 max-w-[86%]"),
            ):
                ui.label(str(message.get("content", ""))).classes("napas-user-bubble px-4 py-3")
                with ui.element("span").classes("napas-avatar napas-avatar-user"):
                    ui.icon("person").classes("text-lg")
            return None, None

        with ui.row().classes("items-start gap-3 w-full napas-fade"):
            with ui.element("span").classes("napas-avatar napas-avatar-guide"):
                ui.icon("air").classes("text-lg")
            with ui.column().classes("napas-assistant gap-2"):
                ui.label("Napas Jakarta").classes("napas-sender-label")
                content = str(message.get("content", ""))
                if not message.get("streaming"):
                    content = linkify_citations(content, message.get("sources", []))
                markdown = ui.markdown(content).classes(
                    "text-[15px] leading-7 napas-assistant-text"
                )
                source_slot = ui.column().classes("w-full napas-source-slot")
                _render_sources(message.get("sources", []), source_slot)
        return markdown, source_slot


def _chat_page() -> None:
    _refresh_runtime_ui()
    client = ui.context.client
    state = client_state()
    _page_header(
        "Ask Napas Jakarta",
        "A grounded guide to current observations, causes, policy, and practical protection.",
    )
    transcript = ui.column().classes("napas-chat-column napas-chat-transcript gap-5")

    def render_starters() -> None:
        with transcript:
            ui.label("What would you like to understand?").classes("text-xl font-medium")
            ui.label(
                "Start with a current reading, an explanation of causes, policy, or ways to reduce exposure."
            ).classes("napas-muted")
            with ui.element("div").classes("grid grid-cols-1 md:grid-cols-2 w-full gap-3"):
                for question, icon in (
                    ("What is the current air quality in Jakarta Pusat?", "location_on"),
                    ("What causes Jakarta's PM2.5 pollution?", "help_outline"),
                    ("What regulations are in place to improve air quality?", "gavel"),
                    ("How can I protect myself on a bad-air day?", "health_and_safety"),
                ):
                    with (
                        ui.card().classes(
                            "napas-card napas-starter napas-rounded-control p-4 cursor-pointer hover:shadow-md transition-shadow"
                        ) as prompt,
                        ui.row().classes("items-start gap-3 no-wrap"),
                    ):
                        ui.icon(icon).classes("text-primary text-xl mt-1")
                        with ui.column().classes("gap-1"):
                            ui.label(
                                {
                                    "location_on": "Current conditions",
                                    "help_outline": "Causes and context",
                                    "gavel": "Policy and regulation",
                                    "health_and_safety": "Personal protection",
                                }[icon]
                            ).classes("text-xs font-medium uppercase tracking-wider text-primary")
                            ui.label(question).classes("text-sm font-medium leading-6")
                    prompt.on("click", lambda q=question: submit(q))

    def render_history() -> None:
        for message in state["messages"]:
            _render_chat_turn(transcript, message)

    if state["messages"]:
        render_history()
    else:
        render_starters()

    with ui.row().classes("napas-chat-column justify-end"):
        new_chat = ui.button("New chat", icon="add_comment").props("flat")

    busy = False

    def persist_chat() -> None:
        payload = json.dumps(chat_payload(state), ensure_ascii=False, separators=(",", ":"))
        client.run_javascript(
            f"sessionStorage.setItem({json.dumps(CHAT_STORAGE_KEY)}, {json.dumps(payload)});"
        )

    async def clear_current_chat() -> None:
        if busy:
            ui.notify("Please wait for the current answer to finish.", type="warning")
            return
        clear_conversation(state)
        client.run_javascript(f"sessionStorage.removeItem({json.dumps(CHAT_STORAGE_KEY)});")
        transcript.clear()
        render_starters()

    new_chat.on_click(clear_current_chat)

    async def submit(question: str | None = None) -> None:
        nonlocal busy
        if busy:
            return
        text = (question if question is not None else composer.value or "").strip()
        if not text:
            return
        busy = True
        composer.value = ""
        if not state["messages"]:
            transcript.clear()
        state["pending_question"] = text
        state["conversation"] = {"last_question": text}
        state["messages"].append({"role": "user", "content": text})
        _render_chat_turn(transcript, {"role": "user", "content": text})
        response, source_slot = _render_chat_turn(
            transcript,
            {
                "role": "assistant",
                "content": "_Searching observations and sources…_",
                "sources": [],
                "streaming": True,
            },
        )
        persist_chat()
        history = state["messages"][:-1]
        deltas: queue.Queue[str] = queue.Queue()
        lifecycle = ChatTurnLifecycle()

        def on_delta(value: str) -> None:
            deltas.put(value)

        send.disable()
        composer.disable()
        new_chat.disable()
        try:
            # A chat can remain open across several cron runs. Refresh just
            # before answering so its structured context is not the snapshot
            # that happened to be loaded when the page was first opened.
            refresh_runtime_measurements()
            task = asyncio.create_task(
                asyncio.to_thread(
                    answer,
                    text,
                    DOCUMENTS,
                    MEASUREMENTS,
                    "hybrid",
                    "rules",
                    state["language"],
                    history,
                    on_delta,
                )
            )
            while not task.done():
                while True:
                    try:
                        delta = deltas.get_nowait()
                    except queue.Empty:
                        break
                    lifecycle.append_stream(delta)
                if lifecycle.visible_text:
                    response.set_content(lifecycle.visible_text)
                await asyncio.sleep(0.04)
            result = await task
        except Exception:  # noqa: BLE001 - provider and connection errors vary
            lifecycle.fail("provider interruption")
            visible = lifecycle.visible_text or "The answer could not be completed. Please try again."
            response.set_content(f"{visible}\n\n_(Response interrupted; please retry.)_")
            state["messages"].append(
                {
                    "role": "assistant",
                    "content": visible,
                    "sources": [],
                    "meta": {"stream_policy": "error", "lifecycle": lifecycle.phase},
                }
            )
            persist_chat()
            return
        finally:
            busy = False
            state["pending_question"] = None
            send.enable()
            composer.enable()
            new_chat.enable()
        while True:
            try:
                lifecycle.append_stream(deltas.get_nowait())
            except queue.Empty:
                break
        canonical = result["answer"]
        try:
            lifecycle.finish(canonical)
        except RuntimeError:
            lifecycle.fail("provider completion changed visible answer")
            visible = lifecycle.visible_text or "The answer could not be completed. Please try again."
            response.set_content(f"{visible}\n\n_(Response changed before completion; please retry.)_")
            state["messages"].append(
                {
                    "role": "assistant",
                    "content": visible,
                    "sources": [],
                    "meta": {"stream_policy": "error", "lifecycle": lifecycle.phase},
                }
            )
            persist_chat()
            return
        response.set_content(linkify_citations(lifecycle.visible_text, result.get("sources", [])))
        _render_sources(result.get("sources", []), source_slot)
        state["messages"].append(
            {
                "role": "assistant",
                "content": lifecycle.visible_text,
                "sources": result.get("sources", []),
                "meta": {
                    "route": result.get("route"),
                    "citation_complete": result.get("citation_complete"),
                    "stream_policy": result.get("stream_policy"),
                    "lifecycle": lifecycle.phase,
                },
            }
        )
        state["conversation"] = {"last_route": result.get("route")}
        persist_chat()

    send = None
    composer = None
    with ui.column().classes("napas-chat-column napas-composer gap-2"):
        composer = (
            ui.textarea(placeholder="Ask about Jakarta air quality…")
            .props("outlined autogrow rows=2")
            .classes("w-full box-border")
        )
        with ui.row().classes("items-center w-full napas-composer-footer"):
            ui.label("Educational information only; not medical advice.").classes(
                "text-xs napas-muted"
            )
            ui.space()
            send = (
                ui.button("Send", icon="send")
                .props("unelevated color=primary")
                .classes("napas-rounded-control")
            )

    send.on_click(lambda: submit())
    composer.on("keydown.enter", lambda _: submit())

    async def hydrate_from_tab_storage() -> None:
        raw = await client.run_javascript(
            f"sessionStorage.getItem({json.dumps(CHAT_STORAGE_KEY)}) || '';"
        )
        try:
            payload = json.loads(raw) if raw else None
        except (TypeError, json.JSONDecodeError):
            payload = None
        restored = restore_chat_payload(state, payload)
        if restored["messages"]:
            transcript.clear()
            render_history()

    # A client timer waits for the websocket before reading browser storage,
    # while avoiding a route-build race where the page has not connected yet.
    ui.timer(0.05, hydrate_from_tab_storage, once=True)


def _render_map_page() -> None:
    _refresh_runtime_ui()
    _page_header(
        "Live map",
        "Explore the latest station snapshot with human-readable categories and freshness filters.",
    )
    rows = ROWS
    with ui.row().classes("w-full gap-3 flex-wrap"):
        _metric(
            "Stations reporting",
            str(sum(row["ispu"] is not None for row in rows)),
            "latest PM2.5 snapshot",
            "sensors",
        )
        observed = [row["ispu"] for row in rows if row["ispu"] is not None]
        _metric(
            "Highest ISPU",
            str(max(observed) if observed else "—"),
            "official unitless index",
            "trending_up",
        )
        _metric(
            "Network median",
            f"{sorted(observed)[len(observed) // 2] if observed else '—'}",
            "for relative context",
            "median",
        )
    selected_rows, filter_controls, update_filter_summary = _station_filter_toolbar(
        rows, "Station filters · map and table"
    )

    map_card = ui.card().classes("napas-card w-full p-0 overflow-hidden")
    with map_card:
        map_view = ui.leaflet(center=(-6.2, 106.82), zoom=9).classes("w-full h-[520px]")
    map_error = ui.label().classes("text-sm text-negative")
    if not rows:
        map_error.text = "No station data is available for this snapshot."
    elif not any(
        row.get("latitude") is not None and row.get("longitude") is not None for row in rows
    ):
        map_error.text = "No valid station coordinates are available; map markers cannot be shown."
    marker_layers = []
    pending_interactions: list[tuple[Any, dict[str, Any]]] = []

    def bind_or_queue(marker: Any, row: dict[str, Any]) -> None:
        if map_view.is_initialized:
            bind_station_marker_interactions(map_view, marker, row)
        else:
            pending_interactions.append((marker, row))

    def flush_pending_interactions(_: object = None) -> None:
        queued = pending_interactions.copy()
        pending_interactions.clear()
        for marker, row in queued:
            bind_station_marker_interactions(map_view, marker, row)

    # Leaflet's layer constructor intentionally returns a NullResponse before
    # client init. Binding on init guarantees initial markers receive commands.
    map_view.on("init", flush_pending_interactions)

    def refresh_markers() -> None:
        for layer in marker_layers:
            try:
                map_view.remove_layer(layer)
            except (ValueError, RuntimeError) as exc:
                map_error.text = f"Could not remove an existing station marker: {exc}"
                raise
        marker_layers.clear()
        pending_interactions.clear()
        map_error.text = ""
        if not rows:
            map_error.text = "No station data is available for this snapshot."
            return
        selected = selected_rows()
        if not selected:
            map_error.text = (
                "No stations match the selected filters. Try widening the district, category, "
                "or freshness filter."
            )
            return
        # The marker glyph itself carries the category color; the popup repeats
        # the text label so status never depends on color alone.
        valid_coordinates = 0
        for row in selected:
            if row.get("latitude") is None or row.get("longitude") is None:
                continue
            valid_coordinates += 1
            # CircleMarker uses Leaflet's native layer API and avoids the
            # fragile custom-icon serialization that previously blanked the map.
            marker = map_view.generic_layer(
                name="circleMarker",
                args=[
                    {"lat": row["latitude"], "lng": row["longitude"]},
                    station_marker_options(row),
                ],
            )
            try:
                bind_or_queue(marker, row)
            except (AttributeError, TypeError, ValueError, RuntimeError) as exc:
                map_error.text = f"Could not bind interactions for {row['station']}: {exc}"
                raise
            marker_layers.append(marker)
        if valid_coordinates == 0:
            map_error.text = "No valid station coordinates are available for the selected filters."

    with ui.row().classes("gap-5 flex-wrap text-sm"):
        for label, color in (
            ("Good", TOKENS["good"]),
            ("Moderate", TOKENS["moderate"]),
            ("Unhealthy", TOKENS["unhealthy"]),
            ("Very unhealthy", TOKENS["very_unhealthy"]),
            ("Hazardous", TOKENS["hazardous"]),
            ("No observation", TOKENS["missing"]),
        ):
            ui.html(
                f'<span><span class="napas-legend-dot" style="background:{color}"></span>{label}</span>'
            )
    ui.label(
        "Categories are official ISPU bands. Relative comparison uses the network median; green does not automatically mean safe."
    ).classes("text-sm napas-muted")
    with ui.card().classes("napas-card w-full p-0"):
        with ui.element("div").classes("napas-table-wrap w-full"):
            table = (
                ui.table(
                    columns=[
                        {"name": "no", "label": "No.", "field": "no", "sortable": True},
                        {
                            "name": "station",
                            "label": "Station",
                            "field": "station",
                            "sortable": True,
                        },
                        {
                            "name": "district",
                            "label": "District",
                            "field": "district",
                            "sortable": True,
                        },
                        {"name": "ispu", "label": "ISPU", "field": "ispu", "sortable": True},
                        {
                            "name": "category",
                            "label": "Category",
                            "field": "category",
                            "sortable": True,
                        },
                        {"name": "observed", "label": "Observed", "field": "observed"},
                    ],
                    rows=[],
                    pagination=20,
                )
                .props("flat bordered separator=horizontal")
                .classes("w-full")
            )

        def filtered() -> list[dict]:
            output = []
            for index, row in enumerate(rows, 1):
                if row not in selected_rows():
                    continue
                output.append(
                    {
                        "no": index,
                        "station": row["station"],
                        "district": row["district"],
                        "ispu": row["ispu"] if row["ispu"] is not None else "—",
                        "category": row["category"],
                        "observed": _time(row["observed_at"]),
                    }
                )
            return output

        table.rows = filtered()
        table.update()

        def refresh(_: object = None) -> None:
            table.rows = filtered()
            table.update()
            update_filter_summary()
            refresh_markers()

        for control in filter_controls:
            control.on_value_change(refresh)
        refresh_markers()


def _render_overview_page() -> None:
    _refresh_runtime_ui()
    _page_header(
        "Current overview",
        "A readable network summary with category distribution, district comparison, and every station.",
    )
    rows = ROWS
    observed_rows = [row for row in rows if row["ispu"] is not None]
    values = [row["ispu"] for row in observed_rows]
    with ui.row().classes("w-full gap-3 flex-wrap"):
        _metric("Stations observed", str(len(observed_rows)), "of all mapped stations", "sensors")
        _metric(
            "Highest current ISPU",
            str(max(values) if values else "—"),
            "highest loaded station",
            "trending_up",
        )
        _metric(
            "Network median ISPU",
            str(sorted(values)[len(values) // 2] if values else "—"),
            "middle station value",
            "median",
        )
        _metric(
            "Moderate or better",
            str(sum(_category(row["category"]) in {"Good", "Moderate"} for row in rows)),
            "stations in lower bands",
            "check_circle",
        )
    distribution = {}
    for row in observed_rows:
        distribution[row["category"]] = distribution.get(row["category"], 0) + 1
    district_values = {}
    for row in observed_rows:
        district_values.setdefault(row["district"], []).append(row["ispu"])
    with ui.row().classes("w-full gap-4 flex-wrap"):
        with ui.card().classes("napas-card flex-1 min-w-[320px] p-4"):
            ui.label("Stations by ISPU category").classes("text-lg font-semibold")
            ui.echart(
                {
                    "tooltip": {"trigger": "item"},
                    "xAxis": {"type": "category", "data": list(distribution)},
                    "yAxis": {"type": "value"},
                    "series": [
                        {
                            "type": "bar",
                            "data": [
                                {"value": v, "itemStyle": {"color": _status_color(k)}}
                                for k, v in distribution.items()
                            ],
                        }
                    ],
                }
            ).classes("w-full h-72")
        with ui.card().classes("napas-card flex-1 min-w-[320px] p-4"):
            ui.label("Median ISPU by district").classes("text-lg font-semibold")
            medians = {k: sorted(v)[len(v) // 2] for k, v in district_values.items()}
            ui.echart(
                {
                    "tooltip": {"trigger": "axis"},
                    "xAxis": {"type": "category", "data": list(medians)},
                    "yAxis": {"type": "value", "name": "ISPU"},
                    "series": [
                        {
                            "type": "bar",
                            "data": list(medians.values()),
                            "itemStyle": {"color": TOKENS["primary"]},
                        }
                    ],
                }
            ).classes("w-full h-72")
    _station_table(rows, title="All stations", top20=False)


def _station_table(rows: list[dict], title: str, top20: bool = False) -> None:
    if top20:
        rows = sorted(rows, key=lambda row: row["ispu"] or -1, reverse=True)[:20]
    ui.label(title).classes("text-xl font-semibold")
    selected_rows, filter_controls, update_filter_summary = _station_filter_toolbar(
        rows, "Station filters · table"
    )
    with ui.element("div").classes("napas-table-wrap w-full"):
        table = (
            ui.table(
                columns=[
                    {"name": "no", "label": "No.", "field": "no", "sortable": True},
                    {"name": "station", "label": "Station", "field": "station", "sortable": True},
                    {
                        "name": "district",
                        "label": "District",
                        "field": "district",
                        "sortable": True,
                    },
                    {"name": "ispu", "label": "ISPU", "field": "ispu", "sortable": True},
                    {
                        "name": "category",
                        "label": "Category",
                        "field": "category",
                        "sortable": True,
                    },
                    {"name": "pm25", "label": "PM2.5 (µg/m³)", "field": "pm25"},
                    {"name": "observed", "label": "Observed (WIB)", "field": "observed"},
                ],
                rows=[],
                pagination=20,
            )
            .props("flat bordered separator=horizontal")
            .classes("w-full")
        )

    def filtered() -> list[dict]:
        selected = selected_rows()
        return [
            {
                "no": index + 1,
                "station": row["station"],
                "district": row["district"],
                "ispu": row["ispu"] if row["ispu"] is not None else "—",
                "category": row["category"],
                "pm25": "—" if row.get("concentration") is None else f"{row['concentration']:.1f}",
                "observed": _time(row.get("observed_at")),
            }
            for index, row in enumerate(selected)
        ]

    table.rows = filtered()
    table.update()

    def refresh(_: object = None) -> None:
        table.rows = filtered()
        table.update()
        update_filter_summary()

    for control in filter_controls:
        control.on_value_change(refresh)


def _date_field(label: str, value: str):
    """Return a compact, labelled date field backed by Quasar's date picker."""
    field = ui.input(label, value=value).props("outlined dense readonly").classes("w-48")
    with field.add_slot("append"):
        trigger = ui.icon("event").classes("cursor-pointer")
        with ui.menu() as menu:
            ui.date(value=value).bind_value(field)
        trigger.on("click", menu.open)
    return field


def build_historical_series(rows: list[dict], pollutant: str) -> list[dict]:
    """Build independently sourced, visibly distinct pollutant series."""
    series = []
    if pollutant in {"PM2.5", "Both"}:
        series.append(
            {
                "name": "PM2.5 (µg/m³)",
                "type": "line",
                "showSymbol": False,
                "itemStyle": {"color": "#086B68"},
                "lineStyle": {"width": 2},
                "data": [[str(r["date"]), r["pm2_5"]] for r in rows if r.get("pm2_5") is not None],
            }
        )
    if pollutant in {"PM10", "Both"}:
        series.append(
            {
                "name": "PM10 (µg/m³)",
                "type": "line",
                "showSymbol": False,
                "itemStyle": {"color": "#D66A00"},
                "lineStyle": {"width": 2, "type": "dashed"},
                "data": [[str(r["date"]), r["pm10"]] for r in rows if r.get("pm10") is not None],
            }
        )
    return series


HISTORICAL_TOOLTIP_FORMATTER = """function (params) {
    const lines = [params[0]?.axisValueLabel || params[0]?.axisValue || ''];
    let pm25 = null;
    let pm10 = null;
    params.forEach((point) => {
        const value = Array.isArray(point.value) ? point.value[1] : point.value;
        lines.push(`${point.marker}${point.seriesName}: ${Number(value).toFixed(1)} µg/m³`);
        if (point.seriesName.startsWith('PM2.5')) pm25 = Number(value);
        if (point.seriesName.startsWith('PM10')) pm10 = Number(value);
    });
    if (pm25 !== null && pm10 !== null) {
        lines.push(`PM10 − PM2.5: ${(pm10 - pm25).toFixed(1)} µg/m³`);
    }
    return lines.join('<br/>');
}"""


def _render_trends_page() -> None:
    _refresh_runtime_ui()
    _page_header(
        "Trends",
        "Inspect up to one year of city-level PM2.5 and PM10 context with explicit dates and units.",
    )
    if not HISTORICAL:
        ui.notify("No historical series is available", type="warning")
        return
    latest = max(row["date"] for row in HISTORICAL)
    earliest = max(min(row["date"] for row in HISTORICAL), latest - timedelta(days=365))
    with ui.row().classes("items-end gap-3 w-full flex-wrap"):
        start = _date_field("Start date", earliest.isoformat())
        end = _date_field("End date", latest.isoformat())
        pollutant_options = []
        if HISTORICAL_META["pm25_available"]:
            pollutant_options.append("PM2.5")
        if HISTORICAL_META["pm10_available"]:
            pollutant_options.append("PM10")
        if len(pollutant_options) == 2:
            pollutant_options.append("Both")
        if not pollutant_options:
            ui.label("No pollutant series is available from this source.").classes("text-warning")
            return
        pollutant = ui.select(
            pollutant_options,
            value="Both" if "Both" in pollutant_options else pollutant_options[0],
            label="Pollutant",
        ).classes("w-40")
    chart = ui.echart({}).classes("napas-card w-full h-[420px] p-3")
    summary = ui.label().classes("text-sm napas-muted")

    def update() -> None:
        try:
            start_date, end_date = (
                date.fromisoformat(str(start.value)),
                date.fromisoformat(str(end.value)),
            )
        except ValueError:
            return
        selected = [row for row in HISTORICAL if start_date <= row["date"] <= end_date]
        series = build_historical_series(selected, pollutant.value)
        chart.options.clear()
        chart.options.update(
            {
                "tooltip": {"trigger": "axis", ":formatter": HISTORICAL_TOOLTIP_FORMATTER},
                "legend": {"data": [s["name"] for s in series]},
                "xAxis": {"type": "time"},
                "yAxis": {"type": "value", "name": "µg/m³"},
                "dataZoom": [{"type": "inside"}, {"type": "slider"}],
                "series": series,
            }
        )
        chart.update()
        summaries = []
        for item in series:
            values = [point[1] for point in item["data"]]
            if values:
                summaries.append(
                    f"{item['name'].split(' (', 1)[0]} median {sorted(values)[len(values) // 2]:.1f} µg/m³"
                )
        summary.text = (
            f"{len(selected)} available days · "
            + " · ".join(summaries)
            + f" · source: {selected[0]['source'] if selected else 'none'} · city model history, not official station observations"
        )

    start.on_value_change(lambda _: update())
    end.on_value_change(lambda _: update())
    pollutant.on_value_change(lambda _: update())
    update()
    with ui.expansion("Definitions and methodology", icon="info").classes("w-full"):
        ui.label(
            "PM2.5 and PM10 are concentrations in micrograms per cubic metre. The historical series is a city-level model context and should not be read as a station measurement or a legal threshold."
        ).classes("text-sm leading-6")
        if not HISTORICAL_META["pm10_available"]:
            ui.label(
                "PM10 unavailable from this historical source; no PM10 values are derived from PM2.5."
            ).classes("text-sm text-warning")
        else:
            whole = HISTORICAL_DIAGNOSTICS["whole"]
            recent = HISTORICAL_DIAGNOSTICS["recent"]
            ui.label(
                "The two pollutant series are independently sourced, not copies. "
                f"Across {whole['paired_rows']:,} paired observations, "
                f"{whole['identical_paired_rows']:,} have exactly equal values; "
                f"overall Pearson correlation is {whole['pearson_correlation']:.3f} "
                f"and the median absolute gap is {whole['median_absolute_difference']:.2f} µg/m³. "
                f"In the latest {HISTORICAL_DIAGNOSTICS['recent_days']}-day refresh, "
                f"correlation is {recent['pearson_correlation']:.3f} with a "
                f"{recent['median_absolute_difference']:.2f} µg/m³ median gap, so recent "
                "visual overlap is plausible without indicating a duplicated series."
            ).classes("text-sm leading-6")

    continuity_gap = HISTORICAL_DIAGNOSTICS["continuity_gap"]
    if continuity_gap:
        before_source = continuity_gap["before_source"] or "the earlier source"
        after_source = continuity_gap["after_source"] or "the later source"
        ui.label(
            "Provenance continuity note: the historical sources have a "
            f"{continuity_gap['missing_days']}-day gap from "
            f"{continuity_gap['start'].isoformat()} through {continuity_gap['end'].isoformat()}. "
            f"{before_source} ends on {continuity_gap['before'].isoformat()}, and "
            f"{after_source} resumes on {continuity_gap['after'].isoformat()}; "
            "the chart does not interpolate those dates."
        ).classes("text-sm napas-muted")


def _monitoring_chart(title: str, subtitle: str, options: dict[str, Any], *, empty: bool = False):
    """Render one telemetry chart with a consistent empty state."""
    with ui.card().classes("napas-card flex-1 min-w-[320px] p-4"):
        ui.label(title).classes("text-lg font-semibold")
        ui.label(subtitle).classes("text-xs napas-muted")
        if empty:
            ui.label("No aggregate data in this window yet.").classes("text-sm napas-muted py-12")
        else:
            ui.echart(options).classes("w-full h-72")


def _render_monitoring_page() -> None:
    """Show privacy-preserving operational aggregates for the running service."""
    _page_header(
        "Service monitoring",
        "Aggregate health and usage signals for Napas Jakarta · Pemantauan layanan, tanpa teks pertanyaan.",
    )
    dashboard = load_dashboard(30)
    summary = dashboard["summary"]
    source_label = dashboard.get("source", "No data")
    ui.label(
        f"Last 30 days · {source_label}. Only counts, rates, timings, and costs are shown; user questions and comments are never displayed."
    ).classes("text-sm napas-muted")
    with ui.row().classes("w-full gap-3 flex-wrap"):
        _metric("Requests · Permintaan", f"{summary['requests']:,}", "completed answers", "forum")
        p50 = "—" if summary["p50_latency_ms"] is None else f"{summary['p50_latency_ms']:.0f} ms"
        p95 = "—" if summary["p95_latency_ms"] is None else f"{summary['p95_latency_ms']:.0f} ms"
        _metric("p50 latency", p50, f"p95 {p95}", "speed")
        citation = "—" if summary["citation_rate"] is None else f"{summary['citation_rate'] * 100:.1f}%"
        _metric("Citation-grounded", citation, "answers with a grounded citation", "verified")
        _metric(
            "Feedback · Umpan balik",
            f"{summary['feedback_total']:,}",
            f"{summary['feedback_positive']:,} helpful · {summary['feedback_negative']:,} needs work",
            "thumbs_up_down",
        )
        _metric(
            "Tokens / estimated cost",
            f"{summary['tokens']:,}",
            f"US${summary['estimated_cost_usd']:.4f}",
            "payments",
        )

    by_day = dashboard["requests_by_day"]
    _monitoring_chart(
        "Requests over time · Permintaan per hari",
        "Completed answer events, grouped by UTC calendar day.",
        {
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": [row["date"] for row in by_day]},
            "yAxis": {"type": "value", "minInterval": 1},
            "series": [{"name": "Requests", "type": "bar", "data": [row["requests"] for row in by_day], "itemStyle": {"color": TOKENS["primary"]}}],
        },
        empty=not by_day,
    )

    latency = dashboard["latency_by_day"]
    _monitoring_chart(
        "Latency · Latensi",
        "p50 is the typical response; p95 shows the slower tail. Values are milliseconds.",
        {
            "tooltip": {"trigger": "axis"},
            "legend": {"data": ["p50", "p95"]},
            "xAxis": {"type": "category", "data": [row["date"] for row in latency]},
            "yAxis": {"type": "value", "name": "ms"},
            "series": [
                {"name": "p50", "type": "line", "connectNulls": True, "data": [row["p50_ms"] for row in latency], "itemStyle": {"color": TOKENS["primary"]}},
                {"name": "p95", "type": "line", "connectNulls": True, "data": [row["p95_ms"] for row in latency], "itemStyle": {"color": TOKENS["unhealthy"]}},
            ],
        },
        empty=not latency,
    )

    route_rows = dashboard["routes"]
    _monitoring_chart(
        "Answer routes · Rute jawaban",
        "Which deterministic answer path handled each request.",
        {
            "tooltip": {"trigger": "item"},
            "legend": {"type": "scroll", "bottom": 0},
            "series": [{"type": "pie", "radius": ["38%", "70%"], "data": [{"name": row["name"], "value": row["count"]} for row in route_rows]}],
        },
        empty=not route_rows,
    )

    retrieval_rows = dashboard["retrieval_modes"]
    _monitoring_chart(
        "Retrieval modes · Mode pencarian",
        "Search strategy selected for evidence retrieval.",
        {
            "tooltip": {"trigger": "item"},
            "xAxis": {"type": "category", "data": [row["name"] for row in retrieval_rows]},
            "yAxis": {"type": "value", "minInterval": 1},
            "series": [{"type": "bar", "data": [row["count"] for row in retrieval_rows], "itemStyle": {"color": "#205C8A"}}],
        },
        empty=not retrieval_rows,
    )

    usage = dashboard["usage_by_day"]
    _monitoring_chart(
        "Tokens and estimated cost · Token dan biaya",
        "Provider-reported token totals and estimated USD cost by day.",
        {
            "tooltip": {"trigger": "axis"},
            "legend": {"data": ["Tokens", "Cost (USD)"]},
            "xAxis": {"type": "category", "data": [row["date"] for row in usage]},
            "yAxis": [{"type": "value", "name": "tokens"}, {"type": "value", "name": "USD"}],
            "series": [
                {"name": "Tokens", "type": "bar", "data": [row["tokens"] for row in usage], "itemStyle": {"color": "#6A1B9A"}},
                {"name": "Cost (USD)", "type": "line", "yAxisIndex": 1, "data": [row["cost_usd"] for row in usage], "itemStyle": {"color": TOKENS["moderate"]}},
            ],
        },
        empty=not usage,
    )

    feedback_rows = dashboard["feedback"]
    _monitoring_chart(
        "Feedback · Umpan balik",
        "Helpful versus needs-improvement signals; comments remain private.",
        {
            "tooltip": {"trigger": "axis"},
            "legend": {"data": ["Helpful", "Needs improvement"]},
            "xAxis": {"type": "category", "data": [row["date"] for row in feedback_rows]},
            "yAxis": {"type": "value", "minInterval": 1},
            "series": [
                {"name": "Helpful", "type": "bar", "stack": "feedback", "data": [row.get("positive", 0) for row in feedback_rows], "itemStyle": {"color": TOKENS["good"]}},
                {"name": "Needs improvement", "type": "bar", "stack": "feedback", "data": [row.get("negative", 0) for row in feedback_rows], "itemStyle": {"color": TOKENS["unhealthy"]}},
            ],
        },
        empty=not feedback_rows,
    )
    with ui.expansion("How to read this page · Cara membaca", icon="info").classes("w-full"):
        ui.label(
            "Requests count completed answer events, not unique people. p50/p95 describe response-time distribution. Citation-grounded means the answer passed the app's citation validation. Estimated cost depends on provider pricing and may be unavailable for local models. Small samples should not be treated as product benchmarks."
        ).classes("text-sm leading-6")


if ui is not None:

    @ui.page("/")
    def ask_page() -> None:
        _shell2("/", _chat_page)

    @ui.page("/map")
    def map_page() -> None:
        _shell2("/map", _render_map_page)

    @ui.page("/overview")
    def overview_page() -> None:
        _shell2("/overview", _render_overview_page)

    @ui.page("/trends")
    def trends_page() -> None:
        _shell2("/trends", _render_trends_page)

    @ui.page("/monitoring")
    def monitoring_page() -> None:
        _shell2("/monitoring", _render_monitoring_page)

    # NiceGUI adds its Vue/Quasar app to the existing FastAPI object.
    ui.run_with(
        api_app,
        mount_path="/",
        title="Napas Jakarta",
        favicon=ICON_PATH if ICON_PATH.exists() else "🌬️",
        language="en-US",
        storage_secret=os.getenv("NICEGUI_STORAGE_SECRET", "napas-jakarta-local"),
    )


app = api_app
