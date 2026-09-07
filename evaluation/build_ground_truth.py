"""Build a stratified seed benchmark for the expanded corpus.

Generated rows remain explicitly pending human review.
"""

from __future__ import annotations

import json
from pathlib import Path

BASE = [
    ("What does ISPU 125 mean?", "Apa arti ISPU 125?", ["ispu"], "policy"),
    ("Where can I find official Jakarta monitoring stations?", "Di mana saya dapat menemukan stasiun pemantauan resmi Jakarta?", ["jakarta-monitoring"], "methodology"),
    ("Are WHO air-quality guidelines Indonesian law?", "Apakah pedoman kualitas udara WHO merupakan hukum Indonesia?", ["who-guidance", "jakarta-regulations"], "regulation"),
    ("What are the main sources of Jakarta PM2.5?", "Apa sumber utama PM2.5 di Jakarta?", ["jakarta-causes"], "causes"),
    ("How do transport, industry, and open burning affect Jakarta air?", "Bagaimana transportasi, industri, dan pembakaran terbuka memengaruhi udara Jakarta?", ["jakarta-causes"], "causes"),
    ("Which Jakarta air-quality regulations are currently in force?", "Peraturan kualitas udara apa yang saat ini berlaku di Jakarta?", ["jakarta-regulations"], "regulation"),
    ("Why was the Jakarta ERP proposal delayed?", "Mengapa usulan ERP Jakarta tertunda?", ["jakarta-policy-status"], "policy_history"),
    ("What interventions could improve Jakarta air quality?", "Intervensi apa yang dapat memperbaiki kualitas udara Jakarta?", ["jakarta-improvements"], "improvement"),
    ("How can an individual reduce their contribution to pollution?", "Bagaimana seseorang dapat mengurangi kontribusinya terhadap polusi?", ["jakarta-improvements"], "individual_emissions"),
    ("How can I reduce my exposure on a polluted day?", "Bagaimana saya mengurangi paparan pada hari yang berpolusi?", ["exposure-protection"], "exposure"),
    ("Is a high-rise apartment always safer than ground level?", "Apakah apartemen bertingkat tinggi selalu lebih aman daripada lantai dasar?", ["vertical-exposure"], "vertical_exposure"),
    ("Why must an observation timestamp be shown?", "Mengapa waktu pengamatan harus ditampilkan?", ["jakarta-monitoring"], "methodology"),
    ("What is the difference between source apportionment and an emissions inventory?", "Apa perbedaan antara source apportionment dan inventarisasi emisi?", ["jakarta-causes"], "causality"),
    ("What does the ERP policy status mean as of 2025?", "Apa status kebijakan ERP per tahun 2025?", ["jakarta-policy-status"], "policy_history"),
    ("How should parents respond when air quality is unhealthy?", "Apa yang sebaiknya dilakukan orang tua saat kualitas udara tidak sehat?", ["exposure-protection"], "exposure"),
]

PREFIXES = {
    "English": ["", "Please explain: ", "In simple terms, ", "For a Jakarta resident, ", "What does the evidence say about this: "],
    "Bahasa Indonesia": ["", "Tolong jelaskan: ", "Secara sederhana, ", "Untuk warga Jakarta, ", "Apa kata bukti resmi tentang ini: "],
}


def build(output: str | Path = "evaluation/ground_truth.jsonl") -> int:
    rows = []
    for english, indonesian, sources, intent in BASE:
        for language, prefixes in PREFIXES.items():
            question = english if language == "English" else indonesian
            for prefix in prefixes:
                rows.append({"id": f"expanded-{len(rows) + 1:03d}", "question": prefix + question,
                             "relevant_document_ids": sources, "intent": intent,
                             "language": language, "review_status": "seeded_pending_human_review"})
    Path(output).write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n")
    return len(rows)


if __name__ == "__main__":
    print({"questions": build()})
