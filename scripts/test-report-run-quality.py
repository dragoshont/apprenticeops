#!/usr/bin/env python3
"""Regression tests for report-run-quality.py."""
from __future__ import annotations

import importlib.util
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
    assert report["dnf_by_inference_strategy"][0]["id"] == "best_of_3_detcheck"
    assert report["usage_by_judge"]["claude"]["tokens_in"] == 10


def main() -> None:
    test_report_flags_reliability_and_strategy()
    print("report-run-quality tests passed")


if __name__ == "__main__":
    main()
