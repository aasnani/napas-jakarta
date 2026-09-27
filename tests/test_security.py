import pytest
from fastapi.testclient import TestClient

from app.security import FixedWindowRateLimiter, internal_token_is_valid


def test_fixed_window_rate_limiter_rejects_until_window_expires():
    limiter = FixedWindowRateLimiter(max_requests=2, window_seconds=10)

    assert limiter.allow("client", now=100.0).allowed is True
    assert limiter.allow("client", now=101.0).allowed is True
    rejected = limiter.allow("client", now=102.0)

    assert rejected.allowed is False
    assert rejected.retry_after_seconds == 8
    assert limiter.allow("client", now=110.0).allowed is True


def test_internal_token_requires_a_configured_secret_in_production():
    assert internal_token_is_valid("secret", "secret", production=True) is True
    assert internal_token_is_valid("wrong", "secret", production=True) is False
    assert internal_token_is_valid(None, "", production=True) is False
    assert internal_token_is_valid(None, "", production=False) is True


def test_feedback_route_requires_the_server_token(monkeypatch):
    from app import api

    monkeypatch.setenv("NAPAS_INTERNAL_TOKEN", "test-secret")
    recorded = []
    monkeypatch.setattr(
        api,
        "log_feedback",
        lambda interaction_id, feedback, comment, session_id=None: recorded.append(
            (interaction_id, feedback, comment, session_id)
        ),
    )
    client = TestClient(api.app)
    payload = {"interaction_id": "answer-1", "feedback": "positive"}

    assert client.post("/feedback", json=payload).status_code == 401
    response = client.post(
        "/feedback",
        headers={"X-Napas-Internal-Token": "test-secret"},
        json=payload,
    )

    assert response.status_code == 200
    assert recorded == [("answer-1", "positive", "", None)]


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("get", "/sources", {}),
        ("get", "/measurements/latest", {}),
        ("post", "/guidance/search", {"json": {"query": "air quality"}}),
    ],
)
def test_internal_read_routes_require_the_server_token(monkeypatch, method, path, kwargs):
    from app import api

    monkeypatch.setenv("NAPAS_INTERNAL_TOKEN", "test-secret")
    client = TestClient(api.app)

    request = getattr(client, method)
    response = request(path, **kwargs)

    assert response.status_code == 401


def test_internal_read_routes_accept_the_server_token(monkeypatch):
    from app import api

    monkeypatch.setenv("NAPAS_INTERNAL_TOKEN", "test-secret")
    client = TestClient(api.app)
    headers = {"X-Napas-Internal-Token": "test-secret"}

    assert client.get("/sources", headers=headers).status_code == 200
    assert client.get("/measurements/latest", headers=headers).status_code == 200
    guidance = client.post(
        "/guidance/search",
        headers=headers,
        json={"query": "air quality guidance"},
    )
    assert guidance.status_code == 200
