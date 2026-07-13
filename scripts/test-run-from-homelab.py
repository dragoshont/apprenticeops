#!/usr/bin/env python3
"""Command-level safety tests for control-to-inference source synchronization."""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "run-from-homelab.sh"


def fixture(root: pathlib.Path) -> tuple[pathlib.Path, dict[str, str], pathlib.Path, pathlib.Path]:
    repo = root / "repo"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(SCRIPT, scripts / SCRIPT.name)
    shutil.copy2(REPO / "recovery_profile.py", repo / "recovery_profile.py")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(
        ["git", "add", "scripts/run-from-homelab.sh", "recovery_profile.py"],
        cwd=repo,
        check=True,
    )
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repo, check=True)

    commands = root / "commands"
    commands.mkdir()
    ssh_log = root / "ssh.log"
    rsync_log = root / "rsync.log"
    ssh = commands / "ssh"
    ssh.write_text(f'''#!/bin/sh
echo "$@" >> {str(ssh_log)!r}
case "$*" in
  *"/proc/[0-9]*/cwd"*) [ "${{TEST_SSH_ACTIVE:-0}}" = 1 ] && exit 1 ;;
    *"remote checkout lacks local-commit marker"*) [ "${{TEST_MARKER_REFUSE:-0}}" = 1 ] && exit 1 ;;
    *"git rev-parse HEAD"*) echo "${{TEST_LOCAL_COMMIT:-}}" ;;
esac
exit 0
''')
    rsync = commands / "rsync"
    rsync.write_text(f'''#!/bin/sh
echo "$@" >> {str(rsync_log)!r}
[ "${{TEST_RSYNC_SUCCESS:-0}}" = 1 ] && exit 0
exit 97
''')
    ssh.chmod(0o755)
    rsync.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{commands}:{os.environ['PATH']}",
        "HOME_AI": "fixture-ai",
        "REMOTE_DIR": "/tmp/apprenticeops-fixture-source",
        "RUN_ID": "sync-fixture",
    }
    return repo, env, ssh_log, rsync_log


def run(repo: pathlib.Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "scripts/run-from-homelab.sh"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
    )


def test_unknown_sync_mode_refuses_before_remote_sync() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, env, _ssh_log, rsync_log = fixture(pathlib.Path(directory))
        env["SYNC_MODE"] = "typo"
        result = run(repo, env)
        assert result.returncode != 0
        assert "SYNC_MODE must be origin, local-commit, or working-tree" in result.stdout
        assert not rsync_log.exists()


def test_recovery_identifier_only_refuses_before_ssh() -> None:
    for key, value in (
        ("MODEL_SET", "timeout-sensitivity-v1"),
        ("SCENARIO_SET", "core-current-timeout-sensitivity-v1"),
    ):
        with tempfile.TemporaryDirectory() as directory:
            repo, env, ssh_log, rsync_log = fixture(pathlib.Path(directory))
            env[key] = value
            result = run(repo, env)
            assert result.returncode != 0
            assert "complete frozen recovery profile" in result.stderr
            assert not ssh_log.exists()
            assert not rsync_log.exists()


def test_active_remote_checkout_refuses_before_sync() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, env, _ssh_log, rsync_log = fixture(pathlib.Path(directory))
        env.update({"SYNC_MODE": "working-tree", "TEST_SSH_ACTIVE": "1"})
        result = run(repo, env)
        assert result.returncode != 0
        assert "refusing to synchronize an active remote checkout" in result.stdout
        assert not rsync_log.exists()


def test_unmarked_local_commit_checkout_refuses_without_deletion() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, env, ssh_log, rsync_log = fixture(pathlib.Path(directory))
        env.update({"SYNC_MODE": "local-commit", "TEST_MARKER_REFUSE": "1"})
        result = run(repo, env)
        assert result.returncode != 0
        assert "not an isolated marker-bound local-commit checkout" in result.stdout
        assert not rsync_log.exists()
        assert "rm -rf" not in ssh_log.read_text()


def test_marker_bound_local_commit_preserves_runtime_evidence() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, env, ssh_log, rsync_log = fixture(pathlib.Path(directory))
        local_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True, capture_output=True, check=True
        ).stdout.strip()
        env.update({
            "SYNC_MODE": "local-commit",
            "TEST_LOCAL_COMMIT": local_commit,
            "TEST_RSYNC_SUCCESS": "1",
        })
        result = run(repo, env)
        assert result.returncode == 0, result.stdout + result.stderr
        rsync_args = rsync_log.read_text()
        for excluded in (
            ".apprenticeops-local-commit-checkout",
            "data/runs/",
            "logs/",
            "outputs/",
            "results.*.jsonl*",
        ):
            assert excluded in rsync_args
        assert "rm -rf" not in ssh_log.read_text()


if __name__ == "__main__":
    test_unknown_sync_mode_refuses_before_remote_sync()
    test_recovery_identifier_only_refuses_before_ssh()
    test_active_remote_checkout_refuses_before_sync()
    test_unmarked_local_commit_checkout_refuses_without_deletion()
    test_marker_bound_local_commit_preserves_runtime_evidence()
    print("run-from-homelab safety tests passed")
