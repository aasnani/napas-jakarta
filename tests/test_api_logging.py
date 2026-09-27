import json

import pytest
from fastapi.testclient import TestClient

from app import api


def _structured_records(output: str) -> list[dict]:
    return [json.loads(line) for line in output.splitlines() if line.startswith("{")]


def test_request_logging_adds_request_id_and_completion_event(capsys):
    response = TestClient(api.app).get("/health", headers={"X-Request-ID": "test-request-1"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-1"
    records = _structured_records(capsys.readouterr().out)
    completed = [record for record in records if record.get("event") == "request_completed"]
    assert completed
    assert completed[-1]["request_id"] == "test-request-1"
    assert completed[-1]["http_status"] == 200


def test_unexpected_chat_failure_emits_alertable_event(capsys, monkeypatch):
    monkeypatch.setattr(api, "refresh_runtime_measurements", lambda: None)

    def fail_answer(*args, **kwargs):
        raise RuntimeError("provider detail must not be logged")

    monkeypatch.setattr(api, "answer", fail_answer)

    with pytest.raises(RuntimeError):
        api.ask(api.AskRequest(question="How is the air?"))

    records = _structured_records(capsys.readouterr().out)
    failures = [record for record in records if record.get("event") == "chat_failure"]
    assert failures
    assert failures[-1]["level"] == "error"
    assert failures[-1]["critical"] is True
    assert failures[-1]["alertable"] is True
    assert "provider detail must not be logged" in failures[-1]["stacktrace"]
