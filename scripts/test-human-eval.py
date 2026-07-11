#!/usr/bin/env python3
"""Regression tests for committed human-packet agreement scoring."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import human_eval  # noqa: E402


def fixture():
    return {
        "source_id": "fixture",
        "items": [
            {"row_id": "H1", "judge_scores": {"judge-a": 1, "judge-b": 1}},
            {"row_id": "H2", "judge_scores": {"judge-a": 3, "judge-b": 3}},
            {"row_id": "H3", "judge_scores": {"judge-a": 5, "judge-b": 5}},
        ],
    }


def test_perfect_agreement_uses_fixed_five_point_scale():
    rows = [
        {"row_id": "H1", "human_score": "1"},
        {"row_id": "H2", "human_score": "3"},
        {"row_id": "H3", "human_score": "5"},
    ]
    report = human_eval.packet_agreement(fixture(), rows)
    assert report["items_scored"] == 3
    assert report["all_judges_meet_preregistered_bar"] is True
    assert report["judge_reports"]["judge-a"]["kappa_quadratic"] == 1.0


def test_incomplete_scores_refuse():
    try:
        human_eval.packet_agreement(fixture(), [{"row_id": "H1", "human_score": "1"}])
    except ValueError as exc:
        assert "not fully scored" in str(exc)
    else:
        raise AssertionError("incomplete packet must fail")


def test_invalid_score_refuses():
    rows = [
        {"row_id": "H1", "human_score": "1"},
        {"row_id": "H2", "human_score": "6"},
        {"row_id": "H3", "human_score": "5"},
    ]
    try:
        human_eval.packet_agreement(fixture(), rows)
    except ValueError as exc:
        assert "invalid human score" in str(exc)
    else:
        raise AssertionError("out-of-range score must fail")


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in sorted(tests, key=lambda item: item.__name__):
        test()
    print(f"human eval tests passed: {len(tests)}")


if __name__ == "__main__":
    main()