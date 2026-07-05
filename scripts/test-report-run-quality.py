#!/usr/bin/env python3
"""Regression tests for report-run-quality.py."""
from __future__ import annotations

import importlib.util
import contextlib
import gzip
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


def write_jsonl_gz(path: pathlib.Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt") as handle:
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
            {"model": "m", "scenario": "s2", "rep": 0, "memory_context": "none", "inference_strategy": "best_of_3_detcheck", "judge_model": "gpt", "score": 1, "verdict": "empty", "evidence": "No answer text was available for judging; the inference row did not produce a completion.", "criteria_met": [], "criteria_missed": ["answer was empty or unavailable"]},
        ])
        report = mod.summarize_run(run_dir)
    assert report["rows"] == 2
    assert report["dnf"] == 1
    assert report["zero_output_stalls"] == 1
    assert report["judge_empty"] == 0
    assert report["empty_answer_judgements"] == 1
    assert report["judge_response_parse_failures"] == 0
    assert report["judge_duplicate_tuples"] == 0
    assert report["dnf_by_inference_strategy"][0]["id"] == "best_of_3_detcheck"
    assert report["usage_by_judge"]["claude"]["tokens_in"] == 10


def test_report_keeps_actual_empty_judge_as_strict_failure():
    with tempfile.TemporaryDirectory() as td:
        run_dir = pathlib.Path(td) / "run-empty-judge"
        run_dir.mkdir()
        (run_dir / "run.meta").write_text(json.dumps({
            "model_set": "dryrun",
            "scenario_set": "external-candidates-v0",
            "memory_context": "none",
            "inference_strategy": "baseline",
            "expect": 1,
            "scenario_count": 1,
            "reps": 1,
            "judges": 1,
        }))
        write_jsonl(run_dir / "_mirror" / "results.run-empty-judge.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0, "env.memory_context": "none", "env.inference_strategy": "baseline", "gen_ai.response.finish_reasons": ["stop"], "dnf": False},
        ])
        write_jsonl(run_dir / "judged.run-empty-judge.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "claude", "score": None, "verdict": "empty", "evidence": "", "criteria_met": [], "criteria_missed": []},
        ])
        report = mod.summarize_run(run_dir)
    assert report["judge_empty"] == 1
    assert report["empty_answer_judgements"] == 0
    assert "empty-judge-rows" in {item["code"] for item in report["strict_failures"]}


def test_report_accepts_machine_readable_no_answer_marker():
    with tempfile.TemporaryDirectory() as td:
        run_dir = pathlib.Path(td) / "run-no-answer-marker"
        run_dir.mkdir()
        (run_dir / "run.meta").write_text(json.dumps({
            "model_set": "dryrun",
            "scenario_set": "external-candidates-v0",
            "memory_context": "none",
            "inference_strategy": "baseline",
            "expect": 1,
            "scenario_count": 1,
            "reps": 1,
            "judges": 1,
        }))
        write_jsonl(run_dir / "_mirror" / "results.run-no-answer-marker.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0, "env.memory_context": "none", "env.inference_strategy": "baseline", "gen_ai.response.finish_reasons": ["DNF:error"], "dnf": True},
        ])
        write_jsonl(run_dir / "judged.run-no-answer-marker.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "claude", "score": 1, "verdict": "empty", "deterministic_no_answer": True, "evidence": "stable marker", "criteria_met": [], "criteria_missed": []},
        ])
        report = mod.summarize_run(run_dir)
    assert report["judge_empty"] == 0
    assert report["empty_answer_judgements"] == 1


def test_report_flags_judge_response_parse_failures():
    with tempfile.TemporaryDirectory() as td:
        run_dir = pathlib.Path(td) / "run-judge-parse-fail"
        run_dir.mkdir()
        (run_dir / "run.meta").write_text(json.dumps({
            "model_set": "dryrun",
            "scenario_set": "external-candidates-v0",
            "memory_context": "none",
            "inference_strategy": "baseline",
            "expect": 1,
            "scenario_count": 1,
            "reps": 1,
            "judges": 1,
        }))
        write_jsonl(run_dir / "_mirror" / "results.run-judge-parse-fail.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0, "env.memory_context": "none", "env.inference_strategy": "baseline", "gen_ai.response.finish_reasons": ["stop"], "dnf": False},
        ])
        write_jsonl(run_dir / "judged.run-judge-parse-fail.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "claude", "score": None, "verdict": "garbled", "evidence": "parse_error", "criteria_met": [], "criteria_missed": ["judge response could not be parsed"]},
        ])
        report = mod.summarize_run(run_dir)
    assert report["judge_response_parse_failures"] == 1
    assert "judge-response-parse-failures" in {item["code"] for item in report["strict_failures"]}


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


def test_strict_gate_fails_judged_only_artifact_without_run_meta():
    with tempfile.TemporaryDirectory() as td:
        run_dir = pathlib.Path(td) / "run-judged-only"
        run_dir.mkdir()
        write_jsonl(run_dir / "judged.run-judged-only.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "claude", "score": 5, "evidence": "ok", "criteria_met": [], "criteria_missed": []},
        ])
        report = mod.summarize_run(run_dir)
    assert report["rows"] == 0
    assert report["judged_rows"] == 1
    assert report["interpretation_ok"] is False
    assert {item["code"] for item in report["strict_failures"]} == {
        "run-meta-missing",
        "result-rows-missing",
    }


def test_report_reads_committed_gz_result_artifacts():
    with tempfile.TemporaryDirectory() as td:
        run_dir = pathlib.Path(td) / "run-gz"
        run_dir.mkdir()
        (run_dir / "run.meta").write_text(json.dumps({
            "model_set": "dryrun",
            "scenario_set": "external-candidates-v1",
            "memory_context": "none",
            "inference_strategy": "baseline",
            "expect": 1,
            "scenario_count": 1,
            "reps": 1,
            "judges": 1,
        }))
        write_jsonl_gz(run_dir / "m.results.jsonl.gz", [
            {"model": "m", "scenario": "s1", "rep": 0, "env.memory_context": "none", "env.inference_strategy": "baseline", "gen_ai.response.finish_reasons": ["stop"], "dnf": False},
        ])
        write_jsonl(run_dir / "judged.run-gz.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "claude", "score": 5, "evidence": "ok", "criteria_met": [], "criteria_missed": []},
        ])
        report = mod.summarize_run(run_dir)
    assert report["rows"] == 1
    assert report["result_file_count"] == 1
    assert report["interpretation_ok"] is True


def main() -> None:
    test_report_flags_reliability_and_strategy()
    test_report_keeps_actual_empty_judge_as_strict_failure()
    test_report_accepts_machine_readable_no_answer_marker()
    test_report_flags_judge_response_parse_failures()
    test_report_flags_duplicate_judge_tuples()
    test_strict_gate_passes_clean_structural_run()
    test_markdown_output_includes_gate_and_duplicate_examples()
    test_strict_gate_fails_judged_only_artifact_without_run_meta()
    test_report_reads_committed_gz_result_artifacts()
    print("report-run-quality tests passed")


if __name__ == "__main__":
    main()
