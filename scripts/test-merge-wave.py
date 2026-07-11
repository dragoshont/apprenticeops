#!/usr/bin/env python3
"""Regression tests for merge-wave snapshot adapter handling."""

from __future__ import annotations

import csv
import importlib.util
import json
import pathlib
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "merge-wave.py"
spec = importlib.util.spec_from_file_location("merge_wave", SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def complete_result_row() -> dict:
    return {
        "model": "m",
        "bracket": "0-1B",
        "scenario": "s",
        "rep": 0,
        "det_score": 1,
        "env.inference_runtime": "ollama",
        "env.run_id": "run-a",
        "env.cpu_no_turbo": "1",
        "env.cpu_governor": "performance",
        "env.cpu_min_perf_pct": "100",
        "env.cpu_max_perf_pct": "100",
        "power.source": "rapl:package-0",
        "power.energy_wh": 0.1,
        "gen_ai.response.finish_reasons": ["stop"],
        "dnf": False,
        "ollama.digest": "sha256:m",
        "ollama.quantization": "Q4_K_M",
        "env.host": "ai",
        "env.kernel": "linux",
        "env.rapl_domain": "package-0",
        "env.num_ctx": 8192,
        "env.ollama_version": "0.30.8",
        "prompt.template_sha256": "p",
        "env.memory_context": "none",
        "env.inference_strategy": "baseline",
        "temp": 0.7,
        "think": False,
        "ollama.parameters": "top_p 0.9",
        "env.scenario_set": "core",
        "env.scenarios_sha": "scenarios-sha",
    }


def test_adapter_is_part_of_snapshot_key() -> None:
    existing = [{
        "model": "m",
        "runtime_adapter": "ollama",
        "scenario": "s",
        "rep": "0",
        "det_score": "0.5",
    }]
    new_rows = [{
        "model": "m",
        "runtime_adapter": "llama_cpp",
        "scenario": "s",
        "rep": "0",
        "det_score": "0.6",
    }]
    added, replaced = mod.upsert(existing, new_rows, better=lambda nw, cur: mod.num(nw["det_score"]) > mod.num(cur["det_score"]))
    assert added == 1
    assert replaced == 0
    assert {row["runtime_adapter"] for row in existing} == {"ollama", "llama_cpp"}


def test_merge_wave_writes_adapter_column() -> None:
    with tempfile.TemporaryDirectory() as td:
        temp = pathlib.Path(td)
        results = temp / "results.jsonl"
        results_csv = temp / "results_snapshot.csv"
        model_lock = temp / "models.lock.jsonl"
        row = {
            "model": "m",
            "bracket": "0-1B",
            "scenario": "s",
            "rep": 0,
            "det_score": 1,
            "env.inference_runtime": "llama_cpp",
            "env.run_id": "test-run",
            "env.cpu_no_turbo": "1",
            "env.cpu_governor": "performance",
            "env.cpu_min_perf_pct": "100",
            "env.cpu_max_perf_pct": "100",
            "power.source": "rapl:package-0",
            "gen_ai.response.finish_reasons": ["stop"],
            "dnf": False,
        }
        results.write_text(json.dumps(row) + "\n")
        model_lock.write_text(json.dumps({"model_id": "m", "tier": "T1"}) + "\n")
        old_argv = mod.sys.argv
        try:
            mod.sys.argv = [
                "merge-wave.py", "--results", str(results),
                "--results-csv", str(results_csv),
                "--model-lock", str(model_lock), "--dry-run",
            ]
            mod.main()
        finally:
            mod.sys.argv = old_argv
        # Dry-run should not write; exercise the cell renderer directly too.
        assert mod.cell(row, "runtime_adapter") == "llama_cpp"


def test_legacy_snapshot_is_normalized_without_conflating_tiers() -> None:
    old = {
        "model": "m",
        "adapter": "ollama",
        "bracket": "4-5GB",
        "scenario": "s",
        "rep": "0",
        "decode_tok_s": "7.5",
        "param_count": "7615616512",
    }
    normalized = mod.normalize_existing(old, mod.RESULT_COLS, {"m": None})
    assert normalized["analysis_schema_version"] == "1"
    assert normalized["runtime_adapter"] == "ollama"
    assert normalized["parameter_tier"] == ""
    assert normalized["legacy_footprint_bracket"] == "4-5GB"
    assert normalized["decode_tokens_per_s"] == "7.5"
    assert "bracket" not in normalized


def test_canonical_snapshot_normalization_preserves_provenance() -> None:
    current = {
        "analysis_schema_version": "1",
        "model": "m",
        "runtime_adapter": "ollama",
        "parameter_tier": "T1",
        "legacy_footprint_bracket": "0-1B",
        "collection_batch": "run-a",
        "cpu_frequency_regime": "turbo_off_locked",
        "power_source": "rapl:package-0",
        "energy_analysis_scope": "descriptive_only",
        "scenario": "s",
        "rep": "0",
    }
    normalized = mod.normalize_existing(current, mod.RESULT_COLS, {"m": "T1"})
    for field in (
        "collection_batch",
        "cpu_frequency_regime",
        "power_source",
        "energy_analysis_scope",
    ):
        assert normalized[field] == current[field]


def test_raw_provenance_is_required_and_derived() -> None:
    row = {
        "env.run_id": "run-a",
        "env.cpu_no_turbo": "1",
        "env.cpu_governor": "performance",
        "env.cpu_min_perf_pct": "100",
        "env.cpu_max_perf_pct": "100",
        "power.source": "rapl:package-0",
        "power.energy_wh": 0.1,
    }
    provenance = mod.provenance_for_raw_row(row)
    assert provenance == {
        "collection_batch": "run-a",
        "cpu_frequency_regime": "performance_turbo_off_perf_100_100",
        "power_source": "rapl:package-0",
        "energy_analysis_scope": "descriptive_only",
    }
    try:
        mod.provenance_for_raw_row({"power.energy_wh": 0.1})
    except ValueError as exc:
        assert "collection_batch" in str(exc)
    else:
        raise AssertionError("new snapshot rows without provenance must fail closed")
    try:
        mod.provenance_for_raw_row({
            "env.run_id": "run-a",
            "cpu_frequency_regime": "base_clock_1700_turbo_off",
        })
    except ValueError as exc:
        assert "power_source" in str(exc)
    else:
        raise AssertionError("new snapshot rows without power provenance must fail closed")


def test_partial_judge_family_is_not_published_as_consensus() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = pathlib.Path(temp_dir)
        results = temp / "results.jsonl"
        judged = temp / "judged.jsonl"
        results_csv = temp / "results.csv"
        judged_csv = temp / "judged.csv"
        model_lock = temp / "models.lock.jsonl"
        row = complete_result_row()
        policy = "deterministic-checks-v1|judges:copilot:claude+copilot:gpt"
        identity = mod.analysis_metrics.analysis_condition(row, evaluation_policy=policy)
        results.write_text(json.dumps(row) + "\n")
        judged.write_text(json.dumps({
            "model": "m",
            "scenario": "s",
            "rep": 0,
            "analysis_condition_key_sha256": identity.sha256,
            "evaluation_policy": policy,
            "judge_backend": "copilot",
            "judge_model": "gpt",
            "score": 4,
        }) + "\n")
        model_lock.write_text(json.dumps({"model_id": "m", "tier": "T1"}) + "\n")
        old_argv = sys.argv
        try:
            sys.argv = [
                "merge-wave.py", "--results", str(results), "--judged", str(judged),
                "--results-csv", str(results_csv), "--judged-csv", str(judged_csv),
                "--model-lock", str(model_lock),
            ]
            mod.main()
        finally:
            sys.argv = old_argv
        with judged_csv.open(newline="") as handle:
            merged = list(csv.DictReader(handle))
        assert merged == []


def test_complete_judge_family_inherits_result_provenance() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = pathlib.Path(temp_dir)
        results = temp / "results.jsonl"
        judged = temp / "judged.jsonl"
        results_csv = temp / "results.csv"
        judged_csv = temp / "judged.csv"
        model_lock = temp / "models.lock.jsonl"
        row = complete_result_row()
        policy = "deterministic-checks-v1|judges:copilot:claude+github:gpt"
        identity = mod.analysis_metrics.analysis_condition(row, evaluation_policy=policy)
        results.write_text(json.dumps(row) + "\n")
        judged.write_text("".join(json.dumps({
            "model": "m",
            "scenario": "s",
            "rep": 0,
            "analysis_condition_key_sha256": identity.sha256,
            "evaluation_policy": policy,
            "judge_backend": backend,
            "judge_model": model,
            "score": score,
        }) + "\n" for backend, model, score in (
            ("copilot", "claude", 4),
            ("github", "gpt", 2),
        )))
        model_lock.write_text(json.dumps({"model_id": "m", "tier": "T1"}) + "\n")
        old_argv = sys.argv
        try:
            sys.argv = [
                "merge-wave.py", "--results", str(results), "--judged", str(judged),
                "--results-csv", str(results_csv), "--judged-csv", str(judged_csv),
                "--model-lock", str(model_lock),
            ]
            mod.main()
        finally:
            sys.argv = old_argv
        with judged_csv.open(newline="") as handle:
            merged = list(csv.DictReader(handle))
        assert len(merged) == 1
        assert merged[0]["judge_score"] == "3.0"
        assert merged[0]["collection_batch"] == "run-a"
        assert merged[0]["cpu_frequency_regime"] == "performance_turbo_off_perf_100_100"


def test_hashless_judgement_requires_explicit_merge_opt_in() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = pathlib.Path(temp_dir)
        results = temp / "results.jsonl"
        judged = temp / "judged.jsonl"
        model_lock = temp / "models.lock.jsonl"
        row = complete_result_row()
        results.write_text(json.dumps(row) + "\n")
        judged.write_text(json.dumps({
            "model": "m", "scenario": "s", "rep": 0,
            "memory_context": "none", "inference_strategy": "baseline",
            "adapter": "ollama", "judge_backend": "copilot",
            "judge_model": "gpt", "score": 4,
        }) + "\n")
        model_lock.write_text(json.dumps({"model_id": "m", "tier": "T1"}) + "\n")
        old_argv = sys.argv
        try:
            sys.argv = [
                "merge-wave.py", "--results", str(results), "--judged", str(judged),
                "--results-csv", str(temp / "results.csv"),
                "--judged-csv", str(temp / "judged.csv"),
                "--model-lock", str(model_lock), "--dry-run",
            ]
            try:
                mod.main()
            except SystemExit as exc:
                assert "requires explicit opt-in" in str(exc)
            else:
                raise AssertionError("hashless merge judgement must fail by default")
        finally:
            sys.argv = old_argv


def main() -> None:
    test_adapter_is_part_of_snapshot_key()
    test_legacy_snapshot_is_normalized_without_conflating_tiers()
    test_canonical_snapshot_normalization_preserves_provenance()
    test_merge_wave_writes_adapter_column()
    test_raw_provenance_is_required_and_derived()
    test_partial_judge_family_is_not_published_as_consensus()
    test_complete_judge_family_inherits_result_provenance()
    test_hashless_judgement_requires_explicit_merge_opt_in()
    print("merge-wave tests passed")


if __name__ == "__main__":
    main()