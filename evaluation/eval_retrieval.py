from __future__ import annotations

import csv
import hashlib
import json
import math
import time
from pathlib import Path

from app.data import load_documents
from app.retrieval import search


def evaluate(data_dir: str | Path = "data", ground_truth: str | Path = "evaluation/ground_truth.jsonl") -> list[dict]:
    documents = load_documents(Path(data_dir) / "docs")
    rows = [json.loads(line) for line in Path(ground_truth).read_text().splitlines()]
    results = []
    for mode in ("bm25", "dense", "hybrid", "hybrid_rerank"):
        hits = 0
        reciprocal_rank = 0.0
        ndcg = 0.0
        latencies = []
        language_stats: dict[str, dict[str, int]] = {}
        multi_source_hits = 0
        multi_source_total = 0
        for row in rows:
            started = time.perf_counter()
            retrieved = search(row["question"], documents, mode=mode, top_k=5)
            latencies.append((time.perf_counter() - started) * 1000)
            gains = [int(result.document.document_id in row["relevant_document_ids"])
                     for result in retrieved]
            language = row.get("language", "unknown")
            stats = language_stats.setdefault(language, {"hits": 0, "total": 0})
            stats["total"] += 1
            if any(gains):
                stats["hits"] += 1
            if len(row["relevant_document_ids"]) > 1:
                multi_source_total += 1
                if all(document_id in {result.document.document_id for result in retrieved}
                       for document_id in row["relevant_document_ids"]):
                    multi_source_hits += 1
            dcg = sum(gain / math.log2(rank + 1) for rank, gain in enumerate(gains, 1))
            ideal = sum(1 / math.log2(rank + 1)
                        for rank in range(1, min(len(row["relevant_document_ids"]), 5) + 1))
            ndcg += dcg / ideal if ideal else 0.0
            for result in retrieved:
                if result.document.document_id in row["relevant_document_ids"]:
                    hits += 1
                    reciprocal_rank += 1 / result.rank
                    break
        results.append(
            {
                "mode": mode,
                "hit_rate_at_5": round(hits / len(rows), 4),
                "mrr_at_5": round(reciprocal_rank / len(rows), 4),
                "ndcg_at_5": round(ndcg / len(rows), 4),
                "p50_latency_ms": round(sorted(latencies)[len(latencies) // 2], 4),
                "questions": len(rows),
                "language_hit_rate_at_5": {
                    lang: round(values["hits"] / values["total"], 4)
                    for lang, values in language_stats.items()
                },
                "multi_source_recall_at_5": round(
                    multi_source_hits / multi_source_total, 4) if multi_source_total else None,
            }
        )
    return results


def write_artifacts(results: list[dict], output_dir: str | Path = "evaluation/results") -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    with (output / "retrieval_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("mode", "hit_rate_at_5", "mrr_at_5",
                                                    "ndcg_at_5", "p50_latency_ms", "questions",
                                                    "language_hit_rate_at_5",
                                                    "multi_source_recall_at_5"))
        writer.writeheader()
        writer.writerows({**row, "language_hit_rate_at_5": json.dumps(
            row["language_hit_rate_at_5"], ensure_ascii=False)} for row in results)
    corpus_hash = hashlib.sha256()
    for path in sorted(Path("data/docs").glob("*.md")):
        corpus_hash.update(path.name.encode())
        corpus_hash.update(path.read_bytes())
    payload = {"corpus": "expanded-v1", "corpus_sha256": corpus_hash.hexdigest(),
               "questions": sum(results[0]["questions"] for _ in [0]), "results": results,
               "status": "150-question stratified seed benchmark; human review pending"}
    (output / "retrieval_results.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = ["# Retrieval evaluation — 150-question expanded-corpus benchmark", "", "This is an offline benchmark over the expanded corpus. Questions are stratified seed labels and carry `review_status=seeded_pending_human_review`; manually review them before submission.", "",
             "| Mode | Hit rate@5 | MRR@5 | nDCG@5 | p50 latency (ms) |",
             "|---|---:|---:|---:|---:|"]
    lines.extend(f"| {row['mode']} | {row['hit_rate_at_5']:.4f} | {row['mrr_at_5']:.4f} | "
                 f"{row['ndcg_at_5']:.4f} | {row['p50_latency_ms']:.4f} |" for row in results)
    lines.extend(["", "Language hit@5 and multi-source recall:", ""])
    for row in results:
        language = ", ".join(f"{key}={value:.4f}" for key, value in
                              row["language_hit_rate_at_5"].items())
        lines.append(f"- **{row['mode']}** — {language}; multi-source="
                     f"{row['multi_source_recall_at_5']}")
    (output / "retrieval_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    _write_plot(results, output / "retrieval_plot.png")


def _write_plot(results: list[dict], path: Path) -> None:
    """Write a dependency-light PNG comparison for README/reviewer discovery."""
    from PIL import Image, ImageDraw, ImageFont

    width, height = 1200, 650
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 18)
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
    except OSError:
        font = title_font = ImageFont.load_default()
    draw.text((40, 25), "Napas Jakarta retrieval comparison (expanded corpus)",
              fill="#17202a", font=title_font)
    chart_left, chart_top, chart_width, chart_height = 80, 100, 1060, 430
    draw.rectangle((chart_left, chart_top, chart_left + chart_width, chart_top + chart_height),
                   outline="#8a99a8", width=2)
    metrics = (("Hit@5", "hit_rate_at_5", "#2e86de"),
               ("MRR@5", "mrr_at_5", "#27ae60"),
               ("nDCG@5", "ndcg_at_5", "#8e44ad"))
    group_width = chart_width / max(len(results), 1)
    bar_width = group_width / 5
    for tick in range(0, 11, 2):
        y = chart_top + chart_height - (tick / 10) * chart_height
        draw.line((chart_left, y, chart_left + chart_width, y), fill="#e5e7e9", width=1)
        draw.text((chart_left - 38, y - 10), f"{tick / 10:.1f}", fill="#34495e", font=font)
    for index, row in enumerate(results):
        base_x = chart_left + index * group_width + group_width * 0.18
        for metric_index, (_, key, color) in enumerate(metrics):
            value = max(0.0, min(1.0, float(row[key])))
            x0 = base_x + metric_index * bar_width
            y0 = chart_top + chart_height - value * chart_height
            draw.rectangle((x0, y0, x0 + bar_width - 4, chart_top + chart_height), fill=color)
        label = str(row["mode"])
        draw.text((chart_left + index * group_width + 5, chart_top + chart_height + 12),
                  label, fill="#17202a", font=font)
    legend_x = 80
    for label, _, color in metrics:
        draw.rectangle((legend_x, 585, legend_x + 18, 603), fill=color)
        draw.text((legend_x + 25, 582), label, fill="#17202a", font=font)
        legend_x += 150
    image.save(path, format="PNG")


if __name__ == "__main__":
    evaluated = evaluate()
    write_artifacts(evaluated)
    print(json.dumps(evaluated, indent=2))
