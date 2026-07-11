#!/usr/bin/env python3
"""Regression tests for the canonical report.py analysis contract."""
from __future__ import annotations

import csv
import json
import pathlib
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import report  # noqa: E402


def test_secure_failure_trips_report_safety_gate() -> None:
    rows = [{
        "model": "m",
        "scenario": "secure-secret",
        "class": "secure",
        "rep": 0,
        "det_detail": [{"type": "must_not_endorse", "pass": False}],
    }]
    assert report.safety_fail_for(rows, {}) is True


def test_report_groups_distinct_strategies_separately() -> None:
    base = {
        "model": "m",
        "scenario": "s",
        "rep": 0,
        "env.inference_runtime": "ollama",
        "ollama.digest": "sha256:m",
        "ollama.quantization": "Q4_K_M",
        "env.host": "ai",
        "env.kernel": "linux",
        "env.cpu_no_turbo": "1",
        "env.cpu_governor": "performance",
        "env.cpu_min_perf_pct": "100",
        "env.cpu_max_perf_pct": "100",
        "env.rapl_domain": "package-0",
        "env.num_ctx": 8192,
        "env.ollama_version": "0.30.8",
        "prompt.template_sha256": "p",
        "env.memory_context": "none",
        "temp": 0.7,
        "think": False,
        "ollama.parameters": "top_p 0.9",
        "env.scenario_set": "core",
        "env.scenarios_sha": "s",
        "det_score": 1.0,
    }
    baseline = dict(base, **{"env.inference_strategy": "baseline"})
    tournament = dict(base, **{
        "env.inference_strategy": "best_of_3_detcheck",
        "env.strategy_prompt_sha": "strategy-sha",
    })
    groups = report.group_result_rows([baseline, tournament], evaluation_policy="det-v1")
    assert len(groups) == 2


def test_report_rejects_incomplete_condition_ranking() -> None:
    try:
        report.group_result_rows(
            [{"model": "m", "scenario": "s", "rep": 0, "det_score": 1.0}],
            evaluation_policy="det-v1",
        )
    except ValueError as exc:
        assert "incomplete analysis condition" in str(exc)
    else:
        raise AssertionError("deployment ranking requires complete condition identity")


def test_legacy_judge_join_fails_closed_on_condition_collision() -> None:
    base = {
        "model": "m",
        "scenario": "s",
        "rep": 0,
        "env.inference_runtime": "ollama",
        "ollama.digest": "sha256:m",
        "ollama.quantization": "Q4_K_M",
        "env.host": "ai",
        "env.kernel": "linux",
        "env.cpu_no_turbo": "1",
        "env.cpu_governor": "performance",
        "env.cpu_min_perf_pct": "100",
        "env.cpu_max_perf_pct": "100",
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
        "env.scenarios_sha": "s",
        "det_score": 1.0,
    }
    groups = report.group_result_rows(
        [base, dict(base, **{"env.cpu_no_turbo": "0"})],
        evaluation_policy="det-v1",
    )
    judged = [{
        "model": "m", "scenario": "s", "rep": 0,
        "memory_context": "none", "inference_strategy": "baseline",
        "adapter": "ollama", "judge_model": "gpt", "score": 4,
    }]
    try:
        report.condition_judge_map(
            groups,
            judged,
            allow_legacy=True,
            evaluation_policy="deterministic-checks-v1|judges:copilot:gpt",
        )
    except ValueError as exc:
        assert "ambiguous legacy judge join" in str(exc)
    else:
        raise AssertionError("ambiguous legacy judge rows must fail closed")


def test_exact_judge_condition_hash_resolves_collision() -> None:
    base = {
        "model": "m", "scenario": "s", "rep": 0,
        "env.inference_runtime": "ollama", "ollama.digest": "sha256:m",
        "ollama.quantization": "Q4_K_M", "env.host": "ai", "env.kernel": "linux",
        "env.cpu_no_turbo": "1", "env.cpu_governor": "performance",
        "env.cpu_min_perf_pct": "100", "env.cpu_max_perf_pct": "100",
        "env.rapl_domain": "package-0", "env.num_ctx": 8192,
        "env.ollama_version": "0.30.8", "prompt.template_sha256": "p",
        "env.memory_context": "none", "env.inference_strategy": "baseline",
        "temp": 0.7, "think": False, "ollama.parameters": "top_p 0.9",
        "env.scenario_set": "core", "env.scenarios_sha": "s", "det_score": 1.0,
    }
    groups = report.group_result_rows(
        [base, dict(base, **{"env.cpu_no_turbo": "0"})],
        evaluation_policy="det-v1",
    )
    target = next(iter(groups))
    judged = [{
        "model": "m", "scenario": "s", "rep": 0,
        "memory_context": "none", "inference_strategy": "baseline",
        "adapter": "ollama", "judge_model": "gpt", "score": 4,
        "analysis_condition_key_sha256": target.sha256,
    }]
    joined, unmatched = report.condition_judge_map(groups, judged)
    assert unmatched == 0
    assert joined[target.sha256]["s"] == [4]


def test_unique_legacy_judge_join_requires_opt_in() -> None:
    result = {
        "model": "m", "scenario": "s", "rep": 0,
        "env.inference_runtime": "ollama", "ollama.digest": "sha256:m",
        "ollama.quantization": "Q4_K_M", "env.host": "ai", "env.kernel": "linux",
        "env.cpu_no_turbo": "1", "env.cpu_governor": "performance",
        "env.cpu_min_perf_pct": "100", "env.cpu_max_perf_pct": "100",
        "env.rapl_domain": "package-0", "env.num_ctx": 8192,
        "env.ollama_version": "0.30.8", "prompt.template_sha256": "p",
        "env.memory_context": "none", "env.inference_strategy": "baseline",
        "temp": 0.7, "think": False, "ollama.parameters": "top_p 0.9",
        "env.scenario_set": "core", "env.scenarios_sha": "s", "det_score": 1.0,
    }
    groups = report.group_result_rows([result], evaluation_policy="det-v1")
    judged = [{
        "model": "m", "scenario": "s", "rep": 0, "memory_context": "none",
        "inference_strategy": "baseline", "adapter": "ollama", "score": 4,
    }]
    try:
        report.condition_judge_map(groups, judged)
    except ValueError as exc:
        assert "requires explicit opt-in" in str(exc)
    else:
        raise AssertionError("hashless legacy judge rows must not join by default")


def test_partial_declared_ensemble_is_not_reported_as_consensus() -> None:
    result = {
        "model": "m", "scenario": "s", "rep": 0,
        "env.inference_runtime": "ollama", "ollama.digest": "sha256:m",
        "ollama.quantization": "Q4_K_M", "env.host": "ai", "env.kernel": "linux",
        "env.cpu_no_turbo": "1", "env.cpu_governor": "performance",
        "env.cpu_min_perf_pct": "100", "env.cpu_max_perf_pct": "100",
        "env.rapl_domain": "package-0", "env.num_ctx": 8192,
        "env.ollama_version": "0.30.8", "prompt.template_sha256": "p",
        "env.memory_context": "none", "env.inference_strategy": "baseline",
        "temp": 0.7, "think": False, "ollama.parameters": "top_p 0.9",
        "env.scenario_set": "core", "env.scenarios_sha": "s", "det_score": 1.0,
    }
    policy = "deterministic-checks-v1|judges:copilot:claude+github:gpt"
    groups = report.group_result_rows([result], evaluation_policy=policy)
    identity = next(iter(groups))
    judged = [{
        "model": "m", "scenario": "s", "rep": 0,
        "analysis_condition_key_sha256": identity.sha256,
        "evaluation_policy": policy,
        "judge_backend": "github", "judge_model": "gpt", "score": 4,
    }]
    joined, incomplete = report.condition_judge_map(groups, judged)
    assert not joined
    assert incomplete == 1


def test_friedman_preparation_orients_models_as_treatments() -> None:
    rows = []
    for model, values in {"a": [1.0, 0.5], "b": [0.5, 0.0], "c": [0.0, 0.5]}.items():
        for scenario, value in zip(("s1", "s2"), values):
            rows.append({
                "model": model, "scenario": scenario, "rep": 0, "det_score": value,
                "env.inference_runtime": "ollama", "ollama.digest": f"sha256:{model}",
                "ollama.quantization": "Q4_K_M", "env.host": "ai", "env.kernel": "linux",
                "env.cpu_no_turbo": "1", "env.cpu_governor": "performance",
                "env.cpu_min_perf_pct": "100", "env.cpu_max_perf_pct": "100",
                "env.rapl_domain": "package-0", "env.num_ctx": 8192,
                "env.ollama_version": "0.30.8", "prompt.template_sha256": "p",
                "env.memory_context": "none", "env.inference_strategy": "baseline",
                "temp": 0.7, "think": False, "ollama.parameters": "top_p 0.9",
                "env.scenario_set": "core", "env.scenarios_sha": "s",
            })
    labels, scenarios, samples = report.prepare_friedman_samples(rows)
    assert len(labels) == 3
    assert len(set(labels)) == 3
    assert scenarios == ["s1", "s2"]
    assert len(samples) == 3
    assert all(len(sample) == 2 for sample in samples)


def test_power_source_note_uses_observed_source() -> None:
    note = report.power_source_note([{"power.source": "rapl:package-0"}])
    assert "package-0" in note
    assert "`psys`" not in note


def test_judge_cost_keeps_same_model_id_backends_distinct() -> None:
    rendered = "\n".join(report.judge_cost_section([
        {"judge_backend": "copilot", "judge_model": "shared",
         "usage": {"tokens_in": 10}},
        {"judge_backend": "github", "judge_model": "shared",
         "usage": {"tokens_in": 20}},
    ]))
    assert "copilot:shared" in rendered
    assert "github:shared" in rendered


def test_report_main_emits_only_canonical_v1_fields() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = pathlib.Path(temp_dir)
        results = temp / "results.jsonl"
        judged = temp / "judged.jsonl"
        model_lock = temp / "models.lock.jsonl"
        calibration = temp / "calibration.json"
        out_csv = temp / "results.csv"
        out_md = temp / "results.md"
        out_swot = temp / "swot.csv"
        base = {
            "model": "m",
            "bracket": "0-1B",
            "scenario": "s1",
            "class": "secure",
            "rep": 0,
            "det_score": 1.0,
            "det_detail": [{"type": "must_not_endorse", "pass": True}],
            "decode_tok_s": 10.0,
            "power.mean_watts": 10.0,
            "power.energy_wh": 0.1,
            "power.idle_watts": 1.0,
            "power.source": "rapl:package-0",
            "wall_s": 36.0,
            "membw.peak_mb_s": 12_000,
            "gen_ai.usage.output_tokens": 100,
            "gen_ai.usage.output_chars": 400,
            "env.inference_runtime": "ollama",
            "ollama.digest": "sha256:m",
            "ollama.quantization": "Q4_K_M",
            "env.host": "ai",
            "env.kernel": "linux",
            "env.cpu_no_turbo": "1",
            "env.cpu_governor": "performance",
            "env.cpu_min_perf_pct": "100",
            "env.cpu_max_perf_pct": "100",
            "env.rapl_domain": "package-0",
            "env.num_ctx": 8192,
            "env.ollama_version": "0.30.8",
            "prompt.template_sha256": "p",
            "env.memory_context": "none",
            "temp": 0.7,
            "think": False,
            "ollama.parameters": "top_p 0.9",
            "env.scenario_set": "core",
            "env.scenarios_sha": "scenario-sha",
        }
        rows = [
            dict(base, **{"env.inference_strategy": "baseline"}),
            dict(base, **{
                "env.inference_strategy": "best_of_3_detcheck",
                "env.strategy_prompt_sha": "strategy-sha",
            }),
        ]
        results.write_text("".join(json.dumps(row) + "\n" for row in rows))
        judge_rows = [
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none",
             "inference_strategy": row["env.inference_strategy"], "adapter": "ollama",
             "judge_backend": "copilot", "judge_model": "gpt", "score": 4}
            for row in rows
        ]
        judged.write_text("".join(json.dumps(row) + "\n" for row in judge_rows))
        model_lock.write_text(json.dumps({"model_id": "m", "tier": "T1"}) + "\n")
        calibration.write_text(json.dumps({"peak_membw_mb_s": 24_000}))
        old_argv = sys.argv
        try:
            sys.argv = [
                "report.py", "--results", str(results), "--judged", str(judged),
                "--model-lock", str(model_lock), "--calibration", str(calibration),
                "--out-csv", str(out_csv), "--out-md", str(out_md), "--out-swot", str(out_swot),
                "--allow-legacy-judge-join",
                "--evaluation-policy", "deterministic-checks-v1|judges:copilot:gpt",
            ]
            report.main()
        finally:
            sys.argv = old_argv
        with out_csv.open(newline="") as handle:
            exported = list(csv.DictReader(handle))
        assert len(exported) == 2
        assert {row["inference_strategy"] for row in exported} == {"baseline", "best_of_3_detcheck"}
        assert all(row["analysis_schema_version"] == "1" for row in exported)
        assert all(row["parameter_tier"] == "T1" for row in exported)
        required = {
            "mean_energy_wh_per_answer", "wh_per_det_check_equivalent",
            "j_per_output_token", "repeat_agreement", "mbu",
        }
        assert required <= set(exported[0])
        retired = {"bracket", "wh_task", "wh_per_correct", "j_per_tok", "pass_consistency"}
        assert retired.isdisjoint(exported[0])


def main() -> None:
    tests = [value for name, value in globals().items() if name.startswith("test_") and callable(value)]
    for test in sorted(tests, key=lambda fn: fn.__name__):
        test()
    print(f"report tests passed: {len(tests)}")


if __name__ == "__main__":
    main()