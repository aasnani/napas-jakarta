from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.data import load_documents, load_measurements
from app.rag import answer
from app.tools import get_most_recent_category_occurrence, query_historical_occurrence

ROOT = Path(__file__).parents[1]


def _state():
    return load_documents(ROOT / "data/docs"), load_measurements(
        ROOT / "data/processed/measurements.csv"
    )


def test_direct_query_returns_most_recent_good_for_district():
    documents, measurements = _state()
    result = answer("When was Jakarta Utara good by the data standards most recently?", documents, measurements)
    assert result["route"] == "most_recent_category"
    assert result["conversation_state"]["district"] == "Jakarta Utara"
    assert "07 Sep 2026, 13:00 WIB" in result["answer"]
    assert "DKI100 SDN 03 Rorotan" in result["answer"]
    assert "whole district" in result["answer"]


def test_exact_two_turn_followup_carries_district_and_avoids_snapshot_summary():
    documents, measurements = _state()
    history = [
        {"role": "user", "content": "What is the air quality in Jakarta Utara?"},
        {"role": "assistant", "content": "The current reading is moderate."},
        {"role": "user", "content": "i mean, when was it good by the data standards most recently?"},
    ]
    result = answer(history[-1]["content"], documents, measurements, history=history)
    assert result["route"] == "most_recent_category"
    assert "Jakarta Utara" in result["condensed_question"]
    assert "most-recent category occurrence" in result["measurement_context"]
    assert "only the displayed observation window" not in result["answer"]


def test_api_accepts_hydrated_nicegui_history_with_sources_and_meta(monkeypatch):
    from app import rag
    from app.api import AskRequest, ask

    documents, measurements = _state()
    from app import api

    monkeypatch.setattr(api, "DOCUMENTS", documents)
    monkeypatch.setattr(api, "MEASUREMENTS", measurements)
    captured = {}

    def fake_generate(question, context, language, **kwargs):
        captured["context"] = context
        return (
            "The most recent Good station observation was 07 Sep 2026, 13:00 WIB "
            "at DKI100 SDN 03 Rorotan in Jakarta Utara: ISPU 16, PM2.5 2.66; "
            "12 stations reported and 5 met Good among 21 stations. "
            "[jakarta-monitoring] [ispu]"
        )

    monkeypatch.setattr(rag, "generate_answer", fake_generate)
    history = [
        {"role": "user", "content": "What is the current air quality in Jakarta Utara?"},
        {
            "role": "assistant",
            "content": "The current reading is moderate.",
            "sources": [
                {
                    "id": "jakarta-monitoring",
                    "title": "Jakarta monitoring stations",
                    "url": "https://udara.jakarta.go.id/lokasi-spku",
                }
            ],
            "meta": {"route": "latest_measurements", "citation_complete": True},
        },
    ]
    result = ask(
        AskRequest(
            question="i mean, when was it good by the data standards most recently?",
            history=history,
            session_id="category-regression",
        )
    )
    assert result["route"] == "most_recent_category"
    assert result["conversation_state"]["district"] == "Jakarta Utara"
    assert "DKI100 SDN 03 Rorotan" in result["answer"]
    assert "07 Sep 2026, 13:00 WIB" in result["answer"]
    assert result["contract_valid"] is True
    assert "tool result" in captured["context"]


def test_followup_carries_district_named_only_by_prior_assistant() -> None:
    documents, measurements = _state()
    history = [
        {"role": "user", "content": "What is the current air quality?"},
        {
            "role": "assistant",
            "content": "The latest loaded Jakarta Utara station reading is moderate.",
            "sources": [],
            "meta": {"route": "latest_measurements"},
        },
    ]
    result = answer(
        "When was it good most recently?", documents, measurements, history=history
    )
    assert result["route"] == "most_recent_category"
    assert result["conversation_state"]["district"] == "Jakarta Utara"
    assert "DKI100 SDN 03 Rorotan" in result["answer"]


def test_category_query_without_district_requests_location() -> None:
    documents, measurements = _state()
    result = answer("When was air quality Good most recently?", documents, measurements)
    assert result["route"] == "most_recent_category"
    assert result["conversation_state"]["district"] is None
    assert "Please name the Jakarta district" in result["answer"]
    assert "Jakarta" not in result["measurement_context"]


def test_indonesian_category_query_is_deterministic():
    documents, measurements = _state()
    result = answer("Kapan terakhir kualitas udara Jakarta Utara Baik?", documents, measurements, language="Bahasa Indonesia")
    assert result["route"] == "most_recent_category"
    assert "07 Sep 2026, 13:00 WIB" in result["answer"]
    assert "observasi stasiun" in result["answer"]


def test_found_result_has_coverage_and_freshness_fields():
    _, measurements = _state()
    result = get_most_recent_category_occurrence(
        measurements, "Jakarta Utara", now=datetime(2026, 9, 7, 14, tzinfo=UTC)
    )
    assert result["found"] is True
    assert result["coverage_timestamps"] == 4
    assert result["coverage_stations"] == 21
    assert result["reported_stations_at_timestamp"] == 12
    assert result["qualifying_stations_at_timestamp"] == 5
    assert result["observed_at_wib"] == "07 Sep 2026, 13:00 WIB"
    assert result["freshness"]["age_seconds"] == 28800.0


def test_no_result_states_explicit_coverage():
    _, measurements = _state()
    base = [item for item in measurements if item.district.endswith("Jakarta Utara")][:2]
    high = [replace(item, ispu_value=51, ispu_category="Sedang") for item in base]
    result = get_most_recent_category_occurrence(high, "Jakarta Utara")
    assert result["found"] is False
    assert result["coverage_start"] and result["coverage_end"]
    assert result["coverage_observations"] == 2
    documents, _ = _state()
    answer_result = answer("When was Jakarta Utara good most recently?", documents, high)
    assert "No Good observation was found within the available coverage" in answer_result["answer"]
    assert "2 station observations from 2 stations" in answer_result["answer"]


def test_multiple_station_semantics_and_threshold_boundary():
    _, measurements = _state()
    base = measurements[0]
    t = datetime(2026, 1, 2, 5, tzinfo=UTC)
    rows = [
        replace(base, station_id="a", station_name="A", district="Jakarta Utara", observed_at=t, ispu_value=50, ispu_category="Sedang"),
        replace(base, station_id="b", station_name="B", district="Jakarta Utara", observed_at=t, ispu_value=51, ispu_category="Baik"),
        replace(base, station_id="c", station_name="C", district="Jakarta Utara", observed_at=t - timedelta(hours=1), ispu_value=40, ispu_category="Baik"),
    ]
    result = get_most_recent_category_occurrence(rows, "Jakarta Utara", now=t + timedelta(hours=1))
    assert result["found"] is True
    assert result["ispu"] == 50
    assert result["station"] == "A"
    assert result["reported_stations_at_timestamp"] == 2
    assert result["qualifying_stations_at_timestamp"] == 1
    assert result["qualifying_observations"] == 2


def test_category_lookup_never_substitutes_city_model_history():
    documents, measurements = _state()
    result = answer("When was Jakarta Utara good most recently?", documents, measurements)
    assert result["route"] == "most_recent_category"
    assert "Open-Meteo" not in result["measurement_context"]
    assert "jakarta-historical-city-series" not in {item["id"] for item in result["sources"]}


def test_generic_occurrence_supports_categories_numeric_thresholds_and_station() -> None:
    _, measurements = _state()
    moderate = query_historical_occurrence(
        measurements, "Jakarta Selatan", threshold_or_category="Moderate"
    )
    assert moderate["found"] is True
    assert moderate["category"] == "Moderate"
    numeric = query_historical_occurrence(
        measurements,
        "Jakarta Barat",
        condition_kind="ispu",
        operator="<",
        threshold_or_category=50,
    )
    assert numeric["found"] is True
    station = query_historical_occurrence(
        measurements,
        "DKI100 SDN 03 Rorotan",
        location_type="station",
        threshold_or_category="Good",
    )
    assert station["found"] is True
    assert station["location_type"] == "station"


def test_historical_condition_router_handles_paraphrase_matrix() -> None:
    from app.router import classify

    cases = {
        "When was it last Good?": "most_recent_category",
        "When was Jakarta Selatan last Moderate?": "most_recent_category",
        "latest reading below ISPU 50 in Jakarta Barat": "most_recent_category",
        "kapan terakhir kualitas udara baik di Jakarta Timur?": "most_recent_category",
        "how many readings were Unhealthy last week?": "most_recent_category",
    }
    for question, expected in cases.items():
        assert classify(question) == expected


def test_contradictory_generated_counts_use_generic_tool_fallback(monkeypatch) -> None:
    from app import rag

    documents, measurements = _state()
    monkeypatch.setattr(
        rag,
        "generate_answer",
        lambda *args, **kwargs: (
            "Jakarta Selatan was Good at a station on an unknown date: ISPU 16; "
            "12 stations reported and 99 were Good."
        ),
    )
    result = answer("When was Jakarta Utara Good most recently?", documents, measurements)
    assert "DKI100 SDN 03 Rorotan" in result["answer"]
    assert "5 met Good" in result["answer"]
    assert "99 were Good" not in result["answer"]


def test_structured_provider_draft_is_buffered_until_validation(monkeypatch) -> None:
    from app import rag
    from app.citations import linkify_citations

    documents, measurements = _state()
    provider_drafts = []

    def fake_generate(*args, **kwargs):
        # Simulate a provider that produced a contradictory stream.  The RAG
        # layer must not expose its callback for a tool-backed answer.
        callback = kwargs.get("on_delta")
        assert callback is None
        provider_drafts.append("Jakarta Barat was Good at an invented station.")
        return provider_drafts[-1]

    monkeypatch.setattr(rag, "generate_answer", fake_generate)
    result = answer(
        "latest reading below ISPU 50 in Jakarta Barat",
        documents,
        measurements,
        history=[{"role": "user", "content": "latest reading below ISPU 50 in Jakarta Barat"}],
        on_delta=lambda value: provider_drafts.append(value),
    )

    assert provider_drafts == ["Jakarta Barat was Good at an invented station."]
    assert result["stream_policy"] == "buffered_structured"
    assert "invented station" not in result["answer"]
    assert result["answer"].count("[jakarta-monitoring]") == 1
    linked = linkify_citations(result["answer"], result["sources"])
    assert linked.count("https://udara.jakarta.go.id/lokasi-spku") == 1
    history = [
        {"role": "user", "content": "latest reading below ISPU 50 in Jakarta Barat"},
        {"role": "assistant", "content": result["answer"], "sources": result["sources"]},
    ]
    assert [item for item in history if item["role"] == "assistant"] == [history[-1]]


def test_valid_structured_provider_answer_is_approved_once(monkeypatch) -> None:
    from app import rag

    documents, measurements = _state()
    valid = (
        "The most recent PM2.5 < 50.0 station observation in Jakarta Barat was "
        "07 Sep 2026, 13:00 WIB at DKI_CENDRAWASIH GOR Cendrawasih: ISPU 64 "
        "(Sedang), PM2.5 31.88 µg/m³. At that timestamp, 10 stations reported "
        "and 6 met PM2.5 < 50.0 (PM2.5 < 50.0); 16 stations and 4 timestamps "
        "are covered; this is a station observation, "
        "not a claim that the whole district was in that condition. "
        "[jakarta-monitoring] [ispu]"
    )
    captured = []

    def fake_generate(*args, **kwargs):
        captured.append(kwargs.get("on_delta"))
        return valid

    monkeypatch.setattr(rag, "generate_answer", fake_generate)
    result = answer("latest reading below ISPU 50 in Jakarta Barat", documents, measurements)

    assert captured == [None]
    assert result["stream_policy"] == "buffered_structured"
    assert result["answer"] == valid


def test_document_rag_keeps_native_provider_streaming(monkeypatch) -> None:
    from app import rag

    documents, measurements = _state()
    deltas = []

    def fake_generate(*args, **kwargs):
        callback = kwargs["on_delta"]
        callback("Grounded ")
        callback("causes [jakarta-causes]")
        return "Grounded causes [jakarta-causes]"

    monkeypatch.setattr(rag, "generate_answer", fake_generate)
    result = answer(
        "What causes Jakarta's PM2.5 pollution?",
        documents,
        measurements,
        on_delta=deltas.append,
    )

    assert deltas == ["Grounded ", "causes [jakarta-causes]"]
    assert result["stream_policy"] == "native_provider"
