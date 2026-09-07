import json
from datetime import UTC, datetime, timedelta

from monitoring.analytics import load_dashboard


def test_jsonl_dashboard_is_aggregate_only_and_has_required_slices(tmp_path, monkeypatch):
    now = datetime.now(UTC).replace(microsecond=0)
    rows = [
        {
            "created_at": now.isoformat(),
            "event": "answer",
            "question": "private question must not be returned",
            "route": "latest_measurements",
            "retrieval_mode": "hybrid",
            "citation_grounded": True,
            "latency_ms": 100,
            "token_usage": 30,
            "estimated_cost": 0.001,
            "conversation_turn": 1,
        },
        {
            "created_at": (now - timedelta(hours=1)).isoformat(),
            "event": "answer",
            "question": "another private question",
            "route": "historical_tool",
            "retrieval_mode": "hybrid",
            "citation_grounded": False,
            "latency_ms": 300,
            "token_usage": 50,
            "estimated_cost": 0.002,
            "error_type": "",
            "abstention_type": "safety",
            "conversation_turn": 2,
        },
        {
            "created_at": now.isoformat(),
            "event": "feedback",
            "question": "must never leak",
            "feedback": "positive",
            "comment": "private comment",
        },
    ]
    path = tmp_path / "interactions.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    dashboard = load_dashboard(30, path=path)
    encoded = json.dumps(dashboard)
    assert "private" not in encoded and "comment" not in encoded and "question" not in encoded
    assert dashboard["source"] == "Local JSONL fallback"
    assert dashboard["summary"]["requests"] == 2
    assert dashboard["summary"]["p50_latency_ms"] == 100
    assert dashboard["summary"]["p95_latency_ms"] == 300
    assert dashboard["summary"]["citation_rate"] == 0.5
    assert dashboard["summary"]["feedback_positive"] == 1
    assert dashboard["summary"]["abstention_count"] == 1
    assert dashboard["routes"]
    assert dashboard["retrieval_modes"]
    assert dashboard["usage_by_day"][0]["tokens"] == 80


def test_dashboard_clamps_window_and_handles_empty_file(tmp_path):
    result = load_dashboard(0, path=tmp_path / "missing.jsonl")
    assert result["window_days"] == 1
    assert result["summary"]["requests"] == 0
    assert result["requests_by_day"] == []

