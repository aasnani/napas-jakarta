from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def log_interaction(payload: dict[str, Any]) -> str:
    interaction_id = str(uuid.uuid4())
    record = {
        "id": interaction_id,
        "interaction_id": payload.get("interaction_id", interaction_id),
        "created_at": datetime.now(UTC).isoformat(),
        "source": "live",
        **payload,
    }
    dsn = os.getenv("POSTGRES_DSN", "").strip()
    if dsn:
        try:
            import psycopg

            with psycopg.connect(dsn) as connection:
                # Existing Compose volumes may predate these observability
                # columns; migrate them safely before the first insert.
                connection.execute("ALTER TABLE interactions ADD COLUMN IF NOT EXISTS session_id TEXT")
                connection.execute("ALTER TABLE interactions ADD COLUMN IF NOT EXISTS interaction_id TEXT")
                connection.execute("ALTER TABLE interactions ADD COLUMN IF NOT EXISTS feedback_comment TEXT")
                connection.execute("ALTER TABLE interactions ADD COLUMN IF NOT EXISTS conversation_turn INTEGER")
                connection.execute("ALTER TABLE interactions ADD COLUMN IF NOT EXISTS history_messages INTEGER")
                connection.execute("ALTER TABLE interactions ADD COLUMN IF NOT EXISTS history_summary_chars INTEGER")
                connection.execute("ALTER TABLE interactions ADD COLUMN IF NOT EXISTS provider_model TEXT")
                connection.execute("ALTER TABLE interactions ADD COLUMN IF NOT EXISTS carried_entities TEXT")
                connection.execute("ALTER TABLE interactions ADD COLUMN IF NOT EXISTS source_count INTEGER")
                connection.execute(
                    """INSERT INTO interactions
                    (id, interaction_id, session_id, created_at, event, question, rewritten_query, route,
                     retrieval_mode, citation_grounded, prompt_version, latency_ms,
                     token_usage, estimated_cost, data_age_seconds, error_type,
                     abstention_type, feedback, feedback_comment, source,
                     conversation_turn, history_messages, history_summary_chars, provider_model,
                     carried_entities, source_count)
                    VALUES (%(id)s, %(interaction_id)s, %(session_id)s, %(created_at)s, %(event)s,
                            %(question)s, %(rewritten_query)s, %(route)s,
                            %(retrieval_mode)s, %(citation_grounded)s, %(prompt_version)s,
                            %(latency_ms)s, %(token_usage)s, %(estimated_cost)s,
                            %(data_age_seconds)s, %(error_type)s, %(abstention_type)s,
                            %(feedback)s, %(feedback_comment)s, %(source)s,
                            %(conversation_turn)s, %(history_messages)s,
                            %(history_summary_chars)s, %(provider_model)s,
                            %(carried_entities)s, %(source_count)s)
                    ON CONFLICT (id) DO NOTHING""",
                    {
                        **record,
                        "interaction_id": record.get("interaction_id"),
                        "session_id": record.get("session_id"),
                        "event": record.get("event", "answer"),
                        "question": record.get("question", ""),
                        "rewritten_query": record.get("rewritten_query"),
                        "route": record.get("route"),
                        "retrieval_mode": record.get("retrieval_mode"),
                        "citation_grounded": record.get("citation_grounded"),
                        "prompt_version": record.get("prompt_version", "v1"),
                        "latency_ms": record.get("latency_ms"),
                        "token_usage": record.get("token_usage"),
                        "estimated_cost": record.get("estimated_cost"),
                        "data_age_seconds": record.get("data_age_seconds"),
                        "error_type": record.get("error_type"),
                        "abstention_type": record.get("abstention_type"),
                        "feedback": record.get("feedback"),
                        "feedback_comment": record.get("comment", record.get("feedback_comment")),
                        "conversation_turn": record.get("conversation_turn"),
                        "history_messages": record.get("history_messages"),
                        "history_summary_chars": record.get("history_summary_chars"),
                        "provider_model": record.get("provider_model"),
                        "carried_entities": record.get("carried_entities"),
                        "source_count": record.get("source_count"),
                    },
                )
                connection.commit()
                return interaction_id
        except (ImportError, OSError, RuntimeError):
            # A monitoring outage must not block an answer; retain the JSONL
            # fallback so local development remains observable.
            pass
        except psycopg.Error:
            # Schema migrations and inserts can fail on a transient database;
            # retain the JSONL fallback rather than failing the answer request.
            pass
    path = Path(os.getenv("MONITORING_DB", "monitoring/interactions.jsonl"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return interaction_id


def log_feedback(interaction_id: str, feedback: str, comment: str = "") -> None:
    log_interaction(
        {
        "event": "feedback",
            "interaction_id": interaction_id,
            "feedback": feedback,
            "comment": comment[:500],
        }
    )
