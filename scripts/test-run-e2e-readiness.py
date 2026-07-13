#!/usr/bin/env python3
"""Command-level tests for consumer-first end-to-end launch readiness."""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "run-e2e.sh"
ROSTER = REPO / "scripts" / "run-roster.sh"


def executable(path: pathlib.Path, body: str) -> pathlib.Path:
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(0o755)
    return path


def fixture(root: pathlib.Path) -> tuple[pathlib.Path, dict[str, str]]:
    repo = root / "repo"
    (repo / "scripts").mkdir(parents=True)
    shutil.copy2(SCRIPT, repo / "scripts" / SCRIPT.name)
    shutil.copy2(REPO / "recovery_profile.py", repo / "recovery_profile.py")
    data = repo / "data"
    data.mkdir()
    (data / "models.txt").write_text("model-a\n")
    (data / "scenarios.json").write_text(json.dumps({
        "scenarios": [{"id": "s1", "class": "test", "difficulty": "easy", "grounding": "closed-book"}],
    }) + "\n")
    (data / "manifest.json").write_text("{}\n")
    env = {
        **os.environ,
        "RUN_ID": "readiness-fixture",
        "MODELS": "data/models.txt",
        "SCENARIOS": "data/scenarios.json",
        "RUN_MANIFEST": "data/manifest.json",
        "PERSIST_MODE": "local-files",
        "JUDGE_MODEL": "claude-test",
        "ENSEMBLE": "copilot:gpt-test",
    }
    return repo, env


def test_consumer_failure_never_launches_producer() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        repo, env = fixture(root)
        producer_marker = root / "producer.called"
        scheduler = executable(root / "scheduler", "exit 7\n")
        producer = executable(root / "producer", f"touch {str(producer_marker)!r}\n")
        setsid = executable(root / "setsid", 'exec "$@"\n')
        env.update({
            "JUDGE_SCHEDULER": str(scheduler),
            "PRODUCER_SCRIPT": str(producer),
            "SETSID_BIN": str(setsid),
        })
        result = subprocess.run(
            ["bash", "scripts/run-e2e.sh"],
            cwd=repo,
            env=env,
            text=True,
            capture_output=True,
        )
        assert result.returncode != 0
        assert "producer was not launched" in (result.stdout + result.stderr)
        assert not producer_marker.exists()


def test_consumer_exit_after_readiness_never_launches_producer() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        repo, env = fixture(root)
        producer_marker = root / "producer.called"
        scheduler = executable(root / "scheduler", '''
ready="data/runs/${RUN_ID}/consumer.ready"
printf '{"persist_mode":"%s","pid":%s,"run_id":"%s"}\n' "$PERSIST_MODE" "$$" "$RUN_ID" > "$ready"
exit 0
''')
        producer = executable(root / "producer", f"touch {str(producer_marker)!r}\n")
        setsid = executable(root / "setsid", 'exec "$@"\n')
        env.update({
            "JUDGE_SCHEDULER": str(scheduler),
            "PRODUCER_SCRIPT": str(producer),
            "SETSID_BIN": str(setsid),
        })
        result = subprocess.run(
            ["bash", "scripts/run-e2e.sh"],
            cwd=repo,
            env=env,
            text=True,
            capture_output=True,
        )
        assert result.returncode != 0
        assert "producer was not launched" in (result.stdout + result.stderr)
        assert not producer_marker.exists()


def test_unknown_status_is_read_only() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        repo, env = fixture(root)
        env["RUN_ID"] = "unknown-run"
        result = subprocess.run(
            ["bash", "scripts/run-e2e.sh", "status"],
            cwd=repo,
            env=env,
            text=True,
            capture_output=True,
        )
        assert result.returncode != 0
        assert "run.meta is missing" in result.stderr
        assert not (repo / "data" / "runs" / "unknown-run").exists()


def test_metadata_loss_before_first_receipt_never_launches_producer() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        repo, env = fixture(root)
        run = repo / "data" / "runs" / env["RUN_ID"]
        run.mkdir(parents=True)
        (run / ".run-authority").write_text(json.dumps({
            "persist_mode": "local-files",
            "run_id": env["RUN_ID"],
            "schema_version": 1,
        }) + "\n")
        producer_marker = root / "producer.called"
        producer = executable(root / "producer", f"touch {str(producer_marker)!r}\n")
        env["PRODUCER_SCRIPT"] = str(producer)
        result = subprocess.run(
            ["bash", "scripts/run-e2e.sh"],
            cwd=repo,
            env=env,
            text=True,
            capture_output=True,
        )
        assert result.returncode != 0
        assert "missing authoritative run.meta" in result.stderr
        assert not producer_marker.exists()


def test_partial_timeout_recovery_profile_refuses_before_run_state() -> None:
    triggers = (
        {"MODEL_SET": "timeout-sensitivity-v1"},
        {"SCENARIO_SET": "core-current-timeout-sensitivity-v1"},
        {
            "SCENARIOS": "data/scenario_sets/core-current-timeout-sensitivity-v1.json",
            "TIMEOUT_POLICY_ID": "ceops-timeout-sensitivity-v1",
        },
    )
    for trigger in triggers:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            repo, env = fixture(root)
            env.update(trigger)
            result = subprocess.run(
                ["bash", "scripts/run-e2e.sh"],
                cwd=repo,
                env=env,
                text=True,
                capture_output=True,
            )
            assert result.returncode != 0
            assert "complete frozen recovery profile" in result.stderr
            assert not (repo / "data" / "runs" / env["RUN_ID"]).exists()


def test_recovery_guards_ignore_hostile_python_environment() -> None:
    for script, scope in ((SCRIPT, "orchestration"), (ROSTER, "producer")):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            repo = root / "repo"
            (repo / "scripts").mkdir(parents=True)
            shutil.copy2(script, repo / "scripts" / script.name)
            shutil.copy2(REPO / "recovery_profile.py", repo / "recovery_profile.py")
            hostile = root / "hostile"
            hostile.mkdir()
            command_marker = root / "python-shim-called"
            python = hostile / "python3"
            python.write_text(f"#!/bin/sh\ntouch {str(command_marker)!r}\nexit 0\n")
            python.chmod(0o755)
            site_marker = root / "sitecustomize-called"
            (hostile / "sitecustomize.py").write_text(
                f"from pathlib import Path\nPath({str(site_marker)!r}).touch()\n"
            )
            env = {
                **os.environ,
                "PATH": f"{hostile}:{os.environ['PATH']}",
                "PYTHONPATH": str(hostile),
                "MODEL_SET": "timeout-sensitivity-v1",
                "RUN_ID": f"hostile-{scope}",
            }
            result = subprocess.run(
                ["bash", f"scripts/{script.name}"],
                cwd=repo,
                env=env,
                text=True,
                capture_output=True,
            )
            assert result.returncode != 0
            assert "complete frozen recovery profile" in result.stderr
            assert not command_marker.exists()
            assert not site_marker.exists()
            assert not (repo / "data" / "runs" / env["RUN_ID"]).exists()


if __name__ == "__main__":
    test_consumer_failure_never_launches_producer()
    test_consumer_exit_after_readiness_never_launches_producer()
    test_unknown_status_is_read_only()
    test_metadata_loss_before_first_receipt_never_launches_producer()
    test_partial_timeout_recovery_profile_refuses_before_run_state()
    test_recovery_guards_ignore_hostile_python_environment()
    print("run-e2e readiness tests passed")