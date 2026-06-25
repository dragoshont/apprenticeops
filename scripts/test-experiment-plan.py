#!/usr/bin/env python3
"""Smoke-test the file-backed experiment-plan controller without running models."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str, ok: bool = True) -> subprocess.CompletedProcess:
    cp = subprocess.run([sys.executable, "scripts/experiment-plan.py", *args], cwd=ROOT,
                        capture_output=True, text=True, check=False)
    if ok and cp.returncode != 0:
        raise SystemExit(cp.stderr or cp.stdout)
    if not ok and cp.returncode == 0:
        raise SystemExit(f"expected failure: {' '.join(args)}")
    return cp


def main() -> None:
    exp_id = "test-memory-plan"
    exp_dir = ROOT / "data" / "experiments" / exp_id
    shutil.rmtree(exp_dir, ignore_errors=True)
    try:
        init = json.loads(run("init", "--experiment-id", exp_id,
                              "--plan-id", "memory-comparison-v1",
                              "--model-set", "dryrun",
                              "--scenario-set", "core-current").stdout)
        assert init["state"]["phases"][0]["status"] == "pending"
        p1 = json.loads(run("launch-phase", "--experiment-id", exp_id,
                            "--plan-id", "memory-comparison-v1",
                            "--phase-id", "phase-1-baseline",
                            "--model-set", "dryrun",
                            "--scenario-set", "core-current",
                            "--dry-run").stdout)
        assert p1["run_id"].endswith("-p1")
        run("launch-phase", "--experiment-id", exp_id,
            "--plan-id", "memory-comparison-v1",
            "--phase-id", "phase-2-memory",
            "--model-set", "dryrun",
            "--scenario-set", "core-current",
            "--dry-run", ok=False)

        state = json.loads((exp_dir / "phase-state.json").read_text())
        phase = state["phases"][0]
        run_dir = ROOT / "data" / "runs" / phase["run_id"]
        shutil.rmtree(run_dir, ignore_errors=True)
        run_dir.mkdir(parents=True)
        meta = {
            "schema_version": 2,
            "run_id": phase["run_id"],
            "model_set": state["model_set"],
            "models": state["models"],
            "models_sha256": state["models_sha256"],
            "scenario_set": state["scenario_set"],
            "scenarios": state["scenarios"],
            "scenarios_sha256": state["scenarios_sha256"],
            "memory_context": phase["memory_context"],
            "memory_context_file": phase["memory_context_file"],
            "memory_context_sha256": phase["memory_context_sha256"],
            "scenario_count": 20,
            "reps": 5,
            "judges": 2,
            "expect": 2,
        }
        (run_dir / "run.meta").write_text(json.dumps(meta) + "\n")
        (run_dir / ".committed").write_text("m1\nm2\n")
        (run_dir / f"judged.{phase['run_id']}.jsonl").write_text("x\n" * (2 * 20 * 5 * 2))
        mirror = run_dir / "_mirror"
        mirror.mkdir()
        (mirror / f"results.{phase['run_id']}.jsonl").write_text("{}\n")
        gate = json.loads(run("gate", "--experiment-id", exp_id,
                              "--phase-id", "phase-1-baseline",
                              "--skip-audit").stdout)
        assert gate["ok"] is True, gate
        review = json.loads(run("review", "--experiment-id", exp_id,
                                "--phase-id", "phase-1-baseline",
                                "--verdict", "PASS",
                                "--reviewer", "test").stdout)
        assert review["status"] == "completed"
        p2 = json.loads(run("launch-phase", "--experiment-id", exp_id,
                            "--plan-id", "memory-comparison-v1",
                            "--phase-id", "phase-2-memory",
                            "--model-set", "dryrun",
                            "--scenario-set", "core-current",
                            "--dry-run").stdout)
        assert p2["run_id"].endswith("-p2")
        print("experiment plan smoke passed")
    finally:
        shutil.rmtree(exp_dir, ignore_errors=True)
        shutil.rmtree(ROOT / "data" / "runs" / f"{exp_id}-p1", ignore_errors=True)
        shutil.rmtree(ROOT / "data" / "runs" / f"{exp_id}-p2", ignore_errors=True)


if __name__ == "__main__":
    main()