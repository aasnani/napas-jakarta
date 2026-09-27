"""Small, process-local guards for the public, no-login deployment.

The free-tier deployment intentionally avoids Redis or another paid state
service. These guards are therefore scoped to one process and are a first
line of defense, not a substitute for a private service boundary or a
provider-side quota.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from hmac import compare_digest
from math import ceil
from threading import Lock
from time import monotonic
from typing import Annotated

from fastapi import Header, HTTPException, Request

from .config import is_production


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int = 0


class FixedWindowRateLimiter:
    """Bound requests by key without requiring a shared external store."""

    def __init__(self, max_requests: int, window_seconds: float, max_keys: int = 10_000) -> None:
        self.max_requests = max(1, int(max_requests))
        self.window_seconds = max(1.0, float(window_seconds))
        self.max_keys = max(1, int(max_keys))
        self._windows: dict[str, tuple[float, int]] = {}
        self._lock = Lock()

    def allow(self, key: str, now: float | None = None) -> RateLimitDecision:
        current = monotonic() if now is None else now
        with self._lock:
            expired = [
                key
                for key, (started_at, _) in self._windows.items()
                if current - started_at >= self.window_seconds
            ]
            for expired_key in expired:
                self._windows.pop(expired_key, None)
            started, count = self._windows.get(key, (current, 0))
            if current - started >= self.window_seconds:
                started, count = current, 0
            if count >= self.max_requests:
                remaining = max(0.0, self.window_seconds - (current - started))
                return RateLimitDecision(False, max(1, ceil(remaining)))
            if key not in self._windows and len(self._windows) >= self.max_keys:
                oldest_key = min(self._windows, key=lambda item: self._windows[item][0])
                self._windows.pop(oldest_key, None)
            self._windows[key] = (started, count + 1)
            return RateLimitDecision(True)


def internal_token_is_valid(
    provided: str | None, expected: str, *, production: bool | None = None
) -> bool:
    """Validate the server-to-server secret without exposing it to browsers."""
    configured = expected.strip()
    if not configured:
        return not (is_production() if production is None else production)
    return bool(provided) and compare_digest(provided.strip(), configured)


def require_internal_token(
    x_napas_internal_token: Annotated[
        str | None, Header(alias="X-Napas-Internal-Token")
    ] = None,
) -> None:
    """FastAPI dependency for web-to-API and admin-only write routes."""
    expected = os.getenv("NAPAS_INTERNAL_TOKEN", "")
    if internal_token_is_valid(x_napas_internal_token, expected):
        return
    if not expected.strip() and is_production():
        raise HTTPException(status_code=503, detail="Internal API token is not configured")
    raise HTTPException(status_code=401, detail="Invalid internal API token")


def request_client_key(request: Request) -> str:
    """Return a stable limiter key without trusting spoofable proxy headers by default."""
    if os.getenv("TRUST_PROXY_HEADERS", "").strip().lower() in {"1", "true", "yes"}:
        forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
        if forwarded:
            return forwarded
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(
    request: Request, limiter: FixedWindowRateLimiter, bucket: str
) -> None:
    decision = limiter.allow(f"{bucket}:{request_client_key(request)}")
    if decision.allowed:
        return
    raise HTTPException(
        status_code=429,
        detail="Request limit reached. Please try again shortly.",
        headers={"Retry-After": str(decision.retry_after_seconds)},
    )


def _configured_positive_int(name: str, fallback: int) -> int:
    try:
        value = int(os.getenv(name, str(fallback)))
    except ValueError:
        return fallback
    return value if value > 0 else fallback


CHAT_RATE_LIMITER = FixedWindowRateLimiter(
    max_requests=_configured_positive_int("CHAT_RATE_LIMIT_MAX", 12),
    window_seconds=_configured_positive_int("CHAT_RATE_LIMIT_WINDOW_SECONDS", 60),
)
TELEMETRY_RATE_LIMITER = FixedWindowRateLimiter(
    max_requests=_configured_positive_int("TELEMETRY_RATE_LIMIT_MAX", 120),
    window_seconds=_configured_positive_int("TELEMETRY_RATE_LIMIT_WINDOW_SECONDS", 60),
)
