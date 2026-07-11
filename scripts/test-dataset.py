#!/usr/bin/env python3
"""Regression tests for the row-grain ML dataset export."""
from __future__ import annotations

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import dataset  # noqa: E402


def row(rep: int) -> dict:
    return {
        "model": "m",
        "bracket": "0-1B",
        "scenario": "s",
        "class": "secure",
        "rep": rep,
        "det_score": 1.0,
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
        "gen_ai.response.finish_reasons": ["stop"],
        "gen_ai.usage.output_tokens": 5,
        "gen_ai.usage.output_chars": 20,
    }


def test_dataset_preserves_one_row_per_repetition() -> None:
    rows = dataset.build_dataset_rows([row(0), row(1)], [])
    assert len(rows) == 2
    assert {item["rep"] for item in rows} == {0, 1}
    assert "pass_all_k" not in rows[0]
    assert "repeat_agreement" not in rows[0]


def test_dataset_exports_condition_identity_without_silent_merge() -> None:
    good = row(0)
    incomplete = row(1)
    incomplete["ollama.digest"] = None
    rows = dataset.build_dataset_rows([good, incomplete], [])
    assert rows[0]["analysis_schema_version"] == 1
    assert rows[0]["analysis_condition_key_sha256"]
    assert rows[0]["condition_identity_incomplete"] == 0
    assert rows[1]["condition_identity_incomplete"] == 1


def test_dataset_legacy_judge_join_fails_closed_on_condition_collision() -> None:
    first = row(0)
    second = row(0)
    second["env.cpu_no_turbo"] = "0"
    judged = [{
        "model": "m", "scenario": "s", "rep": 0,
        "memory_context": "none", "inference_strategy": "baseline",
        "adapter": "ollama", "judge_model": "gpt", "score": 4,
    }]
    try:
        dataset.build_dataset_rows(
            [first, second],
            judged,
            allow_legacy_judge_join=True,
            evaluation_policy="deterministic-checks-v1|judges:copilot:gpt",
        )
    except ValueError as exc:
        assert "ambiguous legacy judge join" in str(exc)
    else:
        raise AssertionError("ambiguous legacy judge rows must fail closed")


def test_dataset_unique_legacy_judge_join_requires_opt_in() -> None:
    judged = [{
        "model": "m", "scenario": "s", "rep": 0,
        "memory_context": "none", "inference_strategy": "baseline",
        "adapter": "ollama", "judge_model": "gpt", "score": 4,
    }]
    try:
        dataset.build_dataset_rows([row(0)], judged)
    except ValueError as exc:
        assert "requires explicit opt-in" in str(exc)
    else:
        raise AssertionError("dataset must reject hashless judge rows by default")


def test_dataset_partial_declared_ensemble_has_no_consensus_score() -> None:
    result = row(0)
    policy = "deterministic-checks-v1|judges:copilot:claude+github:gpt"
    identity = dataset.analysis_metrics.analysis_condition(result, evaluation_policy=policy)
    judged = [{
        "model": "m", "scenario": "s", "rep": 0,
        "analysis_condition_key_sha256": identity.sha256,
        "evaluation_policy": policy,
        "judge_backend": "github", "judge_model": "gpt", "score": 4,
    }]
    exported = dataset.build_dataset_rows([result], judged)
    assert exported[0]["judge_score"] is None


def main() -> None:
    tests = [value for name, value in globals().items() if name.startswith("test_") and callable(value)]
    for test in sorted(tests, key=lambda fn: fn.__name__):
        test()
    print(f"dataset tests passed: {len(tests)}")


if __name__ == "__main__":
    main()