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
        temperature=0,
        seed=1,
    )
    assert tel["dnf"] is True
    assert tel["gen_ai.response.finish_reasons"] == ["DNF:runtime_unsupported"]


def test_runtime_name_is_snapshot_adapter_name() -> None:
    assert mod.INFERENCE_RUNTIME in {"ollama", "llama_cpp"}


def main() -> None:
    test_artifact_only_dirty_is_not_source_dirty()
    test_source_dirty_is_distinct_from_artifacts()
    test_llama_cpp_resolves_explicit_file_path()
    test_llama_cpp_resolves_direct_gguf_from_model_dir()
    test_llama_cpp_rejects_ollama_wrapped_model_without_mapping()
    test_llama_cpp_runtime_unsupported_telemetry_is_fail_closed()
    test_runtime_name_is_snapshot_adapter_name()
    print("run env provenance tests passed")


if __name__ == "__main__":
    main()