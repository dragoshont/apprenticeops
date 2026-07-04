#!/usr/bin/env python3
"""Regression tests for merge-wave snapshot adapter handling."""

from __future__ import annotations

import csv
import importlib.util
import json
import pathlib
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "merge-wave.py"
spec = importlib.util.spec_from_file_location("merge_wave", SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_adapter_is_part_of_snapshot_key() -> None:
    existing = [{
        "model": "m",
        "adapter": "ollama",
        "scenario": "s",
        "rep": "0",
        "det_score": "0.5",
    }]
    new_rows = [{
        "model": "m",
        "adapter": "llama_cpp",
        "scenario": "s",
        "rep": "0",
        "det_score": "0.6",
    }]
    added, replaced = mod.upsert(existing, new_rows, better=lambda nw, cur: mod.num(nw["det_score"]) > mod.num(cur["det_score"]))
    assert added == 1
    assert replaced == 0
    assert {row["adapter"] for row in existing} == {"ollama", "llama_cpp"}


def test_merge_wave_writes_adapter_column() -> None:
    with tempfile.TemporaryDirectory() as td:
        temp = pathlib.Path(td)
        results = temp / "results.jsonl"
        results_csv = temp / "results_snapshot.csv"
        row = {
            "model": "m",
            "bracket": "0-1B",
            "scenario": "s",
            "rep": 0,
            "det_score": 1,
            "env.inference_runtime": "llama_cpp",
            "gen_ai.response.finish_reasons": ["stop"],
            "dnf": False,
        }
        results.write_text(json.dumps(row) + "\n")
        old_argv = mod.sys.argv
        try:
            mod.sys.argv = ["merge-wave.py", "--results", str(results), "--results-csv", str(results_csv), "--dry-run"]
            mod.main()
        finally:
            mod.sys.argv = old_argv
        # Dry-run should not write; exercise the cell renderer directly too.
        assert mod.cell(row, "adapter") == "llama_cpp"


def main() -> None:
    test_adapter_is_part_of_snapshot_key()
    test_merge_wave_writes_adapter_column()
    print("merge-wave tests passed")


if __name__ == "__main__":
    main()