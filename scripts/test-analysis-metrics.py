#!/usr/bin/env python3
"""Regression tests for the canonical ApprenticeOps analysis schema v1."""
from __future__ import annotations

import math
import importlib.util
import csv
import json
import pathlib
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import analysis_metrics as metrics  # noqa: E402

METRICS_SCRIPT = REPO / "scripts" / "metrics.py"
spec = importlib.util.spec_from_file_location("metrics_cli", METRICS_SCRIPT)
assert spec and spec.loader
metrics_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics_cli)


def complete_row(**overrides):
    row = {
        "model": "model-a",
        "env.inference_runtime": "ollama",
        "ollama.digest": "sha256:model-a",
        "ollama.quantization": "Q4_K_M",
        "env.host": "home-ai",
        "env.kernel": "linux",
        "env.cpu_no_turbo": "1",
        "env.cpu_governor": "performance",
        "env.cpu_min_perf_pct": "100",
        "env.cpu_max_perf_pct": "100",
        "env.rapl_domain": "package-0",
        "env.num_ctx": 8192,
        "env.ollama_version": "0.30.8",
        "prompt.template_sha256": "prompt-sha",
        "env.memory_context": "none",
        "env.memory_context_sha": None,
        "env.inference_strategy": "baseline",
        "env.strategy_prompt_sha": None,
        "temp": 0.7,
        "think": False,
        "ollama.parameters": "top_k 40\ntop_p 0.9",
        "env.scenario_set": "core-current",
        "env.scenarios_sha": "scenario-sha",
        "class": "diagnose",
        "scenario": "s1",
        "rep": 0,
        "det_score": 1.0,
        "power.energy_wh": 0.1,
        "gen_ai.response.finish_reasons": ["stop"],
        "gen_ai.completion": "answer",
    }
    row.update(overrides)
    return row


def test_condition_key_is_complete_and_splits_real_conditions() -> None:
    first = metrics.analysis_condition(complete_row(), evaluation_policy="det-v1|judges:gpt+claude")
    second = metrics.analysis_condition(
        complete_row(**{
            "env.inference_strategy": "best_of_3_detcheck",
            "env.strategy_prompt_sha": "strategy-sha",
        }),
        evaluation_policy="det-v1|judges:gpt+claude",
    )
    assert first.incomplete is False
    assert first.key != second.key
    assert first.sha256 != second.sha256


def test_single_schema_v1_and_manifest_gate() -> None:
    schema = metrics.load_analysis_schema(str(REPO / "data" / "analysis.schema.json"))
    assert schema["schema_version"] == 1
    assert "v2" not in json.dumps(schema).lower()
    required = schema["artifacts"]["condition_scenario_reliability_csv"]["required_columns"]
    assert metrics.validate_artifact_columns(
        schema,
        "condition_scenario_reliability_csv",
        required,
    ) == []
    assert "forbidden column/key: bracket" in metrics.validate_artifact_columns(
        schema,
        "condition_scenario_reliability_csv",
        [*required, "bracket"],
    )
    manifest = {
        "analysis_schema_version": 1,
        "source_kind": "completed_run",
        "source_id": "run-a",
        "source_sha256": {"results": "a" * 64},
        "claim_status": "provisional",
    }
    assert metrics.validate_analysis_manifest(manifest, claim_bearing=False) == []
    assert metrics.validate_analysis_manifest(manifest, claim_bearing=True) == [
        "claim-bearing surfaces require claim_status=locked"
    ]


def test_explicit_evaluation_policy_survives_partial_judge_output() -> None:
    requested = "deterministic-checks-v1|judges:copilot:claude+copilot:gpt"
    partial = [{
        "judge_backend": "copilot",
        "judge_model": "gpt",
        "evaluation_policy": requested,
    }]
    assert metrics.evaluation_policy_id(partial) == requested
    try:
        metrics.evaluation_policy_id([
            partial[0],
            {"judge_backend": "copilot", "judge_model": "gpt",
             "evaluation_policy": "deterministic-checks-v1|judges:copilot:gpt"},
        ])
    except ValueError as exc:
        assert "conflicting evaluation_policy" in str(exc)
    else:
        raise AssertionError("mixed explicit evaluation policies must fail closed")


def test_hashless_compatibility_requires_requested_policy() -> None:
    legacy = [{"judge_backend": "copilot", "judge_model": "gpt", "score": 4}]
    try:
        metrics.resolve_evaluation_policy(legacy, allow_legacy=True)
    except ValueError as exc:
        assert "requires an explicit evaluation_policy" in str(exc)
    else:
        raise AssertionError("surviving legacy rows cannot define the requested ensemble")
    policy = "deterministic-checks-v1|judges:copilot:claude+copilot:gpt"
    assert metrics.resolve_evaluation_policy(
        legacy,
        explicit=policy,
        allow_legacy=True,
    ) == policy


def test_condition_key_fails_closed_without_artifact_identity() -> None:
    identity = metrics.analysis_condition(
        complete_row(**{"ollama.digest": None}),
        evaluation_policy="det-v1",
    )
    assert identity.incomplete is True
    assert "artifact_identity" in identity.missing_fields


def test_nonbaseline_condition_requires_strategy_prompt_hash() -> None:
    identity = metrics.analysis_condition(
        complete_row(**{"env.inference_strategy": "best_of_3_detcheck"}),
        evaluation_policy="det-v1",
    )
    assert identity.incomplete is True
    assert "strategy_prompt_sha" in identity.missing_fields


def test_explicit_normalized_runtime_default_sampler_is_complete() -> None:
    row = complete_row(**{
        "ollama.parameters": None,
        "analysis.sampler_policy": {
            "kind": "runtime_defaults",
            "runtime_adapter": "ollama",
            "runtime_version": "0.30.8",
            "temperature": 0.7,
            "think": False,
        },
    })
    identity = metrics.analysis_condition(row, evaluation_policy="det-v1")
    assert identity.incomplete is False


def test_ollama_process_snapshot_can_supply_explicit_artifact_identity() -> None:
    row = complete_row(**{
        "ollama.digest": None,
        "ollama.ps.before": {
            "models": [{
                "name": "model-a:latest",
                "digest": "a" * 64,
            }],
        },
    })
    normalized = metrics.normalize_condition_provenance(row)
    assert normalized["analysis.artifact_identity"] == "ollama-ps-sha256:" + "a" * 64
    assert normalized["analysis.artifact_identity_source"] == "ollama.ps.before"
    identity = metrics.analysis_condition(normalized, evaluation_policy="det-v1")
    assert identity.incomplete is False


def test_incomplete_condition_is_excluded_from_judge_index() -> None:
    complete = complete_row()
    incomplete = complete_row(model="model-b", **{"ollama.digest": None})
    complete_identity = metrics.analysis_condition(complete, evaluation_policy="det-v1")
    incomplete_identity = metrics.analysis_condition(incomplete, evaluation_policy="det-v1")
    exact, legacy = metrics.judge_condition_index([
        (complete_identity, complete),
        (incomplete_identity, incomplete),
    ])
    assert exact == frozenset({complete_identity.sha256})
    assert metrics.legacy_judge_join_key(incomplete) not in legacy


def test_evaluation_policy_exposes_backend_aware_judge_set() -> None:
    policy = "deterministic-checks-v1|judges:copilot:gpt+github:gpt"
    assert metrics.evaluation_policy_judges(policy) == frozenset({
        ("copilot", "gpt"),
        ("github", "gpt"),
    })


def test_measured_mbu_is_not_dense_stream_proxy() -> None:
    assert metrics.measured_mbu(12_000, 24_000) == 0.5
    assert metrics.dense_weight_stream_equivalent_ratio(2_000_000_000, 10, 20_000) == 1.0


def test_energy_equivalent_keeps_zero_score_energy_in_numerator() -> None:
    rows = [
        {"power.energy_wh": 0.1, "det_score": 1.0},
        {"power.energy_wh": 0.1, "det_score": 0.0},
    ]
    assert metrics.wh_per_det_check_equivalent(rows) == 0.2


def test_output_token_energy_and_invalid_counter() -> None:
    assert metrics.j_per_output_token(0.1, 100) == 3.6
    assert metrics.j_per_output_token(0.1, 0) is None
    assert metrics.safe_ratio(10, 0) is None


def test_kv_cache_uses_real_q8_block_storage() -> None:
    field, value = metrics.kv_cache_payload_mb(
        blocks=2,
        kv_heads=2,
        embedding_length=8,
        attention_heads=4,
        token_count=100,
        dtype="q8_0",
    )
    assert field == "kv_cache_q8_0_payload_mb"
    expected = 2 * 2 * 2 * (8 / 4) * 100 * (34 / 32) / 1e6
    assert math.isclose(value, expected)


def test_unknown_kv_dtype_is_explicit_fp16_equivalent() -> None:
    field, value = metrics.kv_cache_payload_mb(
        blocks=2,
        kv_heads=2,
        embedding_length=8,
        attention_heads=4,
        token_count=100,
        dtype=None,
    )
    assert field == "kv_cache_fp16_equivalent_mb"
    assert value is not None


def test_repeated_failure_is_stable_but_not_successful() -> None:
    result = metrics.repetition_metrics([False] * 5, [True] * 5)
    assert result == {
        "repeat_count": 5,
        "repeat_agreement": 1.0,
        "pass_1": 0.0,
        "pass_all_k": 0,
        "all_safe_k": 1,
    }


def test_one_unsafe_repetition_fails_all_safe() -> None:
    result = metrics.repetition_metrics([True] * 5, [True, True, False, True, True])
    assert result["pass_all_k"] == 1
    assert result["all_safe_k"] == 0


def test_safety_membership_includes_secure_and_lifecycle_risk() -> None:
    assert metrics.is_safety_scenario({"class": "secure"}) is True
    assert metrics.is_safety_scenario({"class": "diagnose", "scenario.lifecycle.action.destructive_risk": True}) is True
    assert metrics.is_safety_scenario({"class": "diagnose"}) is False


def test_friedman_samples_are_models_over_scenario_blocks() -> None:
    rows = []
    for model, values in {"a": [1.0, 0.5], "b": [0.5, 0.0], "c": [0.0, 0.5]}.items():
        for scenario, value in zip(("s1", "s2"), values):
            rows.append({"condition": model, "scenario": scenario, "det_score": value})
    labels, scenarios, samples = metrics.friedman_samples(
        rows,
        condition=lambda row: row["condition"],
    )
    assert labels == ["a", "b", "c"]
    assert scenarios == ["s1", "s2"]
    assert samples == [[1.0, 0.5], [0.5, 0.0], [0.0, 0.5]]


def test_scenario_cluster_ci_is_deterministic_and_clustered() -> None:
    rows = [
        {"scenario": "s1", "value": 0.0},
        {"scenario": "s1", "value": 0.0},
        {"scenario": "s2", "value": 1.0},
    ]
    first = metrics.scenario_cluster_mean_ci(rows, value_field="value", samples=500, seed=7)
    second = metrics.scenario_cluster_mean_ci(rows, value_field="value", samples=500, seed=7)
    assert first == second
    assert first[0] == 1 / 3
    assert first[1] <= first[0] <= first[2]


def test_scenario_cluster_contrast_is_paired_by_scenario() -> None:
    rows = [
        {"scenario": "s1", "arm": "left", "value": 0.9},
        {"scenario": "s1", "arm": "left", "value": 0.7},
        {"scenario": "s1", "arm": "right", "value": 0.2},
        {"scenario": "s2", "arm": "left", "value": 0.4},
        {"scenario": "s2", "arm": "right", "value": 0.3},
        {"scenario": "unpaired", "arm": "left", "value": 1.0},
    ]
    first = metrics.scenario_cluster_contrast_ci(
        rows,
        group_field="arm",
        left_group="left",
        right_group="right",
        value_field="value",
        samples=500,
        seed=11,
    )
    second = metrics.scenario_cluster_contrast_ci(
        rows,
        group_field="arm",
        left_group="left",
        right_group="right",
        value_field="value",
        samples=500,
        seed=11,
    )
    assert first == second
    assert math.isclose(first[0], 0.35)
    assert first[1] <= first[0] <= first[2]


def test_completion_outcomes_are_distinct() -> None:
    assert metrics.completion_outcome(complete_row()) == "stop"
    assert metrics.completion_outcome(complete_row(**{"gen_ai.response.finish_reasons": ["length"]})) == "length"
    assert metrics.completion_outcome(complete_row(**{"gen_ai.completion": ""})) == "blank_stop"
    assert metrics.completion_outcome(complete_row(**{"dnf": True, "gen_ai.response.finish_reasons": ["DNF:timeout"]})) == "dnf_timeout"
    assert metrics.completion_outcome(complete_row(**{"gen_ai.response.finish_reasons": ["DNF:after_done_missing"]})) == "incomplete_stream"


def test_metrics_adapter_uses_canonical_v1_names() -> None:
    row = complete_row(**{
        "decode_tok_s": 10.0,
        "ollama.size_bytes": 2_000_000_000,
        "membw.peak_mb_s": 12_000,
        "ollama.parameter_count": 1_000_000_000,
        "ollama.block_count": 2,
        "ollama.head_count_kv": 2,
        "ollama.embedding_length": 8,
        "ollama.head_count": 4,
        "gen_ai.usage.input_tokens": 100,
        "gen_ai.usage.output_tokens": 100,
        "power.energy_wh": 0.1,
        "env.ollama_kv_cache_type": "q8_0",
    })
    derived = metrics_cli.per_run(row, 24_000)
    assert derived["mbu"] == 0.5
    assert derived["dense_weight_stream_equivalent_ratio"] == 0.8333
    assert derived["j_per_output_token"] == 3.6
    assert "energy_per_correct_wh" not in derived
    assert "kv_cache_mb" not in derived
    assert "kv_cache_q8_0_payload_mb" in derived


def test_metrics_adapter_emits_group_reliability_separately() -> None:
    rows = [
        complete_row(rep=rep, det_score=score, **{"class": "secure"})
        for rep, score in enumerate((1.0, 1.0, 0.0, 1.0, 1.0))
    ]
    rows[2]["det_detail"] = [{"type": "must_not_endorse", "pass": False}]
    exported = metrics_cli.build_reliability_rows(rows, evaluation_policy="det-v1")
    assert len(exported) == 1
    item = exported[0]
    assert item["analysis_schema_version"] == 1
    assert item["repeat_count"] == 5
    assert item["pass_1"] == 0.8
    assert item["pass_all_k"] == 0
    assert item["all_safe_k"] == 0


def test_text_output_lookup_prefers_repeat_zero_sidecar() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = pathlib.Path(temp_dir)
        (root / "model-a__s1__r0.txt").write_text("repeat-zero")
        (root / "model-a__s1.txt").write_text("legacy-unsuffixed")
        text = metrics_cli.read_output(str(root), "model-a", "s1", 0)
    assert text == "repeat-zero"


def test_metrics_cli_evaluation_policy_matches_shared_condition_hash() -> None:
    row = complete_row()
    judged = [
        {"model": "model-a", "judge_backend": "copilot", "judge_model": "gpt-5.4"},
        {"model": "model-a", "judge_backend": "copilot", "judge_model": "claude-opus-4.6"},
    ]
    with tempfile.TemporaryDirectory() as temp_dir:
        path = pathlib.Path(temp_dir) / "judged.jsonl"
        path.write_text("".join(json.dumps(item) + "\n" for item in judged))
        policy = metrics_cli.resolve_evaluation_policy([str(path)])
    assert policy == metrics.evaluation_policy_id(judged)
    expected = metrics.analysis_condition(row, evaluation_policy=policy)
    actual = metrics.analysis_condition(
        row,
        evaluation_policy=metrics_cli.resolve_evaluation_policy(explicit=policy),
    )
    assert actual.sha256 == expected.sha256


def test_metrics_cli_writes_three_canonical_artifacts() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = pathlib.Path(temp_dir)
        results = temp / "results.jsonl"
        calibration = temp / "calibration.json"
        model_lock = temp / "models.lock.jsonl"
        enriched = temp / "enriched.jsonl"
        summary = temp / "summary.csv"
        reliability = temp / "reliability.csv"
        rows = [
            complete_row(
                rep=rep,
                **{
                    "decode_tok_s": 10.0,
                    "ollama.size_bytes": 2_000_000_000,
                    "membw.peak_mb_s": 12_000,
                    "gen_ai.usage.input_tokens": 100,
                    "gen_ai.usage.output_tokens": 100,
                    "power.energy_wh": 0.1,
                },
            )
            for rep in range(2)
        ]
        results.write_text("".join(json.dumps(row) + "\n" for row in rows))
        calibration.write_text(json.dumps({"peak_membw_mb_s": 24_000}))
        model_lock.write_text(json.dumps({"model_id": "model-a", "tier": "T1"}) + "\n")
        old_argv = sys.argv
        try:
            sys.argv = [
                "metrics.py", str(results), "--calibration", str(calibration),
                "--model-lock", str(model_lock), "--out", str(enriched),
                "--summary", str(summary), "--reliability", str(reliability),
            ]
            metrics_cli.main()
        finally:
            sys.argv = old_argv
        enriched_row = json.loads(enriched.read_text().splitlines()[0])
        with summary.open(newline="") as handle:
            summary_row = next(csv.DictReader(handle))
        with reliability.open(newline="") as handle:
            reliability_row = next(csv.DictReader(handle))
        assert enriched_row["analysis_schema_version"] == 1
        assert "dense_weight_stream_equivalent_ratio" in enriched_row
        assert summary_row["parameter_tier"] == "T1"
        assert "wh_per_det_check_equivalent" in summary_row
        assert reliability_row["pass_all_k"] == "1"
        retired = {"bracket", "energy_per_correct_wh", "energy_per_ktok_wh", "pass_consistency"}
        assert retired.isdisjoint(enriched_row)
        assert retired.isdisjoint(summary_row)


def main() -> None:
    tests = [value for name, value in globals().items() if name.startswith("test_") and callable(value)]
    for test in sorted(tests, key=lambda fn: fn.__name__):
        test()
    print(f"analysis metric tests passed: {len(tests)}")


if __name__ == "__main__":
    main()