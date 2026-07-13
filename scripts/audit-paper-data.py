#!/usr/bin/env python3
"""Audit committed ApprenticeOps paper/data artifacts for structural consistency."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import analysis_metrics  # noqa: E402

REPO = Path(__file__).resolve().parents[1]

REQUIRED_SITE = [
    "data/site/summary.json",
    "data/site/models.csv",
    "data/site/models.json",
    "data/site/controlled_models.csv",
    "data/site/pareto.csv",
    "data/site/quality_safety_pareto.csv",
    "data/site/axis_quality.csv",
    "data/site/axis_safety_arm.csv",
    "data/site/axis_safety_bracket.csv",
    "data/site/axis_energy.csv",
    "data/site/judge_pairs.csv",
]

REQUIRED_SNAPSHOTS = [
    "data/snapshots/results_snapshot.csv",
    "data/snapshots/judged_snapshot.csv",
    "data/snapshots/judged_snapshot.det.csv",
]

STRICT_RUNS = {
    "external-v1-spread10-baseline-clean-20260703-164337": {
        "allow_legacy_persistence": True,
        "judges": ("copilot:claude-opus-4.6", "copilot:gpt-5.4"),
    },
}


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
        "analysis_schema_version": 1,
        "source_id": "paper-94-model-corrected-v1",
        "claim_status": "locked",
        "breadth_analysis_scope": "quality_safety_94_functional_models",
        "breadth_model_count": 94,
        "breadth_quality_safety_pareto_count": 2,
        "controlled_analysis_scope": "var_base_clock_1700_turbo_off_package0",
        "controlled_model_count": 24,
        "controlled_three_axis_pareto_count": 7,
        "controlled_three_axis_dominated_count": 17,
        "energy_cross_batch_comparison_allowed": False,
        "quality_knee_grouping_kind": "legacy_footprint_bracket",
        "quality_knee_grouping_value": "2-3B",
        "quality_2_3B_pct": 51.3,
        "quality_3_4B_pct": 52.1,
        "quality_4_5GB_pct": 56.8,
        "quality_4_5gb_minus_3_4b_points": 4.6,
        "quality_4_5gb_minus_3_4b_ci_low_points": 1.9,
        "quality_4_5gb_minus_3_4b_ci_high_points": 7.4,
        "safety_instruct_pct": 71.4,
        "safety_reasoning_pct": 47.2,
        "safety_instruct_minus_reasoning_points": 24.2,
        "safety_instruct_minus_reasoning_ci_low_points": 15.2,
        "safety_instruct_minus_reasoning_ci_high_points": 32.5,
        "contrast_interval_method": "paired scenario-cluster bootstrap, 10000 samples",
        "controlled_three_axis_pick": "qwen3:4b-instruct-2507-q4_K_M",
        "controlled_quality_max_model": "qwen3:4b-instruct-2507-q8_0",
        "breadth_quality_max_model": "hf.co/unsloth/Qwen3-4B-GGUF:Q4_K_M",
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            fail(f"summary {key}={summary.get(key)!r} expected {value!r}")
    if (summary["controlled_three_axis_pareto_count"]
            + summary["controlled_three_axis_dominated_count"]
            != summary["controlled_model_count"]):
        fail("controlled Pareto and dominated counts must equal controlled population")
    pareto_rows = count_csv_rows("data/site/pareto.csv")
    quality_safety_pareto_rows = count_csv_rows("data/site/quality_safety_pareto.csv")
    model_rows = count_csv_rows("data/site/models.csv")
    controlled_rows = count_csv_rows("data/site/controlled_models.csv")
    if pareto_rows != summary["controlled_three_axis_pareto_count"]:
        fail("pareto.csv does not match controlled Pareto count")
    if quality_safety_pareto_rows != summary["breadth_quality_safety_pareto_count"]:
        fail("quality_safety_pareto.csv does not match breadth Pareto count")
    if model_rows != summary["breadth_model_count"]:
        fail("models.csv does not match breadth model count")
    if controlled_rows != summary["controlled_model_count"]:
        fail("controlled_models.csv does not match controlled model count")
    if count_csv_rows("data/site/judge_pairs.csv") != 8_909:
        fail("judge_pairs.csv must contain the locked 8,909 paired judgements")
    models_csv = list(csv.DictReader((REPO / "data/site/models.csv").open(newline="")))
    models_json = json.loads((REPO / "data/site/models.json").read_text())
    numeric_fields = {
        "judge_score_fraction",
        "safety_fraction",
    }
    normalized_csv = []
    for row in models_csv:
        item: dict[str, object] = {}
        for key, value in row.items():
            if value == "":
                item[key] = None
            elif key == "analysis_schema_version":
                item[key] = int(value)
            elif key in numeric_fields:
                item[key] = round(float(value), 10)
            elif key == "quality_safety_pareto":
                item[key] = value == "True"
            else:
                item[key] = value
        normalized_csv.append(item)
    if models_json != normalized_csv:
        fail("models.json does not mirror models.csv")
    print("site summary audit passed")


def audit_snapshots() -> None:
    for path in REQUIRED_SNAPSHOTS:
        require_file(path)
    result_rows = count_csv_rows("data/snapshots/results_snapshot.csv")
    judged_rows = count_csv_rows("data/snapshots/judged_snapshot.csv")
    det_rows = count_csv_rows("data/snapshots/judged_snapshot.det.csv")
    expected_rows = {
        "data/snapshots/results_snapshot.csv": 9_025,
        "data/snapshots/judged_snapshot.csv": 9_025,
        "data/snapshots/judged_snapshot.det.csv": 475,
    }
    observed_rows = {
        "data/snapshots/results_snapshot.csv": result_rows,
        "data/snapshots/judged_snapshot.csv": judged_rows,
        "data/snapshots/judged_snapshot.det.csv": det_rows,
    }
    if observed_rows != expected_rows:
        fail(f"snapshot row counts changed: {observed_rows!r}")
    for relative_path in REQUIRED_SNAPSHOTS:
        with (REPO / relative_path).open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        if "runtime_adapter" not in (rows[0].keys() if rows else []):
            fail(f"{relative_path} is missing required runtime_adapter column")
        adapters = {row.get("runtime_adapter") for row in rows}
        if not adapters <= {"ollama", "llama_cpp", "llama_cpp_server"}:
            fail(f"{relative_path} has invalid adapter values: {sorted(adapters)}")
        versions = {row.get("analysis_schema_version") for row in rows}
        if versions != {"1"}:
            fail(f"{relative_path} analysis schema values changed: {sorted(versions)}")
    with (REPO / "data/snapshots/results_snapshot.csv").open(newline="") as handle:
        result_data = list(csv.DictReader(handle))
    result_by_key = {
        (row["runtime_adapter"], row["model"], row["scenario"], row["rep"]): row
        for row in result_data
    }
    if len(result_by_key) != len(result_data):
        fail("results snapshot has duplicate runtime/model/scenario/repetition keys")
    with (REPO / "data/snapshots/judged_snapshot.csv").open(newline="") as handle:
        judged_data = list(csv.DictReader(handle))
    judged_by_key = {
        (row["runtime_adapter"], row["model"], row["scenario"], row["rep"]): row
        for row in judged_data
    }
    if len(judged_by_key) != len(judged_data) or set(judged_by_key) != set(result_by_key):
        fail("judged snapshot is not one-to-one with frozen result provenance")
    for key, judged_row in judged_by_key.items():
        result_row = result_by_key[key]
        for field in ("collection_batch", "cpu_frequency_regime"):
            if judged_row.get(field) != result_row.get(field):
                fail(f"judged snapshot provenance mismatch for {key}: {field}")
    provenance = Counter(
        (
            row.get("collection_batch"),
            row.get("cpu_frequency_regime"),
            row.get("power_source"),
            row.get("energy_analysis_scope"),
        )
        for row in result_data
    )
    expected_provenance = Counter({
        ("var", "base_clock_1700_turbo_off", "rapl:package-0", "controlled_three_axis"): 2_375,
        ("wave2", "dynamic_above_base_turbo_on", "rapl:package-0", "descriptive_only"): 6_080,
        ("wave2", "dynamic_above_base_turbo_on", "rapl:psys", "descriptive_only"): 570,
    })
    if provenance != expected_provenance:
        fail(f"snapshot power-regime provenance changed: {dict(provenance)!r}")
    print(f"snapshot audit passed: results={result_rows} judged={judged_rows} det={det_rows}")


def audit_analysis_contract() -> None:
    path = require_file("data/analysis.schema.json")
    schema = analysis_metrics.load_analysis_schema(str(path))
    if schema.get("status") != "corrected-final":
        fail("analysis schema must have status=corrected-final")
    global_forbidden = set(schema.get("global_forbidden_columns") or [])
    artifacts = schema.get("artifacts") or {}
    if not artifacts:
        fail("analysis schema has no artifact contracts")
    for name, contract in artifacts.items():
        required = set(contract.get("required_columns") or contract.get("required_keys") or [])
        if not required:
            fail(f"analysis artifact contract has no required fields: {name}")
        overlap = required & global_forbidden
        if overlap:
            fail(f"analysis artifact {name} requires globally forbidden fields: {sorted(overlap)}")
    print(f"analysis schema v1 contract audit passed: artifacts={len(artifacts)}")


def audit_strict_runs() -> None:
    for run_id, policy in STRICT_RUNS.items():
        run_path = REPO / "data/runs" / run_id
        require_file(str(Path("data/runs") / run_id / "run.meta"))
        if not run_path.exists():
            fail(f"missing committed run directory: {run_id}")
        command = [sys.executable, "scripts/report-run-quality.py", "--strict"]
        if policy["allow_legacy_persistence"]:
            command.append("--allow-legacy-persistence")
        for judge in policy["judges"]:
            command.extend(["--judge", judge])
        command.append(str(run_path))
        run_check(command)


def main() -> None:
    run_check([sys.executable, "scripts/validate-analysis-environment.py"])
    run_check([sys.executable, "scripts/audit-tool-licenses.py"])
    audit_analysis_contract()
    run_check([sys.executable, "scripts/validate-analysis-schema.py"])
    run_check([sys.executable, "scripts/export-judge-pairs.py", "--check"])
    audit_site_summary()
    audit_snapshots()
    run_check([sys.executable, "scripts/validate-model-lock.py"])
    run_check([sys.executable, "scripts/audit-model-metadata.py"])
    run_check([sys.executable, "scripts/validate-runtime-policy.py"])
    run_check([sys.executable, "scripts/test-run-env-static.py"])
    run_check([sys.executable, "scripts/test-judge-row-schema.py"])
    run_check([sys.executable, "scripts/test-lock-completed-run.py"])
    run_check([sys.executable, "scripts/test-report-run-quality.py"])
    run_check([sys.executable, "scripts/test-analysis-metrics.py"])
    run_check([sys.executable, "scripts/test-compare-notebook-outputs.py"])
    run_check([sys.executable, "scripts/test-report.py"])
    run_check([sys.executable, "scripts/test-dataset.py"])
    run_check([sys.executable, "scripts/test-merge-wave.py"])
    run_check([sys.executable, "scripts/test-human-eval.py"])
    run_check([sys.executable, "scripts/validate-human-eval.py"])
    run_check([sys.executable, "scripts/test-croissant.py"])
    run_check([sys.executable, "scripts/audit-release-metadata.py"])
    run_check([sys.executable, "scripts/validate-external-candidates.py"])
    run_check([sys.executable, "scripts/validate-scenarios.py"])
    audit_strict_runs()
    print("paper/data artifact audit passed")


if __name__ == "__main__":
    main()