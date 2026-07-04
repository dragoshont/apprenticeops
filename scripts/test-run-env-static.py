#!/usr/bin/env python3
"""Regression tests for run.py environment provenance helpers."""

from __future__ import annotations

import importlib.util
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "run.py"
spec = importlib.util.spec_from_file_location("run_module", SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_artifact_only_dirty_is_not_source_dirty() -> None:
    source_dirty, artifact_dirty = mod._classify_git_status(
        "?? calibration.json\n"
        "?? results.example.jsonl\n"
        "?? logs/run/driver.log\n"
        "?? outputs/model__scenario.txt\n"
    )
    assert source_dirty is False
    assert artifact_dirty is True


def test_source_dirty_is_distinct_from_artifacts() -> None:
    source_dirty, artifact_dirty = mod._classify_git_status(
        " M run.py\n"
        "?? data/runs/example/run.meta\n"
    )
    assert source_dirty is True
    assert artifact_dirty is True


def main() -> None:
    test_artifact_only_dirty_is_not_source_dirty()
    test_source_dirty_is_distinct_from_artifacts()
    print("run env provenance tests passed")


if __name__ == "__main__":
    main()