import json
from datetime import UTC, datetime, timedelta

from monitoring.logging import cleanup_expired_interactions, log_feedback, log_interaction


def test_feedback_keeps_parent_interaction_id(tmp_path, monkeypatch):
    path = tmp_path / "interactions.jsonl"
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    monkeypatch.setenv("MONITORING_DB", str(path))
    parent = log_interaction({"event": "answer", "session_id": "session-1"})
    log_feedback(parent, "positive", "clear", "session-1")
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert rows[0]["interaction_id"] == parent
    assert rows[1]["interaction_id"] == parent
    assert rows[1]["event"] == "feedback"
    assert rows[1]["session_id"] == "session-1"


def test_chat_telemetry_keeps_answer_text_and_session(tmp_path, monkeypatch):
    path = tmp_path / "interactions.jsonl"
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    monkeypatch.setenv("MONITORING_DB", str(path))
    interaction = log_interaction(
        {
            "event": "answer",
            "interaction_id": "eve-answer-1",
            "session_id": "anonymous-session-1",
            "question": "How is the air?",
            "answer_text": "Moderate in the demo snapshot.",
        }
    )
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert interaction == rows[0]["id"]
    assert rows[0]["interaction_id"] == "eve-answer-1"
    assert rows[0]["session_id"] == "anonymous-session-1"
    assert rows[0]["answer_text"] == "Moderate in the demo snapshot."


def test_jsonl_fallback_applies_retention_cleanup(tmp_path, monkeypatch):
    path = tmp_path / "interactions.jsonl"
    now = datetime.now(UTC)
    old = {"id": "old", "created_at": (now - timedelta(days=8)).isoformat()}
    recent = {"id": "recent", "created_at": (now - timedelta(days=2)).isoformat()}
    path.write_text(json.dumps(old) + "\n" + json.dumps(recent) + "\n", encoding="utf-8")
    monkeypatch.setenv("MONITORING_DB", str(path))

    removed = cleanup_expired_interactions("", retention_days=7)

    assert removed == 1
    assert [json.loads(line)["id"] for line in path.read_text().splitlines()] == ["recent"]


def test_jsonl_writer_runs_retention_cleanup_before_append(tmp_path, monkeypatch):
    path = tmp_path / "interactions.jsonl"
    now = datetime.now(UTC)
    path.write_text(
        json.dumps({"id": "old", "created_at": (now - timedelta(days=8)).isoformat()})
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    monkeypatch.setenv("MONITORING_DB", str(path))
    monkeypatch.setenv("INTERACTION_RETENTION_DAYS", "7")
    monkeypatch.setenv("INTERACTION_CLEANUP_INTERVAL_SECONDS", "0")

    log_interaction({"event": "answer", "question": "new"})

    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert [row["id"] for row in rows] != ["old"]
    assert all(row.get("question") != "old" for row in rows)


def test_railway_cron_runs_jsonl_retention_without_postgres(tmp_path, monkeypatch):
    from ingestion import railway_cron

    path = tmp_path / "interactions.jsonl"
    now = datetime.now(UTC)
    path.write_text(
        json.dumps({"id": "old", "created_at": (now - timedelta(days=8)).isoformat()})
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    monkeypatch.setenv("MONITORING_DB", str(path))
    monkeypatch.setenv("INTERACTION_RETENTION_DAYS", "7")
    monkeypatch.setenv("HISTORICAL_REFRESH_UTC_HOUR", "99")
    monkeypatch.setattr(railway_cron, "run_ingestion", lambda _data_dir: {"rows": 0})

    result = railway_cron.main()

    assert result["retention_cleanup"]["deleted_interactions"] == 1
    assert path.read_text(encoding="utf-8").strip() == ""
