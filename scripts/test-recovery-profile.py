#!/usr/bin/env python3
"""Regression tests for the shared timeout-sensitivity profile guard."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import tempfile

import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import recovery_profile


def exact_profile() -> dict[str, object]:
    return {
        **recovery_profile.PRODUCER_EXPECTED,
        **recovery_profile.ORCHESTRATION_EXPECTED,
    }


def test_non_recovery_profile_is_ignored() -> None:
    assert recovery_profile.validate_profile(
        {"model_set": "dryrun", "scenario_set": "core-current"},
        repo_root=REPO,
        scope="orchestration",
    ) is False


def test_exact_profile_and_hashes_pass() -> None:
    assert recovery_profile.validate_profile(
        exact_profile(), repo_root=REPO, scope="orchestration"
    ) is True


def test_every_identifier_and_path_triggers_full_profile() -> None:
    for key, value in recovery_profile.TRIGGERS.items():
        try:
            recovery_profile.validate_profile(
                {key: value}, repo_root=REPO, scope="producer"
            )
        except ValueError as exc:
            assert "complete frozen recovery profile" in str(exc)
        else:
            raise AssertionError(f"partial recovery selector was accepted: {key}")


def test_missing_literal_recovery_path_still_selects_profile() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        selected = {"models": recovery_profile.RECOVERY_ROSTER}
        assert recovery_profile.profile_selected(selected, repo_root=root)
        try:
            recovery_profile.validate_profile(selected, repo_root=root, scope="producer")
        except ValueError as exc:
            assert "complete frozen recovery profile" in str(exc)
        else:
            raise AssertionError("missing literal recovery path bypassed profile selection")


def test_equivalent_recovery_paths_trigger_and_pass() -> None:
    aliases = (
        f"./{recovery_profile.RECOVERY_ROSTER}",
        str(REPO / recovery_profile.RECOVERY_ROSTER),
        "data/../data/models.timeout-sensitivity-v1.txt",
    )
    for alias in aliases:
        partial = {"models": alias}
        assert recovery_profile.profile_selected(partial, repo_root=REPO)
        try:
            recovery_profile.validate_profile(
                partial,
                repo_root=REPO,
                scope="producer",
            )
        except ValueError as exc:
            assert "complete frozen recovery profile" in str(exc)
        else:
            raise AssertionError(f"partial alias was accepted: {alias}")

        complete = exact_profile()
        complete["models"] = alias
        assert recovery_profile.validate_profile(
            complete,
            repo_root=REPO,
            scope="orchestration",
        )


def test_case_and_hardlink_aliases_use_file_identity() -> None:
    canonical = REPO / recovery_profile.RECOVERY_ROSTER
    case_alias = REPO / "DATA" / pathlib.Path(recovery_profile.RECOVERY_ROSTER).name
    if case_alias.exists() and os.path.samefile(case_alias, canonical):
        complete = exact_profile()
        complete["models"] = str(case_alias)
        assert recovery_profile.validate_profile(
            complete, repo_root=REPO, scope="orchestration"
        )

    with tempfile.TemporaryDirectory(dir=REPO.parent) as directory:
        alias = pathlib.Path(directory) / "external-roster-hardlink.txt"
        os.link(canonical, alias)
        partial = {"models": str(alias)}
        assert recovery_profile.profile_selected(partial, repo_root=REPO)
        complete = exact_profile()
        complete.update(partial)
        try:
            recovery_profile.validate_profile(
                complete, repo_root=REPO, scope="orchestration"
            )
        except ValueError as exc:
            assert "complete frozen recovery profile" in str(exc)
        else:
            raise AssertionError("external hardlink recovery selector was accepted")

    with tempfile.TemporaryDirectory(dir=REPO / "data") as directory:
        alias = pathlib.Path(directory) / "roster-hardlink.txt"
        os.link(canonical, alias)
        complete = exact_profile()
        complete["models"] = str(alias.relative_to(REPO))
        assert recovery_profile.validate_profile(
            complete, repo_root=REPO, scope="orchestration"
        )


def test_symlink_alias_triggers_but_is_rejected() -> None:
    with tempfile.TemporaryDirectory(dir=REPO / "data") as directory:
        alias = pathlib.Path(directory) / "roster-symlink.txt"
        alias.symlink_to(REPO / recovery_profile.RECOVERY_ROSTER)
        partial = {"models": str(alias.relative_to(REPO))}
        assert recovery_profile.profile_selected(partial, repo_root=REPO)
        complete = exact_profile()
        complete.update(partial)
        try:
            recovery_profile.validate_profile(
                complete, repo_root=REPO, scope="orchestration"
            )
        except ValueError as exc:
            assert "complete frozen recovery profile" in str(exc)
        else:
            raise AssertionError("symlink-mediated recovery profile was accepted")


def test_hash_mismatch_refuses() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        data = root / "data"
        (data / "scenario_sets").mkdir(parents=True)
        profile = exact_profile()
        sources = {
            recovery_profile.RECOVERY_ROSTER: b"model-a\n",
            recovery_profile.RECOVERY_SCENARIOS: b'{"scenarios":[]}\n',
            recovery_profile.RECOVERY_MANIFEST: b"{}\n",
            recovery_profile.RECOVERY_ARTIFACT_LOCK: b"{}\n",
        }
        output_hashes = {}
        for relative, payload in sources.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            output_hashes[path.name] = __import__("hashlib").sha256(payload).hexdigest()
        manifest = root / recovery_profile.RECOVERY_ANALYSIS_MANIFEST
        manifest.write_text(json.dumps({"output_sha256": output_hashes}) + "\n")
        (root / recovery_profile.RECOVERY_ROSTER).write_text("tampered\n")
        try:
            recovery_profile.validate_profile(profile, repo_root=root, scope="orchestration")
        except ValueError as exc:
            assert "hash mismatch" in str(exc)
        else:
            raise AssertionError("tampered recovery profile was accepted")


def test_external_hardlink_selects_after_canonical_path_is_removed() -> None:
    with tempfile.TemporaryDirectory() as directory:
        container = pathlib.Path(directory)
        root = container / "repo"
        sources = {
            recovery_profile.RECOVERY_ROSTER: b"model-a\n",
            recovery_profile.RECOVERY_SCENARIOS: b'{"scenarios":[{"id":"s1"}]}\n',
            recovery_profile.RECOVERY_MANIFEST: b"{}\n",
            recovery_profile.RECOVERY_ARTIFACT_LOCK: b"{}\n",
        }
        output_hashes = {}
        for relative, payload in sources.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            output_hashes[path.name] = __import__("hashlib").sha256(payload).hexdigest()
        manifest = root / recovery_profile.RECOVERY_ANALYSIS_MANIFEST
        manifest.write_text(json.dumps({"output_sha256": output_hashes}) + "\n")

        canonical = root / recovery_profile.RECOVERY_ROSTER
        external = container / "external-roster-hardlink.txt"
        os.link(canonical, external)
        canonical.unlink()

        partial = {"models": str(external)}
        assert recovery_profile.profile_selected(partial, repo_root=root)
        try:
            recovery_profile.validate_profile(partial, repo_root=root, scope="producer")
        except ValueError as exc:
            assert "complete frozen recovery profile" in str(exc)
        else:
            raise AssertionError("external hardlink bypassed selection after canonical removal")


def test_direct_run_and_roster_identifier_refuse_before_output_state() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        run_outputs = root / "run-outputs"
        env = {**os.environ, "MODEL_SET": recovery_profile.RECOVERY_PROFILE_ID}
        result = subprocess.run(
            [
                sys.executable,
                "run.py",
                "--models", "data/models.dryrun.txt",
                "--scenarios", "data/scenario_sets/core-current.json",
                "--outputs-dir", str(run_outputs),
                "--preflight-only",
            ],
            cwd=REPO,
            env=env,
            text=True,
            capture_output=True,
        )
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "complete frozen recovery profile" in combined, repr(combined)
        assert not run_outputs.exists()

        log_dir = root / "logs"
        roster_outputs = root / "roster-outputs"
        env.update({"LOGDIR": str(log_dir), "OUTPUTS_DIR": str(roster_outputs)})
        result = subprocess.run(
            ["bash", "scripts/run-roster.sh"],
            cwd=REPO,
            env=env,
            text=True,
            capture_output=True,
        )
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "complete frozen recovery profile" in combined, repr(combined)
        assert not log_dir.exists()
        assert not roster_outputs.exists()


def main() -> None:
    tests = [value for name, value in globals().items() if name.startswith("test_") and callable(value)]
    for test in sorted(tests, key=lambda item: item.__name__):
        test()
    print(f"recovery profile tests passed: {len(tests)}")


if __name__ == "__main__":
    main()
