from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from monitoring.analytics import load_dashboard
from monitoring.logging import log_feedback, log_interaction

from .config import build_metadata, selected_retrieval_mode
from .evidence import compare_study_findings, get_source_apportionment
from .policy import get_policy_status, get_policy_timeline
from .provenance import source_manifest
from .provider import selected_prompt_variant, selected_prompt_version
from .rag import answer
from .runtime_data import RuntimeRepository
from .security import (
    CHAT_RATE_LIMITER,
    TELEMETRY_RATE_LIMITER,
    enforce_rate_limit,
    require_internal_token,
)
from .stations import display_district_name, display_station_name, load_runtime_stations
from .tools import (
    compare_locations,
    compare_measurement_with_standard,
    get_historical_summary,
    get_latest_measurements,
    get_unhealthy_day_count,
    latest_data_age_seconds,
)

ROOT = Path(__file__).parents[1]
RUNTIME = RuntimeRepository(os.getenv("DATA_DIR", ROOT / "data"), os.getenv("POSTGRES_DSN", ""))
DOCUMENTS = RUNTIME.documents()
MEASUREMENTS = RUNTIME.measurements(force=True)
app = FastAPI(title="Napas Jakarta API", version=build_metadata()["app_version"])


def _public_station_category(
    category: object, ispu: object, freshness: object | None = None
) -> str:
    freshness_record = freshness if isinstance(freshness, dict) else {}
    freshness_status = str(freshness_record.get("status", "")).strip().lower()
    freshness_is_current = (
        freshness_record.get("stale") is False or freshness_status == "fresh"
    )
    # The catalog is a public presentation boundary. If the upstream row does
    # not carry an explicit freshness result, fail closed rather than allowing
    # a numeric value to look like a current reading.
    if (
        ispu is None
        or not isinstance(freshness, dict)
        or not freshness_is_current
    ):
        return "Stale / missing"
    normalized = str(category or "").strip().upper()
    if normalized in {"BAIK", "GOOD"}:
        return "Good"
    if normalized in {"SEDANG", "MODERATE"}:
        return "Moderate"
    if normalized in {
        "TIDAK SEHAT",
        "UNHEALTHY",
        "SANGAT TIDAK SEHAT",
        "VERY UNHEALTHY",
        "BERBAHAYA",
        "HAZARDOUS",
    }:
        return "Unhealthy"
    try:
        score = float(ispu)
    except (TypeError, ValueError):
        return "Stale / missing"
    if score <= 50:
        return "Good"
    if score <= 100:
        return "Moderate"
    return "Unhealthy"


def build_station_catalog(
    station_records: list[dict], latest_rows: list[dict], source_mode: str
) -> dict[str, Any]:
    """Join station coordinates with the latest observation for map consumers."""
    latest_by_id = {str(row["station_id"]): row for row in latest_rows}
    stations: list[dict[str, Any]] = []
    for record in station_records:
        station_id = str(record["station_id"])
        observation = latest_by_id.get(station_id)
        source = (observation or {}).get("source") or record.get("source") or ""
        source_url = (
            source if str(source).startswith(("http://", "https://")) else None
        )
        ispu = (observation or {}).get("ispu")
        category = _public_station_category(
            (observation or {}).get("category"),
            ispu,
            (observation or {}).get("freshness"),
        )
        stations.append(
            {
                "id": station_id,
                "name": display_station_name(record.get("station") or (observation or {}).get("station")),
                "district": display_district_name(record.get("district") or (observation or {}).get("district")),
                "latitude": float(record["latitude"]),
                "longitude": float(record["longitude"]),
                "ispu": ispu,
                "pm25": (observation or {}).get("concentration"),
                "category": category,
                "observed_at": (observation or {}).get("observed_at"),
                "source": source,
                "source_url": source_url,
                "freshness": (observation or {}).get("freshness"),
            }
        )

    reporting = [row for row in stations if row["category"] != "Stale / missing"]
    counts = {
        category: sum(row["category"] == category for row in stations)
        for category in ("Good", "Moderate", "Unhealthy", "Stale / missing")
    }
    newest = max(
        (row["observed_at"] for row in reporting if row["observed_at"]),
        default=None,
    )
    highest_ispu = max((float(row["ispu"]) for row in reporting), default=None)
    overall_category = "Stale / missing"
    if highest_ispu is not None:
        if highest_ispu <= 50:
            overall_category = "Good"
        elif highest_ispu <= 100:
            overall_category = "Moderate"
        else:
            overall_category = "Unhealthy"
    return {
        "contract_version": 1,
        "stations": stations,
        "summary": {
            "station_count": len(stations),
            "reporting_count": len(reporting),
            "good_count": counts["Good"],
            "moderate_count": counts["Moderate"],
            "unhealthy_count": counts["Unhealthy"],
            "stale_count": counts["Stale / missing"],
            "latest_observed_at": newest,
            "overall_category": overall_category,
            "source_mode": source_mode,
        },
    }


def refresh_runtime_measurements(force: bool = False) -> list:
    """Refresh the shared measurement list when a configured DB cache expires."""
    if RUNTIME.dsn:
        MEASUREMENTS[:] = RUNTIME.measurements(force=force)
    return MEASUREMENTS


def refresh_runtime_historical(force: bool = False) -> list[dict]:
    """Return historical city data, preferring the durable DB when configured."""
    return RUNTIME.historical(force=force)


def _runtime_provenance() -> dict[str, Any]:
    """Describe loaded runtime facts without relabelling packaged fallback data."""
    refresh_runtime_measurements()
    runtime_sources = sorted({item.source for item in MEASUREMENTS})
    newest = max(MEASUREMENTS, key=lambda item: item.observed_at, default=None)
    store = RUNTIME.last_measurement_source
    live_rows = any(not item.source.startswith("Udara Jakarta demo") for item in MEASUREMENTS)
    fallback_reason = None
    if store != "postgres":
        fallback_reason = (
            "PostgreSQL is not configured; packaged fallback data is loaded."
            if not RUNTIME.dsn
            else RUNTIME.last_database_error
            or "PostgreSQL has no measurement rows; packaged fallback data is loaded."
        )
    ingestion = None
    if RUNTIME.dsn:
        try:
            from .db import load_latest_ingestion_run

            ingestion = load_latest_ingestion_run(RUNTIME.dsn)
        except (ImportError, OSError, RuntimeError, ValueError):
            ingestion = None
    return {
        "mode": "live" if live_rows else "demo",
        "store": store,
        "measurement_rows": len(MEASUREMENTS),
        "measurement_sources": runtime_sources,
        "newest_observation_at": newest.observed_at.isoformat() if newest else None,
        "data_age_seconds": latest_data_age_seconds(MEASUREMENTS),
        "last_successful_ingestion": ingestion,
        "fallback_reason": fallback_reason,
    }


def _source_manifest() -> dict[str, Any]:
    manifest = source_manifest(os.getenv("DATA_DIR", ROOT / "data"))
    runtime = _runtime_provenance()
    return {
        "mode": runtime["mode"],
        "runtime": runtime,
        "packaged_fallback": manifest["packaged_fallback"],
        "sources": manifest["sources"],
        "structured_evidence": manifest["structured_evidence"],
    }


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    retrieval_mode: Literal["bm25", "dense", "hybrid", "hybrid_rerank", "qdrant_hybrid"] = Field(
        default_factory=selected_retrieval_mode
    )
    rewrite_mode: Literal["off", "rules"] = "rules"
    language: Literal["English", "Bahasa Indonesia"] = "English"
    # NiceGUI persists assistant citations/meta alongside string content. Keep
    # the history envelope permissive here; the RAG layer still accepts only
    # user/assistant roles and string content when constructing model context.
    history: list[dict[str, Any]] = Field(default_factory=list, max_length=12)
    session_id: str | None = Field(default=None, max_length=64)


class FeedbackRequest(BaseModel):
    interaction_id: str = Field(min_length=1, max_length=64)
    session_id: str | None = Field(default=None, max_length=128)
    feedback: str = Field(pattern="^(positive|negative)$")
    comment: str = Field(default="", max_length=500)


class ChatTelemetryRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    interaction_id: str = Field(min_length=1, max_length=128)
    question: str = Field(min_length=1, max_length=4000)
    answer: str = Field(min_length=1, max_length=20000)
    conversation_turn: int = Field(ge=1, le=100)
    history_messages: int = Field(ge=0, le=200)


class CompareRequest(BaseModel):
    locations: list[str] = Field(min_length=1, max_length=10)
    pollutant: str = "PM2.5"


class HistoryRequest(BaseModel):
    location: str = Field(min_length=2, max_length=100)
    start: date
    end: date
    pollutant: str = Field(default="PM2.5", min_length=2, max_length=20)


class StandardRequest(BaseModel):
    value: float = Field(ge=0, le=100000)
    pollutant: str = Field(default="PM2.5", min_length=2, max_length=20)


class StudyCompareRequest(BaseModel):
    source_ids: list[str] = Field(default_factory=list, max_length=10)


@app.get("/health")
def health() -> dict[str, str | int | float | None]:
    refresh_runtime_measurements()
    runtime = _runtime_provenance()
    return {
        "status": "ok",
        "documents": len(DOCUMENTS),
        "measurements": len(MEASUREMENTS),
        "source_mode": runtime["mode"],
        "measurement_store": runtime["store"],
        "data_age_seconds": runtime["data_age_seconds"],
        "retrieval_mode": selected_retrieval_mode(),
        "prompt_variant": selected_prompt_variant(),
    }


@app.get("/version")
def version() -> dict[str, str]:
    """Return safe deploy metadata, never credentials or environment values."""
    return {
        **build_metadata(),
        "retrieval_mode": selected_retrieval_mode(),
        "prompt_variant": selected_prompt_variant(),
        "prompt_version": selected_prompt_version(),
    }


@app.get("/monitoring/summary", dependencies=[Depends(require_internal_token)])
def monitoring_summary(http_request: Request = None, days: int = 30) -> dict:
    """Return aggregate telemetry only; user-entered text is never exposed."""
    if http_request is not None:
        enforce_rate_limit(http_request, TELEMETRY_RATE_LIMITER, "monitoring-summary")
    return load_dashboard(days)


@app.get("/sources")
def sources() -> dict:
    return _source_manifest()


@app.get("/policies/timeline")
def policy_timeline(instrument: str) -> dict:
    try:
        return {"timeline": get_policy_timeline(instrument)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/policies/status")
def policy_status(instrument: str, as_of: str | None = None) -> dict:
    try:
        return {"status": get_policy_status(instrument, as_of)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/evidence/source-apportionment")
def source_apportionment(
    pollutant: str = "PM2.5", season: str | None = None, location: str | None = None
) -> dict:
    return {"findings": get_source_apportionment(pollutant, season, location)}


@app.post("/evidence/compare")
def evidence_compare(request: StudyCompareRequest) -> dict:
    return compare_study_findings(request.source_ids)


@app.get("/measurements/latest")
def latest_measurements(location: str | None = None, pollutant: str = "PM2.5") -> dict:
    refresh_runtime_measurements()
    return {
        "measurements": get_latest_measurements(MEASUREMENTS, location, pollutant),
        "source_mode": _source_manifest()["mode"],
    }


@app.get("/stations")
def stations(pollutant: str = "PM2.5") -> dict[str, Any]:
    """Return map-ready station metadata joined to the latest observation."""
    refresh_runtime_measurements()
    data_dir = RUNTIME.data_dir
    station_records = load_runtime_stations(
        path=data_dir / "demo" / "stations.csv",
        persisted_path=data_dir / "processed" / "stations.csv",
        source_url=os.getenv("SOURCE_DATA_URL", ""),
        prefer_persisted=True,
    )
    return build_station_catalog(
        station_records,
        get_latest_measurements(MEASUREMENTS, pollutant=pollutant),
        _source_manifest()["mode"],
    )


@app.post("/measurements/compare")
def compare_measurements(request: CompareRequest) -> dict:
    refresh_runtime_measurements()
    return {
        "comparisons": compare_locations(MEASUREMENTS, request.locations, request.pollutant),
        "source_mode": _source_manifest()["mode"],
    }


@app.post("/measurements/history")
def historical_measurements(request: HistoryRequest) -> dict:
    refresh_runtime_measurements()
    if request.end < request.start:
        raise HTTPException(status_code=422, detail="end must not be before start")
    try:
        summary = get_historical_summary(
            MEASUREMENTS, request.location, request.start, request.end, request.pollutant
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"summary": summary, "source_mode": _source_manifest()["mode"]}


@app.post("/measurements/unhealthy-days")
def unhealthy_days(request: HistoryRequest) -> dict:
    refresh_runtime_measurements()
    if request.end < request.start:
        raise HTTPException(status_code=422, detail="end must not be before start")
    return {
        "summary": get_unhealthy_day_count(
            MEASUREMENTS, request.location, request.start, request.end
        ),
        "source_mode": _source_manifest()["mode"],
    }


@app.post("/measurements/standard")
def measurement_standard(request: StandardRequest) -> dict:
    try:
        comparison = compare_measurement_with_standard(request.value, request.pollutant)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"comparison": comparison}


@app.post("/ask", dependencies=[Depends(require_internal_token)])
def ask(request: AskRequest, http_request: Request = None) -> dict:
    if http_request is not None:
        enforce_rate_limit(http_request, CHAT_RATE_LIMITER, "ask")
    refresh_runtime_measurements()
    started = perf_counter()
    source_mode = _source_manifest()["mode"]
    session_id = request.session_id or f"api-{uuid4()}"
    try:
        result = answer(
            request.question,
            DOCUMENTS,
            MEASUREMENTS,
            retrieval_mode=request.retrieval_mode,
            rewrite_mode=request.rewrite_mode,
            language=request.language,
            history=request.history,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    interaction_id = log_interaction(
        {
            "event": "answer",
            "session_id": session_id,
            "question": request.question,
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
            "conversation_turn": 1
            + sum(1 for item in request.history if item.get("role") == "user"),
            "history_messages": len(request.history),
            "history_summary_chars": 0,
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
    return {
        "interaction_id": interaction_id,
        "session_id": session_id,
        "source_mode": source_mode,
        **result,
    }


@app.post("/feedback", dependencies=[Depends(require_internal_token)])
def feedback(request: FeedbackRequest, http_request: Request = None) -> dict[str, str]:
    if http_request is not None:
        enforce_rate_limit(http_request, TELEMETRY_RATE_LIMITER, "feedback")
    log_feedback(request.interaction_id, request.feedback, request.comment, request.session_id)
    return {"status": "recorded"}


@app.post("/chat-telemetry", dependencies=[Depends(require_internal_token)])
def chat_telemetry(
    request: ChatTelemetryRequest, http_request: Request = None
) -> dict[str, str]:
    if http_request is not None:
        enforce_rate_limit(http_request, TELEMETRY_RATE_LIMITER, "chat-telemetry")
    log_interaction(
        {
            "event": "answer",
            "interaction_id": request.interaction_id,
            "session_id": request.session_id,
            "question": request.question,
            "answer_text": request.answer,
            "conversation_turn": request.conversation_turn,
            "history_messages": request.history_messages,
            "source": "eve",
        }
    )
    return {"status": "recorded", "interaction_id": request.interaction_id}
