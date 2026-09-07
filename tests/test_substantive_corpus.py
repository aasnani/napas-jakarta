from pathlib import Path

from app.data import load_documents, load_measurements
from app.rag import answer
from app.router import classify
from evaluation.eval_substantive import evaluate

ROOT = Path(__file__).parents[1]


def _state():
    return (
        load_documents(ROOT / "data/docs"),
        load_measurements(ROOT / "data/demo/measurements.csv"),
    )


def test_substantive_routes_are_distinct_and_localized():
    assert classify("What should I do on a bad-air day in Jakarta?") == "exposure_reduction"
    assert classify("Why have Jakarta air regulations not produced sufficient improvement?") == "policy_implementation"
    assert classify("What can a Jakarta resident do to reduce emissions?") == "individual_emission_reduction"


def test_exposure_retrieval_keeps_health_local_and_filter_sources():
    documents, measurements = _state()
    result = answer("What should I do on a bad-air day in Jakarta?", documents, measurements)
    source_ids = {source["id"] for source in result["sources"]}
    assert {"bad-air-day-protection", "clean-air-room", "jakarta-seasonal-exposure"}.issubset(source_ids)
    assert result["citation_complete"] is True


def test_policy_gap_retrieval_keeps_rule_and_implementation_evidence():
    documents, measurements = _state()
    result = answer("Why have Jakarta air regulations not produced sufficient improvement?", documents, measurements)
    source_ids = {source["id"] for source in result["sources"]}
    assert result["route"] == "policy_implementation"
    assert {"jakarta-policy-implementation", "jakarta-regulations"}.issubset(source_ids)


def test_offline_substantive_evaluation_has_complete_contracts():
    result = evaluate()
    assert result["questions"] >= 8
    assert result["route_accuracy"] == 1.0
    assert result["preferred_source_recall"] == 1.0
    assert result["fallback_structure_rate"] == 1.0
    assert all(row["citation_complete"] and row["citation_grounded"] for row in result["results"])
