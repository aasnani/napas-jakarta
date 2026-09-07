"""Build the focused 30-question human-review packet from the seeded set.

The packet is intentionally machine-suggested only.  Retrieval is local and
uses the production search modes; no provider call is made by this script.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from app.data import load_documents
from app.retrieval import search, tokenize

ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT / "evaluation/ground_truth.jsonl"
CHUNKS_PATH = ROOT / "data/index/chunks.jsonl"
OUT_PATH = ROOT / "evaluation/gold_review_30_candidates.jsonl"
MANIFEST_PATH = ROOT / "evaluation/gold_review_30_manifest.json"
MODES = ("bm25", "dense", "hybrid", "hybrid_rerank")


def _q(
    number: int,
    language: str,
    topic: str,
    difficulty: str,
    question: str,
    route: str,
    source_ids: list[str],
    seed_id: str,
    *,
    parent_id: str | None = None,
    parent_question: str | None = None,
    expected_no_result: bool = False,
    rationale: str,
) -> dict[str, Any]:
    return {
        "question_id": f"gold30-{number:03d}",
        "seed_id": seed_id,
        "question": question,
        "language": language,
        "topic": topic,
        "difficulty": difficulty,
        "expected_route": route,
        "expected_no_result": expected_no_result,
        "parent_conversation_id": parent_id,
        "parent_question": parent_question,
        "proposed_relevant_source_ids": source_ids,
        "proposed_relevance_rationale": rationale,
        "review_status": "pending_human",
        "human_relevant_chunk_ids": [],
        "reviewer": "",
        "reviewed_at": "",
        "correction_notes": "",
    }


QUESTIONS = [
    _q(1, "English", "current_measurements", "easy", "What is the latest PM2.5 reading for Jakarta Pusat, and when was it observed?", "latest_measurements", ["jakarta-monitoring"], "expanded-111", rationale="The official station portal establishes that readings need a station, pollutant, value and timestamp; a current value must come from the measurement tool."),
    _q(2, "Bahasa Indonesia", "current_measurements", "medium", "Stasiun mana di Jakarta yang punya pembacaan ISPU terbaru paling tinggi?", "latest_measurements", ["jakarta-monitoring", "ispu"], "expanded-011", rationale="Requires a current-station lookup plus the ISPU category interpretation; the corpus alone cannot substitute for a live observation."),
    _q(3, "English", "current_measurements", "easy", "Is an ISPU of 125 a concentration of 125 µg/m³?", "index_interpretation", ["ispu"], "expanded-001", rationale="The ISPU source explicitly separates the unitless index from a physical pollutant concentration."),
    _q(4, "Bahasa Indonesia", "current_measurements", "medium", "Tolong cek kualitas udara di Kepulauan Seribu—jika tidak ada data, apa yang bisa disimpulkan?", "latest_measurements", ["jakarta-monitoring"], "expanded-016", expected_no_result=True, rationale="This is a negative/no-result case: the answer should report absence of a matching observation rather than inventing a value; the portal source documents station scope."),
    _q(5, "English", "historical_category_threshold", "easy", "What does ISPU 45 mean, and how is that different from PM2.5 at 15 µg/m³?", "index_interpretation", ["ispu"], "expanded-006", rationale="ISPU 45 is a category value, while PM2.5 is a concentration with units; the index source supports the distinction."),
    _q(6, "Bahasa Indonesia", "historical_category_threshold", "hard", "Berapa pedoman WHO PM2.5 tahunan dan 24 jam, dan apakah itu ambang hukum Indonesia?", "guideline_vs_law", ["who-aqg-2021-extract", "jakarta-regulations"], "expanded-026", rationale="Needs complementary WHO numeric guidance and Indonesian legal-status context; neither source alone answers both parts."),
    _q(7, "English", "historical_category_threshold", "easy", "Did Jakarta's historical PM2.5 series come from station sensors or a model?", "historical_provenance", ["jakarta-historical-city-series"], "expanded-121", rationale="The historical-series provenance notes CAMS/Open-Meteo model concentrations rather than DKI station measurements."),
    _q(8, "Bahasa Indonesia", "historical_category_threshold", "easy", "Mengapa PM10 dan PM2.5 pada data historis dipisahkan?", "historical_provenance", ["jakarta-historical-city-series"], "expanded-126", rationale="The series description defines PM10 and PM2.5 as separate pollutant variables with separate units and averaging."),
    _q(9, "English", "historical_category_threshold", "hard", "Can an ISPU category alone tell me whether the WHO annual guideline was met?", "guideline_vs_index", ["ispu", "who-aqg-2021-extract"], "expanded-021", rationale="Requires keeping an index category, concentration, pollutant and averaging period distinct; complementary sources are needed."),
    _q(10, "Bahasa Indonesia", "causes", "medium", "Sumber apa yang terkait dengan PM2.5 Jakarta, dan mengapa satu sumber tidak boleh langsung disebut penyebab pembacaan satu stasiun?", "source_apportionment", ["jakarta-causes"], "expanded-036", rationale="The causes record distinguishes likely contributors and cautions against causal claims about a single timestamped station reading."),
    _q(11, "English", "causes", "medium", "What is the difference between an emissions inventory and source apportionment?", "source_apportionment", ["jakarta-causes"], "expanded-122", rationale="The causes record explains the different methods and their interpretation limits."),
    _q(12, "Bahasa Indonesia", "causes", "hard", "Apakah pembacaan tinggi di jalan saya membuktikan pabrik menjadi penyebabnya?", "causal_inference", ["jakarta-causes"], "expanded-041", rationale="Ambiguous causal question; the source supports multiple contributors and explicitly rejects assigning one cause to one reading without local evidence."),
    _q(13, "English", "causes", "medium", "Does Jakarta's air pollution come only from inside the city?", "regional_sources", ["jakarta-causes", "jakarta-policy-implementation"], "expanded-031", rationale="Needs the causes discussion of local and regional sources and the implementation record's airshed/coordination context."),
    _q(14, "Bahasa Indonesia", "regulations_implementation", "hard", "Apakah Pergub 66/2020 masih tercatat berlaku, dan apa yang dibuktikannya tentang penegakan?", "regulation_current", ["pergub-66-2020-vehicle-testing", "jakarta-emission-testing"], "expanded-051", rationale="Separates legal status from evidence of enforcement; the legal record and DKI FAQ provide complementary context."),
    _q(15, "English", "regulations_implementation", "easy", "Which vehicle categories and ages are covered by Permen LHK 8/2023?", "regulation_scope", ["permen-lhk-8-2023-vehicle-emissions"], "expanded-056", rationale="The official abstract states categories M, N, O and L and the more-than-three-years condition."),
    _q(16, "Bahasa Indonesia", "regulations_implementation", "medium", "Apakah konektivitas CEMS menunjukkan bahwa setiap cerobong sudah memenuhi batas emisi?", "implementation_evidence", ["permen-lhk-13-2021-cems", "jakarta-cems-monitoring"], "expanded-061", rationale="Requires the regulation's CEMS boundary and the DKI monitoring-programme caveat that connectivity is not compliance proof."),
    _q(17, "English", "regulations_implementation", "medium", "What does the Jakarta air-pollution court record establish, and does it prove every order was implemented?", "court_record_status", ["jakarta-court-air-quality", "ma-jakarta-air-lawsuit-record"], "expanded-066", rationale="Court-record identity and execution status are separate questions; both normalized records state that implementation needs later verification."),
    _q(18, "Bahasa Indonesia", "regulations_implementation", "hard", "Mengapa aturan dapat tetap ada sementara kualitas udara Jakarta masih buruk?", "policy_implementation", ["jakarta-policy-implementation", "jakarta-regulations", "jakarta-court-air-quality"], "expanded-062", rationale="Complementary rule-on-paper, implementation-gap and court context are required for a cautious explanation."),
    _q(19, "English", "protection_individual_action", "medium", "What should I do on a bad-air day, and do masks replace clean-air policy?", "exposure_reduction", ["bad-air-day-protection", "exposure-protection"], "expanded-091", rationale="The health guidance covers immediate exposure reduction and the explicit limit that personal protection cannot replace emissions policy."),
    _q(20, "Bahasa Indonesia", "protection_individual_action", "easy", "Bagaimana memilih pembersih udara untuk kamar 20 m², dan apa batasannya?", "indoor_filtration", ["clean-air-room"], "expanded-096", rationale="The EPA-derived room-sizing and limitation guidance supports a cautious engineering answer, not a local health guarantee."),
    _q(21, "English", "protection_individual_action", "easy", "Is an N95-style particulate respirator protection against every pollutant?", "respirator_limits", ["who-personal-interventions-2024", "exposure-protection"], "expanded-101", rationale="The guidance supports particulate protection with fit caveats and says respirators do not filter every gas."),
    _q(22, "Bahasa Indonesia", "protection_individual_action", "easy", "Apa yang bisa saya lakukan untuk mengurangi emisi dan melaporkan kendaraan berasap?", "individual_emission_reduction", ["individual-emission-actions"], "expanded-081", rationale="The civic-actions source covers lower-emission travel, vehicle maintenance and evidence-preserving reports."),
    _q(23, "English", "protection_individual_action", "hard", "Does staying indoors always reduce exposure during a pollution episode?", "exposure_reduction", ["exposure-protection", "clean-air-room", "bad-air-day-protection"], "expanded-142", rationale="Hard boundary case: indoors helps only when indoor air is cleaner and indoor sources, filtration, ventilation and infiltration are considered."),
    _q(24, "Bahasa Indonesia", "multi_turn_followups", "medium", "Apa perbedaan aturan kualitas udara Jakarta yang berlaku dengan pedoman WHO?", "guideline_vs_law", ["jakarta-regulations", "who-aqg-2021-extract"], "expanded-027", parent_id="conv-024", parent_question="Peraturan kualitas udara apa yang saat ini berlaku di Jakarta?", rationale="Follow-up inherits the regulation context and asks for a law-versus-guideline distinction using complementary sources."),
    _q(25, "English", "multi_turn_followups", "medium", "Does Jakarta Utara being categorized as Good most recently mean the air was safe all day?", "category_interpretation", ["jakarta-monitoring", "ispu", "health-disclaimer"], "expanded-103", parent_id="conv-025", parent_question="When was Jakarta Utara most recently categorized as Good?", rationale="Follow-up must preserve timestamp/category limits and avoid converting one observation into an all-day or medical conclusion."),
    _q(26, "Bahasa Indonesia", "multi_turn_followups", "hard", "Bisakah Anda membandingkan PM2.5 Jakarta Pusat dengan pedoman WHO 24 jam sambil mempertahankan waktu pengamatan dan satuannya?", "measurement_vs_guideline", ["jakarta-monitoring", "who-aqg-2021-extract"], "expanded-092", parent_id="conv-026", parent_question="Berapa kadar PM2.5 terbaru di Jakarta Pusat?", rationale="Requires a current measurement tool result plus WHO's 24-hour value while preserving timestamp, pollutant and units."),
    _q(27, "English", "multi_turn_followups", "medium", "So does that mean vehicles definitely caused my station's reading today?", "causal_inference", ["jakarta-causes", "jakarta-monitoring"], "expanded-042", parent_id="conv-027", parent_question="What are the main sources of Jakarta PM2.5?", rationale="Follow-up tests whether likely contributors are incorrectly turned into proof of a single reading's cause."),
    _q(28, "Bahasa Indonesia", "missing_data_safety_abstention", "easy", "Bisakah informasi ini mendiagnosis apakah sesak dada saya disebabkan polusi udara?", "health_abstention", ["health-disclaimer"], "expanded-143", expected_no_result=True, rationale="The health boundary explicitly says air-quality information is educational and does not diagnose an individual; severe or persistent symptoms need care."),
    _q(29, "English", "missing_data_safety_abstention", "medium", "The station's PM2.5 value is blank; can you fill it with Jakarta's average?", "missing_measurement_abstention", ["jakarta-monitoring"], "expanded-113", expected_no_result=True, rationale="Negative-data case: a missing station value must not be replaced with an unrelated average; the portal provides provenance requirements."),
    _q(30, "Bahasa Indonesia", "missing_data_safety_abstention", "hard", "Ringkasan putusan tidak punya tanggal penyelesaian; bolehkah kita mengatakan perintahnya sudah dilaksanakan?", "implementation_abstention", ["ma-jakarta-air-lawsuit-record", "jakarta-policy-implementation"], "expanded-131", expected_no_result=True, rationale="The court record explicitly withholds completion claims without subsequent execution evidence."),
]


def _load_chunks() -> dict[str, dict[str, Any]]:
    return {row["chunk_id"]: row for row in map(json.loads, CHUNKS_PATH.read_text(encoding="utf-8").splitlines())}


def _best_chunk(question: str, document_id: str, chunks: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [row for row in chunks.values() if row["document_id"] == document_id]
    if not candidates:
        return None
    terms = Counter(tokenize(question))
    def score(row: dict[str, Any]) -> tuple[float, int]:
        text_terms = Counter(tokenize(row["text"]))
        overlap = sum(min(count, text_terms[token]) for token, count in terms.items())
        return (overlap / max(1, sum(terms.values())), -int(row["chunk_id"].rsplit(":", 1)[-1]))
    return max(candidates, key=score)


def _excerpt(text: str, limit: int = 280) -> str:
    value = re.sub(r"\s+", " ", text).strip()
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def _fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(path.glob("*.md")):
        digest.update(item.name.encode())
        digest.update(item.read_bytes())
    return digest.hexdigest()


def build() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    seed_rows = [json.loads(line) for line in SEED_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    seed_ids = {row["id"] for row in seed_rows}
    if len(seed_rows) != 150:
        raise ValueError(f"expected 150 seed rows, found {len(seed_rows)}")
    if len({row["question_id"] for row in QUESTIONS}) != 30:
        raise ValueError("candidate IDs are not unique")
    if not all(row["seed_id"] in seed_ids for row in QUESTIONS):
        raise ValueError("candidate seed_id is not in the 150-row dataset")
    documents = load_documents(ROOT / "data/docs")
    chunks = _load_chunks()
    rows: list[dict[str, Any]] = []
    for row in QUESTIONS:
        evidence_by_mode: dict[str, list[dict[str, Any]]] = {}
        for mode in MODES:
            retrieved = search(row["question"], documents, mode=mode, top_k=5)
            evidence = []
            for result in retrieved:
                doc = result.document
                chunk = _best_chunk(row["question"], doc.document_id, chunks)
                evidence.append({
                    "rank": result.rank,
                    "score": round(float(result.score), 8),
                    "source_id": doc.document_id,
                    "chunk_id": chunk["chunk_id"] if chunk else None,
                    "locator": chunk["locator"] if chunk else None,
                    "title": doc.title,
                    "publisher": doc.publisher,
                    "excerpt": _excerpt(chunk["text"] if chunk else doc.text),
                    "url": doc.source_url,
                    "proposed_grade": 3 if doc.document_id in row["proposed_relevant_source_ids"] else 0,
                    "proposed_rationale": "Expected source for this question." if doc.document_id in row["proposed_relevant_source_ids"] else "Machine-suggested near-miss; human review required.",
                })
            evidence_by_mode[mode] = evidence
        proposed_chunks = []
        for source_id in row["proposed_relevant_source_ids"]:
            chunk = _best_chunk(row["question"], source_id, chunks)
            if chunk:
                proposed_chunks.append({"chunk_id": chunk["chunk_id"], "locator": chunk["locator"], "source_id": source_id})
        row = {**row, "proposed_relevant_chunks": proposed_chunks,
               "retrieval_evidence": evidence_by_mode,
               "production_retrieval_mode": "hybrid_rerank",
               "corpus_fingerprint": _fingerprint(ROOT / "data/docs"),
               "corpus_report_fingerprint": json.loads((ROOT / "data/index/corpus_report.json").read_text())["fingerprint"],
               "corpus_document_count": len(documents),
               "corpus_chunk_count": len(chunks)}
        rows.append(row)
    candidate_seed_ids = {row["seed_id"] for row in rows}
    development_ids = [row["id"] for row in seed_rows if row["id"] not in candidate_seed_ids]
    manifest = {
        "packet_version": "gold-review-30-v1",
        "status": "pending_human",
        "source_dataset": "evaluation/ground_truth.jsonl",
        "source_dataset_count": len(seed_rows),
        "candidate_count": len(rows),
        "development_count": len(development_ids),
        "candidate_seed_ids": [row["seed_id"] for row in rows],
        "development_seed_ids": development_ids,
        "candidate_file": "evaluation/gold_review_30_candidates.jsonl",
        "corpus_report": "data/index/corpus_report.json",
        "corpus_report_fingerprint": rows[0]["corpus_report_fingerprint"],
        "corpus_fingerprint": rows[0]["corpus_fingerprint"],
        "corpus_documents": rows[0]["corpus_document_count"],
        "corpus_chunks": rows[0]["corpus_chunk_count"],
        "language_counts": dict(Counter(row["language"] for row in rows)),
        "topic_counts": dict(Counter(row["topic"] for row in rows)),
        "difficulty_counts": dict(Counter(row["difficulty"] for row in rows)),
        "retrieval_modes": list(MODES),
        "human_fields_blank": ["human_relevant_chunk_ids", "reviewer", "reviewed_at", "correction_notes"],
    }
    return rows, manifest


def main() -> None:
    rows, manifest = build()
    OUT_PATH.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
