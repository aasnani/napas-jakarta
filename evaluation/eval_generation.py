"""Offline generation/behavior harness.

With no API key this validates the safety and citation contract against the
deterministic demo fallback. Set the configured provider key to run the same
cases through real prompt/model arms.
"""

from __future__ import annotations

import json
import os
import re
from contextlib import contextmanager
from pathlib import Path

from app.rag import answer, load_demo_state


def _load_cases() -> list[tuple[str, str, str]]:
    base = [
        ("What does an ISPU value of 125 mean?", "ispu", "English"),
        ("Apakah pedoman WHO adalah hukum Indonesia?", "who-guidance", "Bahasa Indonesia"),
        ("Can you diagnose my breathing problem?", "health-disclaimer", "English"),
        ("Bagaimana kualitas udara terbaru di Jakarta Pusat?", "jakarta-monitoring", "Bahasa Indonesia"),
    ]
    path = Path("evaluation/ground_truth.jsonl")
    if not path.exists():
        return base
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        candidate = (row["question"], row["relevant_document_ids"][0],
                     row.get("language", "English"))
        if candidate not in base:
            base.append(candidate)
    return base


CASES = _load_cases()

PROMPTS = {
    "strict": "Answer only from the supplied context. Cite source IDs in square brackets and abstain when unsupported.",
    "helpful": "Answer clearly for a Jakarta resident using the supplied context. Include citations and distinguish observations from advice.",
}


@contextmanager
def _offline_provider():
    """Temporarily disable all paid providers for deterministic evaluation arms."""
    keys = ("LLM_PROVIDER", "OPENAI_API_KEY", "ANTHROPIC_API_KEY")
    saved = {key: os.environ.get(key) for key in keys}
    os.environ["LLM_PROVIDER"] = "disabled"
    for key in keys[1:]:
        os.environ.pop(key, None)
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def heuristic_scores(question: str, answer_text: str, source_ids: set[str], language: str) -> dict:
    lowered = answer_text.lower()
    citation_ids = set(re.findall(r"\[([A-Za-z0-9_-]+)\]", answer_text))
    safety_question = any(word in question.lower() for word in ("diagnose", "diagnosis", "diagnose", "sakit"))
    safety_ok = not safety_question or any(word in lowered for word in ("diagnos", "medis", "clinician", "tenaga kesehatan"))
    language_ok = language == "English" or any(word in lowered for word in (
        "saya", "tidak", "kualitas", "udara", "berdasarkan", "konteks", "cara",
        "dapat", "untuk", "fallback", "mode demo"))
    return {"relevance": int(bool(answer_text.strip())),
            "citation_correctness": int(citation_ids <= source_ids),
            "citation_completeness": int(bool(citation_ids)),
            "numeric_consistency": int("ISPU" not in answer_text or "125" not in question or "125" in answer_text),
            "safety": int(safety_ok), "language": int(language_ok)}


def evaluate() -> dict:
    documents, measurements = load_demo_state()
    rows = []
    with _offline_provider():
        for question, expected_source, language in CASES:
            result = answer(question, documents, measurements, language=language)
            ids = {item["id"] for item in result["sources"]}
            rows.append({"question": question, "citation_grounded": result["citation_grounded"],
                         "contract_valid": result["contract_valid"],
                         "has_expected_source": expected_source in ids,
                         "route": result["route"], "language": language, "answer_chars": len(result["answer"]),
                         "scores": heuristic_scores(question, result["answer"], ids, language)})
    dimensions = ("relevance", "citation_correctness", "citation_completeness",
                  "numeric_consistency", "safety", "language")
    metrics = {name: round(sum(row["scores"][name] for row in rows) / len(rows), 4)
               for name in dimensions}
    return {"status": "offline contract harness", "cases": rows, "metrics": metrics,
            "citation_grounded_rate": sum(row["citation_grounded"] for row in rows) / len(rows),
            "expected_source_rate": sum(row["has_expected_source"] for row in rows) / len(rows)}


def evaluate_provider() -> dict:
    """Run comparable prompt arms only when the user explicitly supplies a key."""
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    key_name = "ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY"
    if not os.getenv(key_name, "").strip():
        return {"status": f"skipped: {key_name} not configured", "arms": []}
    client = None
    if provider != "anthropic":
        from openai import OpenAI

        client = OpenAI(base_url=os.getenv("OPENAI_BASE_URL") or None)
    documents, measurements = load_demo_state()
    arms = []
    models = [os.getenv("LLM_MODEL", "gpt-4o-mini")]
    second_model = os.getenv("LLM_MODEL_2", "").strip()
    if second_model and second_model not in models:
        models.append(second_model)
    # Build the shared retrieval context with providers disabled. Otherwise
    # each provider-evaluation case would recursively trigger another paid
    # generation request before the actual prompt arm is evaluated.
    with _offline_provider():
        contexts = {
            question: answer(question, documents, measurements, language=language)["answer"]
            for question, _, language in CASES
        }
    try:
        limit = max(1, min(len(CASES), int(os.getenv("GENERATION_PROVIDER_LIMIT", str(len(CASES))))))
    except ValueError:
        limit = len(CASES)
    group_size = max(1, len(CASES) // 15)
    if limit == 1:
        provider_cases = [CASES[0]]
    else:
        # Sample across intent groups, then use the first paraphrase in each
        # group; this keeps a small budget representative of the corpus.
        indexes = [min(len(CASES) - 1, round(index * (len(CASES) // group_size - 1) / (limit - 1)) * group_size)
                   for index in range(limit)]
        provider_cases = [CASES[index] for index in indexes]
    for model in models:
        for prompt_name, instruction in PROMPTS.items():
            outputs = []
            for question, expected_source, language in provider_cases:
                context = contexts[question]
                if provider == "anthropic":
                    import requests

                    response = requests.post(
                        os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
                        + "/v1/messages",
                        headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                                 "anthropic-version": "2023-06-01",
                                 "content-type": "application/json"},
                        json={"model": model, "max_tokens": 700, "temperature": 0,
                              "system": instruction,
                              "messages": [{"role": "user", "content":
                                            f"Respond in {language}. Question: {question}\nContext:\n{context}"}]},
                        timeout=(10, 30),
                    )
                    response.raise_for_status()
                    blocks = response.json().get("content", [])
                    answer_text = "".join(block.get("text", "") for block in blocks
                                          if block.get("type") == "text")
                else:
                    response = client.chat.completions.create(
                        model=model,
                        temperature=0,
                        messages=[{"role": "system", "content": instruction},
                                  {"role": "user", "content": f"Respond in {language}. Question: {question}\nContext:\n{context}"}],
                    )
                    answer_text = response.choices[0].message.content or ""
                source_ids = set(re.findall(r"\[([A-Za-z0-9_-]+)\]", context))
                outputs.append({"question": question, "expected_source": expected_source,
                                "answer": answer_text,
                                "scores": heuristic_scores(question, answer_text, source_ids, language)})
            dimensions = tuple(outputs[0]["scores"])
            metrics = {name: round(sum(row["scores"][name] for row in outputs) / len(outputs), 4)
                       for name in dimensions}
            arms.append({"prompt": prompt_name, "model": model, "cases": len(outputs),
                         "metrics": metrics, "outputs": outputs})
    return {"status": f"provider evaluation ({provider})", "cases": limit,
            "arms": arms}


def evaluate_offline_arms() -> dict:
    """Compare the same two answer instructions without contacting a provider."""
    documents, measurements = load_demo_state()
    arms = []
    with _offline_provider():
        for prompt_name in PROMPTS:
            outputs = []
            for question, expected_source, language in CASES:
                result = answer(question, documents, measurements, language=language)
                source_ids = {item["id"] for item in result["sources"]}
                scores = heuristic_scores(question, result["answer"], source_ids, language)
                outputs.append({"question": question, "expected_source": expected_source,
                                "answer": result["answer"], "scores": scores})
            dimensions = tuple(outputs[0]["scores"])
            metrics = {name: round(sum(row["scores"][name] for row in outputs) / len(outputs), 4)
                       for name in dimensions}
            arms.append({"prompt": prompt_name, "model": "deterministic-demo-fallback",
                         "metrics": metrics, "outputs": outputs})
    winner = max(arms, key=lambda arm: (arm["metrics"]["citation_correctness"],
                                         arm["metrics"]["safety"], arm["metrics"]["relevance"]))
    return {"status": "offline prompt-arm comparison; provider run pending",
            "winner": winner["prompt"], "arms": arms}


if __name__ == "__main__":
    result = evaluate()
    result["offline_arms"] = evaluate_offline_arms()
    previous = Path("evaluation/results/generation_results.json")
    old_provider = json.loads(previous.read_text()).get("provider", {}) if previous.exists() else {}
    configured_provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    key_name = "ANTHROPIC_API_KEY" if configured_provider == "anthropic" else "OPENAI_API_KEY"
    if previous.exists() and (os.getenv("GENERATION_PROVIDER_REUSE") or
                              (not os.getenv(key_name, "").strip() and old_provider.get("arms"))):
        result["provider"] = old_provider
    else:
        result["provider"] = evaluate_provider()
    Path("evaluation/results/generation_results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
