from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from monitoring.analytics import load_dashboard
from monitoring.logging import log_feedback, log_interaction

from .evidence import compare_study_findings, get_source_apportionment
from .policy import get_policy_status, get_policy_timeline
from .provenance import source_manifest
from .rag import answer
from .runtime_data import RuntimeRepository
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
app = FastAPI(title="Napas Jakarta API", version="0.1.0")


def refresh_runtime_measurements(force: bool = False) -> list:
    """Refresh the shared measurement list when a configured DB cache expires."""
    if RUNTIME.dsn:
        MEASUREMENTS[:] = RUNTIME.measurements(force=force)
    return MEASUREMENTS


def refresh_runtime_historical(force: bool = False) -> list[dict]:
    """Return historical city data, preferring the durable DB when configured."""
    return RUNTIME.historical(force=force)


def _source_manifest() -> dict:
    refresh_runtime_measurements()
    manifest = source_manifest(os.getenv("DATA_DIR", ROOT / "data"))
    runtime_sources = sorted({item.source for item in MEASUREMENTS})
    manifest["runtime_measurements"] = len(MEASUREMENTS)
    manifest["runtime_measurement_sources"] = runtime_sources
    if any(not item.source.startswith("Udara Jakarta demo") for item in MEASUREMENTS):
        manifest["mode"] = "live"
        manifest["source_data_url_configured"] = True
    return manifest


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    retrieval_mode: Literal["bm25", "dense", "hybrid", "hybrid_rerank", "qdrant_hybrid"] = "hybrid"
    rewrite_mode: Literal["off", "rules"] = "rules"
    language: Literal["English", "Bahasa Indonesia"] = "English"
    # NiceGUI persists assistant citations/meta alongside string content. Keep
    # the history envelope permissive here; the RAG layer still accepts only
    # user/assistant roles and string content when constructing model context.
    history: list[dict[str, Any]] = Field(default_factory=list, max_length=12)
    session_id: str | None = Field(default=None, max_length=64)


class FeedbackRequest(BaseModel):
    interaction_id: str = Field(min_length=1, max_length=64)
    feedback: str = Field(pattern="^(positive|negative)$")
    comment: str = Field(default="", max_length=500)


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
    manifest = _source_manifest()
    return {
        "status": "ok",
        "documents": len(DOCUMENTS),
        "measurements": len(MEASUREMENTS),
        "source_mode": manifest["mode"],
        "measurement_store": "postgres" if os.getenv("POSTGRES_DSN", "").strip() else "local",
        "data_age_seconds": latest_data_age_seconds(MEASUREMENTS),
    }


@app.get("/monitoring/summary")
def monitoring_summary(days: int = 30) -> dict:
    """Return aggregate telemetry only; user-entered text is never exposed."""
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


@app.post("/ask")
def ask(request: AskRequest) -> dict:
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
            "prompt_version": "v1",
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


@app.post("/feedback")
def feedback(request: FeedbackRequest) -> dict[str, str]:
    log_feedback(request.interaction_id, request.feedback, request.comment)
    return {"status": "recorded"}
