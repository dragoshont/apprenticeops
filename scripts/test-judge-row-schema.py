#!/usr/bin/env python3
"""Regression tests for judged-row schema completeness."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "judge.py"
sys.path.insert(0, str(ROOT))


def load_module():
    spec = importlib.util.spec_from_file_location("judge_module", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_detail_contract(row):
    assert "score" in row
    assert isinstance(row["verdict"], str) and row["verdict"]
    assert isinstance(row["evidence"], str) and row["evidence"]
    assert isinstance(row["criteria_met"], list)
    assert isinstance(row["criteria_missed"], list)


def test_empty_answer_contract():
    module = load_module()
    row = module.normalize_judgement(
        {},
        fallback_score=1,
        fallback_verdict="empty",
        fallback_evidence="No answer text was available for judging; the inference row did not produce a completion.",
        fallback_criteria_missed=["answer was empty or unavailable"],
    )
    assert row["score"] == 1
    assert row["verdict"] == "empty"
    assert row["criteria_met"] == []
    assert row["criteria_missed"] == ["answer was empty or unavailable"]
    assert_detail_contract(row)


def test_partial_judge_payload_is_completed():
    module = load_module()
    row = module.normalize_judgement({"score": 2, "evidence": "partial", "verdict": "partial"})
    assert row["score"] == 2
    assert row["criteria_met"] == []
    assert row["criteria_missed"] == []
    assert_detail_contract(row)


def test_parse_error_fallback_contract():
    module = load_module()

    class BadJudge:
        def complete(self, *_args, **_kwargs):
            return "not json"

    scenario = {
        "context": "ctx",
        "question": "task",
        "gold_answer": "gold",
        "judge_rubric": "rubric",
    }
    row = module.judge_one(BadJudge(), scenario, "answer")
    assert row["score"] is None
    assert row["evidence"] == "parse_error"
    assert row["criteria_missed"] == ["judge response could not be parsed"]
    assert_detail_contract(row)


def test_result_condition_provenance_is_stamped():
    module = load_module()
    result = {
        "model": "m", "env.inference_runtime": "ollama",
        "ollama.digest": "sha256:m", "ollama.quantization": "Q4_K_M",
        "env.host": "ai", "env.kernel": "linux", "env.cpu_no_turbo": "1",
        "env.cpu_governor": "performance", "env.cpu_min_perf_pct": "100",
        "env.cpu_max_perf_pct": "100", "env.rapl_domain": "package-0",
        "env.num_ctx": 8192, "env.ollama_version": "0.30.8",
        "prompt.template_sha256": "p", "env.memory_context": "none",
        "env.inference_strategy": "baseline", "temp": 0.7, "think": False,
        "ollama.parameters": "top_p 0.9", "env.scenario_set": "core",
        "env.scenarios_sha": "s",
    }
    fields = module.analysis_condition_fields(
        result,
        "deterministic-checks-v1|judges:copilot:gpt",
    )
    assert fields["analysis_schema_version"] == 1
    assert len(fields["analysis_condition_key_sha256"]) == 64
    assert fields["condition_identity_incomplete"] is False
    assert fields["evaluation_policy"] == "deterministic-checks-v1|judges:copilot:gpt"


def test_runtime_default_sampler_is_normalized_before_judging():
    module = load_module()
    result = {
        "model": "m", "env.inference_runtime": "ollama",
        "ollama.digest": "sha256:m", "ollama.quantization": "Q4_K_M",
        "env.host": "ai", "env.kernel": "linux", "env.cpu_no_turbo": "1",
        "env.cpu_governor": "performance", "env.cpu_min_perf_pct": "100",
        "env.cpu_max_perf_pct": "100", "env.rapl_domain": "package-0",
        "env.num_ctx": 8192, "env.ollama_version": "ollama version is 0.30.8",
        "prompt.template_sha256": "p", "env.memory_context": "none",
        "env.inference_strategy": "baseline", "temp": 0.7, "think": False,
        "ollama.parameters": None, "env.scenario_set": "core",
        "env.scenarios_sha": "s",
    }
    policy = "deterministic-checks-v1|judges:copilot:gpt"
    fields = module.analysis_condition_fields(result, policy)
    normalized = module.analysis_metrics.normalize_condition_provenance(result)
    expected = module.analysis_metrics.analysis_condition(
        normalized,
        evaluation_policy=policy,
    )
    assert fields["condition_identity_incomplete"] is False
    assert fields["analysis_condition_key_sha256"] == expected.sha256
    assert normalized["analysis.sampler_policy"]["kind"] == "runtime_defaults"


def test_incomplete_result_condition_cannot_be_judged():
    module = load_module()
    result = {
        "model": "m",
        "env.inference_runtime": "ollama",
        "env.memory_context": "none",
        "env.inference_strategy": "baseline",
    }
    try:
        module.analysis_condition_fields(result, "deterministic-checks-v1|judges:copilot:gpt")
    except ValueError as exc:
        assert "incomplete analysis condition" in str(exc)
    else:
        raise AssertionError("judge rows require a complete source condition")


def test_hashless_resume_requires_explicit_opt_in():
    module = load_module()
    result = {
        "model": "m", "scenario": "s", "rep": 0,
        "env.memory_context": "none", "env.inference_strategy": "baseline",
        "env.inference_runtime": "ollama",
    }
    _, legacy_key = module.judgement_resume_keys(
        result,
        condition_sha="condition-a",
        judge_backend="copilot",
        judge_model="gpt",
    )
    kwargs = {
        "condition_sha": "condition-a",
        "judge_backend": "copilot",
        "judge_model": "gpt",
        "done_exact": set(),
        "done_legacy": {legacy_key},
        "legacy_resume_safe": True,
    }
    assert module.judgement_is_done(
        result,
        allow_legacy_resume=False,
        **kwargs,
    ) is False
    assert module.judgement_is_done(
        result,
        allow_legacy_resume=True,
        **kwargs,
    ) is True


def test_exact_resume_distinguishes_backend_family():
    module = load_module()
    result = {"model": "m", "scenario": "s", "rep": 0}
    exact_key, _ = module.judgement_resume_keys(
        result,
        condition_sha="condition-a",
        judge_backend="copilot",
        judge_model="shared-model-id",
    )
    common = {
        "condition_sha": "condition-a",
        "judge_model": "shared-model-id",
        "done_exact": {exact_key},
        "done_legacy": set(),
        "legacy_resume_safe": False,
        "allow_legacy_resume": False,
    }
    assert module.judgement_is_done(
        result,
        judge_backend="copilot",
        **common,
    ) is True
    assert module.judgement_is_done(
        result,
        judge_backend="github",
        **common,
    ) is False


def test_scheduler_completion_identity_includes_backend():
    scheduler = (ROOT / "scripts" / "judge-scheduler.sh").read_text()
    assert '(.judge_backend // "unknown")' in scheduler


def main() -> None:
    test_empty_answer_contract()
    test_partial_judge_payload_is_completed()
    test_parse_error_fallback_contract()
    test_result_condition_provenance_is_stamped()
    test_incomplete_result_condition_cannot_be_judged()
    test_hashless_resume_requires_explicit_opt_in()
    test_exact_resume_distinguishes_backend_family()
    print("judge row schema tests passed")


if __name__ == "__main__":
    main()