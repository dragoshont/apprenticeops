#!/usr/bin/env python3
"""Regression test that parse-failed judge attempts remain retryable."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
SCRIPT = REPO / "judge.py"
SPEC = importlib.util.spec_from_file_location("judge_module", SCRIPT)
assert SPEC and SPEC.loader
judge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(judge)


def test_parse_failure_is_not_a_completed_resume_key() -> None:
    row = {
        "model": "model-a",
        "scenario": "s1",
        "rep": 0,
        "env.memory_context": "none",
        "env.inference_strategy": "baseline",
    }
    condition = "a" * 64
    exact, _legacy = judge.judgement_resume_keys(
        row,
        condition_sha=condition,
        judge_backend="copilot",
        judge_model="gpt-test",
    )
    parse_failure_done = set()
    assert not judge.judgement_is_done(
        row,
        condition_sha=condition,
        judge_backend="copilot",
        judge_model="gpt-test",
        done_exact=parse_failure_done,
        done_legacy=set(),
        legacy_resume_safe=False,
        allow_legacy_resume=False,
    )
    assert judge.judgement_is_done(
        row,
        condition_sha=condition,
        judge_backend="copilot",
        judge_model="gpt-test",
        done_exact={exact},
        done_legacy=set(),
        legacy_resume_safe=False,
        allow_legacy_resume=False,
    )


def test_torn_tail_is_truncated_and_durable_append_survives() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = pathlib.Path(directory) / "judged.jsonl"
        first = {"score": 4, "verdict": "ok"}
        path.write_bytes(json.dumps(first).encode() + b"\n{\"score\":")
        judge.recover_jsonl_tail(path)
        assert [json.loads(line) for line in path.read_text().splitlines()] == [first]
        second = {"score": None, "evidence": "parse_error"}
        judge.append_jsonl_durable(path, second)
        assert [json.loads(line) for line in path.read_text().splitlines()] == [first, second]


def test_malformed_interior_row_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = pathlib.Path(directory) / "judged.jsonl"
        path.write_text('{"score":4}\nnot-json\n')
        try:
            judge.recover_jsonl_tail(path)
        except ValueError as exc:
            assert "malformed durable JSON" in str(exc)
        else:
            raise AssertionError("malformed interior judge row was accepted")


def test_invalid_non_null_score_is_not_resumable() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = pathlib.Path(directory) / "judged.jsonl"
        base = {
            "model": "model-a",
            "scenario": "s1",
            "rep": 0,
            "analysis_condition_key_sha256": "a" * 64,
            "judge_backend": "copilot",
            "judge_model": "gpt-test",
            "verdict": "bad score",
            "evidence": "grounded",
            "criteria_met": [],
            "criteria_missed": [],
        }
        judge.append_jsonl_durable(path, {**base, "score": 99})
        exact, legacy = judge.load_judgement_resume_state(path)
        assert exact == set()
        assert legacy == set()
        judge.append_jsonl_durable(path, {**base, "score": 4})
        exact, legacy = judge.load_judgement_resume_state(path)
        assert len(exact) == 1
        assert legacy == set()


if __name__ == "__main__":
    test_parse_failure_is_not_a_completed_resume_key()
    test_torn_tail_is_truncated_and_durable_append_survives()
    test_malformed_interior_row_is_rejected()
    test_invalid_non_null_score_is_not_resumable()
    print("judge resume tests passed")