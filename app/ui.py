from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.citations import linkify_citations
from app.config import selected_retrieval_mode
from app.history import load_historical_city
from app.provider import selected_prompt_version
from app.rag import answer, load_runtime_state
from app.stations import display_district_name, display_station_name, load_runtime_stations
from app.tools import get_latest_measurements, latest_data_age_seconds
from monitoring.logging import log_feedback, log_interaction

JAKARTA_TZ = ZoneInfo("Asia/Jakarta")
ICON_PATH = PROJECT_ROOT / "assets" / "napas-jakarta-air-icon.png"


def _human_category(value: object) -> str:
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
        "NO OBSERVATION": "No observation",
    }
    text = str(value or "").strip()
    return labels.get(text.upper(), text.title() if text else "No observation")


def _friendly_timestamp(value: object) -> str:
    if value is None or str(value).strip() in {"", "NaT", "None"}:
        return "No observation"
    try:
        parsed = datetime.fromisoformat(str(value))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=JAKARTA_TZ)
        return parsed.astimezone(JAKARTA_TZ).strftime("%d %b %Y, %H:%M WIB")
    except (TypeError, ValueError):
        return str(value)


def _friendly_source(value: object) -> str:
    source = str(value or "").strip()
    if not source:
        return "No source recorded"
    if source.startswith(("http://", "https://")):
        if "udara.jakarta.go.id" in source:
            return "Official Jakarta monitoring"
        return source.split("//", 1)[-1].split("/", 1)[0]
    if source.lower().startswith("udara jakarta demo"):
        return "Demo snapshot"
    return source


def _inject_styles(st) -> None:
    st.markdown(
        """
        <style>
        :root { --napas-ink:#153047; --napas-teal:#087f8c; --napas-mint:#e8f7f5; }
        .napas-hero { border:1px solid #d5e9e9; border-radius:18px; padding:1rem 1.25rem;
          background:linear-gradient(120deg,#effafa 0%,#ffffff 58%,#fff7ed 100%);
          margin:.25rem 0 1rem; animation:napas-fade .45s ease-out; }
        .napas-hero h2 { color:var(--napas-ink); margin:0 0 .25rem; }
        .napas-hero p { color:#486273; margin:0; }
        [data-testid="stChatMessage"] { border-radius:16px; animation:napas-fade .3s ease-out; }
        [data-testid="stChatInput"] { border-color:#89c8c9; box-shadow:0 4px 18px rgba(8,127,140,.12); }
        @keyframes napas-fade { from { opacity:0; transform:translateY(4px); }
          to { opacity:1; transform:translateY(0); } }
        @media (prefers-reduced-motion: reduce) { *, *::before, *::after {
          animation-duration:.01ms !important; animation-iteration-count:1 !important; } }
        @media (max-width: 700px) { .napas-hero { padding:.8rem; } }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_terms(st, language: str) -> None:
    title = "Air-quality terms" if language == "English" else "Istilah kualitas udara"
    with st.expander(f"{title} · PM2.5, PM10, ISPU and more"):
        if language == "English":
            st.markdown(
                "- **PM2.5**: fine particles no wider than 2.5 micrometres; they can travel deep into the lungs.\n"
                "- **PM10**: particles no wider than 10 micrometres. PM2.5 is a smaller subset of PM10.\n"
                "- **ISPU**: Indonesia's unitless air-pollution index; it is not a concentration.\n"
                "- **µg/m³**: micrograms per cubic metre, the unit used for pollutant concentration.\n"
                "- **Station**: a monitoring location; **stale/missing** means the observation is old or unavailable.\n"
                "- **Network median**: the middle ISPU value across loaded stations, used only for comparison."
            )
        else:
            st.markdown(
                "- **PM2.5**: partikel halus berdiameter hingga 2,5 mikrometer yang dapat masuk jauh ke paru-paru.\n"
                "- **PM10**: partikel berdiameter hingga 10 mikrometer; PM2.5 adalah bagian yang lebih kecil.\n"
                "- **ISPU**: indeks pencemaran udara Indonesia tanpa satuan, bukan konsentrasi.\n"
                "- **µg/m³**: mikrogram per meter kubik, satuan konsentrasi polutan.\n"
                "- **Stasiun**: lokasi pemantauan; **usang/tidak tersedia** berarti data lama atau tidak ada.\n"
                "- **Median jaringan**: nilai ISPU tengah semua stasiun yang dimuat, hanya untuk perbandingan."
            )


def _render_assistant_details(st, message: dict, language: str) -> None:
    meta = message.get("meta") or {}
    interaction_id = meta.get("interaction_id")
    if not interaction_id:
        return
    positive, negative = st.columns(2)
    if positive.button("Helpful", key=f"positive-{interaction_id}"):
        log_feedback(interaction_id, "positive")
    if negative.button("Needs improvement", key=f"negative-{interaction_id}"):
        log_feedback(interaction_id, "negative")
    with st.expander("Sources and retrieval details"):
        st.json(
            {
                "rewritten_query": meta.get("rewritten_query"),
                "route": meta.get("route"),
                "retrieval_mode": meta.get("retrieval_mode"),
                "sources": meta.get("sources", []),
                "citation_complete": meta.get("citation_complete"),
                "source_mode": meta.get("source_mode"),
                "data_age_seconds": meta.get("data_age_seconds"),
                "generation_usage": meta.get("generation_usage", {}),
            }
        )
    with st.expander("Process and provenance"):
        st.write(
            {
                "stages": [
                    "observations checked",
                    "Jakarta evidence searched",
                    "citations validated",
                ],
                "route": meta.get("route"),
                "tools": meta.get("tools", []),
                "prompt_version": selected_prompt_version(),
                "language": language,
                "conversation_turn": meta.get("conversation_turn"),
            }
        )
    ungrounded = meta.get("ungrounded_citations", [])
    if ungrounded:
        st.warning("Possible ungrounded citations: " + ", ".join(ungrounded))


def _render_chat_message(st, message: dict, language: str) -> None:
    role = message.get("role", "assistant")
    # Keep the product mark out of chat avatars; the page header owns branding.
    with st.chat_message(role):
        content = message.get("content", "")
        # Canonical answer text remains unchanged in session state/history;
        # only the rendered presentation gets resolved source hyperlinks.
        st.markdown(linkify_citations(content, (message.get("meta") or {}).get("sources", [])))
        if role == "assistant":
            _render_assistant_details(st, message, language)


def _render_near_bottom_controller(st) -> None:
    """Follow growth only when the reader was already near the document end."""
    st.iframe(
        """
        <script>
        (() => {
          const root = window.parent;
          if (root.__napasNearBottomController) return;
          const state = {following: false, active: true};
          root.__napasNearBottomController = state;
          const threshold = 160;
          const nearBottom = () =>
            root.scrollY + root.innerHeight >= root.document.documentElement.scrollHeight - threshold;
          const update = () => { state.following = nearBottom(); };
          root.addEventListener('scroll', update, {passive: true});
          update();
          const observer = new root.MutationObserver(() => {
            if (!state.active || !state.following) return;
            root.requestAnimationFrame(() => {
              if (state.active && state.following) {
                root.scrollTo(0, root.document.documentElement.scrollHeight);
              }
            });
          });
          observer.observe(root.document.body, {childList: true, subtree: true, characterData: true});
          state.stop = () => {
            state.active = false;
            observer.disconnect();
            root.removeEventListener('scroll', update);
            delete root.__napasNearBottomController;
          };
        })();
        </script>
        """,
        height=1,
        tab_index=-1,
    )


def _stop_near_bottom_controller(st) -> None:
    st.iframe(
        """
        <script>
        (() => {
          const controller = window.parent.__napasNearBottomController;
          if (controller && controller.stop) controller.stop();
        })();
        </script>
        """,
        height=1,
        tab_index=-1,
    )


def _stream_pending_question(st, pending: dict, documents, measurements, language: str) -> None:
    started = perf_counter()
    question = pending["question"]
    history = st.session_state.messages
    source_mode = pending["source_mode"]
    streamed_parts: list[str] = []
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        response_placeholder.caption("Searching observations and sources…")
        _render_near_bottom_controller(st)

        def on_delta(text: str) -> None:
            streamed_parts.append(text)
            response_placeholder.markdown("".join(streamed_parts))

        result = answer(
            question,
            documents,
            measurements,
            retrieval_mode=selected_retrieval_mode(),
            language=language,
            history=history,
            on_delta=on_delta,
        )
        _stop_near_bottom_controller(st)
        final_text = result["answer"]
        # Offline/provider-failure answers arrive buffered. Keep that fallback
        # explicit and never present it as provider streaming.
        if not streamed_parts or "".join(streamed_parts) != final_text:
            response_placeholder.markdown(linkify_citations(final_text, result.get("sources", [])))
        else:
            # Replace the raw streaming text in the same placeholder after the
            # provider has completed, so citations become usable links.
            response_placeholder.markdown(linkify_citations(final_text, result.get("sources", [])))
    interaction_id = log_interaction(
        {
            "event": "answer",
            "session_id": st.session_state.session_id,
            "question": question,
            "rewritten_query": result["rewritten_query"],
            "route": result["route"],
            "retrieval_mode": result["retrieval_mode"],
            "citation_grounded": result["citation_grounded"],
            "citation_complete": result["citation_complete"],
            "prompt_version": selected_prompt_version(),
            "latency_ms": round((perf_counter() - started) * 1000, 2),
            "data_age_seconds": result["data_age_seconds"],
            "abstention_type": (
                "safety"
                if result["route"] == "safety_abstention"
                else "out_of_domain"
                if result["route"] == "out_of_domain"
                else None
            ),
            "source": source_mode,
            "conversation_turn": len(history) // 2,
            "history_messages": len(history),
            "history_summary_chars": len(
                (
                    " ".join(
                        item.get("content", "")
                        for item in history[:-6]
                        if item.get("role") == "user"
                    )
                )[:1200]
            ),
            "provider_model": result.get("generation_usage", {}).get(
                "model", os.getenv("LLM_MODEL", "")
            ),
            "token_usage": result.get("generation_usage", {}).get("total_tokens"),
            "estimated_cost": result.get("generation_usage", {}).get("estimated_cost_usd"),
            "carried_entities": json.dumps(
                result.get("conversation_state", {}), ensure_ascii=False
            ),
            "source_count": len(result.get("sources", [])),
        }
    )
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "meta": {
                "interaction_id": interaction_id,
                "rewritten_query": result["rewritten_query"],
                "route": result["route"],
                "retrieval_mode": result["retrieval_mode"],
                "sources": result["sources"],
                "citation_complete": result["citation_complete"],
                "source_mode": source_mode,
                "data_age_seconds": result["data_age_seconds"],
                "ungrounded_citations": result["ungrounded_citations"],
                "tools": ["deterministic measurement summary"]
                if result["measurement_context"]
                else [],
                "conversation_turn": len(history) // 2,
                "generation_usage": result.get("generation_usage", {}),
            },
        }
    )
    st.session_state.pop("pending_prompt", None)
    _render_assistant_details(st, st.session_state.messages[-1], language)


def _render_chat(st, documents, measurements, language: str, source_mode: str) -> None:
    st.markdown(
        "<div class='napas-hero'><h2>Ask Napas Jakarta</h2>"
        "<p>Explore current observations, causes, policy, and practical ways to reduce exposure.</p></div>",
        unsafe_allow_html=True,
    )
    if st.button("New conversation", key="new-conversation"):
        st.session_state.messages = []
        st.session_state.pop("pending_prompt", None)
        st.rerun()
    pending = st.session_state.get("pending_prompt")
    if pending is None:
        queued = st.session_state.pop("queued_question", None)
        if queued:
            st.session_state.messages.append({"role": "user", "content": queued})
            st.session_state.pending_prompt = {"question": queued, "source_mode": source_mode}
            st.rerun()
    if not st.session_state.messages:
        st.caption("Try a starter question")
        starters = (
            [
                "What is the current air quality in Jakarta Pusat?",
                "What causes Jakarta's PM2.5 pollution?",
                "How can I protect myself on a bad-air day?",
            ]
            if language == "English"
            else [
                "Bagaimana kualitas udara Jakarta Pusat saat ini?",
                "Apa penyebab polusi PM2.5 Jakarta?",
                "Bagaimana melindungi diri saat udara buruk?",
            ]
        )
        columns = st.columns(len(starters))
        for index, starter in enumerate(starters):
            if columns[index].button(starter, key=f"starter-{index}"):
                st.session_state.queued_question = starter
                st.rerun()
    for message in st.session_state.messages:
        _render_chat_message(st, message, language)
    pending = st.session_state.get("pending_prompt")
    if pending is not None:
        _stream_pending_question(st, pending, documents, measurements, language)
    st.info("Educational information only; this is not medical advice.")
    placeholder = (
        "Ask about Jakarta air quality"
        if language == "English"
        else "Tanyakan kualitas udara Jakarta"
    )
    with st.container():
        question = st.chat_input(placeholder)
    if question and st.session_state.get("pending_prompt") is None:
        st.session_state.messages.append({"role": "user", "content": question})
        st.session_state.pending_prompt = {"question": question, "source_mode": source_mode}
        st.rerun()


def _build_map_rows(stations: list[dict], latest_rows: list[dict]) -> list[dict]:
    station_lookup = {row["station_id"]: row for row in latest_rows}
    map_rows = []
    for station in stations:
        row = station_lookup.get(station.get("station_id"))
        raw_station = station.get("station") or (row or {}).get("station") or ""
        raw_district = station.get("district") or (row or {}).get("district") or ""
        values = {
            "station": display_station_name(raw_station),
            "station_raw": raw_station,
            "district": display_district_name(raw_district),
            "district_raw": raw_district,
        }
        if row:
            values.update(
                {
                    "ispu": row["ispu"],
                    "category": row["category"],
                    "observed_at": row["observed_at"],
                    "concentration": row["concentration"],
                    "source": row["source"],
                }
            )
        else:
            values.update(
                {
                    "ispu": None,
                    "category": "No observation",
                    "observed_at": None,
                    "concentration": None,
                    "source": "",
                }
            )
        map_rows.append({**station, **values})
    return map_rows


def _render_map(st, map_rows: list[dict], source_url: str, pd) -> None:
    st.subheader("Live map")
    if source_url and len(map_rows) <= 5:
        st.warning(
            "Official station coordinates could not be loaded; showing the demo coordinate set. Measurements remain sourced separately."
        )
    elif source_url:
        st.caption(f"Official coordinate snapshot · {len(map_rows)} mapped stations")
    else:
        st.caption(
            "Approximate demo coordinates; configure SOURCE_DATA_URL for official station metadata."
        )
    map_frame = pd.DataFrame(map_rows)
    if map_frame.empty:
        st.info("No station coordinates are loaded.")
        return
    map_frame["category"] = map_frame["category"].map(_human_category)
    observed_times = pd.to_datetime(map_frame["observed_at"], errors="coerce")
    newest = observed_times.max()
    counts = map_frame["category"].value_counts()
    distribution = " · ".join(
        f"{label}: {int(counts.get(label, 0))}"
        for label in (
            "Good",
            "Moderate",
            "Unhealthy",
            "Very unhealthy",
            "Hazardous",
            "No observation",
        )
        if counts.get(label, 0)
    )
    newest_label = _friendly_timestamp(newest.isoformat()) if pd.notna(newest) else "No observation"
    st.info(
        f"Map snapshot: newest loaded observation **{newest_label}** · {len(map_frame)} stations · {distribution or 'no categories'}"
    )
    st.caption(
        "Official categories come directly from the loaded feed. A Good/Moderate map describes this snapshot, not a live guarantee; stale or missing stations are shown separately."
    )
    filter_a, filter_b, filter_c, filter_d = st.columns(4)
    districts = ["All districts"] + sorted(map_frame["district"].dropna().unique().tolist())
    categories = ["All categories"] + sorted(map_frame["category"].dropna().unique().tolist())
    with filter_a:
        district_filter = st.selectbox("District", districts, key="map-district")
    with filter_b:
        category_filter = st.selectbox("Health category", categories, key="map-category")
    with filter_c:
        freshness_filter = st.selectbox(
            "Data freshness", ["All data", "Fresh only", "Stale or missing"], key="map-freshness"
        )
    with filter_d:
        color_mode = st.selectbox(
            "Color meaning",
            ["Health category", "Compared with network median"],
            key="map-color-mode",
        )
    visible = map_frame.copy()
    if district_filter != "All districts":
        visible = visible[visible["district"] == district_filter]
    if category_filter != "All categories":
        visible = visible[visible["category"] == category_filter]
    if freshness_filter != "All data":
        now = pd.Timestamp.now(tz="Asia/Jakarta")
        ages = (now - pd.to_datetime(visible["observed_at"], errors="coerce")).dt.total_seconds()
        visible = visible[
            (ages <= 3 * 3600)
            if freshness_filter == "Fresh only"
            else (ages > 3 * 3600) | ages.isna()
        ]
    st.caption(f"Showing {len(visible)} of {len(map_frame)} stations")
    category_colors = {
        "Good": [46, 125, 50, 210],
        "Moderate": [251, 192, 45, 220],
        "Unhealthy": [239, 108, 44, 225],
        "Very unhealthy": [198, 40, 40, 230],
        "Hazardous": [106, 27, 154, 235],
        "No observation": [120, 120, 120, 180],
    }
    if color_mode == "Compared with network median" and visible["ispu"].notna().any():
        baseline = float(map_frame["ispu"].median())
        visible["color"] = visible["ispu"].apply(
            lambda value: (
                [46, 125, 50, 210]
                if value < baseline - 10
                else [239, 108, 44, 225]
                if value > baseline + 10
                else [251, 192, 45, 220]
            )
        )
        st.caption(
            f"Comparison colors use the network median ISPU baseline ({baseline:.0f}); green means lower than the network, not necessarily safe."
        )
    else:
        visible["color"] = visible["category"].map(category_colors)
        st.caption("Health colors use official ISPU categories; this is not a relative ranking.")
    visible["color"] = visible["color"].apply(
        lambda value: value if isinstance(value, list) else [120, 120, 120, 180]
    )
    visible["display_time"] = visible["observed_at"].apply(_friendly_timestamp)
    visible["display_ispu"] = visible["ispu"].apply(
        lambda value: "—" if pd.isna(value) else f"{int(value)}"
    )
    visible["display_concentration"] = visible["concentration"].apply(
        lambda value: "—" if pd.isna(value) else f"{value:.1f}"
    )
    visible["display_source"] = visible["source"].apply(_friendly_source)
    try:
        import pydeck as pdk

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=visible,
            get_position="[longitude, latitude]",
            get_radius=550,
            get_fill_color="color",
            pickable=True,
        )
        view = pdk.ViewState(latitude=-6.2, longitude=106.82, zoom=10.2)
        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=view,
            tooltip={
                "html": "<b>{station}</b><br/>District: {district}<br/>ISPU: {display_ispu}<br/>PM2.5: {display_concentration} µg/m³<br/>Category: {category}<br/>Observed: {display_time}<br/>Source: {display_source}",
                "style": {"backgroundColor": "#f8fafc", "color": "#111827"},
            },
        )
        st.pydeck_chart(deck, width="stretch")
    except ImportError:
        st.map(visible, latitude="latitude", longitude="longitude", size=10)
    if color_mode == "Compared with network median":
        st.markdown(
            "**Legend** · 🟢 Lower than median · 🟡 Near median · 🟠 Higher than median · ⚪ No observation"
        )
    else:
        st.markdown(
            "**Legend** · 🟢 Good · 🟡 Moderate · 🟠 Unhealthy · 🔴 Very unhealthy · 🟣 Hazardous · ⚪ No observation"
        )


def _table_rows(frame, start: int, end: int, pd, include_source: bool = False):
    selected = frame.iloc[start:end].copy()
    output = pd.DataFrame(
        {
            "No.": range(start + 1, start + len(selected) + 1),
            "Station": selected["station"].tolist(),
            "District": selected["district"].tolist(),
            "ISPU": selected["ispu"].tolist(),
            "Category": selected["category"].tolist(),
            "PM2.5 (µg/m³)": selected["concentration"].tolist(),
            "Observed (WIB)": selected["observed_at"].apply(_friendly_timestamp).tolist(),
        }
    )
    if include_source:
        output["Data source"] = selected["source"].apply(_friendly_source).tolist()
    return output


def _render_overview(st, latest_rows: list[dict], map_rows: list[dict], pd) -> None:
    st.subheader("Current network overview")
    if not latest_rows:
        st.info("No observations are loaded.")
        return
    frame = pd.DataFrame(latest_rows)
    frame["station_raw"] = frame["station"]
    frame["district_raw"] = frame["district"]
    frame["station"] = frame["station"].apply(display_station_name)
    frame["district"] = frame["district"].apply(display_district_name)
    frame["category"] = frame["category"].map(_human_category)
    a, b, c = st.columns(3)
    worst = frame.sort_values("ispu", ascending=False).iloc[0]
    a.metric("Highest current ISPU", int(worst["ispu"]))
    b.metric("Median station ISPU", f"{frame['ispu'].median():.0f}")
    c.metric("Stations observed", len(frame))
    left, right = st.columns(2)
    with left:
        st.caption("Stations by official ISPU category · PM2.5 readings")
        st.bar_chart(frame["category"].value_counts())
    with right:
        st.caption("Median ISPU by district")
        st.bar_chart(frame.groupby("district")["ispu"].median().sort_values(ascending=False))
    st.caption(
        f"Newest observation: {_friendly_timestamp(frame['observed_at'].max())} · source: {_friendly_source(frame['source'].iloc[0])}"
    )
    st.markdown("**20 highest current readings**")
    st.caption("Sorted by ISPU, the official unitless index. The table is capped at 20 rows.")
    st.dataframe(
        _table_rows(frame.sort_values("ispu", ascending=False), 0, 20, pd),
        hide_index=True,
        width="stretch",
    )
    st.markdown("**All stations**")
    all_stations = pd.DataFrame(map_rows)
    if not all_stations.empty:
        all_stations["category"] = all_stations["category"].map(_human_category)
    search = st.text_input("Filter station or district", key="overview-search").strip().lower()
    table = (
        all_stations
        if not search
        else all_stations[
            all_stations.apply(
                lambda row: (
                    search
                    in " ".join(
                        str(row.get(column, ""))
                        for column in ("station", "station_raw", "district", "district_raw")
                    ).lower()
                ),
                axis=1,
            )
        ]
    )
    table = table.sort_values(["district", "station"], na_position="last")
    page_size = st.selectbox("Rows per page", [20, 50, 100], index=0, key="overview-page-size")
    pages = max(1, (len(table) + page_size - 1) // page_size)
    if st.session_state.get("overview-page", 1) > pages:
        st.session_state["overview-page"] = 1
    page = st.number_input(
        "Page", min_value=1, max_value=pages, value=1, step=1, key="overview-page"
    )
    start = (page - 1) * page_size
    st.caption(
        f"Showing {min(start + 1, len(table)) if len(table) else 0}–{min(start + page_size, len(table))} of {len(table)} matching stations"
    )
    st.dataframe(
        _table_rows(table, start, start + page_size, pd, include_source=True),
        hide_index=True,
        width="stretch",
    )


def _render_trends(st, historical_city: list[dict], measurements, pd) -> None:
    st.subheader("Trends")
    if historical_city:
        trend = pd.DataFrame(historical_city)
        latest_date = trend["date"].max()
        start_date = st.date_input(
            "Trend start date",
            max(trend["date"].min(), latest_date - pd.Timedelta(days=365)),
            key="trend-start",
        )
        end_date = st.date_input("Trend end date", latest_date, key="trend-end")
        if start_date > end_date:
            st.error("Trend start date must be on or before the end date.")
            return
        trend = trend[(trend["date"] >= start_date) & (trend["date"] <= end_date)]
        st.caption(
            "City-level historical context from Zenodo/Open-Meteo CAMS; it is not a replacement for official station observations."
        )
        st.line_chart(
            trend.set_index("date")[["pm2_5", "pm10"]].rename(
                columns={"pm2_5": "PM2.5 (µg/m³)", "pm10": "PM10 (µg/m³)"}
            )
        )
        st.dataframe(
            trend.rename(
                columns={
                    "date": "Date",
                    "pm2_5": "PM2.5 (µg/m³)",
                    "pm10": "PM10 (µg/m³)",
                    "us_aqi": "US AQI",
                }
            ),
            hide_index=True,
            width="stretch",
        )
        return
    timestamps = sorted({item.observed_at for item in measurements})
    if len(timestamps) < 2:
        st.info(
            "Trend charts are disabled until multiple observation timestamps are accumulated. The current feed is a snapshot."
        )
        return
    trend_frame = pd.DataFrame(
        [
            {"observed_at": item.observed_at, "PM2.5": item.concentration, "ISPU": item.ispu_value}
            for item in measurements
        ]
    )
    trend_frame = trend_frame.groupby("observed_at").median(numeric_only=True)
    st.caption(
        f"Network median across {len(timestamps)} observation timestamps; coverage varies by timestamp."
    )
    st.line_chart(trend_frame[["PM2.5", "ISPU"]])


def _render_brand_header(st) -> None:
    brand_icon = str(ICON_PATH) if ICON_PATH.exists() else None
    icon_column, title_column = st.columns([0.08, 0.92], vertical_alignment="center")
    with icon_column:
        if brand_icon:
            st.image(brand_icon, width=52)
        else:
            st.markdown("<div style='font-size:2.5rem'>🌬️</div>", unsafe_allow_html=True)
    with title_column:
        st.title("Napas Jakarta")


def main() -> None:
    import pandas as pd
    import streamlit as st

    page_icon = str(ICON_PATH) if ICON_PATH.exists() else "🌬️"
    st.set_page_config(page_title="Napas Jakarta", page_icon=page_icon, layout="wide")
    _inject_styles(st)
    _render_brand_header(st)
    language = st.selectbox("Language / Bahasa", ["English", "Bahasa Indonesia"])
    st.caption(
        "A demo, citation-grounded Jakarta air-quality assistant."
        if language == "English"
        else "Asisten kualitas udara Jakarta dengan sumber kutipan."
    )
    documents, measurements = load_runtime_state(
        os.getenv("DATA_DIR", "data"), os.getenv("POSTGRES_DSN", "")
    )
    source_mode = (
        "live"
        if os.getenv("SOURCE_DATA_URL", "").strip()
        or any(not item.source.startswith("Udara Jakarta demo") for item in measurements)
        else "demo"
    )
    source_label = "official loaded snapshot" if source_mode == "live" else "demo snapshot"
    data_age_seconds = latest_data_age_seconds(measurements)
    st.caption(
        f"Measurement source: {source_label}; newest observation age: {data_age_seconds:.0f}s"
        if data_age_seconds is not None
        else f"Measurement source: {source_label}; no observations loaded"
    )
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"ui-{uuid4()}"
    source_url = os.getenv("SOURCE_DATA_URL", "")
    stations = load_runtime_stations(source_url=source_url)
    latest_rows = get_latest_measurements(measurements)
    map_rows = _build_map_rows(stations, latest_rows)
    historical_city = load_historical_city(
        os.path.join(os.getenv("DATA_DIR", "data"), "processed", "historical_city_air_quality.csv")
    )
    _render_terms(st, language)
    pages = ["Ask", "Live map", "Current overview", "Trends"]
    if "active_view" not in st.session_state:
        st.session_state.active_view = "Ask"
    view = st.radio("View", pages, key="active_view", horizontal=True, label_visibility="collapsed")
    if view == "Ask":
        _render_chat(st, documents, measurements, language, source_mode)
    elif view == "Live map":
        _render_map(st, map_rows, source_url, pd)
    elif view == "Current overview":
        _render_overview(st, latest_rows, map_rows, pd)
    else:
        _render_trends(st, historical_city, measurements, pd)


if __name__ == "__main__":
    main()
