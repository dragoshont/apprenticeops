#!/usr/bin/env python3
"""Regression tests for the completed-run summary schema.

The summary is a claim-bearing document, so the tests are mostly about honesty
rather than arithmetic: nothing hardcoded from another lane, no contrast
presented as pre-registered, and absences explained rather than dropped.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile

import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import analysis_lane  # noqa: E402
import analysis_summary  # noqa: E402

LANE_ID = "full-chatok-core20-r5-ollama-20260705-150053"
FAULTS = REPO / "data/models.ollama-chat-faults.json"


def _lane():
    directory = analysis_lane.SNAPSHOTS / LANE_ID
    return analysis_lane.resolve(LANE_ID) if directory.is_dir() else None


def _qbrk(order):
    return pd.DataFrame(
        [(g, 100 * (i + 1), 0.2 + 0.05 * i, 0.15 + 0.05 * i, 0.25 + 0.05 * i)
         for i, g in enumerate(order)],
        columns=["grouping_value", "n", "mean", "lo", "hi"])


def _build(lane, **kw):
    results = pd.read_csv(lane.results)
    judged = pd.read_csv(lane.judged)
    return analysis_summary.build(lane, results, judged, _qbrk(lane.grouping_order),
                                  faults_path=FAULTS, **kw)


def test_kappa_is_computed_not_inherited() -> None:
    """The frozen lane's 0.906 must never appear on a completed run."""
    lane = _lane()
    if lane is None:
        return
    summary = _build(lane)
    kappa = summary["evaluation"]["cross_judge_kappa_quad"]
    assert kappa != 0.906, "inherited the frozen lane's kappa"
    assert 0.0 < kappa < 1.0, kappa
    assert summary["evaluation"]["jointly_scored_cells"] == 15200


def test_judges_come_from_the_lane() -> None:
    lane = _lane()
    if lane is None:
        return
    axis = _build(lane)["evaluation"]["quality_axis"]
    assert "claude-opus-4.6" in axis and "gpt-5.4" in axis, axis
    # the frozen pair must not leak in
    assert "4.8" not in axis and "5.5" not in axis, axis


def test_no_gate_is_claimed_as_pre_registered() -> None:
    lane = _lane()
    if lane is None:
        return
    summary = _build(lane)
    assert summary["pre_registered_gates"] == []
    assert "not transferable" in summary["pre_registered_gates_note"]


def test_contrasts_are_labelled_descriptive() -> None:
    lane = _lane()
    if lane is None:
        return
    for contrast in _build(lane)["descriptive_contrasts"]:
        assert contrast["status"] == "descriptive_not_pre_registered", contrast


def test_population_separates_roster_from_analysis_population() -> None:
    lane = _lane()
    if lane is None:
        return
    pop = _build(lane)["population"]
    assert pop["roster_models"] == 152
    assert pop["in_population_models"] == 137
    assert pop["out_of_population_models"] == 15
    assert pop["roster_models"] == pop["in_population_models"] + pop["out_of_population_models"]


def test_roster_screen_is_always_disclosed() -> None:
    lane = _lane()
    if lane is None:
        return
    screen = _build(lane)["roster_screen"]
    assert screen["recorded"] is True
    assert screen["candidates"] == 173 and screen["ran"] == 152
    assert screen["excluded_despite_serving"] == 7
    assert len(screen["excluded_despite_serving_models"]) == 7
    assert "conditional on models that emit visible text" in screen["disclosure"]


def test_missing_arms_are_explained_not_dropped() -> None:
    lane = _lane()
    if lane is None:
        return
    safety = _build(lane, safety_by_arm=pd.Series({"instruct": 0.8}))["safety"]
    assert safety["arms_computed"] is True
    assert safety["arms_present"] == ["instruct"]
    assert safety["instruct_vs_reasoning_contrast_available"] is False
    reason = safety["reasoning_arm_absent_reason"]
    assert "deepseek-r1" in reason and "screen" in reason
    assert "must not be carried over" in reason


def test_uncomputed_arms_differ_from_absent_arms() -> None:
    lane = _lane()
    if lane is None:
        return
    safety = _build(lane)["safety"]
    assert safety["arms_computed"] is False
    assert "arms_present" not in safety, "absent and not-computed must not blur"


def test_conditions_report_single_batch() -> None:
    lane = _lane()
    if lane is None:
        return
    cond = _build(lane)["conditions"]
    assert cond["collection_batches"] == 1
    assert cond["cpu_frequency_regimes"] == 1
    assert cond["energy_comparable_fraction"] == 1.0
    assert cond["cross_batch_energy_pooling_required"] is False


def test_human_validation_is_declared_false() -> None:
    lane = _lane()
    if lane is None:
        return
    evaluation = _build(lane)["evaluation"]
    assert evaluation["human_validated"] is False
    assert "un-validated" in evaluation["human_validation_note"]


def test_reliability_is_reported_not_hidden() -> None:
    lane = _lane()
    if lane is None:
        return
    rel = _build(lane)["reliability"]
    assert rel["rows"] == 15200
    assert rel["dnf_rows"] == 208
    assert rel["truncated_rows"] == 1452


def test_missing_screen_record_is_marked_unrecorded() -> None:
    lane = _lane()
    if lane is None:
        return
    with tempfile.TemporaryDirectory() as tmp:
        summary = _build(lane, )
        del summary
        screen = analysis_summary.roster_screen(pathlib.Path(tmp) / "absent.json")
    assert screen == {"recorded": False}


def test_summary_is_json_serialisable() -> None:
    lane = _lane()
    if lane is None:
        return
    json.dumps(_build(lane))


def main() -> None:
    tests = [value for name, value in globals().items()
             if name.startswith("test_") and callable(value)]
    for test in sorted(tests, key=lambda fn: fn.__name__):
        test()
    print(f"analysis summary tests passed: {len(tests)}")


if __name__ == "__main__":
    main()
