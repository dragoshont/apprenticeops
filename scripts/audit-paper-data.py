#!/usr/bin/env python3
"""Audit committed ApprenticeOps paper/data artifacts for structural consistency."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

REQUIRED_SITE = [
    "data/site/summary.json",
    "data/site/models.csv",
    "data/site/pareto.csv",
    "data/site/axis_quality.csv",
    "data/site/axis_safety_arm.csv",
    "data/site/axis_energy.csv",
    "data/site/judge_pairs.csv",
]

REQUIRED_SNAPSHOTS = [
    "data/snapshots/results_snapshot.csv",
    "data/snapshots/judged_snapshot.csv",
    "data/snapshots/judged_snapshot.det.csv",
]

STRICT_RUNS = [
    "external-v1-spread10-baseline-clean-20260703-164337",
]


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def require_file(relative_path: str) -> Path:
    path = REPO / relative_path
    if not path.exists():
        fail(f"missing required artifact: {relative_path}")
    if path.stat().st_size == 0:
        fail(f"empty required artifact: {relative_path}")
    return path


def count_csv_rows(relative_path: str) -> int:
    path = require_file(relative_path)
    with path.open(newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def run_check(command: list[str]) -> None:
    result = subprocess.run(command, cwd=REPO, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        print(result.stdout)
        fail(f"command failed: {' '.join(command)}")
    print(result.stdout.strip())


def audit_site_summary() -> None:
    for path in REQUIRED_SITE:
        require_file(path)
    summary = json.loads((REPO / "data/site/summary.json").read_text())
    expected = {
        "n_models": 94,
        "n_pareto": 12,
        "n_dominated": 82,
        "quality_knee_bracket": "2-3B",
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            fail(f"summary {key}={summary.get(key)!r} expected {value!r}")
    if summary["n_pareto"] + summary["n_dominated"] != summary["n_models"]:
        fail("summary n_pareto + n_dominated must equal n_models")
    pareto_rows = count_csv_rows("data/site/pareto.csv")
    model_rows = count_csv_rows("data/site/models.csv")
    if pareto_rows != summary["n_pareto"]:
        fail(f"pareto.csv rows {pareto_rows} != n_pareto {summary['n_pareto']}")
    if model_rows != summary["n_models"]:
        fail(f"models.csv rows {model_rows} != n_models {summary['n_models']}")
    print("site summary audit passed")


def audit_snapshots() -> None:
    for path in REQUIRED_SNAPSHOTS:
        require_file(path)
    result_rows = count_csv_rows("data/snapshots/results_snapshot.csv")
    judged_rows = count_csv_rows("data/snapshots/judged_snapshot.csv")
    det_rows = count_csv_rows("data/snapshots/judged_snapshot.det.csv")
    if result_rows < 1 or judged_rows < 1 or det_rows < 1:
        fail("snapshot CSV files must contain rows")
    print(f"snapshot audit passed: results={result_rows} judged={judged_rows} det={det_rows}")


def audit_strict_runs() -> None:
    for run_id in STRICT_RUNS:
        run_path = REPO / "data/runs" / run_id
        require_file(str(Path("data/runs") / run_id / "run.meta"))
        if not run_path.exists():
            fail(f"missing committed run directory: {run_id}")
        run_check([sys.executable, "scripts/report-run-quality.py", "--strict", str(run_path)])


def main() -> None:
    audit_site_summary()
    audit_snapshots()
    run_check([sys.executable, "scripts/validate-model-lock.py"])
    run_check([sys.executable, "scripts/audit-model-metadata.py"])
    run_check([sys.executable, "scripts/test-run-env-static.py"])
    run_check([sys.executable, "scripts/validate-human-eval.py"])
    run_check([sys.executable, "scripts/validate-external-candidates.py"])
    run_check([sys.executable, "scripts/validate-scenarios.py"])
    audit_strict_runs()
    print("paper/data artifact audit passed")


if __name__ == "__main__":
    main()