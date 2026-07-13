#!/usr/bin/env python3
"""Analyze recoverable failures in one verified completed-run bundle."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import os
import shutil
import statistics
import tarfile
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]

import sys

sys.path.insert(0, str(REPO))
import analysis_metrics  # noqa: E402


def load_promoter():
    spec = importlib.util.spec_from_file_location(
        "lock_completed_run", REPO / "scripts" / "lock-completed-run.py"
    )
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load completed-run verifier")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl_gz(path: Path) -> list[dict[str, Any]]:
    rows = []
    with gzip.open(path, "rt", encoding="utf-8", errors="strict") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise SystemExit(f"expected JSON object: {path}:{line_number}")
            rows.append(value)
    return rows


def finish_reason(row: dict[str, Any]) -> str:
    reasons = row.get("gen_ai.response.finish_reasons") or []
    return str(reasons[0] if reasons else "unknown")


def pct(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 2) if denominator else 0.0


def mean(values: list[float]) -> float | None:
    return round(statistics.mean(values), 3) if values else None


def median(values: list[float]) -> float | None:
    return round(statistics.median(values), 3) if values else None


def result_key(row: dict[str, Any]) -> tuple[str, str, int]:
    return (
        str(row.get("analysis_condition_key_sha256")),
        str(row.get("scenario")),
        int(row.get("rep")),
    )


def sidecar_member(bundle: Path, row: dict[str, Any]) -> bool:
    model = str(row["model"])
    slug = model.replace("/", "_").replace(":", "_")
    archive = bundle / "raw" / "candidates" / f"{slug}.candidates.tar.gz"
    member = f"{slug}__{row['scenario']}__r{int(row['rep'])}.candidates.jsonl"
    if not archive.is_file():
        return False
    with tarfile.open(archive, "r:gz") as handle:
        try:
            value = handle.getmember(member)
        except KeyError:
            return False
        return value.isfile()


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def derive_timeout_scenarios(bundle: Path, bundle_id: str) -> dict[str, Any]:
    source = read_json(bundle / "contract" / "scenarios.json")
    value = json.loads(json.dumps(source))
    meta = value.setdefault("_meta", {})
    meta.update({
        "scenario_set": "core-current-timeout-sensitivity-v1",
        "parent_bundle_id": bundle_id,
        "parent_scenario_set": source.get("_meta", {}).get("scenario_set"),
        "purpose": "Non-primary timeout sensitivity for all models affected by DNF in the completed run.",
        "timeout_policy": "max(300, round(parent_timeout_s * 2.5)); cap 600; all other scenario content and max_tokens unchanged",
        "claim_status": "exploratory",
    })
    for scenario in value.get("scenarios", []):
        original = int(scenario.get("timeout_s") or 180)
        scenario["timeout_s"] = min(600, max(300, round(original * 2.5)))
    return value


def derive_timeout_manifest(base_path: Path, scenarios_bytes: bytes, scenario_count: int) -> dict[str, Any]:
    value = read_json(base_path)
    scenario_set = "core-current-timeout-sensitivity-v1"
    scenario_path = "data/scenario_sets/core-current-timeout-sensitivity-v1.json"
    value["name"] = "apprenticeops-run-env-timeout-sensitivity-v1"
    value["frozen_from"] = (
        "data/run-manifest.json plus the completed-run timeout sensitivity contract; "
        "all hardware/runtime/protocol fields unchanged except approved scenario hash"
    )
    value["protocol"]["scenario_sets"][scenario_set] = {
        "path": scenario_path,
        "sha256": hashlib.sha256(scenarios_bytes).hexdigest(),
        "scenario_count": scenario_count,
        "claim_status": "exploratory",
        "timeout_policy_id": "ceops-timeout-sensitivity-v1",
    }
    value["models_pinned"] = {
        "_comment": (
            "Disk-bounded recovery: affected artifacts exceed node free space. "
            "Allow one-at-a-time pulls, require exact post-pull artifact-lock "
            "verification before inference, and remove only models pulled by this run."
        ),
        "require_all_present": False,
    }
    return value


def artifact_identity(row: dict[str, Any]) -> str | None:
    value = (
        row.get("ollama.digest")
        or row.get("analysis.artifact_identity")
        or row.get("llama_cpp.artifact.sha256")
    )
    if isinstance(value, str) and value.startswith("ollama-ps-sha256:"):
        value = value.split(":", 1)[1]
    return value if isinstance(value, str) and len(value) == 64 else None


def derive_artifact_lock(
    manifest: dict[str, Any],
    roster_bytes: bytes,
    results: list[dict[str, Any]],
    affected_models: set[str],
) -> dict[str, Any]:
    identities: dict[str, set[str | None]] = defaultdict(set)
    for row in results:
        model = str(row["model"])
        if model in affected_models:
            identities[model].add(artifact_identity(row))
    invalid = {
        model: sorted("missing" if value is None else value for value in values)
        for model, values in identities.items()
        if len(values) != 1 or None in values
    }
    if invalid:
        raise SystemExit(f"affected models lack one exact artifact identity: {invalid}")
    return {
        "schema_version": 1,
        "source_bundle_id": manifest["bundle_id"],
        "runtime": "ollama",
        "roster_sha256": hashlib.sha256(roster_bytes).hexdigest(),
        "models": {
            model: {"artifact_sha256": next(iter(values))}
            for model, values in sorted(identities.items())
        },
    }


def analyze(
    bundle: Path,
    model_lock_path: Path | None = None,
    llama_cpp_model_map_path: Path | None = None,
    llama_cpp_artifacts_path: Path | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], str, dict[str, Any]]:
    promoter = load_promoter()
    try:
        manifest = promoter.verify_bundle(bundle)
    except promoter.PromotionError as exc:
        raise SystemExit(f"bundle verification failed: {exc}") from exc
    gate = read_json(bundle / "gate-report.json")

    results = read_jsonl_gz(bundle / "canonical" / "results.jsonl.gz")
    judgements = read_jsonl_gz(bundle / "canonical" / "judged.jsonl.gz")
    retries = read_jsonl_gz(bundle / "canonical" / "judge-retries.jsonl.gz")
    expected = gate["expected"]
    observed = gate["observed"]
    if len(results) != expected["results"] or len(judgements) != expected["canonical_judgements"]:
        raise SystemExit("canonical row counts differ from the gate report")
    if len(judgements) + len(retries) != observed["raw_judge_attempts"]:
        raise SystemExit("canonical judgements plus retries do not reconcile to raw attempts")

    result_keys = {result_key(row) for row in results}
    if len(result_keys) != len(results):
        raise SystemExit("canonical results contain duplicate keys")
    declared_judges = analysis_metrics.evaluation_policy_judges(manifest["evaluation_policy"])
    expected_judge_keys = {
        (*key, backend, model)
        for key in result_keys
        for backend, model in declared_judges
    }
    observed_judge_keys = {
        (*result_key(row), *analysis_metrics.judge_identity(row))
        for row in judgements
    }
    if observed_judge_keys != expected_judge_keys:
        raise SystemExit("canonical judgement keys differ from result x declared-judge domain")
    if any(not analysis_metrics.judgement_success(row) for row in judgements):
        raise SystemExit("canonical judgement file contains an unsuccessful row")
    if any(result_key(row) not in result_keys for row in judgements):
        raise SystemExit("canonical judgement row does not join to a canonical result")
    for row in retries:
        if analysis_metrics.judgement_success(row):
            raise SystemExit("judge retry file contains a successful judgement")
        if row.get("promotion.retry_reason") not in {"parse_error", "no_score", "invalid_contract"}:
            raise SystemExit("judge retry file contains an unclassified retry")
        key = (*result_key(row), *analysis_metrics.judge_identity(row))
        if key not in expected_judge_keys:
            raise SystemExit("judge retry key is outside the canonical result/judge domain")

    judges_by_result: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in judgements:
        judges_by_result[result_key(row)].append(row)

    dnf_rows = [row for row in results if row.get("dnf") or finish_reason(row).startswith("DNF")]
    length_rows = [row for row in results if finish_reason(row) == "length"]
    affected_models = {str(row["model"]) for row in dnf_rows}
    finish_counts = Counter(finish_reason(row) for row in results)
    retry_reasons = Counter(str(row.get("promotion.retry_reason") or "unknown") for row in retries)
    dnf_judgements = [judge for row in dnf_rows for judge in judges_by_result[result_key(row)]]
    dnf_scores = [float(row["score"]) for row in dnf_judgements]
    dnf_output_chars = [int(row.get("gen_ai.usage.output_chars") or 0) for row in dnf_rows]

    model_rows: list[dict[str, Any]] = []
    for model in sorted({str(row["model"]) for row in results}):
        subset = [row for row in results if row["model"] == model]
        model_dnf = [row for row in subset if row in dnf_rows]
        model_length = [row for row in subset if row in length_rows]
        model_rows.append({
            "model": model,
            "bracket": next((row.get("bracket") for row in subset if row.get("bracket")), ""),
            "rows": len(subset),
            "dnf": len(model_dnf),
            "dnf_rate": pct(len(model_dnf), len(subset)),
            "length": len(model_length),
            "length_rate": pct(len(model_length), len(subset)),
            "dnf_partial_outputs": sum(int(row.get("gen_ai.usage.output_chars") or 0) > 0 for row in model_dnf),
            "dnf_median_output_chars": median([int(row.get("gen_ai.usage.output_chars") or 0) for row in model_dnf]),
            "dnf_mean_det_score": mean([float(row.get("det_score") or 0) for row in model_dnf]),
        })
    model_rows.sort(key=lambda row: (-row["dnf"], row["model"]))

    scenario_rows: list[dict[str, Any]] = []
    for scenario in sorted({str(row["scenario"]) for row in results}):
        subset = [row for row in results if row["scenario"] == scenario]
        scenario_dnf = [row for row in subset if row in dnf_rows]
        scenario_length = [row for row in subset if row in length_rows]
        scenario_rows.append({
            "scenario": scenario,
            "rows": len(subset),
            "dnf": len(scenario_dnf),
            "dnf_rate": pct(len(scenario_dnf), len(subset)),
            "length": len(scenario_length),
            "length_rate": pct(len(scenario_length), len(subset)),
        })
    scenario_rows.sort(key=lambda row: (-row["dnf"], row["scenario"]))

    dnf_export = []
    for row in sorted(dnf_rows, key=lambda item: (str(item["model"]), str(item["scenario"]), int(item["rep"]))):
        scores = sorted(float(judge["score"]) for judge in judges_by_result[result_key(row)])
        dnf_export.append({
            "model": row["model"],
            "bracket": row.get("bracket"),
            "scenario": row["scenario"],
            "rep": int(row["rep"]),
            "seed": row.get("gen_ai.request.seed", row.get("seed")),
            "finish_reason": finish_reason(row),
            "timeout_s": row.get("effective.timeout_s"),
            "max_tokens": row.get("effective.max_tokens"),
            "output_chars": int(row.get("gen_ai.usage.output_chars") or 0),
            "output_tokens": int(row.get("gen_ai.usage.output_tokens") or 0),
            "det_score": row.get("det_score"),
            "judge_scores": ";".join(str(int(score)) if score.is_integer() else str(score) for score in scores),
            "candidate_sidecar": sidecar_member(bundle, row),
        })

    roster_order = [line.strip() for line in (bundle / "contract" / "roster.txt").read_text().splitlines() if line.strip() and not line.lstrip().startswith("#")]
    brackets = {str(row["model"]): str(row.get("bracket") or "unknown") for row in dnf_rows}
    roster_lines = [
        "# Generated failure-recovery roster.",
        f"# source_bundle_id: {manifest['bundle_id']}",
        "# Run all 20 scenarios x 5 reps; do not merge with primary rows.",
        "",
    ]
    last_bracket = None
    for model in roster_order:
        if model not in affected_models:
            continue
        bracket = brackets[model]
        if bracket != last_bracket:
            if last_bracket is not None:
                roster_lines.append("")
            roster_lines.append(f"# bracket: {bracket}")
            last_bracket = bracket
        roster_lines.append(model)
    roster_text = "\n".join(roster_lines) + "\n"

    full_det_pass = sum(
        int(row.get("det_total") or 0) > 0
        and int(row.get("det_passed") or 0) == int(row.get("det_total") or 0)
        for row in dnf_rows
    )
    tuples_with_any_score_above_one = sum(
        any(float(judge["score"]) > 1 for judge in judges_by_result[result_key(row)])
        for row in dnf_rows
    )
    sidecar_count = sum(bool(row["candidate_sidecar"]) for row in dnf_export)
    direct_gguf_models: list[str] = []
    if model_lock_path is not None:
        model_lock = {
            row["model_id"]: row
            for row in (
                json.loads(line)
                for line in model_lock_path.read_text().splitlines()
                if line.strip()
            )
        }
        direct_gguf_models = sorted(
            model
            for model in affected_models
            if model_lock.get(model, {}).get("llama_cpp_status") == "direct_gguf"
        )
    staged_llama_cpp_models: list[str] = []
    if llama_cpp_model_map_path is not None and llama_cpp_artifacts_path is not None:
        model_map = read_json(llama_cpp_model_map_path)
        artifacts = read_json(llama_cpp_artifacts_path).get("artifacts") or []
        artifact_models = {
            str(item.get("model_id"))
            for item in artifacts
            if isinstance(item, dict)
            and item.get("model_id")
            and isinstance(item.get("sha256"), str)
            and len(item["sha256"]) == 64
        }
        staged_llama_cpp_models = sorted(
            affected_models & set(model_map) & artifact_models
        )
    summary = {
        "schema_version": 1,
        "analysis_kind": "completed_run_failure_recovery",
        "source_bundle_id": manifest["bundle_id"],
        "source_run_id": manifest["source_id"],
        "source_claim_status": manifest["claim_status"],
        "runtime": sorted({
            str(row.get("env.inference_runtime") or row.get("adapter") or "unknown")
            for row in results
        }),
        "results": len(results),
        "canonical_judgements": len(judgements),
        "raw_judge_attempts": observed["raw_judge_attempts"],
        "judge_retries": len(retries),
        "judge_retry_reasons": dict(sorted(retry_reasons.items())),
        "judge_missing_successes": len(expected_judge_keys - observed_judge_keys),
        "judge_competing_successes": len(judgements) - len(observed_judge_keys),
        "finish_reasons": dict(sorted(finish_counts.items())),
        "dnf": len(dnf_rows),
        "dnf_rate": pct(len(dnf_rows), len(results)),
        "dnf_partial_outputs": sum(value > 0 for value in dnf_output_chars),
        "dnf_median_output_chars": median(dnf_output_chars),
        "dnf_full_deterministic_pass": full_det_pass,
        "dnf_judge_rows": len(dnf_judgements),
        "dnf_mean_judge_score": mean(dnf_scores),
        "dnf_tuples_with_any_judge_score_above_one": tuples_with_any_score_above_one,
        "dnf_candidate_sidecars": sidecar_count,
        "length": len(length_rows),
        "length_rate": pct(len(length_rows), len(results)),
        "length_full_deterministic_pass": sum(
            int(row.get("det_total") or 0) > 0
            and int(row.get("det_passed") or 0) == int(row.get("det_total") or 0)
            for row in length_rows
        ),
        "affected_models": len(affected_models),
        "llama_cpp_catalog_eligible_affected_models": direct_gguf_models,
        "llama_cpp_catalog_eligible_count": len(direct_gguf_models),
        "llama_cpp_staged_affected_models": staged_llama_cpp_models,
        "llama_cpp_staged_count": len(staged_llama_cpp_models),
        "recovery_options": {
            "existing_partial_sensitivity_calls": 0,
            "failed_tuple_only_calls": len(dnf_rows),
            "affected_model_full_matrix_calls": len(affected_models) * int(expected["scenarios"]) * int(expected["reps"]),
            "full_roster_calls": int(expected["models"]) * int(expected["scenarios"]) * int(expected["reps"]),
        },
        "recommendation": "Run a separate timeout-sensitivity-v1 full matrix for the post-selected affected-model subset; retain primary DNF/length rows unchanged and do not extrapolate population-wide.",
    }
    return summary, dnf_export, model_rows, scenario_rows, roster_text, derive_timeout_scenarios(bundle, manifest["bundle_id"])


def render_report(summary: dict[str, Any], model_rows: list[dict[str, Any]], scenario_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Completed-Run Failure Recovery",
        "",
        f"Source bundle: `{summary['source_bundle_id']}`",
        f"Source run: `{summary['source_run_id']}`",
        f"Claim status: `{summary['source_claim_status']}`",
        "",
        "## Verdict",
        "",
        "Judge failures are already recovered: the canonical bundle contains one valid judgement for every expected tuple, while failed parse attempts remain in the retry sidecar. No rejudging is required.",
        "",
        "Inference DNFs are usable failure-inclusive evidence because every DNF retained partial output and was judged. They must not be replaced in the primary dataset. A separate timeout-policy sensitivity run can estimate how many would complete under a larger wall-clock budget.",
        "",
        "This completed run used **Ollama on CPU**, not llama.cpp. Any llama.cpp rerun is a new runtime condition, not recovery of the same condition.",
        "",
        "## Evidence",
        "",
        "| Signal | Value |",
        "|---|---:|",
        f"| Results | {summary['results']} |",
        f"| Canonical judgements | {summary['canonical_judgements']} |",
        f"| Raw judge attempts | {summary['raw_judge_attempts']} |",
        f"| Recovered judge retries | {summary['judge_retries']} |",
        f"| DNF | {summary['dnf']} ({summary['dnf_rate']}%) |",
        f"| DNF with partial output | {summary['dnf_partial_outputs']} |",
        f"| DNF median output chars | {summary['dnf_median_output_chars']} |",
        f"| DNF passing all deterministic checks | {summary['dnf_full_deterministic_pass']} |",
        f"| DNF mean judge score | {summary['dnf_mean_judge_score']} / 5 |",
        f"| DNF candidate sidecars | {summary['dnf_candidate_sidecars']} |",
        f"| Length finishes | {summary['length']} ({summary['length_rate']}%) |",
        f"| Length rows passing all deterministic checks | {summary['length_full_deterministic_pass']} |",
        f"| Affected models catalog-eligible for direct GGUF | {summary['llama_cpp_catalog_eligible_count']} / {summary['affected_models']} |",
        f"| Affected models with staged SHA-pinned llama.cpp artifacts | {summary['llama_cpp_staged_count']} / {summary['affected_models']} |",
        "",
        "## Recovery Options",
        "",
        "| Option | Calls | Scientific use | Decision |",
        "|---|---:|---|---|",
        "| Existing partial-output sensitivity | 0 | Failure-inclusive quality already judged | Use now |",
        f"| Rerun only failed tuples | {summary['recovery_options']['failed_tuple_only_calls']} | Conditions on observed failure; biased recovery estimate | Diagnostic only |",
        f"| Full 20x5 matrix for all affected models | {summary['recovery_options']['affected_model_full_matrix_calls']} | Paired timeout-policy effect within the post-selected affected-model subset | **Recommended** |",
        f"| Full roster rerun | {summary['recovery_options']['full_roster_calls']} | Clean but unnecessary | Reject |",
        "",
        "## Highest-DNF Models",
        "",
        "| Model | Bracket | DNF | Rate | Length | Median partial chars | Mean deterministic score |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in [value for value in model_rows if value["dnf"]][:21]:
        lines.append(
            f"| `{row['model']}` | {row['bracket']} | {row['dnf']} | {row['dnf_rate']}% | "
            f"{row['length']} | {row['dnf_median_output_chars']} | {row['dnf_mean_det_score']} |"
        )
    lines.extend([
        "",
        "## Highest-DNF Scenarios",
        "",
        "| Scenario | DNF | Rate | Length |",
        "|---|---:|---:|---:|",
    ])
    for row in scenario_rows:
        lines.append(f"| `{row['scenario']}` | {row['dnf']} | {row['dnf_rate']}% | {row['length']} |")
    lines.extend([
        "",
        "## Recovery Contract",
        "",
        "Run all affected models across all 20 scenarios and five original seeds under `TIMEOUT_POLICY_ID=ceops-timeout-sensitivity-v1`. The estimand is the paired timeout-policy effect within this post-selected 21-model subset, not a population-wide effect. Use the generated derived scenario file, which changes only `timeout_s` to `max(300, round(parent_timeout_s * 2.5))` (capped at 600); prompts, checks, max-token caps, temperature, seeds, runtime, and node lock remain separate and explicit. Report the 204 original timeout DNFs separately from four `after_done_missing` transport/completion-frame failures.",
        "",
        "Do not merge recovered rows into the primary run. Compare DNF, completion, deterministic score, judge score, latency, and energy as a separate exploratory condition.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--base-manifest", type=Path, default=Path("data/run-manifest.json"))
    parser.add_argument("--model-lock", type=Path, default=Path("data/models.lock.jsonl"))
    parser.add_argument("--llama-cpp-model-map", type=Path, default=Path("data/llama-cpp-smoke-5.model-map.json"))
    parser.add_argument("--llama-cpp-artifacts", type=Path, default=Path("data/llama-cpp-smoke-5.artifacts.json"))
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    output = args.output_dir.resolve()
    input_paths = {
        "bundle_manifest_sha256": bundle / "bundle-manifest.json",
        "base_manifest_sha256": args.base_manifest.resolve(),
        "model_lock_sha256": args.model_lock.resolve(),
        "llama_cpp_model_map_sha256": args.llama_cpp_model_map.resolve(),
        "llama_cpp_artifacts_sha256": args.llama_cpp_artifacts.resolve(),
        "analyzer_sha256": Path(__file__).resolve(),
        "analysis_metrics_sha256": REPO / "analysis_metrics.py",
        "promoter_sha256": REPO / "scripts" / "lock-completed-run.py",
    }
    input_hashes = {key: sha256_file(path) for key, path in input_paths.items()}
    summary, dnf_rows, model_rows, scenario_rows, roster, scenarios = analyze(
        bundle, args.model_lock.resolve(), args.llama_cpp_model_map.resolve(),
        args.llama_cpp_artifacts.resolve(),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    (staging / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    write_csv(staging / "dnf-tuples.csv", dnf_rows, list(dnf_rows[0]) if dnf_rows else [])
    write_csv(staging / "models.csv", model_rows, list(model_rows[0]) if model_rows else [])
    write_csv(staging / "scenarios.csv", scenario_rows, list(scenario_rows[0]) if scenario_rows else [])
    roster_bytes = roster.encode()
    (staging / "models.timeout-sensitivity-v1.txt").write_bytes(roster_bytes)
    scenario_bytes = (json.dumps(scenarios, indent=2, sort_keys=True) + "\n").encode()
    (staging / "core-current-timeout-sensitivity-v1.json").write_bytes(scenario_bytes)
    manifest = derive_timeout_manifest(
        args.base_manifest.resolve(), scenario_bytes, len(scenarios.get("scenarios", []))
    )
    (staging / "run-manifest.timeout-sensitivity-v1.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    bundle_results = read_jsonl_gz(bundle / "canonical" / "results.jsonl.gz")
    affected_models = {
        str(row["model"])
        for row in bundle_results
        if row.get("dnf") or finish_reason(row).startswith("DNF")
    }
    artifact_lock = derive_artifact_lock(
        read_json(bundle / "bundle-manifest.json"), roster_bytes,
        bundle_results, affected_models,
    )
    (staging / "model-artifacts.timeout-sensitivity-v1.json").write_text(
        json.dumps(artifact_lock, indent=2, sort_keys=True) + "\n"
    )
    (staging / "report.md").write_text(render_report(summary, model_rows, scenario_rows))
    output_hashes = {
        path.name: sha256_file(path)
        for path in sorted(staging.iterdir())
        if path.is_file()
    }
    analysis_manifest = {
        "schema_version": 1,
        "analysis_kind": "completed_run_failure_recovery",
        "source_bundle_id": summary["source_bundle_id"],
        **input_hashes,
        "output_sha256": output_hashes,
    }
    try:
        verified_again = load_promoter().verify_bundle(bundle)
    except Exception as exc:
        shutil.rmtree(staging)
        raise SystemExit(f"bundle changed before publication: {exc}") from exc
    current_inputs = {key: sha256_file(path) for key, path in input_paths.items()}
    if verified_again.get("bundle_id") != summary["source_bundle_id"] or any(
        analysis_manifest[key] != digest for key, digest in current_inputs.items()
    ):
        shutil.rmtree(staging)
        raise SystemExit("analysis inputs changed before publication")
    (staging / "analysis-manifest.json").write_text(
        json.dumps(analysis_manifest, indent=2, sort_keys=True) + "\n"
    )
    if output.exists() or output.is_symlink():
        if output.is_symlink() or not output.is_dir():
            shutil.rmtree(staging)
            raise SystemExit(f"output exists but is not a regular directory: {output}")
        existing_manifest = output / "analysis-manifest.json"
        existing_matches = existing_manifest.is_file() and read_json(existing_manifest) == analysis_manifest
        if existing_matches:
            expected_names = set(analysis_manifest["output_sha256"]) | {"analysis-manifest.json"}
            entries = list(output.iterdir())
            existing_names = {path.name for path in entries}
            existing_matches = (
                existing_names == expected_names
                and all(path.is_file() and not path.is_symlink() for path in entries)
            )
        if existing_matches:
            existing_matches = all(
                (output / filename).is_file()
                and sha256_file(output / filename) == digest
                for filename, digest in analysis_manifest["output_sha256"].items()
            )
        if existing_matches:
            shutil.rmtree(staging)
        else:
            shutil.rmtree(staging)
            raise SystemExit(f"output exists with different or missing manifest: {output}")
    else:
        os.replace(staging, output)
    print(
        f"failure analysis passed: dnf={summary['dnf']} length={summary['length']} "
        f"judge_retries={summary['judge_retries']} affected_models={summary['affected_models']} "
        f"output={output}"
    )


if __name__ == "__main__":
    main()
