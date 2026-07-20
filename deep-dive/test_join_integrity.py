"""Join-integrity guard tests for full_data.load_full().

Runs under the deep-dive venv (needs pandas), NOT the stdlib scripts/ gate:
    ./deep-dive/.venv/bin/python deep-dive/test_join_integrity.py

Proves (1) the real 152 frame passes the guard and forms a full, 2-judge, 1-to-1
grid, and (2) every corruption the guard exists to catch actually raises. This is
the executable form of the MSc reflection lesson that a left_join can run clean but
still be wrong.
"""
from __future__ import annotations

import pathlib
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import full_data as fd  # noqa: E402

CELL = fd._CELL


def _clean_trio():
    """A minimal, valid (results, judged, consensus) trio: 3 cells, each judged twice."""
    cells = [("m1", "s1", 1), ("m1", "s1", 2), ("m2", "s1", 1)]
    res = pd.DataFrame(cells, columns=CELL)
    jud = pd.DataFrame(
        [(*c, j, 3.0) for c in cells for j in ("gpt-5.4", "claude-opus-4.6")],
        columns=CELL + ["judge_model", "score"])
    cons = jud.groupby(CELL)["score"].mean().rename("judge_score").reset_index()
    return res, jud, cons


def _recons(jud):
    return jud.groupby(CELL)["score"].mean().rename("judge_score").reset_index()


def _expect_raise(label, res, jud, cons):
    try:
        fd._assert_join_integrity(res, jud, cons)
    except AssertionError as exc:
        assert "join-integrity" in str(exc), f"{label}: unexpected error text: {exc}"
        print(f"  ok  {label}: raised -> {str(exc)[:72]}...")
        return
    raise SystemExit(f"FAIL {label}: expected AssertionError, none raised")


def test_clean_passes():
    fd._assert_join_integrity(*_clean_trio())
    print("  ok  clean trio passes the guard")


def test_duplicate_result_key():
    res, jud, cons = _clean_trio()
    res = pd.concat([res, res.iloc[[0]]], ignore_index=True)  # fan-out risk
    _expect_raise("duplicate result key", res, jud, cons)


def test_single_judge_cell():
    res, jud, _ = _clean_trio()
    jud = jud.drop(index=0).reset_index(drop=True)  # first cell now has 1 judge
    _expect_raise("single-judge cell", res, jud, _recons(jud))


def test_double_scored_cell():
    res, jud, _ = _clean_trio()
    extra = pd.DataFrame([("m1", "s1", 1, "gpt-5.4", 2.0)], columns=CELL + ["judge_model", "score"])
    jud = pd.concat([jud, extra], ignore_index=True)  # 3 rows, still 2 distinct judges
    _expect_raise("double-scored cell", res, jud, _recons(jud))


def test_unmatched_result_cell():
    res, jud, cons = _clean_trio()
    res = pd.concat([res, pd.DataFrame([("m9", "s9", 9)], columns=CELL)], ignore_index=True)
    _expect_raise("result cell with no judgement", res, jud, cons)


def test_unmatched_judged_cell():
    res, jud, _ = _clean_trio()
    extra = pd.DataFrame([(*("m9", "s9", 9), j, 3.0) for j in ("gpt-5.4", "claude-opus-4.6")],
                         columns=CELL + ["judge_model", "score"])
    jud = pd.concat([jud, extra], ignore_index=True)
    _expect_raise("judged cell with no results row", res, jud, _recons(jud))


def test_real_152_frame():
    df = fd.load_full()
    n = len(df)
    grid = df["model"].nunique() * df["scenario"].nunique() * df["rep"].nunique()
    assert n == grid, f"not a full grid: {n} rows != {grid} (models*scenarios*reps)"
    assert df["judge_score"].notna().all(), "some cells have NaN judge_score (unmatched)"
    print(f"  ok  real 152 frame: {n} rows, full "
          f"{df['model'].nunique()}x{df['scenario'].nunique()}x{df['rep'].nunique()} grid, "
          "0 NaN judge_score")


if __name__ == "__main__":
    test_clean_passes()
    test_duplicate_result_key()
    test_single_judge_cell()
    test_double_scored_cell()
    test_unmatched_result_cell()
    test_unmatched_judged_cell()
    test_real_152_frame()
    print("PASS: join-integrity guard (5 negative + real-frame positive)")
