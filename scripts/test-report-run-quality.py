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


def summarize(run_dir: pathlib.Path, *judge_models: str) -> dict:
    judges = frozenset(("unknown", model) for model in judge_models) if judge_models else None
    return mod.summarize_run(run_dir, explicit_judges=judges)


def modern_fixture(root: pathlib.Path) -> pathlib.Path:
    repo = root / "repo"
    run_dir = repo / "data" / "runs" / "modern-run"
    run_dir.mkdir(parents=True)
    roster = repo / "data" / "models.modern.txt"
    scenarios = repo / "data" / "scenarios.modern.json"
    roster.write_text("model-a\n")
    scenarios.write_text(json.dumps({"scenarios": [{"id": "s1"}]}) + "\n")
    (run_dir / "run.meta").write_text(json.dumps({
        "schema_version": 2,
        "run_id": "modern-run",
        "model_set": "modern",
        "models": "data/models.modern.txt",
        "models_sha256": mod.sha256_file(roster),
        "models_count": 1,
        "expect": 1,
        "scenario_set": "modern",
        "scenarios": "data/scenarios.modern.json",
        "scenarios_sha256": mod.sha256_file(scenarios),
        "scenario_count": 1,
        "scenario_ids": ["s1"],
        "reps": 1,
        "judges": 1,
        "judge_identities": [
            {"judge_backend": "copilot", "judge_model": "claude"},
        ],
        "persist_mode": "git-push",
        "memory_context": "none",
        "inference_strategy": "baseline",
    }) + "\n")
    write_jsonl(run_dir / "_mirror" / "results.modern-run.jsonl", [{
        "model": "model-a", "scenario": "s1", "rep": 0,
        "env.memory_context": "none", "env.inference_strategy": "baseline",
        "gen_ai.response.finish_reasons": ["stop"], "dnf": False,
    }])
    write_jsonl(run_dir / "_mirror" / "results.modern-run.jsonl.done", [
        {"model": "model-a", "units": 1},
    ])
    write_jsonl(run_dir / "judged.modern-run.jsonl", [{
        "model": "model-a", "scenario": "s1", "rep": 0,
        "memory_context": "none", "inference_strategy": "baseline",
        "judge_backend": "copilot", "judge_model": "claude",
        "score": 5, "verdict": "ok", "evidence": "ok",
        "criteria_met": [], "criteria_missed": [],
    }])
    (run_dir / ".committed").write_text("model-a\n")
    (run_dir / ".push-pending").write_text("")
    return run_dir


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
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "best_of_3_detcheck", "judge_model": "claude", "score": 5, "verdict": "ok", "evidence": "ok", "criteria_met": [], "criteria_missed": [], "usage": {"tokens_in": 10, "tokens_out": 2, "ai_credits": 1.5}},
            {"model": "m", "scenario": "s2", "rep": 0, "memory_context": "none", "inference_strategy": "best_of_3_detcheck", "judge_model": "gpt", "score": 1, "verdict": "empty", "evidence": "No answer text was available for judging; the inference row did not produce a completion.", "criteria_met": [], "criteria_missed": ["answer was empty or unavailable"]},
        ])
        report = summarize(run_dir, "claude", "gpt")
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
        report = summarize(run_dir, "claude")
    assert report["judge_response_parse_failures"] == 1
    assert report["judge_unresolved_parse_failures"] == 1
    assert "unresolved-judge-response-parse-failures" in {item["code"] for item in report["strict_failures"]}


def test_report_accepts_parse_failure_followed_by_one_success():
    with tempfile.TemporaryDirectory() as td:
        run_dir = pathlib.Path(td) / "run-retry"
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
        write_jsonl(run_dir / "_mirror" / "results.run-retry.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0, "env.memory_context": "none", "env.inference_strategy": "baseline", "gen_ai.response.finish_reasons": ["stop"], "dnf": False},
        ])
        write_jsonl(run_dir / "judged.run-retry.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "claude", "score": None, "verdict": "garbled", "evidence": "parse_error", "criteria_met": [], "criteria_missed": ["judge response could not be parsed"]},
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "claude", "score": 4, "verdict": "ok", "evidence": "valid retry", "criteria_met": [], "criteria_missed": []},
        ])
        report = summarize(run_dir, "claude")
    assert report["judged_rows"] == 2
    assert report["judge_canonical_successes"] == 1
    assert report["judge_retry_attempts"] == 1
    assert report["judge_response_parse_failures"] == 1
    assert report["judge_unresolved_parse_failures"] == 0
    assert report["judge_missing_success_tuples"] == 0
    assert report["judge_competing_success_tuples"] == 0
    assert report["judge_evidence_missing"] == 0
    assert report["judge_criteria_missing"] == 0
    assert report["interpretation_ok"] is True


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
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "claude", "score": 5, "verdict": "ok", "evidence": "ok", "criteria_met": [], "criteria_missed": []},
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "gpt", "score": 4, "verdict": "ok", "evidence": "ok", "criteria_met": [], "criteria_missed": []},
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "gpt", "score": 4, "verdict": "ok", "evidence": "retry duplicate", "criteria_met": [], "criteria_missed": []},
        ])
        report = summarize(run_dir, "claude", "gpt")
    assert report["judged_rows"] == 3
    assert report["expected_judged_rows"] == 2
    assert report["judge_unique_tuples"] == 2
    assert report["judge_duplicate_tuples"] == 1
    assert report["judge_canonical_successes"] == 1
    assert report["judge_competing_success_tuples"] == 1
    assert report["judge_duplicate_examples"] == [{
        "count": 2,
        "model": "m",
        "scenario": "s1",
        "rep": 0,
        "memory_context": "none",
        "inference_strategy": "baseline",
        "judge_backend": "unknown",
        "judge_model": "gpt",
    }]
    assert report["interpretation_ok"] is False
    assert {item["code"] for item in report["strict_failures"]} == {
        "judged-success-count-mismatch",
        "competing-successful-judge-tuples",
    }


def test_report_keeps_same_model_id_from_different_backends_distinct():
    with tempfile.TemporaryDirectory() as td:
        run_dir = pathlib.Path(td) / "run-backends"
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
        write_jsonl(run_dir / "_mirror" / "results.run-backends.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0,
             "env.memory_context": "none", "env.inference_strategy": "baseline",
             "gen_ai.response.finish_reasons": ["stop"], "dnf": False},
        ])
        write_jsonl(run_dir / "judged.run-backends.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0,
             "memory_context": "none", "inference_strategy": "baseline",
             "judge_backend": "copilot", "judge_model": "shared", "score": 5,
             "verdict": "ok", "evidence": "ok", "criteria_met": [], "criteria_missed": [],
             "usage": {"tokens_in": 10}},
            {"model": "m", "scenario": "s1", "rep": 0,
             "memory_context": "none", "inference_strategy": "baseline",
             "judge_backend": "github", "judge_model": "shared", "score": 4,
             "verdict": "ok", "evidence": "ok", "criteria_met": [], "criteria_missed": [],
             "usage": {"tokens_in": 20}},
        ])
        report = mod.summarize_run(
            run_dir,
            explicit_judges=frozenset({("copilot", "shared"), ("github", "shared")}),
        )
    assert report["judge_unique_tuples"] == 2
    assert report["judge_duplicate_tuples"] == 0
    assert report["usage_by_judge"]["copilot:shared"]["tokens_in"] == 10
    assert report["usage_by_judge"]["github:shared"]["tokens_in"] == 20
    assert report["interpretation_ok"] is True


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
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "claude", "score": 5, "verdict": "ok", "evidence": "ok", "criteria_met": [], "criteria_missed": []},
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "gpt", "score": 4, "verdict": "ok", "evidence": "ok", "criteria_met": [], "criteria_missed": []},
        ])
        report = summarize(run_dir, "claude", "gpt")
    assert report["interpretation_ok"] is True
    assert report["strict_failure_count"] == 0
    assert report["strict_failures"] == []


def test_modern_strict_gate_binds_exact_contract_and_persistence_domains():
    with tempfile.TemporaryDirectory() as directory:
        run_dir = modern_fixture(pathlib.Path(directory))
        report = mod.summarize_run(run_dir)
        assert report["interpretation_ok"] is True

    attacks = (
        ("model", "model-b", {"missing-result-domain-keys", "extra-result-domain-keys"}),
        ("scenario", "s2", {"missing-result-domain-keys", "extra-result-domain-keys"}),
    )
    for field, value, expected_codes in attacks:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = modern_fixture(pathlib.Path(directory))
            results = run_dir / "_mirror" / "results.modern-run.jsonl"
            rows = [json.loads(line) for line in results.read_text().splitlines()]
            rows[0][field] = value
            write_jsonl(results, rows)
            report = mod.summarize_run(run_dir)
            codes = {item["code"] for item in report["strict_failures"]}
            assert expected_codes <= codes

    with tempfile.TemporaryDirectory() as directory:
        run_dir = modern_fixture(pathlib.Path(directory))
        (run_dir / ".committed").write_text("model-b\n")
        report = mod.summarize_run(run_dir)
        assert "persistence-domain-invalid" in {
            item["code"] for item in report["strict_failures"]
        }


def test_modern_strict_gate_rejects_unclassified_failed_judge_attempt() -> None:
    with tempfile.TemporaryDirectory() as directory:
        run_dir = modern_fixture(pathlib.Path(directory))
        judged = run_dir / "judged.modern-run.jsonl"
        failed = json.loads(judged.read_text().splitlines()[0])
        failed.update({"score": None, "evidence": "unknown_failure", "verdict": "failed"})
        with judged.open("a") as handle:
            handle.write(json.dumps(failed) + "\n")
        report = mod.summarize_run(run_dir)
        assert "unclassified-judge-failures" in {
            item["code"] for item in report["strict_failures"]
        }


def test_modern_contract_cannot_downgrade_by_deleting_schema_version() -> None:
    for value in (None, 1, "2", True):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = modern_fixture(pathlib.Path(directory))
            meta_path = run_dir / "run.meta"
            meta = json.loads(meta_path.read_text())
            if value is None:
                meta.pop("schema_version")
            else:
                meta["schema_version"] = value
            meta_path.write_text(json.dumps(meta) + "\n")
            report = mod.summarize_run(run_dir)
            assert "run-contract-invalid" in {
                item["code"] for item in report["strict_failures"]
            }


def test_modern_contract_requires_valid_persistence_mode_and_evidence() -> None:
    for value in (None, "unknown", 1, False):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = modern_fixture(pathlib.Path(directory))
            meta_path = run_dir / "run.meta"
            meta = json.loads(meta_path.read_text())
            if value is None:
                meta.pop("persist_mode")
            else:
                meta["persist_mode"] = value
            meta_path.write_text(json.dumps(meta) + "\n")
            (run_dir / ".committed").unlink(missing_ok=True)
            (run_dir / "_mirror" / "results.modern-run.jsonl.done").unlink(missing_ok=True)
            report = mod.summarize_run(run_dir)
            codes = {item["code"] for item in report["strict_failures"]}
            assert "run-contract-invalid" in codes
            assert "persistence-domain-invalid" in codes


def test_legacy_persistence_requires_explicit_opt_in() -> None:
    with tempfile.TemporaryDirectory() as directory:
        run_dir = modern_fixture(pathlib.Path(directory))
        meta_path = run_dir / "run.meta"
        meta = json.loads(meta_path.read_text())
        meta.pop("persist_mode")
        meta_path.write_text(json.dumps(meta) + "\n")
        (run_dir / ".committed").unlink()
        (run_dir / "_mirror" / "results.modern-run.jsonl.done").unlink()
        default = mod.summarize_run(run_dir)
        opted_in = mod.summarize_run(run_dir, allow_legacy_persistence=True)
        assert default["interpretation_ok"] is False
        assert opted_in["interpretation_ok"] is True
        assert opted_in["legacy_persistence_opt_in"] is True


def test_modern_done_marker_rejects_parse_errors_and_boolean_units() -> None:
    with tempfile.TemporaryDirectory() as directory:
        run_dir = modern_fixture(pathlib.Path(directory))
        done = run_dir / "_mirror" / "results.modern-run.jsonl.done"
        with done.open("a") as handle:
            handle.write("not-json\n")
        report = mod.summarize_run(run_dir)
        assert "persistence-domain-invalid" in {
            item["code"] for item in report["strict_failures"]
        }
    with tempfile.TemporaryDirectory() as directory:
        run_dir = modern_fixture(pathlib.Path(directory))
        write_jsonl(
            run_dir / "_mirror" / "results.modern-run.jsonl.done",
            [{"model": "model-a", "units": True}],
        )
        report = mod.summarize_run(run_dir)
        assert "persistence-domain-invalid" in {
            item["code"] for item in report["strict_failures"]
        }


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
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "claude", "score": 5, "verdict": "ok", "evidence": "ok", "criteria_met": [], "criteria_missed": []},
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "gpt", "score": 4, "verdict": "ok", "evidence": "ok", "criteria_met": [], "criteria_missed": []},
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "gpt", "score": 4, "verdict": "ok", "evidence": "retry duplicate", "criteria_met": [], "criteria_missed": []},
        ])
        report = summarize(run_dir, "claude", "gpt")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            mod.print_markdown([report])
    rendered = output.getvalue()
    assert "## run-md" in rendered
    assert "### Interpretation Gate" in rendered
    assert "**FAIL** (`strict_failures=2`)" in rendered
    assert "`competing-successful-judge-tuples`" in rendered
    assert "### Multiple Judge Attempt Examples" in rendered


def test_strict_gate_fails_judged_only_artifact_without_run_meta():
    with tempfile.TemporaryDirectory() as td:
        run_dir = pathlib.Path(td) / "run-judged-only"
        run_dir.mkdir()
        write_jsonl(run_dir / "judged.run-judged-only.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "claude", "score": 5, "verdict": "ok", "evidence": "ok", "criteria_met": [], "criteria_missed": []},
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
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "claude", "score": 5, "verdict": "ok", "evidence": "ok", "criteria_met": [], "criteria_missed": []},
        ])
        report = summarize(run_dir, "claude")
    assert report["rows"] == 1
    assert report["result_file_count"] == 1
    assert report["interpretation_ok"] is True


def test_report_rejects_missing_expected_key_plus_extra_observed_key():
    with tempfile.TemporaryDirectory() as td:
        run_dir = pathlib.Path(td) / "run-domain-substitution"
        run_dir.mkdir()
        (run_dir / "run.meta").write_text(json.dumps({
            "model_set": "dryrun",
            "scenario_set": "fixture",
            "memory_context": "none",
            "inference_strategy": "baseline",
            "expect": 1,
            "scenario_count": 1,
            "reps": 1,
            "judges": 1,
        }))
        write_jsonl(run_dir / "_mirror" / "results.run-domain-substitution.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0, "env.memory_context": "none", "env.inference_strategy": "baseline", "gen_ai.response.finish_reasons": ["stop"], "dnf": False},
        ])
        write_jsonl(run_dir / "judged.run-domain-substitution.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "extra", "score": 4, "verdict": "ok", "evidence": "wrong judge", "criteria_met": [], "criteria_missed": []},
        ])
        report = summarize(run_dir, "expected")
    codes = {item["code"] for item in report["strict_failures"]}
    assert report["judge_canonical_successes"] == 0
    assert report["judge_missing_keys"] == 1
    assert report["judge_extra_keys"] == 1
    assert "missing-judge-keys" in codes
    assert "extra-judge-keys" in codes
    assert report["interpretation_ok"] is False


def test_report_rejects_explicit_judge_substitution_against_metadata():
    with tempfile.TemporaryDirectory() as td:
        run_dir = modern_fixture(pathlib.Path(td))
        matching = mod.summarize_run(
            run_dir,
            explicit_judges=frozenset({("copilot", "claude")}),
        )
        substituted = mod.summarize_run(
            run_dir,
            explicit_judges=frozenset({("copilot", "substitute")}),
        )
    assert matching["judge_domain_conflict"] is False
    assert matching["interpretation_ok"] is True
    assert substituted["judge_domain_conflict"] is True
    assert "judge-domain-conflict" in {
        item["code"] for item in substituted["strict_failures"]
    }
    assert substituted["interpretation_ok"] is False


def test_report_rejects_malformed_modern_judge_metadata():
    malformed_values = (
        None,
        "copilot:expected",
        [],
        [{}],
        [{"judge_backend": "", "judge_model": "expected"}],
        [
            {"judge_backend": "copilot", "judge_model": "expected"},
            {"judge_backend": "copilot", "judge_model": "expected"},
        ],
    )
    for index, malformed in enumerate(malformed_values):
        with tempfile.TemporaryDirectory() as td:
            run_dir = pathlib.Path(td) / f"run-malformed-domain-{index}"
            run_dir.mkdir()
            (run_dir / "run.meta").write_text(json.dumps({
                "expect": 1,
                "scenario_count": 1,
                "reps": 1,
                "judges": 1,
                "judge_identities": malformed,
            }))
            write_jsonl(run_dir / "_mirror" / f"results.{run_dir.name}.jsonl", [
                {"model": "m", "scenario": "s1", "rep": 0, "env.memory_context": "none", "env.inference_strategy": "baseline", "gen_ai.response.finish_reasons": ["stop"], "dnf": False},
            ])
            write_jsonl(run_dir / f"judged.{run_dir.name}.jsonl", [
                {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_backend": "copilot", "judge_model": "substitute", "score": 4, "verdict": "ok", "evidence": "valid", "criteria_met": [], "criteria_missed": []},
            ])
            report = mod.summarize_run(
                run_dir,
                explicit_judges=frozenset({("copilot", "substitute")}),
            )
        assert report["judge_metadata_error"]
        assert "judge-metadata-invalid" in {
            item["code"] for item in report["strict_failures"]
        }
        assert report["interpretation_ok"] is False

    with tempfile.TemporaryDirectory() as td:
        run_dir = pathlib.Path(td) / "run-cardinality-domain"
        run_dir.mkdir()
        (run_dir / "run.meta").write_text(json.dumps({
            "expect": 1,
            "scenario_count": 1,
            "reps": 1,
            "judges": 2,
            "judge_identities": [
                {"judge_backend": "copilot", "judge_model": "expected"},
            ],
        }))
        write_jsonl(run_dir / "_mirror" / "results.run-cardinality-domain.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0, "env.memory_context": "none", "env.inference_strategy": "baseline", "gen_ai.response.finish_reasons": ["stop"], "dnf": False},
        ])
        report = mod.summarize_run(run_dir)
    assert "cardinality" in report["judge_metadata_error"]
    assert report["interpretation_ok"] is False


def test_report_requires_strict_positive_integer_judge_count():
    invalid_counts = (2.5, "2", "two", {}, [], True, False, 0, -1, None)
    for index, invalid in enumerate(invalid_counts):
        with tempfile.TemporaryDirectory() as td:
            run_dir = pathlib.Path(td) / f"run-invalid-count-{index}"
            run_dir.mkdir()
            meta = {
                "expect": 1,
                "scenario_count": 1,
                "reps": 1,
                "judges": invalid,
                "judge_identities": [
                    {"judge_backend": "copilot", "judge_model": "expected"},
                ],
            }
            (run_dir / "run.meta").write_text(json.dumps(meta))
            write_jsonl(run_dir / "_mirror" / f"results.{run_dir.name}.jsonl", [
                {"model": "m", "scenario": "s1", "rep": 0, "env.memory_context": "none", "env.inference_strategy": "baseline", "gen_ai.response.finish_reasons": ["stop"], "dnf": False},
            ])
            report = mod.summarize_run(run_dir)
        assert report["judge_count_error"]
        assert "judge-count-invalid" in {
            item["code"] for item in report["strict_failures"]
        }
        assert report["interpretation_ok"] is False

    with tempfile.TemporaryDirectory() as td:
        run_dir = pathlib.Path(td) / "run-missing-count"
        run_dir.mkdir()
        (run_dir / "run.meta").write_text(json.dumps({
            "expect": 1,
            "scenario_count": 1,
            "reps": 1,
            "judge_identities": [
                {"judge_backend": "copilot", "judge_model": "expected"},
            ],
        }))
        report = mod.summarize_run(run_dir)
    assert report["judge_count_error"]
    assert report["interpretation_ok"] is False

    assert mod.analysis_metrics.metadata_judge_count({"judges": 1}) == 1


def test_report_rejects_verdictless_or_wrong_type_success():
    with tempfile.TemporaryDirectory() as td:
        run_dir = pathlib.Path(td) / "run-malformed-success"
        run_dir.mkdir()
        (run_dir / "run.meta").write_text(json.dumps({
            "expect": 1,
            "scenario_count": 1,
            "reps": 1,
            "judges": 1,
        }))
        write_jsonl(run_dir / "_mirror" / "results.run-malformed-success.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0, "env.memory_context": "none", "env.inference_strategy": "baseline", "gen_ai.response.finish_reasons": ["stop"], "dnf": False},
        ])
        write_jsonl(run_dir / "judged.run-malformed-success.jsonl", [
            {"model": "m", "scenario": "s1", "rep": 0, "memory_context": "none", "inference_strategy": "baseline", "judge_model": "claude", "score": 4, "evidence": 123, "criteria_met": [], "criteria_missed": []},
        ])
        report = summarize(run_dir, "claude")
    assert report["judge_canonical_successes"] == 0
    assert report["judge_missing_success_tuples"] == 1
    assert report["interpretation_ok"] is False


def main() -> None:
    tests = [value for name, value in globals().items() if name.startswith("test_") and callable(value)]
    for test in sorted(tests, key=lambda item: item.__name__):
        test()
    print(f"report-run-quality tests passed: {len(tests)}")


if __name__ == "__main__":
    main()
