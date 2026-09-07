"""Offline multi-turn memory contract evaluation."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path

from app.rag import answer, load_demo_state

CASES = [
    (["What is the current air quality in Jakarta Pusat?", "How does that compare with the north?"],
     "Jakarta Pusat", "Jakarta Utara", "historical_tool"),
    (["What is the current air quality in Jakarta Selatan?", "What about the east?"],
     "Jakarta Selatan", "Jakarta Timur", "latest_measurements"),
    (["What are Jakarta's air pollution sources?", "What can individuals do?"],
     "Jakarta", "", "exposure_reduction"),
    (["Tell me about ERP in Jakarta.", "Was it enacted?"], "ERP", "", "policy_history"),
    (["Is Jakarta air safe for exercise?", "What about for a child?"], "Jakarta", "", "exposure_reduction"),
    (["What is the latest reading in Jakarta Barat?", "What about the north?"], "Jakarta Barat", "Jakarta Utara", "latest_measurements"),
    (["How is Jakarta Timur today?", "And the south?"], "Jakarta Timur", "Jakarta Selatan", "latest_measurements"),
    (["Compare Jakarta Barat and Jakarta Timur.", "What about their difference from the north?"], "Jakarta Barat", "Jakarta Utara", "historical_tool"),
    (["Why is Jakarta polluted?", "What about transport?"], "Jakarta", "", "pollution_causes"),
    (["What causes Jakarta PM2.5?", "How can we improve it?"], "Jakarta", "", "improvement_strategies"),
    (["What causes Jakarta PM2.5?", "How can I reduce my emissions?"], "Jakarta", "", "individual_emission_reduction"),
    (["Explain ERP in Jakarta.", "Is it currently enacted?"], "ERP", "", "policy_history"),
    (["What is the low emission zone plan?", "Is it active?"], "low emission", "", "policy_history"),
    (["Which Jakarta air rules are in force?", "Which authority enforces them?"], "Jakarta", "", "regulation_current"),
    (["What protection is recommended on polluted days?", "What about for pregnancy?"], "polluted days", "", "exposure_reduction"),
    (["Should I wear a mask outside?", "What about children?"], "mask", "", "exposure_reduction"),
    (["Does living on a high floor change exposure?", "What about the rooftop?"], "high", "", "vertical_exposure"),
    (["Is a high-rise always safer than ground level?", "Does higher always mean safer?"], "high", "", "vertical_exposure"),
    (["What is the current air quality in Jakarta Pusat?", "Would running there be sensible?"], "Jakarta Pusat", "", "latest_measurements"),
    (["Is outdoor exercise safe today?", "What symptoms need medical help?"], "exercise", "", "safety_abstention"),
    (["What are Jakarta's pollution sources?", "Now explain the regulations."], "Jakarta", "", "regulation_current"),
    (["Tell me about Jakarta regulations.", "Now explain the main pollution sources."], "Jakarta", "", "pollution_causes"),
    (["What is current air quality in Jakarta Pusat?", "How does it compare with Jakarta Utara?", "What about exercise there?"], "Jakarta Utara", "", "exposure_reduction"),
    (["What is current air quality in Jakarta Selatan?", "What about the east?", "Would a child be safe outdoors there?"], "east", "", "exposure_reduction"),
    (["What are the sources of PM2.5?", "What can residents do?", "What about avoiding open burning?"], "What can residents do", "", "individual_emission_reduction"),
    (["Tell me about ERP.", "Was it enacted?", "What is its status now?"], "Was it enacted", "", "policy_history"),
    (["How should I reduce exposure?", "What about indoor filtration?", "And for a child?"], "indoor filtration", "", "exposure_reduction"),
    (["What does high-rise evidence say?", "What about street-canyon wind?", "Is there a universal safe floor?"], "street-canyon", "", "vertical_exposure"),
    (["What are the current regulations?", "What is the difference from WHO guidance?", "Are WHO guidelines law?"], "difference from WHO", "", "regulation_current"),
]


@contextmanager
def _offline_provider():
    saved = {key: os.environ.get(key) for key in ("LLM_PROVIDER", "OPENAI_API_KEY", "ANTHROPIC_API_KEY")}
    os.environ["LLM_PROVIDER"] = "disabled"
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def evaluate() -> dict:
    documents, measurements = load_demo_state()
    rows = []
    with _offline_provider():
        for case_id, (questions, expected_first, expected_second, expected_route) in enumerate(CASES, 1):
            history: list[dict[str, str]] = []
            result = None
            for question in questions:
                result = answer(question, documents, measurements, history=history)
                history.extend([{"role": "user", "content": question},
                                {"role": "assistant", "content": result["answer"]}])
            assert result is not None
            resolved = expected_first.lower() in result["condensed_question"].lower() and (
                not expected_second or expected_second.lower() in result["rewritten_query"].lower()
            )
            route_ok = result["route"] == expected_route
            rows.append({"case_id": f"conversation-{case_id:02d}", "questions": questions,
                         "condensed_question": result["condensed_question"],
                         "rewritten_query": result["rewritten_query"],
                         "route": result["route"], "resolved": resolved, "route_correct": route_ok})
    return {"cases": len(rows), "resolution_accuracy": sum(row["resolved"] for row in rows) / len(rows),
            "route_accuracy": sum(row["route_correct"] for row in rows) / len(rows),
            "history_strategy": "six recent messages plus deterministic older-user summary",
            "rows": rows, "status": "offline multi-turn conversation evaluation"}


if __name__ == "__main__":
    result = evaluate()
    Path("evaluation/results/conversation_results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, indent=2))
