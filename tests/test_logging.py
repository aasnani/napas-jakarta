import json

from monitoring.logging import log_feedback, log_interaction


def test_feedback_keeps_parent_interaction_id(tmp_path, monkeypatch):
    path = tmp_path / "interactions.jsonl"
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    monkeypatch.setenv("MONITORING_DB", str(path))
    parent = log_interaction({"event": "answer", "session_id": "session-1"})
    log_feedback(parent, "positive", "clear")
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert rows[0]["interaction_id"] == parent
    assert rows[1]["interaction_id"] == parent
    assert rows[1]["event"] == "feedback"
