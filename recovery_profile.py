#!/usr/bin/env python3
"""Fail-closed contract for the timeout-sensitivity recovery condition."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

RECOVERY_PROFILE_ID = "timeout-sensitivity-v1"
RECOVERY_SCENARIO_SET = "core-current-timeout-sensitivity-v1"
RECOVERY_POLICY_ID = "ceops-timeout-sensitivity-v1"
RECOVERY_ROSTER = "data/models.timeout-sensitivity-v1.txt"
RECOVERY_SCENARIOS = "data/scenario_sets/core-current-timeout-sensitivity-v1.json"
RECOVERY_MANIFEST = "data/run-manifest.timeout-sensitivity-v1.json"
RECOVERY_ARTIFACT_LOCK = "data/model-artifacts.timeout-sensitivity-v1.json"
RECOVERY_ANALYSIS_MANIFEST = "data/timeout-recovery-sensitivity-v1.analysis-manifest.json"

TRIGGERS = {
    "model_set": RECOVERY_PROFILE_ID,
    "scenario_set": RECOVERY_SCENARIO_SET,
    "models": RECOVERY_ROSTER,
    "scenarios": RECOVERY_SCENARIOS,
    "run_manifest": RECOVERY_MANIFEST,
    "model_artifact_lock": RECOVERY_ARTIFACT_LOCK,
    "timeout_policy_id": RECOVERY_POLICY_ID,
}
PATH_FIELDS = {"models", "scenarios", "run_manifest", "model_artifact_lock"}

PRODUCER_EXPECTED: dict[str, Any] = {
    **TRIGGERS,
    "memory_context": "none",
    "memory_context_file": "",
    "inference_strategy": "baseline",
    "inference_runtime": "ollama",
    "max_tokens_cap": "",
    "run_repeats": 5,
    "run_temp": 0.7,
    "run_allow_unlocked": False,
}

ORCHESTRATION_EXPECTED: dict[str, Any] = {
    "judge_model": "claude-opus-4.6",
    "ensemble": "copilot:gpt-5.4",
    "sync_mode": "local-commit",
    "persist_mode": "git-push",
}


def _normalized(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return ""
        if stripped.lower() in {"true", "false"}:
            return stripped.lower() == "true"
        try:
            return int(stripped)
        except ValueError:
            try:
                return float(stripped)
            except ValueError:
                return stripped
    return value


def _profile_value(key: str, value: Any, repo_root: Path) -> Any:
    normalized = _normalized(value)
    if key not in PATH_FIELDS or not isinstance(normalized, str) or not normalized:
        return normalized
    path = Path(normalized)
    if not path.is_absolute():
        path = repo_root / path
    return str(path.resolve(strict=False))


def _path_uses_symlink(path: Path) -> bool:
    current = path.absolute()
    while True:
        if current.is_symlink():
            return True
        if current == current.parent:
            return False
        current = current.parent


def _path_identity_matches(
    actual: Any,
    expected: str,
    repo_root: Path,
    *,
    reject_symlink: bool = True,
) -> bool:
    actual_value = _normalized(actual)
    if not isinstance(actual_value, str) or not actual_value:
        return False
    actual_path = Path(actual_value)
    if not actual_path.is_absolute():
        actual_path = repo_root / actual_path
    expected_path = repo_root / expected
    try:
        actual_resolved = actual_path.resolve(strict=True)
        expected_resolved = expected_path.resolve(strict=True)
        actual_resolved.relative_to(repo_root.resolve(strict=True))
    except (FileNotFoundError, OSError, ValueError):
        return False
    if reject_symlink and _path_uses_symlink(actual_path):
        return False
    try:
        return os.path.samefile(actual_resolved, expected_resolved)
    except OSError:
        return False


def _path_selector_matches(actual: Any, expected: str, repo_root: Path) -> bool:
    """Detect a recovery path even when the selected file is missing."""

    actual_value = _normalized(actual)
    if not isinstance(actual_value, str) or not actual_value:
        return False
    actual_path = Path(actual_value)
    if not actual_path.is_absolute():
        actual_path = repo_root / actual_path
    expected_path = repo_root / expected
    try:
        if actual_path.resolve(strict=False) == expected_path.resolve(strict=False):
            return True
    except OSError:
        pass
    try:
        return os.path.samefile(
            actual_path.resolve(strict=True),
            expected_path.resolve(strict=True),
        )
    except (FileNotFoundError, OSError):
        pass

    # The canonical path may have been removed after an external hardlink or
    # byte-for-byte copy was created. The frozen analysis manifest remains the
    # independent selector in that case; strict acceptance below still rejects
    # paths outside the repository and missing canonical contracts.
    manifest_path = repo_root / RECOVERY_ANALYSIS_MANIFEST
    try:
        if manifest_path.is_symlink() or not manifest_path.is_file():
            return False
        manifest = json.loads(manifest_path.read_text())
        expected_digest = manifest.get("output_sha256", {}).get(Path(expected).name)
        if not isinstance(expected_digest, str) or len(expected_digest) != 64:
            return False
        actual_resolved = actual_path.resolve(strict=True)
        if not actual_resolved.is_file():
            return False
        return hashlib.sha256(actual_resolved.read_bytes()).hexdigest() == expected_digest
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError):
        return False


def _profile_field_matches(key: str, actual: Any, expected: Any, repo_root: Path) -> bool:
    if key in PATH_FIELDS:
        return _path_identity_matches(actual, str(expected), repo_root)
    return _normalized(actual) == expected


def profile_selected(values: Mapping[str, Any], *, repo_root: Path) -> bool:
    return any(
        _path_selector_matches(values.get(key), str(expected), repo_root)
        if key in PATH_FIELDS
        else _normalized(values.get(key)) == expected
        for key, expected in TRIGGERS.items()
    )


def validate_profile(
    values: Mapping[str, Any],
    *,
    repo_root: Path,
    scope: str,
) -> bool:
    if scope not in {"producer", "orchestration"}:
        raise ValueError(f"unknown recovery profile scope: {scope}")
    repo_root = repo_root.resolve()
    if not profile_selected(values, repo_root=repo_root):
        return False

    expected = dict(PRODUCER_EXPECTED)
    if scope == "orchestration":
        expected.update(ORCHESTRATION_EXPECTED)
    mismatches = {
        key: {
            "actual": _profile_value(key, values.get(key), repo_root),
            "expected": _profile_value(key, wanted, repo_root),
        }
        for key, wanted in expected.items()
        if not _profile_field_matches(key, values.get(key), wanted, repo_root)
    }
    if mismatches:
        raise ValueError(
            "timeout-sensitivity-v1 requires its complete frozen recovery profile: "
            + json.dumps(mismatches, sort_keys=True, separators=(",", ":"))
        )

    manifest_path = repo_root / RECOVERY_ANALYSIS_MANIFEST
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("recovery analysis manifest is missing or symlinked")
    manifest = json.loads(manifest_path.read_text())
    output_hashes = manifest.get("output_sha256")
    if not isinstance(output_hashes, dict):
        raise ValueError("recovery analysis manifest lacks output hashes")
    for relative in (
        RECOVERY_ROSTER,
        RECOVERY_SCENARIOS,
        RECOVERY_MANIFEST,
        RECOVERY_ARTIFACT_LOCK,
    ):
        path = repo_root / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"recovery profile file is missing or symlinked: {relative}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if output_hashes.get(path.name) != digest:
            raise ValueError(f"recovery profile hash mismatch: {relative}")
    return True


def profile_from_environment() -> dict[str, Any]:
    return {
        "models": os.environ.get("MODELS", "data/models.txt"),
        "model_set": os.environ.get("MODEL_SET", "manual"),
        "scenarios": os.environ.get("SCENARIOS", "data/scenarios.json"),
        "scenario_set": os.environ.get("SCENARIO_SET", "all"),
        "run_manifest": os.environ.get("RUN_MANIFEST", "data/run-manifest.json"),
        "model_artifact_lock": os.environ.get("MODEL_ARTIFACT_LOCK", ""),
        "timeout_policy_id": os.environ.get("TIMEOUT_POLICY_ID", "ceops-v2-zero-stall-retry"),
        "memory_context": os.environ.get("MEMORY_CONTEXT", "none"),
        "memory_context_file": os.environ.get("MEMORY_CONTEXT_FILE", ""),
        "inference_strategy": os.environ.get("INFERENCE_STRATEGY", "baseline"),
        "inference_runtime": os.environ.get("INFERENCE_RUNTIME", "ollama"),
        "max_tokens_cap": os.environ.get("MAX_TOKENS_CAP", ""),
        "run_repeats": os.environ.get("RUN_REPEATS", ""),
        "run_temp": os.environ.get("RUN_TEMP", ""),
        "run_allow_unlocked": os.environ.get("RUN_ALLOW_UNLOCKED", "") in {"1", "true", "True"},
        "judge_model": os.environ.get("JUDGE_MODEL", "claude-opus-4.6"),
        "ensemble": os.environ.get("ENSEMBLE", "copilot:gpt-5.4"),
        "sync_mode": os.environ.get("SYNC_MODE", "origin"),
        "persist_mode": os.environ.get("PERSIST_MODE", "git-push"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("producer", "orchestration"), required=True)
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    try:
        selected = validate_profile(
            profile_from_environment(),
            repo_root=Path(args.repo_root).resolve(),
            scope=args.scope,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"FATAL: {exc}") from exc
    print("recovery_profile=selected" if selected else "recovery_profile=not-selected")


if __name__ == "__main__":
    main()
