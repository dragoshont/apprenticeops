#!/usr/bin/env python3
"""Regression tests for judged-row schema completeness."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "judge.py"


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


def main() -> None:
    test_empty_answer_contract()
    test_partial_judge_payload_is_completed()
    test_parse_error_fallback_contract()
    print("judge row schema tests passed")


if __name__ == "__main__":
    main()