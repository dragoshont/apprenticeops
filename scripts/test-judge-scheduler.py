#!/usr/bin/env python3
"""Command-level tests for no-push consumer restart and readiness safety."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import time

REPO = pathlib.Path(__file__).resolve().parents[1]
SCHEDULER = REPO / "scripts" / "judge-scheduler.sh"
PERSIST_SCRIPT = REPO / "scripts" / "persist-run-model.py"
SPEC = importlib.util.spec_from_file_location("persist_run_model", PERSIST_SCRIPT)
assert SPEC and SPEC.loader
local_persistence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(local_persistence)


def write_jsonl(path: pathlib.Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def complete_result(model: str, scenario: str, rep: int, scenario_sha: str) -> dict:
    return {
        "model": model, "scenario": scenario, "rep": rep,
        "adapter": "ollama", "env.inference_runtime": "ollama",
        "ollama.digest": f"sha256:{model}", "ollama.quantization": "Q4_K_M",
        "env.host": "fixture-ai", "env.kernel": "linux", "env.cpu_no_turbo": "1",
        "env.cpu_governor": "performance", "env.cpu_min_perf_pct": "100",
        "env.cpu_max_perf_pct": "100", "env.rapl_domain": "package-0",
        "env.num_ctx": 8192, "env.ollama_version": "0.30.8",
        "prompt.template_sha256": "prompt-sha", "env.memory_context": "none",
        "env.inference_strategy": "baseline", "temp": 0.7, "think": False,
        "ollama.parameters": "top_k 40\ntop_p 0.9", "env.scenario_set": "fixture-core",
        "env.scenarios_sha": scenario_sha, "strategy.candidates": [{"index": 0}],
    }


def stamp_judgement_conditions(
    result_rows: list[dict], judged_rows: list[dict], judges: frozenset[tuple[str, str]]
) -> None:
    policy, conditions, _digest = local_persistence.result_condition_contract(result_rows, judges)
    for row in judged_rows:
        row["analysis_condition_key_sha256"] = conditions[(row["scenario"], row["rep"])]
        row["condition_identity_incomplete"] = False
        row["evaluation_policy"] = policy


def populate_complete_git_model(
    run: pathlib.Path, meta: dict
) -> None:
    mirror = run / "_mirror"
    outputs = mirror / "outputs"
    result_rows = [complete_result("model-a", "s1", 0, meta["scenarios_sha256"])]
    write_jsonl(mirror / f"results.{meta['run_id']}.jsonl", result_rows)
    write_jsonl(outputs / "model-a__s1__r0.candidates.jsonl", [{
        "model": "model-a", "scenario": "s1", "rep": 0, "index": 0,
    }])
    write_jsonl(mirror / f"results.{meta['run_id']}.jsonl.done", [{
        "model": "model-a", "units": 1,
    }])
    judged_rows = [
        {
            "model": "model-a", "scenario": "s1", "rep": 0,
            "scenarios_sha256": meta["scenarios_sha256"],
            "judge_backend": "copilot", "judge_model": judge,
            "score": 4, "verdict": "ok", "evidence": "grounded",
            "criteria_met": [], "criteria_missed": [],
        }
        for judge in ("claude-test", "gpt-test")
    ]
    stamp_judgement_conditions(
        result_rows,
        judged_rows,
        frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
    )
    write_jsonl(run / f"judged.{meta['run_id']}.jsonl", judged_rows)


def fixture(
    root: pathlib.Path,
    run_id: str = "scheduler-fixture",
    persist_mode: str = "local-files",
) -> tuple[pathlib.Path, pathlib.Path, dict]:
    repo = root / "repo"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(SCHEDULER, scripts / SCHEDULER.name)
    shutil.copy2(PERSIST_SCRIPT, scripts / PERSIST_SCRIPT.name)
    shutil.copy2(REPO / "judge.py", repo / "judge.py")
    shutil.copy2(REPO / "analysis_metrics.py", repo / "analysis_metrics.py")
    scenarios = repo / "data" / "scenarios.json"
    models = repo / "data" / "models.txt"
    scenarios.parent.mkdir(parents=True)
    scenarios.write_text(json.dumps({"scenarios": [{"id": "s1"}]}) + "\n")
    models.write_text("model-a\n")
    run = repo / "data" / "runs" / run_id
    run.mkdir(parents=True)
    meta = {
        "schema_version": 2,
        "run_id": run_id,
        "models_count": 1,
        "models": "data/models.txt",
        "models_sha256": hashlib.sha256(models.read_bytes()).hexdigest(),
        "expect": 1,
        "scenarios": "data/scenarios.json",
        "scenarios_sha256": hashlib.sha256(scenarios.read_bytes()).hexdigest(),
        "scenario_count": 1,
        "scenario_ids": ["s1"],
        "reps": 1,
        "judge_model": "claude-test",
        "judge_ensemble": "copilot:gpt-test",
        "judge_identities": [
            {"judge_backend": "copilot", "judge_model": "claude-test"},
            {"judge_backend": "copilot", "judge_model": "gpt-test"},
        ],
        "judges": 2,
        "persist_mode": persist_mode,
    }
    (run / "run.meta").write_text(json.dumps(meta) + "\n")
    if persist_mode == "local-files":
        (run / ".run-authority").write_text(json.dumps({
            "persist_mode": "local-files",
            "run_id": run_id,
            "schema_version": 1,
        }, sort_keys=True, separators=(",", ":")) + "\n")
    return repo, run, meta


def commands(root: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
    git_log = root / "git.log"
    git = root / "git"
    git.write_text(f"#!/bin/sh\necho \"$@\" >> {str(git_log)!r}\nexit 97\n")
    flock = root / "flock"
    flock.write_text("#!/bin/sh\nexit \"${TEST_FLOCK_EXIT:-0}\"\n")
    rsync = root / "rsync"
    rsync.write_text("#!/bin/sh\nexit 0\n")
    copilot = root / "copilot"
    copilot.write_text("#!/bin/sh\nprintf 'COPILOT_BACKEND_OK\\n'\n")
    for path in (git, flock, rsync, copilot):
        path.chmod(0o755)
    return git, flock, rsync


def environment(run_id: str, git: pathlib.Path, flock: pathlib.Path, rsync: pathlib.Path) -> dict[str, str]:
    return {
        **os.environ,
        "RUN_ID": run_id,
        "GIT_BIN": str(git),
        "FLOCK_BIN": str(flock),
        "RSYNC_BIN": str(rsync),
        "COPILOT_BIN": str(git.parent / "copilot"),
        "POLL_S": "60",
    }


def wait_for(path: pathlib.Path, process: subprocess.Popen[str], timeout: float = 5) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if path.is_file():
            return
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise AssertionError(f"scheduler exited before readiness: {stdout}\n{stderr}")
        time.sleep(0.05)
    raise AssertionError("scheduler readiness timed out")


def test_local_restart_reaches_readiness_without_git() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        repo, run, meta = fixture(root)
        git, flock, rsync = commands(root)
        process = subprocess.Popen(
            ["bash", "scripts/judge-scheduler.sh"],
            cwd=repo,
            env=environment(meta["run_id"], git, flock, rsync),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            wait_for(run / "consumer.ready", process)
            assert process.poll() is None
            assert not (root / "git.log").exists()
        finally:
            process.terminate()
            process.wait(timeout=5)


def test_mode_conflict_refuses_before_git() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        repo, _run, meta = fixture(root)
        git, flock, rsync = commands(root)
        env = environment(meta["run_id"], git, flock, rsync)
        env["PERSIST_MODE"] = "git-push"
        result = subprocess.run(
            ["bash", "scripts/judge-scheduler.sh"],
            cwd=repo,
            env=env,
            text=True,
            capture_output=True,
        )
        assert result.returncode != 0
        assert "differs from run.meta value" in result.stderr
        assert not (root / "git.log").exists()


def test_non_dedicated_branch_refuses_before_git() -> None:
    for branch in ("main", "experiment/other-run", "refs/heads/main"):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            repo, _run, meta = fixture(root, persist_mode="git-push")
            git, flock, rsync = commands(root)
            env = environment(meta["run_id"], git, flock, rsync)
            env["BRANCH"] = branch
            result = subprocess.run(
                ["bash", "scripts/judge-scheduler.sh"],
                cwd=repo,
                env=env,
                text=True,
                capture_output=True,
            )
            assert result.returncode != 0
            assert "BRANCH must be the dedicated result branch" in result.stderr
            assert not (root / "git.log").exists()


def test_metadata_loss_with_authority_refuses_before_git() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        repo, run, meta = fixture(root)
        (run / "run.meta").unlink()
        git, flock, rsync = commands(root)
        result = subprocess.run(
            ["bash", "scripts/judge-scheduler.sh"],
            cwd=repo,
            env=environment(meta["run_id"], git, flock, rsync),
            text=True,
            capture_output=True,
        )
        assert result.returncode != 0
        assert "missing authoritative run.meta" in result.stderr
        assert not (root / "git.log").exists()


def test_malformed_metadata_refuses_before_git() -> None:
    mutations = (
        lambda meta: meta.update(judge_identities=[]),
        lambda meta: meta.pop("persist_mode"),
        lambda meta: meta.update(expect=1.5),
        lambda meta: meta.update(reps=True),
        lambda meta: meta.update(scenarios="../outside.json"),
    )
    for mutate in mutations:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            repo, run, meta = fixture(root)
            mutate(meta)
            (run / "run.meta").write_text(json.dumps(meta) + "\n")
            git, flock, rsync = commands(root)
            result = subprocess.run(
                ["bash", "scripts/judge-scheduler.sh"],
                cwd=repo,
                env=environment(meta["run_id"], git, flock, rsync),
                text=True,
                capture_output=True,
            )
            assert result.returncode != 0
            assert "cannot load authoritative consumer contract" in result.stderr
            assert not (root / "git.log").exists()


def test_scenario_identity_substitution_refuses_before_git() -> None:
    mutations = (
        ["other"],
        ["s1", "s1"],
        [],
    )
    for identifiers in mutations:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            repo, run, meta = fixture(root)
            meta["scenario_ids"] = identifiers
            (run / "run.meta").write_text(json.dumps(meta) + "\n")
            git, flock, rsync = commands(root)
            result = subprocess.run(
                ["bash", "scripts/judge-scheduler.sh"],
                cwd=repo,
                env=environment(meta["run_id"], git, flock, rsync),
                text=True,
                capture_output=True,
            )
            assert result.returncode != 0
            assert "cannot load authoritative consumer contract" in result.stderr
            assert not (root / "git.log").exists()


def test_repetition_conflict_refuses_before_git() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        repo, _run, meta = fixture(root)
        git, flock, rsync = commands(root)
        env = environment(meta["run_id"], git, flock, rsync)
        env["RUN_REPEATS"] = "2"
        result = subprocess.run(
            ["bash", "scripts/judge-scheduler.sh"],
            cwd=repo,
            env=env,
            text=True,
            capture_output=True,
        )
        assert result.returncode != 0
        assert "differs from run.meta value" in result.stderr
        assert not (root / "git.log").exists()


def test_invalid_committed_domain_refuses_readiness() -> None:
    for values in ("model-a\nmodel-a\n", "outside-model\n"):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            repo, run, meta = fixture(root)
            (run / ".committed").write_text(values)
            git, flock, rsync = commands(root)
            result = subprocess.run(
                ["bash", "scripts/judge-scheduler.sh"],
                cwd=repo,
                env=environment(meta["run_id"], git, flock, rsync),
                text=True,
                capture_output=True,
            )
            assert result.returncode != 0
            assert "committed-model marker failed roster validation" in (result.stdout + result.stderr)
            assert not (run / "consumer.ready").exists()
            assert not (root / "git.log").exists()


def test_unsafe_run_id_and_symlinked_run_path_refuse() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        repo, _run, _meta = fixture(root)
        git, flock, rsync = commands(root)
        result = subprocess.run(
            ["bash", "scripts/judge-scheduler.sh"],
            cwd=repo,
            env=environment("../unsafe", git, flock, rsync),
            text=True,
            capture_output=True,
        )
        assert result.returncode != 0
        assert "unsafe characters" in result.stderr
        outside = root / "outside-run"
        outside.mkdir()
        linked = repo / "data" / "runs" / "linked-run"
        linked.symlink_to(outside, target_is_directory=True)
        result = subprocess.run(
            ["bash", "scripts/judge-scheduler.sh"],
            cwd=repo,
            env=environment("linked-run", git, flock, rsync),
            text=True,
            capture_output=True,
        )
        assert result.returncode != 0
        assert "run path contains a symlink" in result.stderr


def test_nested_symlinked_evidence_refuses_before_lock_or_log() -> None:
    for relative in ("_mirror", "_mirror/outputs", ".consumer.lock", "judge-scheduler.log", "judge-scheduler.status"):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            repo, run, meta = fixture(root)
            target = root / "outside"
            target.mkdir()
            path = run / relative
            if path.exists():
                if path.is_dir():
                    __import__("shutil").rmtree(path)
                else:
                    path.unlink()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.symlink_to(target, target_is_directory=True)
            git, flock, rsync = commands(root)
            result = subprocess.run(
                ["bash", "scripts/judge-scheduler.sh"],
                cwd=repo,
                env=environment(meta["run_id"], git, flock, rsync),
                text=True,
                capture_output=True,
            )
            assert result.returncode != 0
            assert "symlink" in (result.stdout + result.stderr).lower()
            assert not (root / "git.log").exists()


def test_lock_contention_refuses_readiness() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        repo, run, meta = fixture(root)
        git, flock, rsync = commands(root)
        env = environment(meta["run_id"], git, flock, rsync)
        env["TEST_FLOCK_EXIT"] = "1"
        result = subprocess.run(
            ["bash", "scripts/judge-scheduler.sh"],
            cwd=repo,
            env=env,
            text=True,
            capture_output=True,
        )
        assert result.returncode != 0
        assert "refusing duplicate" in result.stderr
        assert not (run / "consumer.ready").exists()
        assert not (root / "git.log").exists()


def test_tampered_committed_receipt_refuses_readiness() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        repo, run, meta = fixture(root)
        git, flock, rsync = commands(root)
        results = run / "_mirror" / f"results.{meta['run_id']}.jsonl"
        outputs = run / "_mirror" / "outputs"
        judged = run / f"judged.{meta['run_id']}.jsonl"
        result_rows = [complete_result("model-a", "s1", 0, meta["scenarios_sha256"])]
        write_jsonl(results, result_rows)
        write_jsonl(outputs / "model-a__s1__r0.candidates.jsonl", [{
            "model": "model-a", "scenario": "s1", "rep": 0, "index": 0,
        }])
        judged_rows = [
            {
                "model": "model-a", "scenario": "s1", "rep": 0,
                "scenarios_sha256": meta["scenarios_sha256"],
                "judge_backend": "copilot", "judge_model": judge,
                "score": 4, "verdict": "ok", "evidence": "grounded",
                "criteria_met": [], "criteria_missed": [],
            }
            for judge in ("claude-test", "gpt-test")
        ]
        judges = frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")})
        stamp_judgement_conditions(result_rows, judged_rows, judges)
        write_jsonl(judged, judged_rows)
        persisted = local_persistence.persist_model(
            results_path=results,
            judged_path=judged,
            outputs_dir=outputs,
            run_dir=run,
            model="model-a",
            units=1,
            scenario_sha256=meta["scenarios_sha256"],
            scenarios_path=repo / meta["scenarios"],
            reps=1,
            judges=judges,
        )
        (run / ".committed").write_text("model-a\n")
        with (run / persisted["result_archive"]).open("ab") as handle:
            handle.write(b"tamper")
        result = subprocess.run(
            ["bash", "scripts/judge-scheduler.sh"],
            cwd=repo,
            env=environment(meta["run_id"], git, flock, rsync),
            text=True,
            capture_output=True,
        )
        assert result.returncode != 0
        assert "receipt failed verification" in (result.stdout + result.stderr)
        assert not (run / "consumer.ready").exists()
        assert not (root / "git.log").exists()


def test_git_persistence_refuses_unresolved_judge_failure_before_staging() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        repo, run, meta = fixture(root, persist_mode="git-push")
        git_log = root / "git.log"
        git = root / "git"
        git.write_text(f'''#!/bin/sh
echo "$@" >> {str(git_log)!r}
if [ "$1" = diff ]; then exit 0; fi
if [ "$1" = rev-parse ] && [ "$2" = --short ]; then echo deadbee; fi
exit 0
''')
        flock = root / "flock"
        flock.write_text("#!/bin/sh\nexit 0\n")
        rsync = root / "rsync"
        rsync.write_text("#!/bin/sh\nexit 0\n")
        copilot = root / "copilot"
        copilot.write_text("#!/bin/sh\nprintf 'COPILOT_BACKEND_OK\\n'\n")
        for path in (git, flock, rsync, copilot):
            path.chmod(0o755)
        mirror = run / "_mirror"
        outputs = mirror / "outputs"
        results = mirror / f"results.{meta['run_id']}.jsonl"
        judged = run / f"judged.{meta['run_id']}.jsonl"
        result_rows = [complete_result("model-a", "s1", 0, meta["scenarios_sha256"])]
        write_jsonl(results, result_rows)
        write_jsonl(outputs / "model-a__s1__r0.candidates.jsonl", [{
            "model": "model-a", "scenario": "s1", "rep": 0, "index": 0,
        }])
        write_jsonl(mirror / f"results.{meta['run_id']}.jsonl.done", [{
            "model": "model-a", "units": 1,
        }])
        judged_rows = [
            {
                "model": "model-a", "scenario": "s1", "rep": 0,
                "scenarios_sha256": meta["scenarios_sha256"],
                "judge_backend": "copilot", "judge_model": "claude-test",
                "score": None, "verdict": "parse_error", "evidence": "parse_error",
                "criteria_met": [],
                "criteria_missed": ["judge response could not be parsed"],
            },
            {
                "model": "model-a", "scenario": "s1", "rep": 0,
                "scenarios_sha256": meta["scenarios_sha256"],
                "judge_backend": "copilot", "judge_model": "gpt-test",
                "score": 4, "verdict": "ok", "evidence": "grounded",
                "criteria_met": [], "criteria_missed": [],
            },
        ]
        stamp_judgement_conditions(
            result_rows,
            judged_rows,
            frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
        )
        write_jsonl(judged, judged_rows)
        (repo / "judge.py").write_text(
            "import sys\n"
            "if '--check-backends' in sys.argv:\n"
            "    print('{\"ok\":true}')\n"
            "raise SystemExit(0)\n"
        )
        env = environment(meta["run_id"], git, flock, rsync)
        env["POLL_S"] = "60"
        process = subprocess.Popen(
            ["bash", "scripts/judge-scheduler.sh"],
            cwd=repo,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            deadline = time.time() + 5
            while time.time() < deadline:
                if "git evidence incomplete" in (run / "judge-scheduler.status").read_text() if (run / "judge-scheduler.status").exists() else "":
                    break
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    raise AssertionError(f"scheduler exited unexpectedly: {stdout}\n{stderr}")
                time.sleep(0.05)
            else:
                raise AssertionError("scheduler did not reject unresolved judge evidence")
            commands_run = git_log.read_text()
            command_lines = commands_run.splitlines()
            assert not any(line.startswith("add ") for line in command_lines)
            assert not any(line.startswith("commit ") for line in command_lines)
        finally:
            process.terminate()
            process.wait(timeout=5)


def test_git_persistence_refuses_dirty_index_before_checkout() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        repo, run, meta = fixture(root, persist_mode="git-push")
        git_log = root / "git.log"
        git = root / "git"
        git.write_text(f'''#!/bin/sh
echo "$@" >> {str(git_log)!r}
if [ "$1" = diff ]; then exit 1; fi
exit 0
''')
        flock = root / "flock"
        flock.write_text("#!/bin/sh\nexit 0\n")
        rsync = root / "rsync"
        rsync.write_text("#!/bin/sh\nexit 0\n")
        copilot = root / "copilot"
        copilot.write_text("#!/bin/sh\nprintf 'COPILOT_BACKEND_OK\\n'\n")
        for path in (git, flock, rsync, copilot):
            path.chmod(0o755)
        result = subprocess.run(
            ["bash", "scripts/judge-scheduler.sh"],
            cwd=repo,
            env=environment(meta["run_id"], git, flock, rsync),
            text=True,
            capture_output=True,
        )
        assert result.returncode != 0
        assert "empty index before branch checkout" in (result.stdout + result.stderr)
        commands_run = git_log.read_text()
        assert "checkout" not in commands_run
        assert "commit" not in commands_run


def test_git_persistence_add_failure_never_commits() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        repo, run, meta = fixture(root, persist_mode="git-push")
        populate_complete_git_model(run, meta)
        git_log = root / "git.log"
        git = root / "git"
        git.write_text(f'''#!/bin/sh
echo "$@" >> {str(git_log)!r}
if [ "$1" = diff ]; then exit 0; fi
if [ "$1" = add ]; then exit 9; fi
if [ "$1" = rev-parse ] && [ "$2" = --short ]; then echo deadbee; fi
exit 0
''')
        flock = root / "flock"
        flock.write_text("#!/bin/sh\nexit 0\n")
        rsync = root / "rsync"
        rsync.write_text("#!/bin/sh\nexit 0\n")
        copilot = root / "copilot"
        copilot.write_text("#!/bin/sh\nprintf 'COPILOT_BACKEND_OK\\n'\n")
        for path in (git, flock, rsync, copilot):
            path.chmod(0o755)
        process = subprocess.Popen(
            ["bash", "scripts/judge-scheduler.sh"],
            cwd=repo,
            env=environment(meta["run_id"], git, flock, rsync),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            deadline = time.time() + 5
            status_path = run / "judge-scheduler.status"
            while time.time() < deadline:
                if status_path.exists() and "git add failed" in status_path.read_text():
                    break
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    raise AssertionError(f"scheduler exited unexpectedly: {stdout}\n{stderr}")
                time.sleep(0.05)
            else:
                status_text = status_path.read_text() if status_path.exists() else "<missing>"
                log_path = run / "judge-scheduler.log"
                log_text = log_path.read_text() if log_path.exists() else "<missing>"
                process.kill()
                raise AssertionError(
                    "scheduler did not surface git add failure\n"
                    f"status={status_text}\nlog={log_text}"
                )
            commands_run = git_log.read_text()
            command_lines = commands_run.splitlines()
            assert any(line.startswith("add ") for line in command_lines)
            assert not any(line.startswith("commit ") for line in command_lines)
        finally:
            process.terminate()
            process.wait(timeout=5)


def test_git_persistence_success_commits_only_validated_paths_and_pushes() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        repo, run, meta = fixture(root, persist_mode="git-push")
        git = shutil.which("git")
        assert git
        remote = root / "remote.git"
        subprocess.run([git, "init", "--bare", "-q", str(remote)], check=True)
        subprocess.run([git, "init", "-q"], cwd=repo, check=True)
        subprocess.run([git, "config", "user.name", "Scheduler Test"], cwd=repo, check=True)
        subprocess.run([git, "config", "user.email", "scheduler@example.invalid"], cwd=repo, check=True)
        subprocess.run([git, "add", "-A"], cwd=repo, check=True)
        subprocess.run([git, "commit", "-qm", "fixture source"], cwd=repo, check=True)
        subprocess.run([git, "remote", "add", "origin", str(remote)], cwd=repo, check=True)

        populate_complete_git_model(run, meta)
        write_jsonl(run / "pipeline-ledger.jsonl", [
            {"model": "model-a", "stage": "inference", "ok": 1},
        ])
        flock = root / "flock"
        flock.write_text("#!/bin/sh\nexit 0\n")
        rsync = root / "rsync"
        rsync.write_text("#!/bin/sh\nexit 0\n")
        copilot = root / "copilot"
        copilot.write_text("#!/bin/sh\nprintf 'COPILOT_BACKEND_OK\\n'\n")
        for path in (flock, rsync, copilot):
            path.chmod(0o755)
        env = environment(meta["run_id"], pathlib.Path(git), flock, rsync)
        env["COPILOT_BIN"] = str(copilot)
        try:
            result = subprocess.run(
                ["bash", "scripts/judge-scheduler.sh"],
                cwd=repo,
                env=env,
                text=True,
                capture_output=True,
                timeout=20,
            )
        except subprocess.TimeoutExpired as exc:
            status_path = run / "judge-scheduler.status"
            log_path = run / "judge-scheduler.log"
            raise AssertionError(
                "successful Git persistence did not finish\n"
                f"stdout={exc.stdout!r}\nstderr={exc.stderr!r}\n"
                f"status={status_path.read_text() if status_path.exists() else '<missing>'}\n"
                f"log={log_path.read_text() if log_path.exists() else '<missing>'}"
            ) from exc
        assert result.returncode == 0, result.stdout + result.stderr
        assert (run / ".committed").read_text().splitlines() == ["model-a"]
        assert (run / ".push-pending").read_text() == ""
        branch = f"experiment/{meta['run_id']}"
        local_head = subprocess.run(
            [git, "rev-parse", branch], cwd=repo, text=True, capture_output=True, check=True
        ).stdout.strip()
        remote_head = subprocess.run(
            [git, "--git-dir", str(remote), "rev-parse", branch],
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        assert local_head == remote_head
        committed_paths = set(subprocess.run(
            [git, "show", "--pretty=format:", "--name-only", local_head],
            cwd=repo,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.splitlines())
        expected_paths = {
            f"data/runs/{meta['run_id']}/model-a.results.jsonl.gz",
            f"data/runs/{meta['run_id']}/model-a.candidates.tar.gz",
            f"data/runs/{meta['run_id']}/model-a.persistence.json",
            f"data/runs/{meta['run_id']}/judged.{meta['run_id']}.jsonl",
            f"data/runs/{meta['run_id']}/pipeline-ledger.jsonl",
            f"data/runs/{meta['run_id']}/judge-scheduler.status",
        }
        assert committed_paths == expected_paths
        assert subprocess.run([git, "diff", "--cached", "--quiet"], cwd=repo).returncode == 0


if __name__ == "__main__":
    test_local_restart_reaches_readiness_without_git()
    test_mode_conflict_refuses_before_git()
    test_non_dedicated_branch_refuses_before_git()
    test_metadata_loss_with_authority_refuses_before_git()
    test_malformed_metadata_refuses_before_git()
    test_scenario_identity_substitution_refuses_before_git()
    test_repetition_conflict_refuses_before_git()
    test_invalid_committed_domain_refuses_readiness()
    test_unsafe_run_id_and_symlinked_run_path_refuse()
    test_nested_symlinked_evidence_refuses_before_lock_or_log()
    test_lock_contention_refuses_readiness()
    test_tampered_committed_receipt_refuses_readiness()
    test_git_persistence_refuses_unresolved_judge_failure_before_staging()
    test_git_persistence_refuses_dirty_index_before_checkout()
    test_git_persistence_add_failure_never_commits()
    test_git_persistence_success_commits_only_validated_paths_and_pushes()
    print("judge scheduler command tests passed")