#!/usr/bin/env python3
"""Regression tests for analysis lane resolution."""
from __future__ import annotations

import csv
import json
import os
import pathlib
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import analysis_lane  # noqa: E402

LANE_ID = "full-chatok-core20-r5-ollama-20260705-150053"


def test_default_follows_the_manifest() -> None:
    """With no override, the lane holding the claim is the lane returned."""
    manifest = json.loads(analysis_lane.MANIFEST.read_text())
    lane = analysis_lane.resolve()
    assert lane.lane_id == manifest["source_id"], (lane.lane_id, manifest["source_id"])
    assert lane.source_kind == manifest["source_kind"]
    assert lane.claim_status == manifest["claim_status"]


def test_env_override_selects_a_completed_run() -> None:
    lane_dir = analysis_lane.SNAPSHOTS / LANE_ID
    if not lane_dir.is_dir():
        return
    previous = os.environ.get(analysis_lane.ENV_VAR)
    os.environ[analysis_lane.ENV_VAR] = LANE_ID
    try:
        lane = analysis_lane.resolve()
    finally:
        if previous is None:
            os.environ.pop(analysis_lane.ENV_VAR, None)
        else:
            os.environ[analysis_lane.ENV_VAR] = previous
    assert lane.lane_id == LANE_ID
    assert lane.source_kind == "completed_run"
    assert not lane.is_frozen


def test_frozen_alias_and_labels() -> None:
    lane = analysis_lane.resolve("frozen")
    assert lane.is_frozen
    assert lane.lane_id == analysis_lane.FROZEN_ID
    assert lane.controlled_scope == analysis_lane.FROZEN_CONTROLLED_SCOPE
    # The frozen lane keeps its historical grouping axis.
    assert lane.grouping_axis == "legacy_footprint_bracket"


def test_completed_run_groups_on_parameter_tier() -> None:
    """legacy_footprint_bracket mixes units on completed runs, so it is not the axis."""
    lane_dir = analysis_lane.SNAPSHOTS / LANE_ID
    if not lane_dir.is_dir():
        return
    lane = analysis_lane.resolve(LANE_ID)
    assert lane.grouping_axis == "parameter_tier"
    assert any("mixes units" in note for note in lane.notes)


def test_every_lane_exposes_readable_canonical_files() -> None:
    for lane_id in analysis_lane.available_lanes():
        lane = analysis_lane.resolve(lane_id)
        for attribute in ("results", "judged", "judge_pairs"):
            path = getattr(lane, attribute)
            assert path.exists(), f"{lane_id}: missing {attribute} at {path}"
            with path.open(newline="") as handle:
                header = next(csv.reader(handle), [])
            assert header, f"{lane_id}: empty {attribute}"
            assert "analysis_schema_version" in header, f"{lane_id}: {attribute} not v1"


def test_lanes_share_canonical_headers() -> None:
    """Both lanes must be drop-in for the same consumer."""
    lanes = [analysis_lane.resolve(lane_id) for lane_id in analysis_lane.available_lanes()]
    if len(lanes) < 2:
        return

    def header(path: pathlib.Path) -> list[str]:
        with path.open(newline="") as handle:
            return next(csv.reader(handle), [])

    for attribute in ("results", "judged", "judge_pairs"):
        headers = {tuple(header(getattr(lane, attribute))) for lane in lanes}
        assert len(headers) == 1, f"{attribute} headers differ across lanes: {headers}"


def test_unknown_lane_fails_loudly() -> None:
    try:
        analysis_lane.resolve("no-such-lane")
    except FileNotFoundError:
        return
    raise AssertionError("unknown lane must raise")


def test_directory_without_lane_json_is_rejected() -> None:
    with tempfile.TemporaryDirectory(dir=analysis_lane.SNAPSHOTS) as tmp:
        try:
            analysis_lane.resolve(pathlib.Path(tmp).name)
        except FileNotFoundError:
            return
    raise AssertionError("a directory without lane.json must not resolve")


def main() -> None:
    tests = [value for name, value in globals().items()
             if name.startswith("test_") and callable(value)]
    for test in sorted(tests, key=lambda fn: fn.__name__):
        test()
    print(f"analysis lane tests passed: {len(tests)}")


if __name__ == "__main__":
    main()
