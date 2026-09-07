"""Small, explicit runtime configuration helpers.

Values are read when a request is handled rather than at import time.  This
keeps local development convenient while making the selected production
behaviour visible to the API and telemetry.
"""

from __future__ import annotations

import os

RETRIEVAL_MODES = frozenset({"bm25", "dense", "hybrid", "hybrid_rerank", "qdrant_hybrid"})
DEFAULT_RETRIEVAL_MODE = "hybrid"


def selected_retrieval_mode() -> str:
    """Return the configured retrieval method, falling back to the evaluated default."""
    configured = os.getenv("RETRIEVAL_MODE", DEFAULT_RETRIEVAL_MODE).strip().lower()
    return configured if configured in RETRIEVAL_MODES else DEFAULT_RETRIEVAL_MODE


def is_production() -> bool:
    """Identify hosted production without making a local checkout cumbersome."""
    environment = os.getenv("ENVIRONMENT", "").strip().lower()
    railway_environment = os.getenv("RAILWAY_ENVIRONMENT", "").strip().lower()
    return environment in {"production", "prod"} or railway_environment == "production"


def build_metadata() -> dict[str, str]:
    """Return only safe build fields suitable for a public version endpoint."""
    return {
        "app_version": os.getenv("APP_VERSION", "0.1.0").strip() or "0.1.0",
        "commit": os.getenv("GIT_COMMIT", "unknown").strip() or "unknown",
        "build_time": os.getenv("BUILD_TIME", "unknown").strip() or "unknown",
    }
