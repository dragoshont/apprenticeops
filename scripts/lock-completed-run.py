#!/usr/bin/env python3
"""Promote one completed ApprenticeOps run into an immutable analysis-v1 bundle."""
from __future__ import annotations

import argparse
import contextlib
import copy
import datetime as dt
import fcntl
import gzip
import hashlib
import json
import math
import os
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import analysis_metrics  # noqa: E402

TOOL_VERSION = "completed-run-promotion-v1"
EXIT_VALIDATION = 2
EXIT_BOUNDARY = 3
EXIT_INCOMPLETE = 4


class PromotionError(RuntimeError):
    def __init__(
        self,
        gate: str,
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
        exit_code: int = EXIT_VALIDATION,
        stage: str | None = None,
    ):
        super().__init__(message)
        self.details = dict(details or {})
        self.gate = gate
        self.exit_code = exit_code
        self.stage = stage


@dataclass(frozen=True)
class JudgeSpec:
    backend: str
    model: str

    @property
    def identity(self) -> tuple[str, str]:
        return (self.backend, self.model)


@dataclass(frozen=True)
class RunInputs:
    run_dir: Path
    run_id: str
    meta: Path
    results: Path
    done: Path
    judged: Path
    pipeline_ledger: Path
    committed: Path
    push_pending: Path
    roster: Path
    scenarios: Path
    result_archives: tuple[Path, ...]
    candidate_archives: tuple[Path, ...]
    logs: tuple[Path, ...]

    def sidecar_sources(self) -> dict[str, Path]:
        sources: dict[str, Path] = {}
        for directory, paths in (
            ("model-results", self.result_archives),
            ("candidates", self.candidate_archives),
            ("logs", self.logs),
        ):
            for path in paths:
                sources[f"raw/{directory}/{path.name}"] = path
        return sources

    def hash_sources(self) -> dict[str, Path]:
        return {
            "raw/run.meta": self.meta,
            "raw/results.source.jsonl": self.results,
            "raw/results.done": self.done,
            "raw/judged.attempts.source.jsonl": self.judged,
            "raw/pipeline-ledger.jsonl": self.pipeline_ledger,
            "raw/committed-models.txt": self.committed,
            "raw/push-pending.txt": self.push_pending,
            "contract/roster.txt": self.roster,
            "contract/scenarios.json": self.scenarios,
            **self.sidecar_sources(),
        }


@dataclass(frozen=True)
class PromotionContext:
    repo_root: Path
    run_dir: Path
    output_root: Path
    judges: tuple[JudgeSpec, ...]
    evaluation_policy: str
    inputs: RunInputs
    meta: Mapping[str, Any]

    @property
    def stage_dir(self) -> Path:
        return self.output_root / ".staging" / self.inputs.run_id

    @property
    def state_dir(self) -> Path:
        return self.output_root / ".state" / self.inputs.run_id

    @property
    def ledger_path(self) -> Path:
        return self.state_dir / "promotion-ledger.jsonl"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def digest_mapping(value: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_json(value))


def duplicate_values(values: Iterable[str]) -> list[str]:
    counts: defaultdict[str, int] = defaultdict(int)
    for value in values:
        counts[value] += 1
    return sorted(value for value, count in counts.items() if count > 1)


def result_key_details(keys: Iterable[tuple[str, str, int]]) -> list[dict[str, Any]]:
    return [
        {"model": model, "scenario": scenario, "rep": rep}
        for model, scenario, rep in sorted(keys)
    ]


def judge_key_details(
    keys: Iterable[tuple[str, str, int, str, str]],
) -> list[dict[str, Any]]:
    return [
        {
            "condition_sha256": condition,
            "scenario": scenario,
            "rep": rep,
            "judge_backend": backend,
            "judge_model": model,
        }
        for condition, scenario, rep, backend, model in sorted(keys)
    ]


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    fsync_directory(path.parent)


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_bytes(path, json.dumps(value, indent=2, sort_keys=True).encode() + b"\n")


def append_jsonl(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:
        handle.write(canonical_json(value) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())


def deterministic_gzip_from_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    with source.open("rb") as incoming, temporary.open("wb") as raw_output:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_output, mtime=0) as compressed:
            shutil.copyfileobj(incoming, compressed, length=1024 * 1024)
        raw_output.flush()
        os.fsync(raw_output.fileno())
    os.replace(temporary, destination)


def atomic_copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    with source.open("rb") as incoming, temporary.open("wb") as outgoing:
        shutil.copyfileobj(incoming, outgoing, length=1024 * 1024)
        outgoing.flush()
        os.fsync(outgoing.fileno())
    os.replace(temporary, destination)
    fsync_directory(destination.parent)


def write_jsonl_gz(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    count = 0
    with temporary.open("wb") as raw_output:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_output, mtime=0) as compressed:
            for row in rows:
                compressed.write(canonical_json(row) + b"\n")
                count += 1
        raw_output.flush()
        os.fsync(raw_output.fileno())
    os.replace(temporary, path)
    return count


def read_json(path: Path, gate: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise PromotionError(gate, f"cannot read {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise PromotionError(gate, f"{path.name} must contain one JSON object")
    return value


def iter_jsonl(path: Path, gate: str) -> Iterator[tuple[int, dict[str, Any]]]:
    try:
        with path.open(encoding="utf-8", errors="strict") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise PromotionError(
                        gate,
                        f"{path.name} line {line_number} is not valid JSON",
                    ) from exc
                if not isinstance(row, dict):
                    raise PromotionError(gate, f"{path.name} line {line_number} is not an object")
                yield line_number, row
    except OSError as exc:
        raise PromotionError(gate, f"cannot read {path.name}: {exc}") from exc


def require_regular_file(path: Path, gate: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise PromotionError(gate, f"required regular file is missing: {path}")


def safe_repo_file(repo_root: Path, relative: Any, gate: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise PromotionError(gate, "run metadata does not name a required repository file")
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise PromotionError(gate, f"unsafe repository-relative path: {relative!r}")
    cursor = repo_root
    for part in raw.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise PromotionError(gate, f"symlinked contract path is not allowed: {relative}")
    resolved = cursor.resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise PromotionError(gate, f"contract path escapes repository root: {relative}") from exc
    require_regular_file(resolved, gate)
    return resolved


def safe_run_file(run_dir: Path, relative: Path, gate: str) -> Path:
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise PromotionError(gate, f"unsafe run-relative path: {relative}")
    cursor = run_dir
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise PromotionError(gate, f"symlinked run evidence path is not allowed: {relative}")
    resolved = cursor.resolve()
    try:
        resolved.relative_to(run_dir.resolve())
    except ValueError as exc:
        raise PromotionError(gate, f"run evidence path escapes the run directory: {relative}") from exc
    require_regular_file(resolved, gate)
    return resolved


def safe_run_glob(run_dir: Path, pattern: str, gate: str) -> tuple[Path, ...]:
    return tuple(
        safe_run_file(run_dir, candidate.relative_to(run_dir), gate)
        for candidate in sorted(run_dir.glob(pattern), key=lambda path: path.name)
    )


def parse_judge_specs(values: Iterable[str]) -> tuple[JudgeSpec, ...]:
    parsed = set()
    for value in values:
        backend, separator, model = value.partition(":")
        if not separator or not backend.strip() or not model.strip():
            raise PromotionError("P4", f"invalid judge identity {value!r}; expected backend:model")
        parsed.add((backend.strip(), model.strip()))
    if not parsed:
        raise PromotionError("P4", "at least one --judge backend:model is required")
    return tuple(JudgeSpec(*identity) for identity in sorted(parsed))


def evaluation_policy_for(judges: Iterable[JudgeSpec]) -> str:
    rows = [
        {"judge_backend": judge.backend, "judge_model": judge.model}
        for judge in judges
    ]
    return analysis_metrics.evaluation_policy_id(rows)


def parse_roster(path: Path) -> list[str]:
    models = [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not models or len(models) != len(set(models)):
        raise PromotionError("P2", "roster must contain unique model identifiers")
    return models


def parse_scenarios(path: Path) -> list[str]:
    payload = read_json(path, "P2")
    rows = payload.get("scenarios")
    if not isinstance(rows, list):
        raise PromotionError("P2", "scenario file must contain a scenarios array")
    identifiers = [row.get("id") for row in rows if isinstance(row, dict)]
    if not identifiers or any(not isinstance(value, str) or not value for value in identifiers):
        raise PromotionError("P2", "every scenario must have a non-empty id")
    if len(identifiers) != len(set(identifiers)):
        raise PromotionError("P2", "scenario identifiers must be unique")
    return identifiers


def file_lines(path: Path, gate: str) -> list[str]:
    require_regular_file(path, gate)
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def build_context(
    *,
    repo_root: Path,
    run_dir: Path,
    output_root: Path,
    judge_values: Iterable[str],
) -> PromotionContext:
    repo_root = repo_root.resolve()
    if run_dir.is_symlink():
        raise PromotionError("P0", f"symlinked run directory is not allowed: {run_dir}")
    run_dir = run_dir.resolve()
    output_root = output_root.resolve()
    if run_dir.is_symlink() or not run_dir.is_dir():
        raise PromotionError("P0", f"run directory is missing or symlinked: {run_dir}")
    judges = parse_judge_specs(judge_values)
    meta_path = run_dir / "run.meta"
    require_regular_file(meta_path, "P2")
    meta = read_json(meta_path, "P2")
    run_id = str(meta.get("run_id") or run_dir.name)
    if run_id != run_dir.name:
        raise PromotionError("P2", f"run.meta run_id {run_id!r} does not match directory name")
    roster = safe_repo_file(repo_root, meta.get("models"), "P2")
    scenarios = safe_repo_file(repo_root, meta.get("scenarios"), "P2")
    inputs = RunInputs(
        run_dir=run_dir,
        run_id=run_id,
        meta=meta_path,
        results=safe_run_file(run_dir, Path("_mirror") / f"results.{run_id}.jsonl", "P0"),
        done=safe_run_file(run_dir, Path("_mirror") / f"results.{run_id}.jsonl.done", "P0"),
        judged=safe_run_file(run_dir, Path(f"judged.{run_id}.jsonl"), "P0"),
        pipeline_ledger=safe_run_file(run_dir, Path("pipeline-ledger.jsonl"), "P0"),
        committed=safe_run_file(run_dir, Path(".committed"), "P0"),
        push_pending=safe_run_file(run_dir, Path(".push-pending"), "P0"),
        roster=roster,
        scenarios=scenarios,
        result_archives=safe_run_glob(run_dir, "*.results.jsonl.gz", "P0"),
        candidate_archives=safe_run_glob(run_dir, "*.candidates.tar.gz", "P0"),
        logs=safe_run_glob(run_dir, "*.log", "P0"),
    )
    for path in inputs.hash_sources().values():
        require_regular_file(path, "P0")
    return PromotionContext(
        repo_root=repo_root,
        run_dir=run_dir,
        output_root=output_root,
        judges=judges,
        evaluation_policy=evaluation_policy_for(judges),
        inputs=inputs,
        meta=meta,
    )


@contextlib.contextmanager
def promotion_lock(context: PromotionContext):
    context.state_dir.mkdir(parents=True, exist_ok=True)
    lock_path = context.state_dir / "promotion.lock"
    with lock_path.open("a+b") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise PromotionError("P0", "another promotion process holds this run lock") from exc
        yield


def record_event(
    context: PromotionContext,
    stage: str,
    ok: bool,
    detail: Mapping[str, Any] | None = None,
    *,
    input_sha256: str | None = None,
    output_sha256: str | None = None,
) -> None:
    append_jsonl(
        context.ledger_path,
        {
            "detail": dict(detail or {}),
            "ok": ok,
            "input_sha256": input_sha256,
            "output_sha256": output_sha256,
            "run_id": context.inputs.run_id,
            "stage": stage,
            "tool_version": TOOL_VERSION,
            "ts": utc_now(),
        },
    )


def set_error_stage(error: PromotionError, stage: str) -> PromotionError:
    if error.stage is None:
        error.stage = stage
    return error


def source_hashes(inputs: RunInputs) -> dict[str, str]:
    for pattern, expected in (
        ("*.results.jsonl.gz", inputs.result_archives),
        ("*.candidates.tar.gz", inputs.candidate_archives),
        ("*.log", inputs.logs),
    ):
        actual = safe_run_glob(inputs.run_dir, pattern, "P7")
        if tuple(path.name for path in actual) != tuple(path.name for path in expected):
            raise PromotionError(
                "P7",
                "run sidecar inventory changed after promotion intake",
                details={
                    "actual": [path.name for path in actual],
                    "expected": [path.name for path in expected],
                    "pattern": pattern,
                },
            )
    return {
        name: sha256_file(path)
        for name, path in sorted(inputs.hash_sources().items())
    }


def validate_terminal_state(context: PromotionContext, roster: list[str]) -> dict[str, Any]:
    for marker in (".paused", ".canceled"):
        if (context.run_dir / marker).exists():
            raise PromotionError("P1", f"run is blocked by {marker}", exit_code=EXIT_INCOMPLETE)
    pending = file_lines(context.inputs.push_pending, "P1")
    if pending:
        raise PromotionError(
            "P1",
            f"run has {len(pending)} pending persistence pushes",
            details={"pending_models": sorted(pending)},
            exit_code=EXIT_INCOMPLETE,
        )
    committed = file_lines(context.inputs.committed, "P5")
    committed_set = set(committed)
    missing = sorted(set(roster) - committed_set)
    extra = sorted(committed_set - set(roster))
    duplicates = duplicate_values(committed)
    if missing or extra or duplicates:
        raise PromotionError(
            "P5",
            "committed-model set does not exactly match the roster",
            details={
                "duplicate_models": duplicates,
                "extra_models": extra,
                "missing_models": missing,
            },
            exit_code=EXIT_INCOMPLETE,
        )
    return {"committed_models": len(committed), "push_pending": 0}


def validate_metadata(
    context: PromotionContext,
    roster: list[str],
    scenarios: list[str],
) -> tuple[int, int]:
    meta = context.meta
    roster_sha = sha256_file(context.inputs.roster)
    if roster_sha != meta.get("models_sha256"):
        raise PromotionError(
            "P2",
            "roster SHA-256 does not match run.meta",
            details={"actual": roster_sha, "expected": meta.get("models_sha256")},
        )
    scenario_sha = sha256_file(context.inputs.scenarios)
    if scenario_sha != meta.get("scenarios_sha256"):
        raise PromotionError(
            "P2",
            "scenario SHA-256 does not match run.meta",
            details={"actual": scenario_sha, "expected": meta.get("scenarios_sha256")},
        )
    models_count = int(meta.get("models_count") or meta.get("expect") or 0)
    scenario_count = int(meta.get("scenario_count") or 0)
    reps = int(meta.get("reps") or meta.get("run_repeats_override") or 0)
    try:
        judge_count = analysis_metrics.metadata_judge_count(meta)
    except ValueError as exc:
        raise PromotionError(
            "P2",
            "run.meta judge count is malformed",
            details={"error": str(exc)},
        ) from exc
    if models_count != len(roster) or int(meta.get("expect") or 0) != len(roster):
        raise PromotionError(
            "P2",
            "run.meta model counts do not match the roster",
            details={
                "models_count": models_count,
                "expect": int(meta.get("expect") or 0),
                "roster_count": len(roster),
            },
        )
    if scenario_count != len(scenarios):
        raise PromotionError(
            "P2",
            "run.meta scenario count does not match the scenario file",
            details={"actual": scenario_count, "expected": len(scenarios)},
        )
    if meta.get("scenario_ids") != scenarios:
        metadata_scenarios = meta.get("scenario_ids") or []
        raise PromotionError(
            "P2",
            "run.meta scenario ordering does not match the scenario file",
            details={
                "actual_order": metadata_scenarios,
                "expected_order": scenarios,
                "extra_scenarios": sorted(set(metadata_scenarios) - set(scenarios)),
                "missing_scenarios": sorted(set(scenarios) - set(metadata_scenarios)),
            },
        )
    if reps <= 0:
        raise PromotionError("P2", "run.meta repetitions must be positive")
    if judge_count != len(context.judges):
        raise PromotionError(
            "P2",
            "run.meta judge count does not match requested judge identities",
            details={
                "actual": judge_count,
                "expected": len(context.judges),
                "requested_judges": [f"{judge.backend}:{judge.model}" for judge in context.judges],
            },
        )
    try:
        authoritative = analysis_metrics.metadata_judge_identities(meta)
    except ValueError as exc:
        raise PromotionError(
            "P2",
            "run.meta judge identity declaration is malformed",
            details={"error": str(exc)},
        ) from exc
    if authoritative is not None:
        requested = {judge.identity for judge in context.judges}
        if authoritative != requested:
            raise PromotionError(
                "P2",
                "requested judge identities differ from authoritative run.meta",
                details={
                    "authoritative_judges": [
                        f"{backend}:{model}" for backend, model in sorted(authoritative)
                    ],
                    "requested_judges": [
                        f"{backend}:{model}" for backend, model in sorted(requested)
                    ],
                },
            )
    return reps, len(roster) * len(scenarios) * reps


def normalized_rep(value: Any, *, gate: str) -> int:
    if isinstance(value, bool):
        raise PromotionError(gate, "repetition must be an integer")
    try:
        rep = int(value)
    except (TypeError, ValueError) as exc:
        raise PromotionError(gate, "repetition must be an integer") from exc
    if str(value) not in {str(rep), f"{rep}.0"} and not isinstance(value, int):
        raise PromotionError(gate, f"invalid repetition value: {value!r}")
    return rep


def normalize_results(
    context: PromotionContext,
    destination: Path,
    roster: list[str],
    scenarios: list[str],
    reps: int,
    expected_results: int,
) -> tuple[
    dict[tuple[Any, ...], tuple[str, dict[str, str]]],
    list[tuple[tuple[str, str, int], str]],
    dict[str, Any],
]:
    roster_index = {model: index for index, model in enumerate(roster)}
    scenario_index = {scenario: index for index, scenario in enumerate(scenarios)}
    seen: set[tuple[str, str, int]] = set()
    legacy_index: dict[tuple[Any, ...], tuple[str, dict[str, str]]] = {}
    legacy_result_keys: dict[tuple[Any, ...], tuple[str, str, int]] = {}
    ordered_keys: list[tuple[tuple[str, str, int], str]] = []
    model_conditions: defaultdict[str, set[str]] = defaultdict(set)
    duplicate_keys: set[tuple[str, str, int]] = set()
    extra_keys: set[tuple[str, str, int]] = set()
    malformed_results: list[dict[str, Any]] = []
    incomplete_rows: list[dict[str, Any]] = []
    invalid_repetitions: list[dict[str, Any]] = []
    legacy_collisions: list[dict[str, Any]] = []
    stored_condition_conflicts: list[dict[str, Any]] = []
    stored_policy_conflicts: list[dict[str, Any]] = []
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("wb") as raw_output:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw_output, mtime=0) as compressed:
                for line_number, source in iter_jsonl(context.inputs.results, "P3"):
                    missing_fields = [
                        field
                        for field in ("model", "scenario", "rep")
                        if source.get(field) is None or source.get(field) == ""
                    ]
                    if source.get("fatal") or missing_fields:
                        malformed_results.append({
                            "fatal": bool(source.get("fatal")),
                            "line": line_number,
                            "missing_fields": missing_fields,
                            "model": source.get("model"),
                            "scenario": source.get("scenario"),
                            "rep": source.get("rep"),
                        })
                        continue
                    row = copy.deepcopy(source)
                    model = str(row.get("model") or "")
                    scenario = str(row.get("scenario") or "")
                    try:
                        rep = normalized_rep(row.get("rep"), gate="P3")
                    except PromotionError:
                        invalid_repetitions.append({
                            "line": line_number,
                            "model": model,
                            "scenario": scenario,
                            "value": row.get("rep"),
                        })
                        continue
                    if model not in roster_index or scenario not in scenario_index or not 0 <= rep < reps:
                        extra_keys.add((model, scenario, rep))
                        continue
                    key = (model, scenario, rep)
                    if key in seen:
                        duplicate_keys.add(key)
                        continue
                    seen.add(key)
                    row["rep"] = rep
                    row = analysis_metrics.normalize_condition_provenance(row)
                    identity = analysis_metrics.analysis_condition(
                        row,
                        evaluation_policy=context.evaluation_policy,
                    )
                    if identity.incomplete:
                        incomplete_rows.append({
                            "model": model,
                            "scenario": scenario,
                            "rep": rep,
                            "missing_fields": list(identity.missing_fields),
                        })
                        continue
                    existing_condition = row.get("analysis_condition_key_sha256")
                    if existing_condition and existing_condition != identity.sha256:
                        stored_condition_conflicts.append({
                            **result_key_details([key])[0],
                            "actual": existing_condition,
                            "expected": identity.sha256,
                        })
                        continue
                    existing_policy = row.get("evaluation_policy")
                    if existing_policy and existing_policy != context.evaluation_policy:
                        stored_policy_conflicts.append({
                            **result_key_details([key])[0],
                            "actual": existing_policy,
                            "expected": context.evaluation_policy,
                        })
                        continue
                    row.update({
                        "analysis_schema_version": analysis_metrics.ANALYSIS_SCHEMA_VERSION,
                        "analysis_condition_key_sha256": identity.sha256,
                        "condition_identity_incomplete": False,
                        "evaluation_policy": context.evaluation_policy,
                    })
                    legacy_key = analysis_metrics.legacy_judge_join_key(row)
                    if legacy_key in legacy_index:
                        legacy_collisions.append({
                            "first": result_key_details([legacy_result_keys[legacy_key]])[0],
                            "second": result_key_details([key])[0],
                        })
                        continue
                    legacy_index[legacy_key] = (
                        identity.sha256,
                        {
                            "inference_runtime": str(row.get("env.inference_runtime") or row.get("adapter") or "ollama"),
                            "memory_context": str(row.get("env.memory_context") or "none"),
                            "inference_strategy": str(row.get("env.inference_strategy") or "baseline"),
                        },
                    )
                    legacy_result_keys[legacy_key] = key
                    model_conditions[model].add(identity.sha256)
                    ordered_keys.append((key, identity.sha256))
                    compressed.write(canonical_json(row) + b"\n")
            raw_output.flush()
            os.fsync(raw_output.fileno())
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    expected_keys = {
        (model, scenario, rep)
        for model in roster
        for scenario in scenarios
        for rep in range(reps)
    }
    missing_keys = expected_keys - seen
    if (
        missing_keys
        or extra_keys
        or duplicate_keys
        or malformed_results
        or incomplete_rows
        or invalid_repetitions
        or legacy_collisions
        or stored_condition_conflicts
        or stored_policy_conflicts
    ):
        raise PromotionError(
            "P3",
            "result validation found incomplete, extra, duplicate, or conflicting units",
            details={
                "actual_count": len(seen),
                "duplicate_results": result_key_details(duplicate_keys),
                "expected_count": expected_results,
                "extra_results": result_key_details(extra_keys),
                "incomplete_results": incomplete_rows,
                "invalid_repetitions": invalid_repetitions,
                "legacy_join_collisions": legacy_collisions,
                "malformed_results": malformed_results,
                "missing_results": result_key_details(missing_keys),
                "stored_condition_conflicts": stored_condition_conflicts,
                "stored_policy_conflicts": stored_policy_conflicts,
            },
            exit_code=EXIT_INCOMPLETE,
        )
    split_conditions = {
        model: sorted(values)
        for model, values in model_conditions.items()
        if len(values) != 1
    }
    if split_conditions:
        raise PromotionError(
            "P6",
            "one or more models span multiple deployment conditions",
            details={"model_conditions": split_conditions},
        )
    ordered_keys.sort(key=lambda item: (
        roster_index[item[0][0]],
        scenario_index[item[0][1]],
        item[0][2],
    ))
    os.replace(temporary, destination)
    written = len(seen)
    return legacy_index, ordered_keys, {
        "conditions": len({condition for _key, condition in ordered_keys}),
        "results": written,
    }


def retry_reason(row: Mapping[str, Any]) -> str:
    if row.get("score") is None and (
        row.get("evidence") == "parse_error"
        or "judge response could not be parsed" in (row.get("criteria_missed") or [])
    ):
        return "parse_error"
    if row.get("score") is None:
        return "no_score"
    return "invalid_contract"


def normalize_judgements(
    context: PromotionContext,
    destination: Path,
    retry_destination: Path,
    legacy_index: Mapping[tuple[Any, ...], tuple[str, dict[str, str]]],
    ordered_results: list[tuple[tuple[str, str, int], str]],
) -> dict[str, Any]:
    expected_judges = {judge.identity for judge in context.judges}
    expected_keys = {
        (condition_sha, scenario, rep, judge.backend, judge.model)
        for (_model, scenario, rep), condition_sha in ordered_results
        for judge in context.judges
    }
    attempt_lines: defaultdict[tuple[str, str, int, str, str], list[int]] = defaultdict(list)
    competing_successes: defaultdict[tuple[str, str, int, str, str], list[int]] = defaultdict(list)
    condition_conflicts: list[dict[str, Any]] = []
    extra_judgement_keys: set[tuple[str, str, int, str, str]] = set()
    invalid_repetitions: list[dict[str, Any]] = []
    policy_conflicts: list[dict[str, Any]] = []
    undeclared_judges: list[dict[str, Any]] = []
    unresolved_attempts: list[dict[str, Any]] = []
    successes: dict[tuple[str, str, int, str, str], dict[str, Any]] = {}
    raw_attempts = 0
    retry_destination.parent.mkdir(parents=True, exist_ok=True)
    retry_temporary = retry_destination.with_name(f".{retry_destination.name}.{os.getpid()}.tmp")
    retry_count = 0
    try:
        with retry_temporary.open("wb") as raw_output:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw_output, mtime=0) as compressed:
                for line_number, source in iter_jsonl(context.inputs.judged, "P4"):
                    raw_attempts += 1
                    row = copy.deepcopy(source)
                    try:
                        rep = normalized_rep(row.get("rep"), gate="P4")
                    except PromotionError:
                        invalid_repetitions.append({
                            "line": line_number,
                            "model": row.get("model"),
                            "scenario": row.get("scenario"),
                            "value": row.get("rep"),
                        })
                        continue
                    row["rep"] = rep
                    legacy_key = analysis_metrics.legacy_judge_join_key(row)
                    resolved = legacy_index.get(legacy_key)
                    if resolved is None:
                        unresolved_attempts.append({
                            "line": line_number,
                            "model": row.get("model"),
                            "scenario": row.get("scenario"),
                            "rep": rep,
                        })
                        continue
                    condition_sha, result_identity = resolved
                    existing_condition = row.get("analysis_condition_key_sha256")
                    if existing_condition and existing_condition != condition_sha:
                        condition_conflicts.append({
                            "actual": existing_condition,
                            "expected": condition_sha,
                            "source_line": line_number,
                        })
                        continue
                    existing_policy = row.get("evaluation_policy")
                    if existing_policy and existing_policy != context.evaluation_policy:
                        policy_conflicts.append({
                            "actual": existing_policy,
                            "expected": context.evaluation_policy,
                            "source_line": line_number,
                        })
                        continue
                    judge_identity = analysis_metrics.judge_identity(row)
                    if judge_identity not in expected_judges:
                        undeclared_judges.append({
                            "judge_backend": judge_identity[0],
                            "judge_model": judge_identity[1],
                            "source_line": line_number,
                        })
                        continue
                    row.update({
                        "analysis_schema_version": analysis_metrics.ANALYSIS_SCHEMA_VERSION,
                        "analysis_condition_key_sha256": condition_sha,
                        "condition_identity_incomplete": False,
                        "evaluation_policy": context.evaluation_policy,
                        "inference_runtime": result_identity["inference_runtime"],
                        "memory_context": result_identity["memory_context"],
                        "inference_strategy": result_identity["inference_strategy"],
                        "promotion.source_line": line_number,
                    })
                    key = (
                        condition_sha,
                        str(row.get("scenario")),
                        rep,
                        judge_identity[0],
                        judge_identity[1],
                    )
                    if key not in expected_keys:
                        extra_judgement_keys.add(key)
                        continue
                    attempt_lines[key].append(line_number)
                    if analysis_metrics.judgement_success(row):
                        if key in successes:
                            if not competing_successes[key]:
                                competing_successes[key].append(
                                    int(successes[key]["promotion.source_line"])
                                )
                            competing_successes[key].append(line_number)
                            continue
                        successes[key] = row
                    else:
                        row["promotion.retry_reason"] = retry_reason(row)
                        compressed.write(canonical_json(row) + b"\n")
                        retry_count += 1
            raw_output.flush()
            os.fsync(raw_output.fileno())
    except Exception:
        retry_temporary.unlink(missing_ok=True)
        raise

    missing_attempts = expected_keys - set(attempt_lines)
    missing_successes = expected_keys - set(successes)
    if (
        missing_attempts
        or missing_successes
        or competing_successes
        or condition_conflicts
        or extra_judgement_keys
        or invalid_repetitions
        or policy_conflicts
        or undeclared_judges
        or unresolved_attempts
    ):
        retry_temporary.unlink(missing_ok=True)
        raise PromotionError(
            "P4",
            "judgement validation found missing, extra, ambiguous, or conflicting attempts",
            details={
                "competing_successes": [
                    {
                        "judge_key": judge_key_details([key])[0],
                        "successful_source_lines": sorted(lines),
                    }
                    for key, lines in sorted(competing_successes.items())
                ],
                "condition_conflicts": condition_conflicts,
                "extra_judgements": judge_key_details(extra_judgement_keys),
                "invalid_repetitions": invalid_repetitions,
                "missing_attempts": judge_key_details(missing_attempts),
                "missing_successes": judge_key_details(missing_successes),
                "policy_conflicts": policy_conflicts,
                "source_lines_without_success": {
                    digest_mapping(judge_key_details([key])[0]): sorted(attempt_lines[key])
                    for key in sorted(missing_successes & set(attempt_lines))
                },
                "undeclared_judges": undeclared_judges,
                "unresolved_attempts": unresolved_attempts,
            },
            exit_code=EXIT_INCOMPLETE,
        )
    os.replace(retry_temporary, retry_destination)
    canonical_rows = [successes[key] for key in sorted(successes)]
    canonical_rows.sort(key=lambda row: (
        row["analysis_condition_key_sha256"],
        row["scenario"],
        int(row["rep"]),
        row.get("judge_backend") or "unknown",
        row.get("judge_model") or "unknown",
    ))
    canonical_count = write_jsonl_gz(destination, canonical_rows)
    if canonical_count + retry_count != raw_attempts:
        raise PromotionError("P7", "canonical and retry rows do not reconcile to raw attempts")
    return {
        "canonical_judgements": canonical_count,
        "judge_retries": retry_count,
        "raw_judge_attempts": raw_attempts,
    }


def validate_done_file(
    context: PromotionContext,
    roster: list[str],
    expected_units: int,
) -> dict[str, Any]:
    rows = [row for _line, row in iter_jsonl(context.inputs.done, "P5")]
    models = [row.get("model") for row in rows]
    model_set = set(models)
    missing = sorted(set(roster) - model_set)
    extra = sorted(model_set - set(roster))
    duplicates = duplicate_values(str(model) for model in models)
    if missing or extra or duplicates:
        raise PromotionError(
            "P5",
            "completed-model marker does not exactly match the roster",
            details={
                "duplicate_models": duplicates,
                "extra_models": extra,
                "missing_models": missing,
            },
            exit_code=EXIT_INCOMPLETE,
        )
    unit_mismatches = [
        {"actual_units": int(row.get("units") or 0), "expected_units": expected_units, "model": row.get("model")}
        for row in rows
        if int(row.get("units") or 0) != expected_units
    ]
    if unit_mismatches:
        raise PromotionError(
            "P5",
            "completed-model marker has unexpected unit counts",
            details={"unit_mismatches": unit_mismatches},
        )
    return {"done_models": len(models), "units_per_model": expected_units}


def validate_pipeline_ledger(context: PromotionContext) -> dict[str, Any]:
    rows = sum(1 for _line, _row in iter_jsonl(context.inputs.pipeline_ledger, "P5"))
    if rows == 0:
        raise PromotionError("P5", "pipeline ledger is empty")
    return {"pipeline_ledger_rows": rows}


def validate_sidecar_inventory(
    context: PromotionContext,
    roster: list[str],
) -> dict[str, Any]:
    incomplete: dict[str, Any] = {}
    slugs = [model.replace("/", "_").replace(":", "_") for model in roster]
    collisions = duplicate_values(slugs)
    if (context.inputs.candidate_archives or context.inputs.result_archives) and collisions:
        incomplete["filename_collisions"] = collisions
    for name, suffix, paths in (
        ("candidate_archives", ".candidates.tar.gz", context.inputs.candidate_archives),
        ("result_archives", ".results.jsonl.gz", context.inputs.result_archives),
    ):
        if not paths:
            continue
        expected = {f"{slug}{suffix}" for slug in slugs}
        actual = {path.name for path in paths}
        if actual != expected:
            incomplete[name] = {
                "extra": sorted(actual - expected),
                "missing": sorted(expected - actual),
            }
    if incomplete:
        raise PromotionError(
            "P5",
            "per-model sidecar inventory is incomplete",
            details=incomplete,
            exit_code=EXIT_INCOMPLETE,
        )
    return {
        "candidate_archives": len(context.inputs.candidate_archives),
        "log_files": len(context.inputs.logs),
        "result_archives": len(context.inputs.result_archives),
    }


def copy_raw_evidence(context: PromotionContext, stage: Path) -> None:
    raw = stage / "raw"
    contract = stage / "contract"
    raw.mkdir(parents=True, exist_ok=True)
    contract.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(raw / "run.meta", context.inputs.meta.read_bytes())
    deterministic_gzip_from_file(context.inputs.results, raw / "results.jsonl.gz")
    atomic_write_bytes(raw / "results.done", context.inputs.done.read_bytes())
    deterministic_gzip_from_file(context.inputs.judged, raw / "judged.attempts.jsonl.gz")
    atomic_write_bytes(raw / "pipeline-ledger.jsonl", context.inputs.pipeline_ledger.read_bytes())
    atomic_write_bytes(raw / "committed-models.txt", context.inputs.committed.read_bytes())
    atomic_write_bytes(raw / "push-pending.txt", context.inputs.push_pending.read_bytes())
    atomic_write_bytes(contract / "roster.txt", context.inputs.roster.read_bytes())
    atomic_write_bytes(contract / "scenarios.json", context.inputs.scenarios.read_bytes())
    for relative, source in context.inputs.sidecar_sources().items():
        atomic_copy_file(source, stage / relative)


def build_stage(context: PromotionContext) -> dict[str, Any]:
    try:
        roster = parse_roster(context.inputs.roster)
        scenarios = parse_scenarios(context.inputs.scenarios)
        terminal = validate_terminal_state(context, roster)
        reps, expected_results = validate_metadata(context, roster, scenarios)
        expected_judgements = expected_results * len(context.judges)
        done = validate_done_file(context, roster, len(scenarios) * reps)
        pipeline = validate_pipeline_ledger(context)
        sidecars = validate_sidecar_inventory(context, roster)
        before_hashes = source_hashes(context.inputs)
        input_digest = digest_mapping(before_hashes)
        record_event(context, "normalize_started", True, input_sha256=input_digest)

        temporary = context.stage_dir.with_name(f"{context.inputs.run_id}.{os.getpid()}.tmp")
        for stale in context.stage_dir.parent.glob(f"{context.inputs.run_id}.*.tmp"):
            if stale.is_symlink():
                raise PromotionError("P0", f"symlinked staging path is not allowed: {stale}")
            if stale.is_dir():
                shutil.rmtree(stale)
            elif stale.exists():
                raise PromotionError("P0", f"non-directory staging path is not allowed: {stale}")
        temporary.mkdir(parents=True, exist_ok=False)
        copy_raw_evidence(context, temporary)
        legacy_index, ordered_results, result_counts = normalize_results(
            context,
            temporary / "canonical" / "results.jsonl.gz",
            roster,
            scenarios,
            reps,
            expected_results,
        )
        judgement_counts = normalize_judgements(
            context,
            temporary / "canonical" / "judged.jsonl.gz",
            temporary / "canonical" / "judge-retries.jsonl.gz",
            legacy_index,
            ordered_results,
        )
        if judgement_counts["canonical_judgements"] != expected_judgements:
            raise PromotionError(
                "P4",
                "canonical judgement count does not match the requested ensemble",
                exit_code=EXIT_INCOMPLETE,
            )
        observed = {
            **terminal,
            **done,
            **pipeline,
            **sidecars,
            **result_counts,
            **judgement_counts,
        }
        expected = {
            "models": len(roster),
            "results": expected_results,
            "canonical_judgements": expected_judgements,
            "judges": len(context.judges),
            "scenarios": len(scenarios),
            "reps": reps,
        }
        gate_report = {
            "analysis_schema_version": analysis_metrics.ANALYSIS_SCHEMA_VERSION,
            "evaluation_policy": context.evaluation_policy,
            "expected": expected,
            "observed": observed,
            "passed": True,
            "run_id": context.inputs.run_id,
            "tool_version": TOOL_VERSION,
        }
        atomic_write_json(temporary / "gate-report.json", gate_report)
        atomic_write_json(
            temporary / "normalization-metadata.json",
            {
                "evaluation_policy": context.evaluation_policy,
                "run_id": context.inputs.run_id,
                "source_sha256": before_hashes,
                "tool_version": TOOL_VERSION,
            },
        )
        context.stage_dir.parent.mkdir(parents=True, exist_ok=True)
        if context.stage_dir.exists():
            shutil.rmtree(context.stage_dir)
        os.replace(temporary, context.stage_dir)
        fsync_directory(context.stage_dir.parent)
        output_digest = digest_mapping(payload_hashes(context.stage_dir))
        record_event(
            context,
            "normalize_passed",
            True,
            {"results": expected_results},
            input_sha256=input_digest,
            output_sha256=output_digest,
        )
        return gate_report
    except PromotionError as exc:
        if "temporary" in locals():
            shutil.rmtree(temporary, ignore_errors=True)
        raise set_error_stage(exc, "normalize")
    except Exception:
        if "temporary" in locals():
            shutil.rmtree(temporary, ignore_errors=True)
        raise


def safe_bundle_relative(relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise PromotionError("P0", f"unsafe bundle-relative path: {relative!r}")
    return path


def require_bundle_file(bundle: Path, relative: str) -> Path:
    safe_relative = safe_bundle_relative(relative)
    cursor = bundle
    for part in safe_relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise PromotionError("P0", f"symlink is not allowed in bundle path: {relative}")
    require_regular_file(cursor, "P7")
    return cursor


def require_unchanged_sources(
    context: PromotionContext,
    expected_hashes: Mapping[str, Any],
) -> dict[str, str]:
    if not isinstance(expected_hashes, dict):
        raise PromotionError("P7", "normalized source hash map is invalid")
    current_hashes = source_hashes(context.inputs)
    if current_hashes != expected_hashes:
        changed = sorted(
            name
            for name in set(current_hashes) | set(expected_hashes)
            if current_hashes.get(name) != expected_hashes.get(name)
        )
        raise PromotionError(
            "P7",
            "source evidence changed after normalization",
            details={"changed_sources": changed},
        )
    return current_hashes


def validate_stage(context: PromotionContext) -> dict[str, Any]:
    try:
        stage = context.stage_dir
        if stage.is_symlink() or not stage.is_dir():
            raise PromotionError("P7", "normalized staging directory does not exist")
        metadata = read_json(stage / "normalization-metadata.json", "P7")
        input_digest = digest_mapping(metadata.get("source_sha256") or {})
        record_event(context, "validate_started", True, input_sha256=input_digest)
        gate_report = read_json(stage / "gate-report.json", "P7")
        if gate_report.get("passed") is not True:
            raise PromotionError("P7", "staged gate report is not PASS")
        if metadata.get("evaluation_policy") != context.evaluation_policy:
            raise PromotionError("P7", "staged evaluation policy differs from this invocation")
        require_unchanged_sources(context, metadata.get("source_sha256") or {})
        for relative in (
            "contract/roster.txt",
            "contract/scenarios.json",
            "raw/run.meta",
            "raw/results.jsonl.gz",
            "raw/results.done",
            "raw/judged.attempts.jsonl.gz",
            "raw/pipeline-ledger.jsonl",
            "raw/committed-models.txt",
            "raw/push-pending.txt",
            "canonical/results.jsonl.gz",
            "canonical/judged.jsonl.gz",
            "canonical/judge-retries.jsonl.gz",
        ):
            require_bundle_file(stage, relative)
        for relative in context.inputs.sidecar_sources():
            require_bundle_file(stage, relative)
        output_digest = sha256_file(stage / "gate-report.json")
        record_event(
            context,
            "validate_passed",
            True,
            gate_report.get("observed"),
            input_sha256=input_digest,
            output_sha256=output_digest,
        )
        return gate_report
    except PromotionError as exc:
        raise set_error_stage(exc, "validate")


def bundle_tree_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise PromotionError(
                "P0",
                f"symlink is not allowed in bundle: {path}",
                exit_code=EXIT_BOUNDARY,
            )
        if path.is_dir():
            continue
        if not path.is_file():
            raise PromotionError(
                "P0",
                f"unsupported filesystem entry in bundle: {path}",
                exit_code=EXIT_BOUNDARY,
            )
        files.append(path)
    return files


def payload_hashes(stage: Path) -> dict[str, str]:
    hashes = {}
    for path in bundle_tree_files(stage):
        if path.name in {"bundle-manifest.json", "promotion-ledger.jsonl"}:
            continue
        relative = path.relative_to(stage).as_posix()
        hashes[relative] = sha256_file(path)
    return hashes


def verify_bundle(bundle: Path) -> dict[str, Any]:
    if bundle.is_symlink():
        raise PromotionError("P7", f"symlinked bundle is not allowed: {bundle}", exit_code=EXIT_BOUNDARY)
    bundle = bundle.resolve()
    if not bundle.is_dir():
        raise PromotionError("P7", f"bundle does not exist: {bundle}", exit_code=EXIT_BOUNDARY)
    manifest = read_json(bundle / "bundle-manifest.json", "P7")
    errors = analysis_metrics.validate_analysis_manifest(manifest, claim_bearing=False)
    if errors:
        raise PromotionError("P7", "; ".join(errors))
    if manifest.get("source_kind") != "completed_run" or manifest.get("bundle_state") != "locked":
        raise PromotionError("P7", "bundle is not a locked completed_run source")
    expected_hashes = manifest.get("source_sha256")
    if not isinstance(expected_hashes, dict) or not expected_hashes:
        raise PromotionError("P7", "bundle source_sha256 map is empty")
    for relative, expected in expected_hashes.items():
        path = require_bundle_file(bundle, relative)
        if sha256_file(path) != expected:
            raise PromotionError("P7", f"bundle hash mismatch: {relative}")
    actual_files = {
        path.relative_to(bundle).as_posix()
        for path in bundle_tree_files(bundle)
    }
    allowed_files = set(expected_hashes) | {"bundle-manifest.json", "promotion-ledger.jsonl"}
    if actual_files != allowed_files:
        raise PromotionError("P7", "bundle contains missing or unlisted files")
    bundle_id = sha256_bytes(canonical_json(expected_hashes))
    if manifest.get("bundle_id") != bundle_id:
        raise PromotionError("P7", "bundle ID does not match its source hash map")
    gate_report = read_json(bundle / "gate-report.json", "P7")
    if gate_report.get("passed") is not True:
        raise PromotionError("P7", "locked bundle has a non-passing gate report")
    return manifest


def lock_stage(
    context: PromotionContext,
    gate_report: Mapping[str, Any] | None = None,
) -> tuple[Path, dict[str, Any]]:
    try:
        gate_report = dict(gate_report or validate_stage(context))
        stage_digest = digest_mapping(payload_hashes(context.stage_dir))
        record_event(context, "lock_started", True, input_sha256=stage_digest)
        atomic_write_bytes(context.stage_dir / "promotion-ledger.jsonl", context.ledger_path.read_bytes())
        hashes = payload_hashes(context.stage_dir)
        bundle_id = sha256_bytes(canonical_json(hashes))
        manifest = {
        "analysis_schema_version": analysis_metrics.ANALYSIS_SCHEMA_VERSION,
        "bundle_id": bundle_id,
        "bundle_state": "locked",
        "claim_status": "provisional",
        "evaluation_policy": context.evaluation_policy,
        "expected": gate_report.get("expected"),
        "locked_at": utc_now(),
        "observed": gate_report.get("observed"),
        "source_id": context.inputs.run_id,
        "source_kind": "completed_run",
        "source_sha256": hashes,
        "tool_version": TOOL_VERSION,
        }
        atomic_write_json(context.stage_dir / "bundle-manifest.json", manifest)
        metadata = read_json(context.stage_dir / "normalization-metadata.json", "P7")
        require_unchanged_sources(context, metadata.get("source_sha256") or {})
        final = context.output_root / f"{context.inputs.run_id}-{bundle_id}"
        if final.exists():
            existing = verify_bundle(final)
            if existing.get("bundle_id") != bundle_id:
                raise PromotionError("P7", "existing bundle path contains different evidence")
            shutil.rmtree(context.stage_dir)
            record_event(
                context,
                "lock_passed",
                True,
                {"bundle": final.name, "idempotent": True},
                input_sha256=stage_digest,
                output_sha256=bundle_id,
            )
            record_event(
                context,
                "promotion_eligible",
                True,
                {"bundle": final.name},
                input_sha256=bundle_id,
                output_sha256=bundle_id,
            )
            return final, existing
        os.replace(context.stage_dir, final)
        fsync_directory(context.output_root)
        verified = verify_bundle(final)
        record_event(
            context,
            "lock_passed",
            True,
            {"bundle": final.name, "idempotent": False},
            input_sha256=stage_digest,
            output_sha256=bundle_id,
        )
        record_event(
            context,
            "promotion_eligible",
            True,
            {"bundle": final.name},
            input_sha256=bundle_id,
            output_sha256=bundle_id,
        )
        return final, verified
    except PromotionError as exc:
        raise set_error_stage(exc, "lock")


def promote(context: PromotionContext) -> tuple[Path, dict[str, Any]]:
    initial_source_digest = digest_mapping(source_hashes(context.inputs))
    record_event(
        context,
        "promotion_started",
        True,
        input_sha256=initial_source_digest,
    )
    build_stage(context)
    gate_report = validate_stage(context)
    return lock_stage(context, gate_report)


def latest_status(output_root: Path, run_id: str) -> dict[str, Any]:
    state = output_root.resolve() / ".state" / run_id
    ledger = state / "promotion-ledger.jsonl"
    events = []
    if ledger.exists():
        events = [row for _line, row in iter_jsonl(ledger, "P0")]
    bundles = sorted(path.name for path in output_root.resolve().glob(f"{run_id}-*") if path.is_dir())
    return {
        "bundles": bundles,
        "last_event": events[-1] if events else None,
        "run_id": run_id,
    }


def command_context(args: argparse.Namespace) -> PromotionContext:
    return build_context(
        repo_root=Path(args.repo_root),
        run_dir=Path(args.run_dir),
        output_root=Path(args.output_root),
        judge_values=args.judge,
    )


def emit(value: Mapping[str, Any]) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def add_promotion_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--repo-root", default=str(REPO))
    parser.add_argument("--output-root", default=str(REPO / "data" / "completed-runs"))
    parser.add_argument("--judge", action="append", default=[], metavar="BACKEND:MODEL")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("normalize", "validate", "lock", "promote"):
        child = subparsers.add_parser(name)
        add_promotion_arguments(child)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--bundle", required=True)
    status = subparsers.add_parser("status")
    status.add_argument("--run-id", required=True)
    status.add_argument("--output-root", default=str(REPO / "data" / "completed-runs"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        if args.command == "verify":
            manifest = verify_bundle(Path(args.bundle))
            emit({"bundle": str(Path(args.bundle).resolve()), "manifest": manifest, "ok": True})
            return
        if args.command == "status":
            emit(latest_status(Path(args.output_root), args.run_id))
            return
        context = command_context(args)
        with promotion_lock(context):
            if args.command == "normalize":
                report = build_stage(context)
                emit({"ok": True, "stage": str(context.stage_dir), "gate_report": report})
            elif args.command == "validate":
                report = validate_stage(context)
                emit({"ok": True, "stage": str(context.stage_dir), "gate_report": report})
            elif args.command == "lock":
                bundle, manifest = lock_stage(context)
                emit({"ok": True, "bundle": str(bundle), "manifest": manifest})
            else:
                bundle, manifest = promote(context)
                emit({"ok": True, "bundle": str(bundle), "manifest": manifest})
    except PromotionError as exc:
        if "context" in locals() and isinstance(context, PromotionContext):
            with contextlib.suppress(Exception):
                record_event(
                    context,
                    f"{exc.stage or args.command}_failed",
                    False,
                    {"details": exc.details, "gate": exc.gate, "message": str(exc)},
                    input_sha256=digest_mapping(source_hashes(context.inputs)),
                )
        print(
            json.dumps(
                {
                    "details": exc.details,
                    "error": str(exc),
                    "gate": exc.gate,
                    "ok": False,
                    "stage": exc.stage or args.command,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        raise SystemExit(exc.exit_code) from exc


if __name__ == "__main__":
    main()