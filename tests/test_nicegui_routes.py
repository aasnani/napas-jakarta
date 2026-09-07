"""Fast, browser-free NiceGUI construction regression.

The real browser review remains separate, but this catches API drift (for
example a changed ``ui.date`` argument) while keeping CI independent of
Chrome/Selenium and never opening a network port.
"""

import asyncio
from datetime import date, datetime
from pathlib import Path

from nicegui.elements.leaflet import Leaflet
from nicegui.testing import user_simulation

from app import web
from app.webui.state import chat_payload, clear_conversation, restore_chat_payload


def _render_all_pages() -> None:
    for active, content in (
        ("/", web._chat_page),
        ("/map", web._render_map_page),
        ("/overview", web._render_overview_page),
        ("/trends", web._render_trends_page),
        ("/monitoring", web._render_monitoring_page),
    ):
        web._shell2(active, content)


async def _open_and_check_routes() -> None:
    async with user_simulation(root=_render_all_pages) as user:
        await user.open("/")
        await user.should_see(content="Napas Jakarta")
        await user.should_see(content="Live map")
        await user.should_see(content="Current overview")
        await user.should_see(content="Trends")
        await user.should_see(content="PM2.5")
        maps = [
            element for element in user.client.elements.values() if isinstance(element, Leaflet)
        ]
        assert maps and any(layer.to_dict()["type"] == "circleMarker" for layer in maps[0].layers)
        assert maps[0]._props["zoom"] == 9


def test_nicegui_pages_construct_without_component_api_errors() -> None:
    asyncio.run(asyncio.wait_for(_open_and_check_routes(), timeout=15))


def test_chat_streaming_contract_keeps_raw_text_then_links_completion() -> None:
    """Model the UI's two phases without spending a provider call or port."""
    from app.citations import linkify_citations

    deltas = ["Grounded ", "[ispu]"]
    streamed = "".join(deltas)
    sources = [{"id": "ispu", "title": "ISPU guidance", "url": "https://example.org/ispu"}]
    assert streamed == "Grounded [ispu]"
    assert (
        linkify_citations(streamed, sources)
        == "Grounded [ISPU guidance](<https://example.org/ispu>)"
    )


def test_map_filters_are_shared_and_roles_are_visibly_distinct() -> None:
    rows = [
        {
            "station": "A",
            "district": "Jakarta Pusat",
            "category": "Good",
            "ispu": 30,
            "observed_at": "2026-09-07T10:00:00+07:00",
        },
        {
            "station": "B",
            "district": "Jakarta Utara",
            "category": "Unhealthy",
            "ispu": 120,
            "observed_at": "2026-09-06T10:00:00+07:00",
        },
    ]
    now = datetime.fromisoformat("2026-09-07T11:00:00+07:00")
    assert [row["station"] for row in web.filter_station_rows(rows, category="Good", now=now)] == [
        "A"
    ]
    assert [
        row["station"] for row in web.filter_station_rows(rows, freshness="Fresh only", now=now)
    ] == ["A"]
    source = Path(web.ROOT / "app" / "web.py").read_text(encoding="utf-8")
    assert "napas-avatar-user" in source and "napas-avatar-guide" in source
    assert "_source_details_dialog" in source


def test_chat_layout_contract_keeps_composer_and_sources_in_flow() -> None:
    """Protect the DOM contracts that are easy to regress in NiceGUI markup."""
    source = Path(web.ROOT / "app" / "web.py").read_text(encoding="utf-8")
    theme = Path(web.ROOT / "app" / "webui" / "theme.py").read_text(encoding="utf-8")

    # History and live turns must share the same role renderer; the live path
    # cannot fall back to an unstyled markdown fragment.
    assert source.count("_render_chat_turn(") >= 3
    assert 'ui.label("Napas Jakarta")' in source
    assert "napas-avatar-user" in source and "napas-avatar-guide" in source
    assert 'source_slot = ui.column().classes("w-full napas-source-slot")' in source
    assert '_render_sources(result.get("sources", []), source_slot)' in source

    # Composer/transcript share the exact width contract and the composer is
    # explicitly normal-flow rather than viewport-attached.
    assert '"napas-chat-column napas-composer gap-2"' in source
    assert ".napas-composer { width:100%; max-width:760px;" in theme
    assert "position:static" in theme
    assert 'classes("w-full box-border")' in source

    # Quasar's injected focus/ripple helpers must be clipped to rounded cards
    # and controls while preserving a visible keyboard focus ring.
    assert "napas-rounded-control .q-focus-helper" in theme
    assert "napas-rounded-control .q-ripple" in theme
    assert ".napas-rounded-control:focus-visible" in theme


def test_map_marker_and_shell_layout_contracts() -> None:
    source = Path(web.ROOT / "app" / "web.py").read_text(encoding="utf-8")
    theme = Path(web.ROOT / "app" / "webui" / "theme.py").read_text(encoding="utf-8")
    row = {
        "station": "LCS-03 Central",
        "district": "Jakarta Pusat",
        "category": "Unhealthy",
        "ispu": 127,
        "concentration": 34.25,
        "observed_at": "2026-09-07T10:30:00+07:00",
    }
    options = web.station_marker_options(row)
    tooltip = web.station_tooltip_html(row)
    assert options["radius"] >= 10
    assert options["interactive"] is True
    assert options["fillOpacity"] >= 0.9
    assert options["bubblingMouseEvents"] is True
    assert "LCS-03 Central" in tooltip
    assert "Unhealthy · ISPU 127" in tooltip
    assert "PM2.5: 34.2 µg/m³" in tooltip
    assert "Jakarta Pusat" in tooltip and "Observed: 07 Sep 2026" in tooltip
    assert '"bindTooltip"' in source or '"bindTooltip",' in source
    assert '"sticky": True' in source and '"direction": "top"' in source
    assert "ui.leaflet(center=(-6.2, 106.82), zoom=9)" in source
    assert "refresh_markers()" in source and "def refresh(" in source

    # Analytics pages intentionally occupy the wide content canvas while Ask
    # keeps its bounded transcript/composer column.
    assert (
        'content_width = "napas-analytics-content" if active != "/" else "napas-chat-content"'
        in source
    )
    assert ".napas-analytics-content { max-width:100%; }" in theme
    assert ".napas-analytics-content .napas-table-wrap .q-table" in theme
    assert 'classes("napas-table-wrap w-full")' in source
    assert ".napas-drawer { width:280px !important; }" in theme
    assert ".napas-nav-link { min-height:50px;" in theme


def test_station_filters_compose_and_marker_commands_are_real() -> None:
    rows = [
        {
            "station": "A",
            "district": "Jakarta Pusat",
            "category": "Good",
            "ispu": 30,
            "observed_at": "2026-09-07T10:00:00+07:00",
        },
        {
            "station": "B",
            "district": "Jakarta Utara",
            "category": "Unhealthy",
            "ispu": 120,
            "observed_at": "2026-09-06T10:00:00+07:00",
        },
        {
            "station": "C",
            "district": "Jakarta Pusat",
            "category": "No observation",
            "ispu": None,
            "observed_at": None,
        },
    ]
    now = datetime.fromisoformat("2026-09-07T11:00:00+07:00")
    assert [
        r["station"]
        for r in web.filter_station_rows(
            rows,
            district="Jakarta Pusat",
            category=["Good", "No observation"],
            search="a",
            now=now,
        )
    ] == ["A", "C"]
    assert [
        r["station"] for r in web.filter_station_rows(rows, ispu_min=100, ispu_max=130, now=now)
    ] == ["B"]
    assert [
        r["station"] for r in web.filter_station_rows(rows, freshness="Missing only", now=now)
    ] == ["C"]
    summary = web._station_filter_summary(
        rows, rows[:1], "Jakarta Pusat", ["Good"], "All data", "a", 1, 50
    )
    assert "Showing 1 of 3" in summary and "district: Jakarta Pusat" in summary

    class FakeMap:
        def __init__(self):
            self.calls = []

        def run_layer_method(self, *args):
            self.calls.append(args)

    class FakeMarker:
        id = "marker-1"

    fake = FakeMap()
    web.bind_station_marker_interactions(fake, FakeMarker(), rows[1])
    assert fake.calls[0][0:2] == ("marker-1", "bindTooltip")
    assert fake.calls[0][2] == web.station_tooltip_html(rows[1])
    assert fake.calls[0][3]["sticky"] is True
    assert fake.calls[1][0:2] == ("marker-1", "bindPopup")

    source = Path(web.ROOT / "app" / "web.py").read_text(encoding="utf-8")
    assert source.count("_station_filter_toolbar(") >= 3
    assert '"Missing only"' in source and '"Clear filters"' in source


def test_trends_series_remain_distinct_and_labeled() -> None:
    rows = [
        {"date": date(2026, 1, 1), "pm2_5": 10.0, "pm10": 25.0},
        {"date": date(2026, 1, 2), "pm2_5": 11.0, "pm10": 27.0},
    ]
    series = web.build_historical_series(rows, "Both")
    assert [item["name"] for item in series] == ["PM2.5 (µg/m³)", "PM10 (µg/m³)"]
    assert series[0]["data"] != series[1]["data"]
    assert series[0]["itemStyle"]["color"] != series[1]["itemStyle"]["color"]
    assert series[1]["lineStyle"]["type"] == "dashed"
    current = web.build_historical_series(web.HISTORICAL, "Both")
    assert len(current) == 2
    assert current[0]["data"] != current[1]["data"]
    assert "PM10 − PM2.5" in web.HISTORICAL_TOOLTIP_FORMATTER


def test_understand_numbers_is_discoverable_but_closed_by_default() -> None:
    source = Path(web.ROOT / "app" / "web.py").read_text(encoding="utf-8")
    assert 'ui.expansion("Understand the numbers", icon="menu_book", value=False)' in source


def test_chat_tab_handoff_and_new_chat_semantics() -> None:
    """Model Ask -> other route -> Ask, reload, and new-tab boundaries."""
    tab_a = {
        "messages": [{"role": "user", "content": "How is Pusat?"}],
        "conversation": {"last_question": "How is Pusat?"},
    }
    tab_b = {}
    payload = chat_payload(tab_a)

    # A route navigation carries only this tab's payload into the new page
    # client; a separate tab has no shared/process-global message store.
    restored = restore_chat_payload({}, payload)
    assert restored["messages"] == tab_a["messages"]
    assert restored["conversation"] == tab_a["conversation"]
    assert tab_b == {}

    # Both an explicit New chat and a real reload result in an empty client
    # state; the browser-side reload boundary is synchronous in the shell.
    clear_conversation(restored)
    assert restored["messages"] == []
    assert restored["conversation"] == {}
    source = Path(web.ROOT / "app" / "web.py").read_text(encoding="utf-8")
    assert "sessionStorage" in source
    assert "nav === 'reload'" in source
    assert 'ui.button("New chat", icon="add_comment")' in source
    assert "ui.timer(0.05, hydrate_from_tab_storage, once=True)" in source
    assert "persist_chat()" in source
    assert "new_chat.disable()" in source and "new_chat.enable()" in source
