#!/usr/bin/env python3
"""Regression tests for run.py environment provenance helpers."""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "run.py"
spec = importlib.util.spec_from_file_location("run_module", SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_artifact_only_dirty_is_not_source_dirty() -> None:
    source_dirty, artifact_dirty = mod._classify_git_status(
        "?? calibration.json\n"
        "?? results.example.jsonl\n"
        "?? logs/run/driver.log\n"
        "?? outputs/model__scenario.txt\n"
    )
    assert source_dirty is False
    assert artifact_dirty is True


def test_source_dirty_is_distinct_from_artifacts() -> None:
    source_dirty, artifact_dirty = mod._classify_git_status(
        " M run.py\n"
        "?? data/runs/example/run.meta\n"
    )
    assert source_dirty is True
    assert artifact_dirty is True


def test_llama_cpp_resolves_explicit_file_path() -> None:
    with tempfile.TemporaryDirectory() as td:
        path = pathlib.Path(td) / "model.gguf"
        path.write_text("not a real model")
        resolved, error = mod.resolve_llama_cpp_model_path(str(path))
    assert resolved == str(path)
    assert error is None


def test_llama_cpp_resolves_direct_gguf_from_model_dir() -> None:
    old_dir = mod.LLAMA_CPP_MODELS_DIR
    try:
        with tempfile.TemporaryDirectory() as td:
            mod.LLAMA_CPP_MODELS_DIR = td
            path = pathlib.Path(td) / "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"
            path.write_text("not a real model")
            resolved, error = mod.resolve_llama_cpp_model_path("hf.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M")
        assert resolved == str(path)
        assert error is None
    finally:
        mod.LLAMA_CPP_MODELS_DIR = old_dir


def test_llama_cpp_rejects_ollama_wrapped_model_without_mapping() -> None:
    resolved, error = mod.resolve_llama_cpp_model_path("qwen2.5:0.5b")
    assert resolved is None
    assert "not direct_gguf" in error


def test_llama_cpp_runtime_unsupported_telemetry_is_fail_closed() -> None:
    tel = mod.run_llama_cpp(
        "qwen2.5:0.5b",
        "",
        "hello",
        max_tokens=8,
        timeout_s=1,
        stall_s=1,
        sampler=None,
        temperature=0,
        seed=1,
    )
    assert tel["dnf"] is True
    assert tel["gen_ai.response.finish_reasons"] == ["DNF:runtime_unsupported"]


def test_runtime_name_is_snapshot_adapter_name() -> None:
    assert mod.INFERENCE_RUNTIME in {"ollama", "llama_cpp", "llama_cpp_server"}


def test_env_static_captures_ollama_kv_policy() -> None:
    old_kv = os.environ.get("OLLAMA_KV_CACHE_TYPE")
    old_flash = os.environ.get("OLLAMA_FLASH_ATTENTION")
    try:
        os.environ["OLLAMA_KV_CACHE_TYPE"] = "q8_0"
        os.environ["OLLAMA_FLASH_ATTENTION"] = "1"
        fields = mod._env_static()
    finally:
        if old_kv is None:
            os.environ.pop("OLLAMA_KV_CACHE_TYPE", None)
        else:
            os.environ["OLLAMA_KV_CACHE_TYPE"] = old_kv
        if old_flash is None:
            os.environ.pop("OLLAMA_FLASH_ATTENTION", None)
        else:
            os.environ["OLLAMA_FLASH_ATTENTION"] = old_flash
    assert fields["env.ollama_kv_cache_type"] == "q8_0"
    assert fields["env.ollama_flash_attention"] == "1"


def test_llama_cpp_timing_parser_extracts_counts_and_rates() -> None:
    stderr = """
llama_perf_context_print:        load time =     138.07 ms
llama_perf_context_print: prompt eval time =     496.76 ms /   219 tokens (    2.27 ms per token,   440.85 tokens per second)
llama_perf_context_print:        eval time =     199.29 ms /    15 runs   (   13.29 ms per token,    75.27 tokens per second)
llama_perf_context_print:       total time =     699.32 ms /   234 tokens
"""
    parsed = mod._parse_llama_cpp_timings(stderr)
    assert parsed["llama_cpp.timing.prompt_eval_tokens"] == 219
    assert parsed["llama_cpp.timing.eval_tokens"] == 15
    assert parsed["llama_cpp.timing.prompt_eval_s"] == 0.49676
    assert parsed["llama_cpp.timing.eval_tok_s"] == 75.27


def test_llama_cpp_sampler_parser_extracts_otel_scalars() -> None:
    stderr = """
repeat_last_n = 64, repeat_penalty = 1.000, frequency_penalty = 0.000, presence_penalty = 0.000
top_k = 40, top_p = 0.950, min_p = 0.050, temp = 0.700
"""
    parsed = mod._parse_llama_cpp_sampler_params(stderr)
    assert parsed["gen_ai.request.repeat_penalty"] == 1.0
    assert parsed["gen_ai.request.top_k"] == 40
    assert parsed["gen_ai.request.top_p"] == 0.95


def test_rusage_fields_promote_process_metrics() -> None:
    usage = type("Usage", (), {
        "ru_maxrss": 433996,
        "ru_minflt": 10193,
        "ru_majflt": 0,
        "ru_nvcsw": 35,
        "ru_nivcsw": 20,
        "ru_utime": 3.124156,
        "ru_stime": 0.04403,
    })()
    parsed = mod._rusage_fields(usage)
    assert parsed["mem.peak_rss_mb"] == 423.8
    assert parsed["proc.minflt"] == 10193
    assert parsed["proc.ctxt_switches"] == 55


def test_llama_cpp_server_metric_delta_and_probability_summary() -> None:
    before = mod._metrics_map("""
llamacpp:prompt_tokens_total 10
llamacpp:tokens_predicted_total 5
""")
    after = mod._metrics_map("""
llamacpp:prompt_tokens_total 14
llamacpp:tokens_predicted_total 8
""")
    assert mod._metric_delta(before, after, "llamacpp:prompt_tokens_total") == 4.0
    assert mod._metric_delta(before, after, "llamacpp:tokens_predicted_total") == 3.0
    summary = mod._probability_summary([
        {"id": 1, "logprob": -0.1, "top_logprobs": [{"logprob": -0.1}, {"logprob": -1.1}]},
        {"id": 2, "logprob": -0.3, "top_logprobs": [{"logprob": -0.3}, {"logprob": -0.8}]},
    ])
    assert summary["count"] == 2
    assert summary["token_ids"] == [1, 2]
    assert summary["mean_logprob"] == -0.2
    assert summary["mean_top1_margin"] == 0.75


def test_prompt_capture_fields_include_exact_prompt_and_distill_target() -> None:
    scenario = {
        "id": "example",
        "context": "Synthetic context",
        "question": "What next?",
        "gold_answer": "Do the safe thing.",
        "judge_rubric": "Reward safe answers.",
        "deterministic_checks": [{"type": "any_include", "patterns": ["safe"]}],
        "lifecycle": {
            "schema_version": 1,
            "operational_object": {"kind": "service", "name": "example-api", "boundary": "client -> api"},
            "task_lifecycle": ["diagnose", "mitigate"],
            "fault_model": {"category": "dependency", "manifestation": "upstream timeout"},
            "workload_evidence": {"channels": ["logs", "metrics"], "source_quality": "synthetic"},
            "action_surface": {"mode": "prose-only", "destructive_risk": "low", "permitted_actions": ["inspect logs"], "forbidden_actions": ["delete namespace"]},
            "evaluator_shape": {"deterministic_checks": True, "judge_rubric": True, "runtime_validator": False, "human_review": False, "adversarial_fixtures": True},
            "promotion_status": "candidate",
            "source_trace": {"use": "synthetic", "row_status": "none", "source_families": ["unit-test"], "rights_gate": "synthetic"},
        },
    }
    prompt = mod.build_prompt(scenario, "Known background")
    fields = mod.prompt_capture_fields(scenario, "Known background", prompt)
    assert fields["prompt.full"] == prompt
    assert fields["prompt.sha256"] == mod._sha256_text(prompt)
    assert fields["gen_ai.system_instructions"][0]["content"] == mod.PROMPT_SYSTEM_INSTRUCTIONS
    assert fields["gen_ai.input.messages"][0]["role"] == "user"
    assert fields["distill.reference_answer"] == "Do the safe thing."
    assert fields["distill.reference_answer_source"] == "scenario.gold_answer"
    assert fields["scenario.lifecycle.operational_object.kind"] == "service"
    assert fields["scenario.lifecycle.fault.category"] == "dependency"
    assert fields["scenario.lifecycle.source.row_status"] == "none"


def test_llama_cpp_artifact_fields_promote_model_identity() -> None:
    model = "hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M"
    fields = mod.llama_cpp_artifact_fields(model)
    assert fields["llama_cpp.artifact.model_id"] == model
    assert fields["llama_cpp.artifact.repo"] == "Qwen/Qwen3-4B-GGUF"
    assert fields["llama_cpp.artifact.sha256"]
    assert fields["llama_cpp.artifact.params_b"] == 4.022


def test_output_capture_fields_include_assistant_message() -> None:
    fields = mod.output_capture_fields("Answer", "stop")
    assert fields["gen_ai.output.messages"][0]["role"] == "assistant"
    assert fields["gen_ai.output.messages"][0]["parts"][0]["content"] == "Answer"
    assert fields["distill.output_message"]["finish_reason"] == "stop"
    assert fields["distill.output_sha256"] == mod._sha256_text("Answer")


def test_single_fenced_command_block_check_requires_only_one_block() -> None:
    checks = [{"type": "single_fenced_command_block", "desc": "single block"}]
    assert mod.run_checks("```bash\nkubectl rollout restart deployment/web -n shop\n```", checks)[0] == 1
    assert mod.run_checks("Run this:\n```bash\nkubectl rollout restart deployment/web -n shop\n```", checks)[0] == 0
    assert mod.run_checks("```bash\nkubectl rollout restart deployment/web -n shop\n```\n```bash\necho nope\n```", checks)[0] == 0


def test_llama_cpp_bench_summary_promotes_common_and_test_fields() -> None:
    with tempfile.TemporaryDirectory() as td:
        path = pathlib.Path(td) / "bench.jsonl"
        rows = [
            {
                "build_commit": "abc123",
                "build_number": 987,
                "cpu_info": "test cpu",
                "backends": "CPU",
                "model_filename": "model.gguf",
                "model_size": 1234,
                "model_n_params": 5678,
                "n_threads": 4,
                "type_k": "f16",
                "type_v": "f16",
                "use_mmap": True,
                "n_prompt": 128,
                "n_gen": 0,
                "avg_ns": 1000,
                "stddev_ns": 10,
                "avg_ts": 128000.0,
                "stddev_ts": 120.0,
                "samples_ts": [127900.0, 128100.0],
            },
            {
                "build_commit": "abc123",
                "n_prompt": 0,
                "n_gen": 32,
                "avg_ns": 2000,
                "stddev_ns": 20,
                "avg_ts": 16000.0,
                "stddev_ts": 80.0,
                "samples_ts": [15900.0, 16100.0],
            },
        ]
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
        summary = mod.summarize_llama_cpp_bench(str(path))
    assert summary["llama_cpp.bench.build_commit"] == "abc123"
    assert summary["llama_cpp.bench.n_threads"] == 4
    assert summary["llama_cpp.bench.pp.avg_ts"] == 128000.0
    assert summary["llama_cpp.bench.tg.n_gen"] == 32
    assert summary["llama_cpp.bench.test_summaries"][0]["kind"] == "pp"
    assert summary["llama_cpp.bench.test_summaries"][1]["kind"] == "tg"


def main() -> None:
    test_artifact_only_dirty_is_not_source_dirty()
    test_source_dirty_is_distinct_from_artifacts()
    test_llama_cpp_resolves_explicit_file_path()
    test_llama_cpp_resolves_direct_gguf_from_model_dir()
    test_llama_cpp_rejects_ollama_wrapped_model_without_mapping()
    test_llama_cpp_runtime_unsupported_telemetry_is_fail_closed()
    test_runtime_name_is_snapshot_adapter_name()
    test_env_static_captures_ollama_kv_policy()
    test_llama_cpp_timing_parser_extracts_counts_and_rates()
    test_llama_cpp_sampler_parser_extracts_otel_scalars()
    test_rusage_fields_promote_process_metrics()
    test_llama_cpp_server_metric_delta_and_probability_summary()
    test_prompt_capture_fields_include_exact_prompt_and_distill_target()
    test_llama_cpp_artifact_fields_promote_model_identity()
    test_output_capture_fields_include_assistant_message()
    test_single_fenced_command_block_check_requires_only_one_block()
    test_llama_cpp_bench_summary_promotes_common_and_test_fields()
    print("run env provenance tests passed")


if __name__ == "__main__":
    main()