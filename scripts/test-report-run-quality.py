#!/usr/bin/env python3
"""Regression tests for report-run-quality.py."""
from __future__ import annotations

import importlib.util
import contextlib
import io
import json
import pathlib
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "report-run-quality.py"
spec = importlib.util.spec_from_file_location("report_run_quality", SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def write_jsonl(path: pathlib.Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_report_flags_reliability_and_strategy():
    with tempfile.TemporaryDirectory() as td:
        run_dir = pathlib.Path(td) / "run-a"
        run_dir.mkdir()
        (run_dir / "run.meta").write_text(json.dumps({
            "model_set": "dryrun",
            "scenario_set": "strategy-pilot-6",
            "memory_context": "none",
            "inference_strategy": "best_of_3_detcheck",
            "expect": 1,
            "scenario_count": 2,
            "reps": 1,
            "judges": 2,
        }))
        write_jsonl(run_dir / "_mirror" / "results.run-a.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0, "env.memory_context": "none", "env.inference_strategy": "best_of_3_detcheck", "gen_ai.response.finish_reasons": ["stop"], "dnf": False, "det_total": 1},
            {"model": "m", "scenario": "s2", "rep": 0, "env.memory_context": "none", "env.inference_strategy": "best_of_3_detcheck", "gen_ai.response.finish_reasons": ["DNF:stall"], "dnf": True, "gen_ai.usage.output_tokens": 0, "progress_trace": [], "det_total": 1},
        ])
        write_jsonl(run_dir / "judged.run-a.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "best_of_3_detcheck", "judge_model": "claude", "score": 5, "evidence": "ok", "criteria_met": [], "criteria_missed": [], "usage": {"tokens_in": 10, "tokens_out": 2, "ai_credits": 1.5}},
            {"model": "m", "scenario": "s2", "rep": 0, "memory_context": "none", "inference_strategy": "best_of_3_detcheck", "judge_model": "gpt", "score": 1, "verdict": "empty", "criteria_met": [], "criteria_missed": []},
        ])
        report = mod.summarize_run(run_dir)
    assert report["rows"] == 2
    assert report["dnf"] == 1
    assert report["zero_output_stalls"] == 1
    assert report["judge_empty"] == 1
    assert report["judge_duplicate_tuples"] == 0
    assert report["dnf_by_inference_strategy"][0]["id"] == "best_of_3_detcheck"
    assert report["usage_by_judge"]["claude"]["tokens_in"] == 10


def test_report_flags_duplicate_judge_tuples():
    with tempfile.TemporaryDirectory() as td:
        run_dir = pathlib.Path(td) / "run-dup"
        run_dir.mkdir()
        (run_dir / "run.meta").write_text(json.dumps({
            "model_set": "dryrun",
            "scenario_set": "external-candidates-v0",
            "memory_context": "none",
            "inference_strategy": "baseline",
            "expect": 1,
            "scenario_count": 1,
            "reps": 1,
            "judges": 2,
        }))
        write_jsonl(run_dir / "_mirror" / "results.run-dup.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0, "env.memory_context": "none", "env.inference_strategy": "baseline", "gen_ai.response.finish_reasons": ["stop"], "dnf": False},
        ])
        write_jsonl(run_dir / "judged.run-dup.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "claude", "score": 5, "evidence": "ok", "criteria_met": [], "criteria_missed": []},
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "gpt", "score": 4, "evidence": "ok", "criteria_met": [], "criteria_missed": []},
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "gpt", "score": 4, "evidence": "retry duplicate", "criteria_met": [], "criteria_missed": []},
        ])
        report = mod.summarize_run(run_dir)
    assert report["judged_rows"] == 3
    assert report["expected_judged_rows"] == 2
    assert report["judge_unique_tuples"] == 2
    assert report["judge_duplicate_tuples"] == 1
    assert report["judge_duplicate_examples"] == [{
        "count": 2,
        "model": "m",
        "scenario": "s1",
        "rep": 0,
        "memory_context": "none",
        "inference_strategy": "baseline",
        "judge_model": "gpt",
    }]
    assert report["interpretation_ok"] is False
    assert {item["code"] for item in report["strict_failures"]} == {
        "judged-row-count-mismatch",
        "duplicate-judge-tuples",
    }


def test_strict_gate_passes_clean_structural_run():
    with tempfile.TemporaryDirectory() as td:
        run_dir = pathlib.Path(td) / "run-clean"
        run_dir.mkdir()
        (run_dir / "run.meta").write_text(json.dumps({
            "model_set": "dryrun",
            "scenario_set": "external-candidates-v0",
            "memory_context": "none",
            "inference_strategy": "baseline",
            "expect": 1,
            "scenario_count": 1,
            "reps": 1,
            "judges": 2,
        }))
        write_jsonl(run_dir / "_mirror" / "results.run-clean.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0, "env.memory_context": "none", "env.inference_strategy": "baseline", "gen_ai.response.finish_reasons": ["stop"], "dnf": False},
        ])
        write_jsonl(run_dir / "judged.run-clean.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "claude", "score": 5, "evidence": "ok", "criteria_met": [], "criteria_missed": []},
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "gpt", "score": 4, "evidence": "ok", "criteria_met": [], "criteria_missed": []},
        ])
        report = mod.summarize_run(run_dir)
    assert report["interpretation_ok"] is True
    assert report["strict_failure_count"] == 0
    assert report["strict_failures"] == []


def test_markdown_output_includes_gate_and_duplicate_examples():
    with tempfile.TemporaryDirectory() as td:
        run_dir = pathlib.Path(td) / "run-md"
        run_dir.mkdir()
        (run_dir / "run.meta").write_text(json.dumps({
            "model_set": "dryrun",
            "scenario_set": "external-candidates-v0",
            "memory_context": "none",
            "inference_strategy": "baseline",
            "expect": 1,
            "scenario_count": 1,
            "reps": 1,
            "judges": 2,
        }))
        write_jsonl(run_dir / "_mirror" / "results.run-md.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0, "env.memory_context": "none", "env.inference_strategy": "baseline", "gen_ai.response.finish_reasons": ["stop"], "dnf": False},
        ])
        write_jsonl(run_dir / "judged.run-md.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "claude", "score": 5, "evidence": "ok", "criteria_met": [], "criteria_missed": []},
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "gpt", "score": 4, "evidence": "ok", "criteria_met": [], "criteria_missed": []},
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "gpt", "score": 4, "evidence": "retry duplicate", "criteria_met": [], "criteria_missed": []},
        ])
        report = mod.summarize_run(run_dir)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            mod.print_markdown([report])
    rendered = output.getvalue()
    assert "## run-md" in rendered
    assert "### Interpretation Gate" in rendered
    assert "**FAIL** (`strict_failures=2`)" in rendered
    assert "`duplicate-judge-tuples`" in rendered
    assert "### Duplicate Judge Examples" in rendered


def main() -> None:
    test_report_flags_reliability_and_strategy()
    test_report_flags_duplicate_judge_tuples()
    test_strict_gate_passes_clean_structural_run()
    test_markdown_output_includes_gate_and_duplicate_examples()
    print("report-run-quality tests passed")


if __name__ == "__main__":
    main()
