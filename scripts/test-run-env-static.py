#!/usr/bin/env python3
"""Regression tests for run.py environment provenance helpers."""

from __future__ import annotations

import importlib.util
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
    assert mod.INFERENCE_RUNTIME in {"ollama", "llama_cpp"}


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


def test_prompt_capture_fields_include_exact_prompt_and_distill_target() -> None:
    scenario = {
        "id": "example",
        "context": "Synthetic context",
        "question": "What next?",
        "gold_answer": "Do the safe thing.",
        "judge_rubric": "Reward safe answers.",
        "deterministic_checks": [{"type": "any_include", "patterns": ["safe"]}],
    }
    prompt = mod.build_prompt(scenario, "Known background")
    fields = mod.prompt_capture_fields(scenario, "Known background", prompt)
    assert fields["prompt.full"] == prompt
    assert fields["prompt.sha256"] == mod._sha256_text(prompt)
    assert fields["gen_ai.system_instructions"][0]["content"] == mod.PROMPT_SYSTEM_INSTRUCTIONS
    assert fields["gen_ai.input.messages"][0]["role"] == "user"
    assert fields["distill.reference_answer"] == "Do the safe thing."
    assert fields["distill.reference_answer_source"] == "scenario.gold_answer"


def test_output_capture_fields_include_assistant_message() -> None:
    fields = mod.output_capture_fields("Answer", "stop")
    assert fields["gen_ai.output.messages"][0]["role"] == "assistant"
    assert fields["gen_ai.output.messages"][0]["parts"][0]["content"] == "Answer"
    assert fields["distill.output_message"]["finish_reason"] == "stop"
    assert fields["distill.output_sha256"] == mod._sha256_text("Answer")


def main() -> None:
    test_artifact_only_dirty_is_not_source_dirty()
    test_source_dirty_is_distinct_from_artifacts()
    test_llama_cpp_resolves_explicit_file_path()
    test_llama_cpp_resolves_direct_gguf_from_model_dir()
    test_llama_cpp_rejects_ollama_wrapped_model_without_mapping()
    test_llama_cpp_runtime_unsupported_telemetry_is_fail_closed()
    test_runtime_name_is_snapshot_adapter_name()
    test_llama_cpp_timing_parser_extracts_counts_and_rates()
    test_llama_cpp_sampler_parser_extracts_otel_scalars()
    test_rusage_fields_promote_process_metrics()
    test_prompt_capture_fields_include_exact_prompt_and_distill_target()
    test_output_capture_fields_include_assistant_message()
    print("run env provenance tests passed")


if __name__ == "__main__":
    main()