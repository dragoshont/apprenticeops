#!/usr/bin/env python3
"""Regression tests for audit-run.py."""
from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "audit-run.py"
spec = importlib.util.spec_from_file_location("audit_run", SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_expected_repeats_prefers_run_meta_for_collected_results() -> None:
    with tempfile.TemporaryDirectory() as td:
        run_dir = pathlib.Path(td) / "data" / "runs" / "run-a"
        mirror = run_dir / "_mirror"
        mirror.mkdir(parents=True)
        (run_dir / "run.meta").write_text(json.dumps({"reps": 1}) + "\n")
        results = mirror / "results.run-a.jsonl"
        results.write_text("\n")

        args = type("Args", (), {"results": str(results), "expected_repeats": None})()
        repeats, source = mod.expected_repeats(args, {"protocol": {"repeats": 5}})

    assert repeats == 1
    assert source == "run.meta"


def test_expected_repeats_falls_back_to_manifest() -> None:
    args = type("Args", (), {"results": "results.example.jsonl", "expected_repeats": None})()
    repeats, source = mod.expected_repeats(args, {"protocol": {"repeats": 5}})

    assert repeats == 5
    assert source == "manifest"


def test_expected_repeats_cli_override_wins() -> None:
    args = type("Args", (), {"results": "results.example.jsonl", "expected_repeats": 2})()
    repeats, source = mod.expected_repeats(args, {"protocol": {"repeats": 5}})

    assert repeats == 2
    assert source == "--expected-repeats"


def main() -> None:
    test_expected_repeats_prefers_run_meta_for_collected_results()
    test_expected_repeats_falls_back_to_manifest()
    test_expected_repeats_cli_override_wins()
    print("audit-run tests passed")


if __name__ == "__main__":
    main()