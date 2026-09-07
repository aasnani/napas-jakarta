"""Reproducible offline ingestion/idempotency evaluation."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

from ingestion.flow import run_ingestion


def evaluate() -> dict:
    root = Path(__file__).parents[1]
    configured_source = os.environ.pop("SOURCE_DATA_URL", None)
    try:
        with tempfile.TemporaryDirectory(prefix="napas-ingestion-") as directory:
            data_dir = Path(directory) / "data"
            shutil.copytree(root / "data/docs", data_dir / "docs")
            shutil.copytree(root / "data/demo", data_dir / "demo")
            first = run_ingestion(data_dir)
            first_report = json.loads((data_dir / "ingestion_report.json").read_text())
            second = run_ingestion(data_dir)
            second_report = json.loads((data_dir / "ingestion_report.json").read_text())
    finally:
        if configured_source is not None:
            os.environ["SOURCE_DATA_URL"] = configured_source
    return {
        "runs": 2,
        "first_counts": first,
        "second_counts": second,
        "idempotent_fingerprint": first_report["measurement_sha256"] == second_report["measurement_sha256"],
        "validation": first_report["validation"],
        "status": "offline deterministic ingestion evaluation",
    }


if __name__ == "__main__":
    result = evaluate()
    Path("evaluation/results/ingestion_results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
