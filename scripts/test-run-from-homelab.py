#!/usr/bin/env python3
"""Command-level safety tests for control-to-inference source synchronization."""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile

import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import recovery_profile

SCRIPT = REPO / "scripts" / "run-from-homelab.sh"
MARKER_VALIDATOR = REPO / "scripts" / "validate-local-commit-checkout.py"


def fixture(root: pathlib.Path) -> tuple[pathlib.Path, dict[str, str], pathlib.Path, pathlib.Path]:
    repo = root / "repo"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(SCRIPT, scripts / SCRIPT.name)
    shutil.copy2(MARKER_VALIDATOR, scripts / MARKER_VALIDATOR.name)
    shutil.copy2(REPO / "recovery_profile.py", repo / "recovery_profile.py")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(
        [
            "git", "add", "scripts/run-from-homelab.sh",
            "scripts/validate-local-commit-checkout.py", "recovery_profile.py",
        ],
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
    *"git rev-parse HEAD"*) echo "${{TEST_LOCAL_COMMIT:-}}" ;;
    *".apprenticeops-local-commit-checkout"*)
        if [ "${{TEST_EXEC_MARKER:-0}}" = 1 ]; then
            command=""
            for argument in "$@"; do command="$argument"; done
            exec /bin/sh -c "$command"
        fi
        [ "${{TEST_MARKER_REFUSE:-0}}" = 1 ] && exit 1
        ;;
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
        "REMOTE_DIR": str(root / "remote-source"),
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


def install_recovery_contracts(repo: pathlib.Path) -> dict[str, str]:
    paths = (
        recovery_profile.RECOVERY_ROSTER,
        recovery_profile.RECOVERY_SCENARIOS,
        recovery_profile.RECOVERY_MANIFEST,
        recovery_profile.RECOVERY_ARTIFACT_LOCK,
        recovery_profile.RECOVERY_ANALYSIS_MANIFEST,
    )
    for relative in paths:
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / relative, destination)
    subprocess.run(["git", "add", *paths], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "recovery contracts"], cwd=repo, check=True)
    profile = {
        "MODELS": recovery_profile.RECOVERY_ROSTER,
        "MODEL_SET": recovery_profile.RECOVERY_PROFILE_ID,
        "SCENARIOS": recovery_profile.RECOVERY_SCENARIOS,
        "SCENARIO_SET": recovery_profile.RECOVERY_SCENARIO_SET,
        "RUN_MANIFEST": recovery_profile.RECOVERY_MANIFEST,
        "MODEL_ARTIFACT_LOCK": recovery_profile.RECOVERY_ARTIFACT_LOCK,
        "TIMEOUT_POLICY_ID": recovery_profile.RECOVERY_POLICY_ID,
        "MEMORY_CONTEXT": "none",
        "MEMORY_CONTEXT_FILE": "",
        "INFERENCE_STRATEGY": "baseline",
        "INFERENCE_RUNTIME": "ollama",
        "MAX_TOKENS_CAP": "",
        "RUN_REPEATS": "5",
        "RUN_TEMP": "0.7",
        "RUN_ALLOW_UNLOCKED": "",
        "JUDGE_MODEL": "claude-opus-4.6",
        "ENSEMBLE": "copilot:gpt-5.4",
        "PERSIST_MODE": "git-push",
    }
    return profile


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


def test_foreign_cwd_cannot_shadow_recovery_guard() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        repo, env, ssh_log, rsync_log = fixture(root)
        foreign = root / "foreign-cwd"
        foreign.mkdir()
        (foreign / "recovery_profile.py").write_text("raise SystemExit(0)\n")
        env["MODEL_SET"] = recovery_profile.RECOVERY_PROFILE_ID
        result = subprocess.run(
            ["bash", str(repo / "scripts" / "run-from-homelab.sh")],
            cwd=foreign,
            env=env,
            text=True,
            capture_output=True,
        )
        assert result.returncode != 0
        assert "complete frozen recovery profile" in result.stderr
        assert not ssh_log.exists()
        assert not rsync_log.exists()


def test_symlinked_entrypoint_cannot_relocate_recovery_guard() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        repo, env, ssh_log, rsync_log = fixture(root)
        foreign = root / "foreign-entrypoint"
        foreign.mkdir()
        (foreign / "recovery_profile.py").write_text("raise SystemExit(0)\n")
        entrypoint = foreign / "run-from-homelab.sh"
        entrypoint.symlink_to(repo / "scripts" / "run-from-homelab.sh")
        env["MODEL_SET"] = recovery_profile.RECOVERY_PROFILE_ID
        result = subprocess.run(
            ["bash", str(entrypoint)],
            cwd=foreign,
            env=env,
            text=True,
            capture_output=True,
        )
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


def test_recovery_direct_sync_requires_local_commit_before_ssh() -> None:
    for mode in ("origin", "working-tree"):
        with tempfile.TemporaryDirectory() as directory:
            repo, env, ssh_log, rsync_log = fixture(pathlib.Path(directory))
            env.update(install_recovery_contracts(repo))
            env["SYNC_MODE"] = mode
            result = run(repo, env)
            assert result.returncode != 0
            assert "complete frozen recovery profile" in result.stderr
            assert not ssh_log.exists()
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


def test_invalid_or_symlink_marker_refuses_before_rsync() -> None:
    for failure_mode in ("wrong-content", "symlink"):
        with tempfile.TemporaryDirectory() as directory:
            repo, env, ssh_log, rsync_log = fixture(pathlib.Path(directory))
            target = pathlib.Path(env["REMOTE_DIR"])
            target.mkdir()
            marker = target / ".apprenticeops-local-commit-checkout"
            if failure_mode == "wrong-content":
                marker.write_text("wrong\n")
            else:
                outside = pathlib.Path(directory) / "outside-marker"
                outside.write_text("apprenticeops-local-commit-v1\n")
                marker.symlink_to(outside)
            env.update({
                "SYNC_MODE": "local-commit",
                "TEST_EXEC_MARKER": "1",
            })
            result = run(repo, env)
            assert result.returncode != 0
            assert "not an isolated marker-bound local-commit checkout" in result.stdout
            assert ".apprenticeops-local-commit-checkout" in ssh_log.read_text()
            assert not rsync_log.exists()


def test_marker_bound_local_commit_preserves_runtime_evidence() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, env, ssh_log, rsync_log = fixture(pathlib.Path(directory))
        local_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True, capture_output=True, check=True
        ).stdout.strip()
        env.update({
            "SYNC_MODE": "local-commit",
            "TEST_LOCAL_COMMIT": local_commit,
            "TEST_EXEC_MARKER": "1",
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
        marker = pathlib.Path(env["REMOTE_DIR"]) / ".apprenticeops-local-commit-checkout"
        assert marker.read_text() == "apprenticeops-local-commit-v1\n"


if __name__ == "__main__":
    test_unknown_sync_mode_refuses_before_remote_sync()
    test_recovery_identifier_only_refuses_before_ssh()
    test_foreign_cwd_cannot_shadow_recovery_guard()
    test_symlinked_entrypoint_cannot_relocate_recovery_guard()
    test_active_remote_checkout_refuses_before_sync()
    test_recovery_direct_sync_requires_local_commit_before_ssh()
    test_unmarked_local_commit_checkout_refuses_without_deletion()
    test_invalid_or_symlink_marker_refuses_before_rsync()
    test_marker_bound_local_commit_preserves_runtime_evidence()
    print("run-from-homelab safety tests passed")
