#!/usr/bin/env python3
"""Regression tests for completed-run failure recovery analysis."""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "analyze-completed-run-failures.py"
SPEC = importlib.util.spec_from_file_location("analyze_completed_run_failures", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def write_gzip(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            for row in rows:
                compressed.write(json.dumps(row, sort_keys=True).encode() + b"\n")


def build_bundle(root: Path) -> tuple[Path, Path, Path, Path, Path]:
    bundle = root / "bundle"
    (bundle / "canonical").mkdir(parents=True)
    (bundle / "contract").mkdir()
    (bundle / "raw" / "candidates").mkdir(parents=True)
    (bundle / "contract" / "roster.txt").write_text("# bracket: 3-4B\nmodel-a\n")
    (bundle / "contract" / "scenarios.json").write_text(json.dumps({
        "_meta": {"scenario_set": "fixture"},
        "scenarios": [
            {"id": "ok", "timeout_s": 120, "max_tokens": 512},
            {"id": "timeout", "timeout_s": 150, "max_tokens": 650},
            {"id": "length", "timeout_s": 120, "max_tokens": 512},
        ],
    }))
    base = {
        "model": "model-a", "bracket": "3-4B", "rep": 0,
        "analysis_condition_key_sha256": "condition", "env.inference_runtime": "ollama",
        "ollama.digest": "d" * 64,
    }
    write_gzip(bundle / "canonical" / "results.jsonl.gz", [
        {**base, "scenario": "ok", "dnf": False, "gen_ai.response.finish_reasons": ["stop"], "det_passed": 1, "det_total": 1},
        {**base, "scenario": "timeout", "dnf": True, "gen_ai.response.finish_reasons": ["DNF:timeout"], "gen_ai.usage.output_chars": 200, "gen_ai.usage.output_tokens": 50, "gen_ai.request.seed": 1, "effective.timeout_s": 150, "effective.max_tokens": 650, "det_passed": 2, "det_total": 2, "det_score": 1.0},
        {**base, "scenario": "length", "dnf": False, "gen_ai.response.finish_reasons": ["length"], "gen_ai.usage.output_tokens": 512, "det_passed": 1, "det_total": 1},
    ])
    write_gzip(bundle / "canonical" / "judged.jsonl.gz", [
        {"analysis_condition_key_sha256": "condition", "scenario": "ok", "rep": 0, "judge_backend": "copilot", "judge_model": "claude", "score": 4, "verdict": "ok", "evidence": "valid", "criteria_met": [], "criteria_missed": []},
        {"analysis_condition_key_sha256": "condition", "scenario": "timeout", "rep": 0, "judge_backend": "copilot", "judge_model": "claude", "score": 2, "verdict": "partial", "evidence": "valid", "criteria_met": [], "criteria_missed": []},
        {"analysis_condition_key_sha256": "condition", "scenario": "length", "rep": 0, "judge_backend": "copilot", "judge_model": "claude", "score": 3, "verdict": "partial", "evidence": "valid", "criteria_met": [], "criteria_missed": []},
    ])
    write_gzip(bundle / "canonical" / "judge-retries.jsonl.gz", [{
        "analysis_condition_key_sha256": "condition", "scenario": "timeout", "rep": 0,
        "judge_backend": "copilot", "judge_model": "claude", "score": None,
        "verdict": "garbled", "evidence": "parse_error", "criteria_met": [],
        "criteria_missed": ["judge response could not be parsed"],
        "promotion.retry_reason": "parse_error",
    }])
    archive = bundle / "raw" / "candidates" / "model-a.candidates.tar.gz"
    payload = b'{"candidate_index":0}\n'
    with tarfile.open(archive, "w:gz") as handle:
        info = tarfile.TarInfo("model-a__timeout__r0.candidates.jsonl")
        info.size = len(payload)
        handle.addfile(info, io.BytesIO(payload))
    (bundle / "gate-report.json").write_text(json.dumps({
        "passed": True,
        "expected": {"results": 3, "canonical_judgements": 3, "models": 1, "scenarios": 3, "reps": 1},
        "observed": {"raw_judge_attempts": 4},
    }))
    (bundle / "promotion-ledger.jsonl").write_text("")
    source_hashes = {
        path.relative_to(bundle).as_posix(): module.sha256_file(path)
        for path in bundle.rglob("*")
        if path.is_file() and path.name != "promotion-ledger.jsonl"
    }
    canonical = json.dumps(source_hashes, sort_keys=True, separators=(",", ":")).encode()
    (bundle / "bundle-manifest.json").write_text(json.dumps({
        "analysis_schema_version": 1,
        "bundle_id": hashlib.sha256(canonical).hexdigest(),
        "bundle_state": "locked",
        "claim_status": "provisional",
        "evaluation_policy": "deterministic-checks-v1|judges:copilot:claude",
        "source_id": "fixture-run",
        "source_kind": "completed_run",
        "source_sha256": source_hashes,
    }))
    model_lock = root / "models.lock.jsonl"
    model_lock.write_text(json.dumps({"model_id": "model-a", "llama_cpp_status": "direct_gguf"}) + "\n")
    base_manifest = root / "run-manifest.json"
    base_manifest.write_text(json.dumps({
        "name": "base",
        "cpu": {"intel_pstate.no_turbo": "1"},
        "protocol": {"scenario_sets": {}},
    }))
    model_map = root / "model-map.json"
    model_map.write_text(json.dumps({"model-a": "/models/model-a.gguf"}))
    artifacts = root / "artifacts.json"
    artifacts.write_text(json.dumps({"artifacts": [{"model_id": "model-a", "sha256": "e" * 64}]}))
    return bundle, model_lock, base_manifest, model_map, artifacts


def refresh_bundle_manifest(bundle: Path) -> None:
    manifest = json.loads((bundle / "bundle-manifest.json").read_text())
    source_hashes = {
        path.relative_to(bundle).as_posix(): module.sha256_file(path)
        for path in bundle.rglob("*")
        if path.is_file() and path.name not in {"bundle-manifest.json", "promotion-ledger.jsonl"}
    }
    manifest["source_sha256"] = source_hashes
    manifest["bundle_id"] = hashlib.sha256(
        json.dumps(source_hashes, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    (bundle / "bundle-manifest.json").write_text(json.dumps(manifest))


def run_analysis(
    bundle: Path, output: Path, base_manifest: Path, model_lock: Path,
    model_map: Path, artifacts: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run([
        sys.executable, str(SCRIPT), "--bundle", str(bundle), "--output-dir", str(output),
        "--base-manifest", str(base_manifest), "--model-lock", str(model_lock),
        "--llama-cpp-model-map", str(model_map), "--llama-cpp-artifacts", str(artifacts),
    ], text=True, capture_output=True)


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    bundle, model_lock, base_manifest, model_map, artifacts = build_bundle(root)
    summary, dnf_rows, model_rows, scenario_rows, roster, scenarios = module.analyze(
        bundle, model_lock, model_map, artifacts
    )
    assert summary["dnf"] == 1
    assert summary["length"] == 1
    assert summary["judge_retries"] == 1
    assert summary["dnf_partial_outputs"] == 1
    assert summary["dnf_full_deterministic_pass"] == 1
    assert summary["dnf_mean_judge_score"] == 2.0
    assert summary["dnf_candidate_sidecars"] == 1
    assert summary["affected_models"] == 1
    assert summary["llama_cpp_catalog_eligible_count"] == 1
    assert summary["llama_cpp_staged_count"] == 1
    assert dnf_rows[0]["judge_scores"] == "2"
    assert model_rows[0]["dnf"] == 1
    assert scenario_rows[0]["scenario"] == "timeout"
    assert "# bracket: 3-4B\nmodel-a" in roster
    assert {row["timeout_s"] for row in scenarios["scenarios"]} == {300, 375}

    output = root / "analysis"
    result = run_analysis(bundle, output, base_manifest, model_lock, model_map, artifacts)
    assert result.returncode == 0, result.stdout + result.stderr
    analysis_manifest = json.loads((output / "analysis-manifest.json").read_text())
    assert analysis_manifest["analyzer_sha256"] == module.sha256_file(SCRIPT)
    assert analysis_manifest["analysis_metrics_sha256"] == module.sha256_file(REPO / "analysis_metrics.py")
    assert analysis_manifest["promoter_sha256"] == module.sha256_file(REPO / "scripts/lock-completed-run.py")
    for filename, digest in analysis_manifest["output_sha256"].items():
        assert module.sha256_file(output / filename) == digest
    artifact_lock = json.loads((output / "model-artifacts.timeout-sensitivity-v1.json").read_text())
    assert artifact_lock["models"] == {"model-a": {"artifact_sha256": "d" * 64}}
    assert artifact_lock["roster_sha256"] == module.sha256_file(output / "models.timeout-sensitivity-v1.txt")

    for entry_kind in ("file", "directory", "symlink"):
        exact_output = root / f"analysis-extra-{entry_kind}"
        result = run_analysis(bundle, exact_output, base_manifest, model_lock, model_map, artifacts)
        assert result.returncode == 0, result.stdout + result.stderr
        unexpected = exact_output / "unexpected"
        if entry_kind == "file":
            unexpected.write_text("unexpected\n")
        elif entry_kind == "directory":
            unexpected.mkdir()
        else:
            unexpected.symlink_to(exact_output / "summary.json")
        result = run_analysis(bundle, exact_output, base_manifest, model_lock, model_map, artifacts)
        assert result.returncode != 0, f"accepted unexpected {entry_kind}"

    retry_base = {
        "analysis_condition_key_sha256": "condition", "scenario": "timeout", "rep": 0,
        "judge_backend": "copilot", "judge_model": "claude", "score": None,
        "verdict": "garbled", "evidence": "parse_error", "criteria_met": [],
        "criteria_missed": ["judge response could not be parsed"],
        "promotion.retry_reason": "parse_error",
    }
    malformed_retries = {
        "successful": {**retry_base, "score": 2, "verdict": "partial", "evidence": "valid"},
        "unclassified": {**retry_base, "promotion.retry_reason": "unknown"},
        "undeclared": {**retry_base, "judge_model": "undeclared"},
    }
    for label, retry in malformed_retries.items():
        bad_retry_bundle = root / f"bad-retry-{label}"
        shutil.copytree(bundle, bad_retry_bundle)
        write_gzip(bad_retry_bundle / "canonical" / "judge-retries.jsonl.gz", [retry])
        refresh_bundle_manifest(bad_retry_bundle)
        refused_retry = root / f"refused-retry-{label}"
        result = run_analysis(
            bad_retry_bundle, refused_retry, base_manifest, model_lock, model_map, artifacts,
        )
        assert result.returncode != 0, f"accepted {label} retry"
        assert not refused_retry.exists()

    (output / "summary.json").write_text("tampered\n")
    result = run_analysis(bundle, output, base_manifest, model_lock, model_map, artifacts)
    assert result.returncode != 0
    try:
        module.derive_artifact_lock(
            {"bundle_id": "b" * 64}, b"model-a\n",
            [
                {"model": "model-a", "ollama.digest": "a" * 64},
                {"model": "model-a", "ollama.digest": "b" * 64},
            ],
            {"model-a"},
        )
    except SystemExit:
        pass
    else:
        raise AssertionError("artifact lock accepted digest drift across model rows")

    tampered = root / "tampered"
    shutil.copytree(bundle, tampered)
    with gzip.open(tampered / "canonical" / "results.jsonl.gz", "ab") as handle:
        handle.write(b"tamper")
    refused = root / "refused"
    result = run_analysis(tampered, refused, base_manifest, model_lock, model_map, artifacts)
    assert result.returncode != 0
    assert not refused.exists()

    bad_gate = json.loads((bundle / "gate-report.json").read_text())
    bad_gate["observed"]["raw_judge_attempts"] = 5
    (bundle / "gate-report.json").write_text(json.dumps(bad_gate))
    refresh_bundle_manifest(bundle)
    unreconciled = root / "unreconciled"
    result = run_analysis(bundle, unreconciled, base_manifest, model_lock, model_map, artifacts)
    assert result.returncode != 0
    assert not unreconciled.exists()

    scenario_bytes = (json.dumps(scenarios, indent=2, sort_keys=True) + "\n").encode()
    recovery_manifest = module.derive_timeout_manifest(base_manifest, scenario_bytes, 3)
    contract = recovery_manifest["protocol"]["scenario_sets"]["core-current-timeout-sensitivity-v1"]
    assert recovery_manifest["cpu"] == {"intel_pstate.no_turbo": "1"}
    assert contract["sha256"] == hashlib.sha256(scenario_bytes).hexdigest()
    assert contract["scenario_count"] == 3
    assert contract["timeout_policy_id"] == "ceops-timeout-sensitivity-v1"
    assert recovery_manifest["models_pinned"]["require_all_present"] is False
    assert "post-pull artifact-lock" in recovery_manifest["models_pinned"]["_comment"]

print("completed-run failure analysis tests passed")
