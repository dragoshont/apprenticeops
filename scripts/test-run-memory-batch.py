#!/usr/bin/env python3
"""Focused tests for scripts/run-memory-batch.py without launching models."""
from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "run-memory-batch.py"
STATUS_PATH = ROOT / "scripts" / "pipeline-status.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_memory_batch", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_status_module():
    spec = importlib.util.spec_from_file_location("pipeline_status", STATUS_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resolve_and_state():
    module = load_module()
    model_set, scenario_set, memories = module.resolve_selection(
        "dryrun", "core-current", ["none", "homelab-okf-v1"]
    )
    assert model_set["_path"] == "data/models.dryrun.txt"
    assert scenario_set["_path"] == "data/scenario_sets/core-current.json"
    assert [memory["id"] for memory in memories] == ["none", "homelab-okf-v1"]
    args = argparse.Namespace(
        batch_id="batch-dryrun-core-test",
        model_set="dryrun",
        scenario_set="core-current",
        runner="local-roster",
        stall_timeout_s=7200,
        user="test",
    )
    state = module.build_state(args, model_set, scenario_set, memories)
    assert state["runner"] == "local-roster"
    assert state["status"] == "running"
    assert [run["memory_context"] for run in state["runs"]] == ["none", "homelab-okf-v1"]
    assert all(len(run["run_id"]) <= 80 for run in state["runs"])


def test_run_meta_creation_is_portable():
    module = load_module()
    model_set, scenario_set, memories = module.resolve_selection(
        "dryrun", "core-current", ["none", "homelab-okf-v1"]
    )
    args = argparse.Namespace(
        batch_id="batch-dryrun-core-test",
        model_set="dryrun",
        scenario_set="core-current",
        runner="local-roster",
        stall_timeout_s=7200,
        user="test",
    )
    state = module.build_state(args, model_set, scenario_set, memories)
    with tempfile.TemporaryDirectory() as tmp:
        old_runs = module.RUNS
        module.RUNS = Path(tmp) / "runs"
        try:
            module.ensure_run_meta(state, state["runs"][1])
            meta_path = module.RUNS / state["runs"][1]["run_id"] / "run.meta"
            meta = json.loads(meta_path.read_text())
            assert meta["schema_version"] == 2
            assert meta["model_set"] == "dryrun"
            assert meta["scenario_set"] == "core-current"
            assert meta["memory_context"] == "homelab-okf-v1"
            assert meta["memory_context_file"] == "data/memory/homelab-okf-v1/context.md"
            assert meta["models_count"] == 2
            assert meta["scenario_count"] == 20
            assert meta["expect"] == 2
        finally:
            module.RUNS = old_runs


def test_existing_run_meta_must_match_selection():
    module = load_module()
    model_set, scenario_set, memories = module.resolve_selection(
        "dryrun", "core-current", ["none", "homelab-okf-v1"]
    )
    args = argparse.Namespace(
        batch_id="batch-dryrun-core-test",
        model_set="dryrun",
        scenario_set="core-current",
        runner="local-roster",
        stall_timeout_s=7200,
        user="test",
    )
    state = module.build_state(args, model_set, scenario_set, memories)
    with tempfile.TemporaryDirectory() as tmp:
        old_runs = module.RUNS
        module.RUNS = Path(tmp) / "runs"
        try:
            run = state["runs"][1]
            run_dir = module.RUNS / run["run_id"]
            run_dir.mkdir(parents=True)
            (run_dir / "run.meta").write_text(json.dumps({
                "models": "data/models.dryrun.txt",
                "models_sha256": "wrong",
                "scenarios": "data/scenario_sets/core-current.json",
                "scenarios_sha256": "wrong",
                "memory_context": "none",
                "memory_context_sha256": None,
            }))
            try:
                module.ensure_run_meta(state, run)
            except RuntimeError as exc:
                assert "does not match" in str(exc)
            else:
                raise AssertionError("stale run.meta was accepted")
        finally:
            module.RUNS = old_runs


def test_pipeline_status_marks_local_roster_done_from_done_markers():
    status_module = load_status_module()
    with tempfile.TemporaryDirectory() as tmp:
        runs_dir = Path(tmp) / "runs"
        run_dir = runs_dir / "local-roster-test"
        mirror = run_dir / "_mirror"
        mirror.mkdir(parents=True)
        (run_dir / "run.meta").write_text(json.dumps({
            "schema_version": 2,
            "run_id": "local-roster-test",
            "runner": "local-roster",
            "judge_expected": False,
            "model_set": "dryrun",
            "models": "data/models.dryrun.txt",
            "scenario_set": "core-current",
            "scenarios": "data/scenario_sets/core-current.json",
            "memory_context": "none",
            "scenario_count": 20,
            "expect": 2,
            "started_at": 1,
        }))
        (mirror / "results.local-roster-test.jsonl.done").write_text(
            '{"model":"a","units":100}\n{"model":"b","units":100}\n'
        )
        old_runs = status_module.RUNS
        old_experiments = status_module.EXPERIMENTS
        try:
            status_module.RUNS = str(runs_dir)
            status_module.EXPERIMENTS = str(Path(tmp) / "experiments")
            rows = status_module.sessions()
            assert rows[0]["state"] == "done"
            assert rows[0]["models_done"] == 2
            assert rows[0]["judge_total"] == 0
        finally:
            status_module.RUNS = old_runs
            status_module.EXPERIMENTS = old_experiments


def test_local_roster_done_requires_result_rows():
    module = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "data" / "scenario_sets").mkdir(parents=True)
        (tmp_path / "data" / "models.dryrun.txt").write_text("a\nb\n")
        (tmp_path / "data" / "scenario_sets" / "core-current.json").write_text(json.dumps({
            "scenarios": [{"id": "s1", "class": "detect", "context": "c", "question": "q"}]
        }))
        old_repo = module.REPO
        old_runs = module.RUNS
        module.REPO = tmp_path
        module.RUNS = tmp_path / "data" / "runs"
        try:
            run_id = "local-roster-test"
            run_dir = module.RUNS / run_id
            run_dir.mkdir(parents=True)
            models_path = tmp_path / "data" / "models.dryrun.txt"
            scenarios_path = tmp_path / "data" / "scenario_sets" / "core-current.json"
            (run_dir / "run.meta").write_text(json.dumps({
                "models": "data/models.dryrun.txt",
                "models_sha256": module.sha256(models_path),
                "scenarios": "data/scenario_sets/core-current.json",
                "scenarios_sha256": module.sha256(scenarios_path),
                "memory_context": "none",
                "memory_context_sha256": None,
                "reps": 1,
                "expect": 2,
            }))
            (tmp_path / f"results.{run_id}.jsonl.done").write_text(
                '{"model":"a","units":1}\n{"model":"b","units":1}\n'
            )
            assert module.local_roster_done({"paths": {"models": "data/models.dryrun.txt", "scenarios": "data/scenario_sets/core-current.json"}}, run_id) is False
        finally:
            module.REPO = old_repo
            module.RUNS = old_runs


def test_launch_run_local_roster_observes_running_then_done():
    module = load_module()

    class FakeProc:
        def __init__(self):
            self.polls = 0

        def poll(self):
            self.polls += 1
            return None if self.polls == 1 else 0

        def wait(self, timeout=None):
            return 0

        def terminate(self):
            raise AssertionError("terminate should not be called")

    statuses = [
        {"state": "running", "progress": {"units_done": 1, "pct": 10}},
        {"state": "stopped", "progress": {"units_done": 2, "pct": 50}},
    ]
    old_popen = module.subprocess.Popen
    old_ensure = module.ensure_run_meta
    old_mirror = module.mirror_local_run
    old_done = module.local_roster_done
    old_status = module.load_status
    old_sleep = module.time.sleep
    try:
        module.subprocess.Popen = lambda *args, **kwargs: FakeProc()
        module.ensure_run_meta = lambda state, run: None
        module.mirror_local_run = lambda run_id: None
        module.local_roster_done = lambda state, run_id: True
        module.load_status = lambda run_id: statuses.pop(0) if statuses else {"state": "stopped", "progress": {"units_done": 2, "pct": 50}}
        module.time.sleep = lambda seconds: None
        state = {
            "runner": "local-roster",
            "user": "test",
            "stall_timeout_s": 7200,
            "paths": {"models": "data/models.dryrun.txt", "scenarios": "data/scenario_sets/core-current.json"},
            "runs": [{
                "run_id": "local-roster-test",
                "model_set": "dryrun",
                "scenario_set": "core-current",
                "memory_context": "none",
                "memory_context_file": None,
                "status": "pending",
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            module.launch_run(state, 0, Path(tmp), 0)
        assert state["runs"][0]["status"] == "done"
        assert state["runs"][0]["progress_pct"] == 100.0
    finally:
        module.subprocess.Popen = old_popen
        module.ensure_run_meta = old_ensure
        module.mirror_local_run = old_mirror
        module.local_roster_done = old_done
        module.load_status = old_status
        module.time.sleep = old_sleep


def test_launch_run_local_roster_rejects_marker_only_done():
    module = load_module()

    class FakeProc:
        def poll(self):
            return 0

        def wait(self, timeout=None):
            return 0

        def terminate(self):
            raise AssertionError("terminate should not be called")

    old_popen = module.subprocess.Popen
    old_ensure = module.ensure_run_meta
    old_mirror = module.mirror_local_run
    old_done = module.local_roster_done
    old_status = module.load_status
    old_sleep = module.time.sleep
    try:
        module.subprocess.Popen = lambda *args, **kwargs: FakeProc()
        module.ensure_run_meta = lambda state, run: None
        module.mirror_local_run = lambda run_id: None
        module.local_roster_done = lambda state, run_id: False
        module.load_status = lambda run_id: {"state": "done", "progress": {"units_done": 2, "pct": 100}}
        module.time.sleep = lambda seconds: None
        state = {
            "runner": "local-roster",
            "user": "test",
            "stall_timeout_s": 0,
            "paths": {"models": "data/models.dryrun.txt", "scenarios": "data/scenario_sets/core-current.json"},
            "runs": [{
                "run_id": "local-roster-test",
                "model_set": "dryrun",
                "scenario_set": "core-current",
                "memory_context": "none",
                "memory_context_file": None,
                "status": "pending",
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            try:
                module.launch_run(state, 0, Path(tmp), 0)
            except RuntimeError as exc:
                assert "stayed stopped" in str(exc)
            else:
                raise AssertionError("marker-only done was accepted")
        assert state["status"] == "failed"
    finally:
        module.subprocess.Popen = old_popen
        module.ensure_run_meta = old_ensure
        module.mirror_local_run = old_mirror
        module.local_roster_done = old_done
        module.load_status = old_status
        module.time.sleep = old_sleep


def main():
    test_resolve_and_state()
    test_run_meta_creation_is_portable()
    test_existing_run_meta_must_match_selection()
    test_pipeline_status_marks_local_roster_done_from_done_markers()
    test_local_roster_done_requires_result_rows()
    test_launch_run_local_roster_observes_running_then_done()
    test_launch_run_local_roster_rejects_marker_only_done()
    print("test-run-memory-batch: PASS")


if __name__ == "__main__":
    main()
