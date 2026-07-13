#!/usr/bin/env python3
"""Atomically persist one fully inferred model without Git or remote push."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import tarfile
import tempfile
from pathlib import Path
from typing import Any

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import analysis_metrics  # noqa: E402

RECEIPT_FIELDS = {
    "analysis_condition_keys_sha256",
    "candidate_archive",
    "candidate_archive_sha256",
    "candidate_files",
    "canonical_judgements",
    "judge_attempts",
    "judgement_attempts_sha256",
    "judge_retries",
    "judges",
    "evaluation_policy",
    "model",
    "persist_mode",
    "reps",
    "result_archive",
    "result_archive_sha256",
    "result_rows",
    "result_rows_sha256",
    "scenario_ids",
    "scenario_sha256",
    "schema_version",
    "units",
}
CANDIDATE_CONTEXT_FIELDS = {"model", "scenario", "rep", "memory_context", "inference_strategy"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def require_regular_file(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"required regular file is missing: {path}")


def fsync_file(path: Path) -> None:
    require_regular_file(path)
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def slug(model: str) -> str:
    return model.replace("/", "_").replace(":", "_")


def strict_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{label} must be an integer >= {minimum}")
    return value


def row_rep(row: dict[str, Any], label: str) -> int:
    return strict_int(row.get("rep"), f"{label}.rep")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    fsync_file(path)
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            rows.append(value)
    return rows


def atomic_deterministic_gzip(path: Path, payload: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
                compressed.write(payload)
            raw.flush()
            os.fsync(raw.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def deterministic_tar_gzip(files: list[Path]) -> bytes:
    raw = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as archive:
            for path in sorted(files, key=lambda item: item.name):
                payload = path.read_bytes()
                info = tarfile.TarInfo(path.name)
                info.size = len(payload)
                info.mtime = 0
                info.mode = 0o644
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                archive.addfile(info, io.BytesIO(payload))
    return raw.getvalue()


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def scenario_ids(path: Path) -> list[str]:
    require_regular_file(path)
    value = json.loads(path.read_text())
    rows = value.get("scenarios") if isinstance(value, dict) else None
    if not isinstance(rows, list):
        raise ValueError("scenario contract must contain a scenarios list")
    identifiers = [row.get("id") for row in rows if isinstance(row, dict)]
    if len(identifiers) != len(rows) or any(not isinstance(value, str) or not value for value in identifiers):
        raise ValueError("every scenario must have a non-empty id")
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("scenario identifiers must be unique")
    return identifiers


def classified_retry(row: dict[str, Any]) -> bool:
    return row.get("score") is None and (
        row.get("evidence") in {"parse_error", "invalid_contract"}
        or "judge response could not be parsed" in (row.get("criteria_missed") or [])
        or "judge response violated the judgement contract" in (row.get("criteria_missed") or [])
    )


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def canonical_rows_sha256(rows: list[dict[str, Any]]) -> str:
    payload = b"".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        for row in sorted(
            rows,
            key=lambda row: (
                str(row.get("scenario")),
                row_rep(row, "judgement"),
                *analysis_metrics.judge_identity(row),
                0 if analysis_metrics.judgement_success(row) else 1,
            ),
        )
    )
    return hashlib.sha256(payload).hexdigest()


def canonical_result_payload(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        for row in sorted(rows, key=lambda row: (str(row.get("scenario")), row_rep(row, "result")))
    )


def decode_jsonl(payload: bytes, label: str) -> list[dict[str, Any]]:
    rows = []
    for line_number, raw in enumerate(payload.splitlines(), 1):
        if not raw.strip():
            continue
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"{label}:{line_number} is not a JSON object")
        rows.append(value)
    return rows


def parse_judges(values: Any, label: str) -> frozenset[tuple[str, str]]:
    if not isinstance(values, list) or not values:
        raise ValueError(f"{label} must be a non-empty list")
    parsed = set()
    for value in values:
        if not isinstance(value, str):
            raise ValueError(f"{label} entries must be BACKEND:MODEL strings")
        backend, separator, model = value.partition(":")
        if not separator or not backend or not model:
            raise ValueError(f"invalid {label} entry: {value!r}")
        parsed.add((backend, model))
    if len(parsed) != len(values):
        raise ValueError(f"{label} entries must be unique")
    return frozenset(parsed)


def evaluation_policy_for(judges: frozenset[tuple[str, str]]) -> str:
    return analysis_metrics.evaluation_policy_id([
        {"judge_backend": backend, "judge_model": model}
        for backend, model in sorted(judges)
    ])


def result_condition_contract(
    rows: list[dict[str, Any]],
    judges: frozenset[tuple[str, str]],
) -> tuple[str, dict[tuple[str, int], str], str]:
    evaluation_policy = evaluation_policy_for(judges)
    conditions: dict[tuple[str, int], str] = {}
    for row in rows:
        key = (str(row.get("scenario")), row_rep(row, "result"))
        normalized = analysis_metrics.normalize_condition_provenance(row)
        identity = analysis_metrics.analysis_condition(
            normalized,
            evaluation_policy=evaluation_policy,
        )
        if identity.incomplete:
            raise ValueError(
                f"result {key} has incomplete condition identity: {identity.missing_fields}"
            )
        existing_condition = row.get("analysis_condition_key_sha256")
        if existing_condition is not None and existing_condition != identity.sha256:
            raise ValueError(f"result {key} condition hash differs from computed identity")
        existing_policy = row.get("evaluation_policy")
        if existing_policy is not None and existing_policy != evaluation_policy:
            raise ValueError(f"result {key} evaluation policy differs from declared judges")
        conditions[key] = identity.sha256
    payload = canonical_json([
        {"condition_sha256": condition, "rep": rep, "scenario": scenario}
        for (scenario, rep), condition in sorted(conditions.items())
    ])
    return evaluation_policy, conditions, hashlib.sha256(payload).hexdigest()


def validate_judgement_rows(
    rows: list[dict[str, Any]],
    *,
    model: str,
    result_conditions: dict[tuple[str, int], str],
    judges: frozenset[tuple[str, str]],
    scenario_sha256: str,
    evaluation_policy: str,
) -> dict[str, int]:
    if any(row.get("model") != model for row in rows):
        raise ValueError(f"model {model} judgement evidence contains a foreign model")
    bad_hashes = sorted({
        str(row.get("scenarios_sha256"))
        for row in rows
        if row.get("scenarios_sha256") != scenario_sha256
    })
    if bad_hashes:
        raise ValueError(f"model {model} judgements have mismatched scenario hashes: {bad_hashes}")
    expected_keys = {
        (condition, scenario, rep, backend, judge_model)
        for (scenario, rep), condition in result_conditions.items()
        for backend, judge_model in judges
    }
    attempts: dict[tuple[str, str, int, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        shallow_key = (str(row.get("scenario")), row_rep(row, "judgement"))
        expected_condition = result_conditions.get(shallow_key)
        if (
            row.get("analysis_condition_key_sha256") != expected_condition
            or row.get("evaluation_policy") != evaluation_policy
            or row.get("condition_identity_incomplete") is not False
        ):
            raise ValueError(
                f"model {model} judgement condition differs from result: {shallow_key} "
                f"actual_condition={row.get('analysis_condition_key_sha256')!r} "
                f"expected_condition={expected_condition!r} "
                f"actual_policy={row.get('evaluation_policy')!r} "
                f"expected_policy={evaluation_policy!r} "
                f"incomplete={row.get('condition_identity_incomplete')!r}"
            )
        key = (
            str(row.get("analysis_condition_key_sha256")),
            str(row.get("scenario")),
            row_rep(row, "judgement"),
            *analysis_metrics.judge_identity(row),
        )
        attempts.setdefault(key, []).append(row)
    observed_keys = set(attempts)
    if observed_keys != expected_keys:
        raise ValueError(
            f"model {model} judgement domain differs from results x judges: "
            f"missing={len(expected_keys - observed_keys)} extra={len(observed_keys - expected_keys)}"
        )
    invalid_successes = {
        key: sum(analysis_metrics.judgement_success(row) for row in rows_for_key)
        for key, rows_for_key in attempts.items()
        if sum(analysis_metrics.judgement_success(row) for row in rows_for_key) != 1
    }
    if invalid_successes:
        raise ValueError(
            f"model {model} must have exactly one successful judgement per key: "
            f"invalid={len(invalid_successes)}"
        )
    invalid_retries = [
        row
        for rows_for_key in attempts.values()
        for row in rows_for_key
        if not analysis_metrics.judgement_success(row) and not classified_retry(row)
    ]
    if invalid_retries:
        raise ValueError(f"model {model} has {len(invalid_retries)} unclassified judge failures")
    return {
        "canonical_judgements": len(expected_keys),
        "judge_attempts": len(rows),
        "judge_retries": len(rows) - len(expected_keys),
    }


def validate_candidate_rows(
    rows: list[dict[str, Any]],
    *,
    model: str,
    result_row: dict[str, Any],
    label: str,
) -> tuple[str, int]:
    if not rows or any(row.get("model") != model for row in rows):
        raise ValueError(f"{label} contains invalid or foreign model rows")
    keys = {(str(row.get("scenario")), row_rep(row, label)) for row in rows}
    if len(keys) != 1:
        raise ValueError(f"{label} has mixed tuples")
    key = next(iter(keys))
    if key != (str(result_row.get("scenario")), row_rep(result_row, "result")):
        raise ValueError(f"{label} tuple differs from result row")
    expected = result_row.get("strategy.candidates")
    if not isinstance(expected, list) or not expected or any(not isinstance(row, dict) for row in expected):
        raise ValueError(f"result row lacks structured strategy candidates for {label}")
    observed = [
        {field: value for field, value in row.items() if field not in CANDIDATE_CONTEXT_FIELDS}
        for row in rows
    ]
    if observed != expected:
        raise ValueError(f"{label} payload differs from result strategy candidates")
    return key


def persist_model(
    *,
    results_path: Path,
    judged_path: Path,
    outputs_dir: Path,
    run_dir: Path,
    model: str,
    units: int,
    scenario_sha256: str,
    scenarios_path: Path,
    reps: int,
    judges: frozenset[tuple[str, str]],
    validate_only: bool = False,
    persist_mode: str = "local-files",
) -> dict[str, Any]:
    if persist_mode not in {"git-push", "local-files"}:
        raise ValueError("persist_mode must be git-push or local-files")
    units = strict_int(units, "units", minimum=1)
    reps = strict_int(reps, "reps", minimum=1)
    if outputs_dir.is_symlink() or not outputs_dir.is_dir():
        raise ValueError(f"outputs directory is missing or symlinked: {outputs_dir}")
    if run_dir.is_symlink():
        raise ValueError(f"run directory is symlinked: {run_dir}")
    declared_scenarios = scenario_ids(scenarios_path)
    expected_result_keys = {
        (scenario, rep)
        for scenario in declared_scenarios
        for rep in range(reps)
    }
    if units != len(expected_result_keys):
        raise ValueError(
            f"units={units} differs from declared scenario x rep domain={len(expected_result_keys)}"
        )
    rows = [row for row in read_jsonl(results_path) if row.get("model") == model]
    result_keys = {(str(row.get("scenario")), row_rep(row, "result")) for row in rows}
    results_by_key = {
        (str(row.get("scenario")), row_rep(row, "result")): row
        for row in rows
    }
    if len(rows) != units or len(result_keys) != units or result_keys != expected_result_keys:
        raise ValueError(
            f"model {model} result domain is incomplete or duplicated: "
            f"rows={len(rows)} unique={len(result_keys)} expected={units}"
        )
    bad_scenario_hashes = sorted({
        str(row.get("env.scenarios_sha"))
        for row in rows
        if row.get("env.scenarios_sha") != scenario_sha256
    })
    if bad_scenario_hashes:
        raise ValueError(f"model {model} has mismatched scenario hashes: {bad_scenario_hashes}")

    if not judges:
        raise ValueError("at least one judge identity is required")
    evaluation_policy, result_conditions, condition_keys_sha256 = result_condition_contract(
        rows, judges
    )
    judgement_rows = [row for row in read_jsonl(judged_path) if row.get("model") == model]
    judgement_counts = validate_judgement_rows(
        judgement_rows,
        model=model,
        result_conditions=result_conditions,
        judges=judges,
        scenario_sha256=scenario_sha256,
        evaluation_policy=evaluation_policy,
    )

    model_slug = slug(model)
    candidate_files = sorted(outputs_dir.glob(f"{model_slug}__*.candidates.jsonl"))
    candidate_keys: set[tuple[str, int]] = set()
    for path in candidate_files:
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"candidate sidecar is not a regular file: {path}")
        candidate_rows = read_jsonl(path)
        provisional_keys = {(str(row.get("scenario")), row_rep(row, "candidate")) for row in candidate_rows}
        if len(provisional_keys) != 1 or next(iter(provisional_keys)) not in results_by_key:
            raise ValueError(f"candidate sidecar has an invalid tuple domain: {path}")
        candidate_keys.add(validate_candidate_rows(
            candidate_rows,
            model=model,
            result_row=results_by_key[next(iter(provisional_keys))],
            label=f"candidate sidecar {path.name}",
        ))
    if len(candidate_files) != units or candidate_keys != result_keys:
        raise ValueError(
            f"model {model} candidate domain differs from results: "
            f"files={len(candidate_files)} tuples={len(candidate_keys)} expected={units}"
        )

    if validate_only:
        return {
            "candidate_files": len(candidate_files),
            **judgement_counts,
            "model": model,
            "result_rows": len(rows),
            "units": units,
            "validated": True,
        }

    run_dir.mkdir(parents=True, exist_ok=True)
    result_archive = run_dir / f"{model_slug}.results.jsonl.gz"
    candidate_archive = run_dir / f"{model_slug}.candidates.tar.gz"
    payload = canonical_result_payload(rows)
    atomic_deterministic_gzip(result_archive, payload)
    candidate_payload = deterministic_tar_gzip(candidate_files)
    atomic_write_bytes(candidate_archive, candidate_payload)
    receipt = {
        "analysis_condition_keys_sha256": condition_keys_sha256,
        "schema_version": 1,
        "persist_mode": persist_mode,
        "candidate_archive": candidate_archive.name,
        "candidate_archive_sha256": sha256_file(candidate_archive),
        "candidate_files": len(candidate_files),
        **judgement_counts,
        "evaluation_policy": evaluation_policy,
        "judgement_attempts_sha256": canonical_rows_sha256(judgement_rows),
        "model": model,
        "judges": [f"{backend}:{judge_model}" for backend, judge_model in sorted(judges)],
        "reps": reps,
        "result_archive": result_archive.name,
        "result_archive_sha256": sha256_file(result_archive),
        "result_rows": len(rows),
        "result_rows_sha256": hashlib.sha256(payload).hexdigest(),
        "scenario_ids": declared_scenarios,
        "scenario_sha256": scenario_sha256,
        "units": units,
    }
    receipt_path = run_dir / f"{model_slug}.persistence.json"
    atomic_write_bytes(
        receipt_path,
        json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode() + b"\n",
    )
    verify_receipt(
        run_dir,
        receipt_path,
        model,
        judged_path,
        results_path,
        outputs_dir,
        scenarios_path,
        reps,
        judges,
        scenario_sha256,
    )
    receipt["receipt"] = receipt_path.name
    receipt["receipt_sha256"] = sha256_file(receipt_path)
    return receipt


def verify_receipt(
    run_dir: Path,
    receipt_path: Path,
    expected_model: str | None = None,
    judged_path: Path | None = None,
    results_path: Path | None = None,
    outputs_dir: Path | None = None,
    scenarios_path: Path | None = None,
    expected_reps: int | None = None,
    expected_judges: frozenset[tuple[str, str]] | None = None,
    expected_scenario_sha256: str | None = None,
) -> dict[str, Any]:
    if run_dir.is_symlink() or not run_dir.is_dir():
        raise ValueError(f"run directory is missing or symlinked: {run_dir}")
    require_regular_file(receipt_path)
    receipt = json.loads(receipt_path.read_text())
    if not isinstance(receipt, dict) or set(receipt) != RECEIPT_FIELDS:
        raise ValueError(f"persistence receipt fields differ from schema: {receipt_path}")
    if strict_int(receipt.get("schema_version"), "receipt.schema_version", minimum=1) != 1:
        raise ValueError(f"invalid persistence receipt: {receipt_path}")
    model = receipt.get("model")
    if not isinstance(model, str) or not model or (expected_model and model != expected_model):
        raise ValueError(f"persistence receipt model mismatch: {receipt_path}")
    if receipt.get("persist_mode") not in {"git-push", "local-files"}:
        raise ValueError(f"persistence receipt mode mismatch: {receipt_path}")
    reps = strict_int(receipt.get("reps"), "receipt.reps", minimum=1)
    units = strict_int(receipt.get("units"), "receipt.units", minimum=1)
    result_count = strict_int(receipt.get("result_rows"), "receipt.result_rows", minimum=1)
    candidate_count = strict_int(receipt.get("candidate_files"), "receipt.candidate_files", minimum=1)
    canonical_count = strict_int(
        receipt.get("canonical_judgements"), "receipt.canonical_judgements", minimum=1
    )
    attempt_count = strict_int(receipt.get("judge_attempts"), "receipt.judge_attempts", minimum=1)
    retry_count = strict_int(receipt.get("judge_retries"), "receipt.judge_retries")
    receipt_judges = parse_judges(receipt.get("judges"), "receipt.judges")
    evaluation_policy = evaluation_policy_for(receipt_judges)
    if receipt.get("evaluation_policy") != evaluation_policy:
        raise ValueError(f"persistence receipt evaluation policy mismatch: {receipt_path}")
    receipt_scenarios = receipt.get("scenario_ids")
    if (
        not isinstance(receipt_scenarios, list)
        or not receipt_scenarios
        or any(not isinstance(value, str) or not value for value in receipt_scenarios)
        or len(receipt_scenarios) != len(set(receipt_scenarios))
    ):
        raise ValueError(f"persistence receipt scenario_ids are invalid: {receipt_path}")
    if expected_reps is not None and reps != strict_int(expected_reps, "expected_reps", minimum=1):
        raise ValueError(f"persistence receipt repetitions mismatch: {receipt_path}")
    if expected_judges is not None and receipt_judges != expected_judges:
        raise ValueError(f"persistence receipt judge domain mismatch: {receipt_path}")
    if expected_scenario_sha256 is not None and receipt.get("scenario_sha256") != expected_scenario_sha256:
        raise ValueError(f"persistence receipt scenario hash mismatch: {receipt_path}")
    if scenarios_path is not None:
        declared_scenarios = scenario_ids(scenarios_path)
        if receipt_scenarios != declared_scenarios or sha256_file(scenarios_path) != receipt.get("scenario_sha256"):
            raise ValueError(f"persistence receipt scenario contract mismatch: {receipt_path}")
    model_slug = slug(model)
    expected_names = {
        "result_archive": f"{model_slug}.results.jsonl.gz",
        "candidate_archive": f"{model_slug}.candidates.tar.gz",
    }
    archives: dict[str, Path] = {}
    for key, expected_name in expected_names.items():
        if receipt.get(key) != expected_name:
            raise ValueError(f"persistence receipt {key} mismatch: {receipt_path}")
        archive = run_dir / expected_name
        require_regular_file(archive)
        if sha256_file(archive) != receipt.get(f"{key}_sha256"):
            raise ValueError(f"persistence receipt hash mismatch: {archive}")
        archives[key] = archive

    with gzip.open(archives["result_archive"], "rb") as handle:
        result_payload = handle.read()
    result_rows = decode_jsonl(result_payload, "result archive")
    canonical_payload = canonical_result_payload(result_rows)
    if result_payload != canonical_payload or hashlib.sha256(canonical_payload).hexdigest() != receipt.get("result_rows_sha256"):
        raise ValueError(f"result archive payload differs from persistence receipt: {receipt_path}")
    result_keys = {(str(row.get("scenario")), row_rep(row, "archived result")) for row in result_rows}
    results_by_key = {
        (str(row.get("scenario")), row_rep(row, "archived result")): row
        for row in result_rows
    }
    expected_keys = {
        (str(scenario), rep)
        for scenario in receipt_scenarios
        for rep in range(reps)
    }
    if (
        len(result_rows) != result_count
        or len(result_rows) != units
        or len(result_rows) != len(result_keys)
        or result_count != candidate_count
        or units != len(expected_keys)
        or canonical_count != len(expected_keys) * len(receipt_judges)
        or result_keys != expected_keys
        or any(row.get("model") != model for row in result_rows)
        or any(row.get("env.scenarios_sha") != receipt.get("scenario_sha256") for row in result_rows)
    ):
        raise ValueError(f"result archive domain differs from persistence receipt: {receipt_path}")
    _, result_conditions, condition_keys_sha256 = result_condition_contract(
        result_rows, receipt_judges
    )
    if receipt.get("analysis_condition_keys_sha256") != condition_keys_sha256:
        raise ValueError(f"persistence receipt condition-key hash mismatch: {receipt_path}")

    candidate_keys: set[tuple[str, int]] = set()
    with tarfile.open(archives["candidate_archive"], "r:gz") as archive:
        members = archive.getmembers()
        if len(members) != candidate_count:
            raise ValueError(f"candidate archive member count mismatch: {receipt_path}")
        for member in members:
            member_path = Path(member.name)
            if not member.isfile() or member_path.is_absolute() or len(member_path.parts) != 1:
                raise ValueError(f"unsafe candidate archive member: {member.name}")
            extracted = archive.extractfile(member)
            if extracted is None:
                raise ValueError(f"cannot read candidate archive member: {member.name}")
            rows = [json.loads(line) for line in extracted.read().decode("utf-8").splitlines() if line.strip()]
            if any(not isinstance(row, dict) for row in rows):
                raise ValueError(f"candidate archive member has invalid rows: {member.name}")
            provisional_keys = {(str(row.get("scenario")), row_rep(row, "archived candidate")) for row in rows}
            if len(provisional_keys) != 1 or next(iter(provisional_keys)) not in results_by_key:
                raise ValueError(f"candidate archive member has invalid tuple: {member.name}")
            candidate_keys.add(validate_candidate_rows(
                rows,
                model=model,
                result_row=results_by_key[next(iter(provisional_keys))],
                label=f"candidate archive member {member.name}",
            ))
    if candidate_keys != expected_keys:
        raise ValueError(f"candidate archive domain differs from persistence receipt: {receipt_path}")
    if judged_path is None or results_path is None or outputs_dir is None:
        raise ValueError("receipt verification requires current results, judged, and candidate evidence")
    if outputs_dir.is_symlink() or not outputs_dir.is_dir():
        raise ValueError(f"outputs directory is missing or symlinked: {outputs_dir}")
    source_candidates = sorted(outputs_dir.glob(f"{model_slug}__*.candidates.jsonl"))
    if len(source_candidates) != candidate_count:
        raise ValueError(f"current candidate inventory differs from persistence receipt: {receipt_path}")
    source_candidate_keys: set[tuple[str, int]] = set()
    for source in source_candidates:
        source_rows = read_jsonl(source)
        provisional_keys = {(str(row.get("scenario")), row_rep(row, "current candidate")) for row in source_rows}
        if len(provisional_keys) != 1 or next(iter(provisional_keys)) not in results_by_key:
            raise ValueError(f"current candidate evidence has invalid tuple: {source}")
        source_candidate_keys.add(validate_candidate_rows(
            source_rows,
            model=model,
            result_row=results_by_key[next(iter(provisional_keys))],
            label=f"current candidate evidence {source.name}",
        ))
    if source_candidate_keys != expected_keys:
        raise ValueError(f"current candidate domain differs from persistence receipt: {receipt_path}")
    if deterministic_tar_gzip(source_candidates) != archives["candidate_archive"].read_bytes():
        raise ValueError(f"current candidates differ from persistence archive: {receipt_path}")
    judgement_rows = [row for row in read_jsonl(judged_path) if row.get("model") == model]
    recomputed = validate_judgement_rows(
        judgement_rows,
        model=model,
        result_conditions=result_conditions,
        judges=receipt_judges,
        scenario_sha256=str(receipt.get("scenario_sha256")),
        evaluation_policy=evaluation_policy,
    )
    if (
        recomputed["canonical_judgements"] != canonical_count
        or recomputed["judge_attempts"] != attempt_count
        or recomputed["judge_retries"] != retry_count
        or canonical_rows_sha256(judgement_rows) != receipt.get("judgement_attempts_sha256")
    ):
        raise ValueError(f"judgement attempts differ from persistence receipt: {receipt_path}")
    current_rows = [row for row in read_jsonl(results_path) if row.get("model") == model]
    current_payload = canonical_result_payload(current_rows)
    if (
        len(current_rows) != result_count
        or current_payload != canonical_payload
        or hashlib.sha256(current_payload).hexdigest() != receipt.get("result_rows_sha256")
    ):
        raise ValueError(f"current results differ from persistence receipt: {receipt_path}")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--judged", type=Path)
    parser.add_argument("--outputs-dir", type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--model")
    parser.add_argument("--units", type=int)
    parser.add_argument("--scenario-sha256")
    parser.add_argument("--scenarios", type=Path)
    parser.add_argument("--reps", type=int)
    parser.add_argument("--judge", action="append", default=[], metavar="BACKEND:MODEL")
    parser.add_argument("--verify-receipt", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--persist-mode", choices=("git-push", "local-files"), default="local-files")
    args = parser.parse_args()
    if args.verify_receipt:
        verify_judges = parse_judges(args.judge, "--judge") if args.judge else None
        result = verify_receipt(
            args.run_dir,
            args.verify_receipt,
            args.model,
            args.judged,
            args.results,
            args.outputs_dir,
            args.scenarios,
            args.reps,
            verify_judges,
            args.scenario_sha256,
        )
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return
    required = {
        "--results": args.results,
        "--judged": args.judged,
        "--outputs-dir": args.outputs_dir,
        "--model": args.model,
        "--units": args.units,
        "--scenario-sha256": args.scenario_sha256,
        "--scenarios": args.scenarios,
        "--reps": args.reps,
        "--judge": args.judge,
    }
    missing = [name for name, value in required.items() if value in (None, [], "")]
    if missing:
        parser.error("persistence requires " + ", ".join(missing))
    judges = set()
    for value in args.judge:
        backend, separator, judge_model = value.partition(":")
        if not separator or not backend or not judge_model:
            parser.error(f"invalid --judge {value!r}; expected BACKEND:MODEL")
        judges.add((backend, judge_model))
    result = persist_model(
        results_path=args.results,
        judged_path=args.judged,
        outputs_dir=args.outputs_dir,
        run_dir=args.run_dir,
        model=args.model,
        units=args.units,
        scenario_sha256=args.scenario_sha256,
        scenarios_path=args.scenarios,
        reps=args.reps,
        judges=frozenset(judges),
        validate_only=args.validate_only,
        persist_mode=args.persist_mode,
    )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()