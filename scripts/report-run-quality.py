#!/usr/bin/env python3
"""Report structural and reliability quality for CEOps run artifacts.

Usage:
    python3 scripts/report-run-quality.py data/runs/<RUN_ID> [data/runs/<RUN_ID> ...]
    python3 scripts/report-run-quality.py <RUN_ID>
    python3 scripts/report-run-quality.py --json <RUN_ID>

The command is intentionally report-first: it does not mutate runs, and it does
not decide whether a scientific comparison is acceptable. It makes the reliability
axis explicit so quality improvements cannot hide DNF/stall/length regressions.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import analysis_metrics  # noqa: E402

RUNS = REPO / "data" / "runs"


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    try:
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", errors="ignore") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    rows.append({"_parse_error": line[:120]})
    except OSError:
        pass
    return rows


def count_lines(path: Path) -> int:
    try:
        return sum(1 for line in path.open(errors="ignore") if line.strip())
    except OSError:
        return 0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def strict_positive_int(value, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def repo_root_for_run(run_dir: Path) -> Path:
    if run_dir.parent.name == "runs" and run_dir.parent.parent.name == "data":
        return run_dir.parent.parent.parent
    return REPO


def safe_contract_file(root: Path, raw, expected_sha256, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"run.meta {label} must name a repository-relative file")
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"run.meta {label} path is unsafe")
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"run.meta {label} path is symlinked")
    if not cursor.is_file():
        raise ValueError(f"run.meta {label} file is missing")
    actual = sha256_file(cursor)
    if not isinstance(expected_sha256, str) or actual != expected_sha256:
        raise ValueError(f"run.meta {label} hash mismatch")
    return cursor


def classified_judge_retry(row: dict) -> bool:
    return row.get("score") is None and (
        row.get("evidence") in {"parse_error", "invalid_contract"}
        or "judge response could not be parsed" in (row.get("criteria_missed") or [])
        or "judge response violated the judgement contract" in (row.get("criteria_missed") or [])
    )


def resolve_run(raw: str) -> Path:
    path = Path(raw)
    if path.exists():
        return path
    run_dir = RUNS / raw
    if run_dir.exists():
        return run_dir
    raise SystemExit(f"unknown run: {raw}")


def pct(n: int, d: int) -> float:
    return round(100 * n / d, 2) if d else 0.0


def inc_bucket(bucket: dict[str, dict], key: str, *, dnf: bool = False) -> None:
    entry = bucket.setdefault(key or "unknown", {"rows": 0, "dnf": 0})
    entry["rows"] += 1
    entry["dnf"] += int(dnf)


def compact_bucket(bucket: dict[str, dict]) -> list[dict]:
    return [
        {"id": key, "rows": value["rows"], "dnf": value["dnf"], "dnf_rate": pct(value["dnf"], value["rows"])}
        for key, value in sorted(bucket.items(), key=lambda item: (-item[1]["dnf"], item[0]))
    ]


def is_deterministic_no_answer_judge(row: dict) -> bool:
    if row.get("deterministic_no_answer") is True:
        return True
    verdict = str(row.get("verdict") or "")
    if verdict not in {"empty", "no_answer"} or row.get("score") != 1:
        return False
    evidence = str(row.get("evidence") or "")
    missed = row.get("criteria_missed") or []
    if not isinstance(missed, list):
        missed = [str(missed)]
    return (
        "No answer text was available" in evidence
        or "answer was empty or unavailable" in missed
    )


def finalize_usage(entry: dict) -> dict:
    tokens_in = int(entry.get("tokens_in") or 0)
    cache_read = int(entry.get("cache_read") or 0)
    cache_write = int(entry.get("cache_write") or 0)
    tokens_out = int(entry.get("tokens_out") or 0)
    entry["uncached_input_tokens"] = max(tokens_in - cache_read, 0)
    entry["cache_read_pct"] = pct(cache_read, tokens_in)
    entry["cache_write_pct"] = pct(cache_write, tokens_in)
    entry["output_input_pct"] = pct(tokens_out, tokens_in)
    return entry


def add_strict_failure(findings: list[dict], code: str, message: str, *, actual=None, expected=None) -> None:
    finding = {"code": code, "message": message}
    if actual is not None:
        finding["actual"] = actual
    if expected is not None:
        finding["expected"] = expected
    findings.append(finding)


def evaluate_interpretation(report: dict) -> dict:
    failures: list[dict] = []
    if not report.get("has_run_meta"):
        add_strict_failure(
            failures,
            "run-meta-missing",
            "run.meta is missing, so expected row counts and run scope cannot be verified",
            actual=0,
            expected=1,
        )
    if report.get("run_meta_parse_error"):
        add_strict_failure(
            failures,
            "run-meta-parse-error",
            "run.meta is not valid JSON",
            actual=1,
            expected=0,
        )
    if report.get("judged_rows", 0) and not report.get("rows", 0):
        add_strict_failure(
            failures,
            "result-rows-missing",
            "judged rows exist but no inference result rows were found",
            actual=0,
            expected="nonzero",
        )
    if report.get("expected_rows") is not None and report["rows"] != report["expected_rows"]:
        add_strict_failure(
            failures,
            "result-row-count-mismatch",
            "inference row count does not match run metadata",
            actual=report["rows"],
            expected=report["expected_rows"],
        )
    if (
        report.get("expected_judged_rows") is not None
        and report["judge_canonical_successes"] != report["expected_judged_rows"]
    ):
        add_strict_failure(
            failures,
            "judged-success-count-mismatch",
            "canonical successful judgement count does not match run metadata",
            actual=report["judge_canonical_successes"],
            expected=report["expected_judged_rows"],
        )
    if report.get("expected_judged_rows") is not None and not report.get("judge_domain_declared"):
        add_strict_failure(
            failures,
            "judge-domain-undeclared",
            "expected judge identities are absent; pass --judge for legacy runs",
            actual=0,
            expected=report.get("meta", {}).get("judges"),
        )
    if report.get("judge_domain_conflict"):
        add_strict_failure(
            failures,
            "judge-domain-conflict",
            "explicit judge identities differ from authoritative run metadata",
            actual=report.get("explicit_judges"),
            expected=report.get("metadata_judges"),
        )
    if report.get("judge_metadata_error"):
        add_strict_failure(
            failures,
            "judge-metadata-invalid",
            "run.meta judge identity declaration is malformed",
            actual=report.get("judge_metadata_error"),
            expected="non-empty unique identities matching judges",
        )
    if report.get("judge_count_error"):
        add_strict_failure(
            failures,
            "judge-count-invalid",
            "run.meta judge count is malformed",
            actual=report.get("judge_count_error"),
            expected="positive integer",
        )
    for field, code, message in (
        ("contract_error_count", "run-contract-invalid", "run metadata roster/scenario contract is invalid"),
        ("result_domain_missing", "missing-result-domain-keys", "declared roster/scenario/repetition results are missing"),
        ("result_domain_extra", "extra-result-domain-keys", "result rows are outside the declared roster/scenario/repetition domain"),
        ("persistence_domain_errors", "persistence-domain-invalid", "done or committed model domains differ from the declared roster"),
        ("judge_unclassified_failures", "unclassified-judge-failures", "judge failures are not classified retry evidence"),
    ):
        value = int(report.get(field) or 0)
        if value:
            add_strict_failure(failures, code, message, actual=value, expected=0)
    for field, code, message in (
        ("parse_errors", "result-parse-errors", "inference result JSONL contains parse errors"),
        ("judge_parse_errors", "judge-parse-errors", "judged JSONL contains parse errors"),
        ("duplicate_result_tuples", "duplicate-result-tuples", "duplicate inference tuples were found"),
        ("judge_missing_success_tuples", "missing-successful-judge-tuples", "judge tuples lack a successful attempt"),
        ("judge_competing_success_tuples", "competing-successful-judge-tuples", "judge tuples have multiple successful attempts"),
        ("judge_missing_keys", "missing-judge-keys", "declared result/judge keys have no attempt"),
        ("judge_extra_keys", "extra-judge-keys", "observed judge attempts are outside the declared result/judge domain"),
        ("judge_unresolved_parse_failures", "unresolved-judge-response-parse-failures", "judge parse failures have no successful retry"),
        ("judge_empty", "empty-judge-rows", "judge backend produced empty verdict rows"),
        ("judge_evidence_missing", "judge-evidence-missing", "judge rows are missing evidence"),
        ("judge_criteria_missing", "judge-criteria-missing", "judge rows are missing criteria fields"),
    ):
        value = int(report.get(field) or 0)
        if value:
            add_strict_failure(failures, code, message, actual=value, expected=0)
    push_pending = int((report.get("persistence") or {}).get("push_pending") or 0)
    if push_pending:
        add_strict_failure(
            failures,
            "push-pending",
            "run has pending persistence push markers",
            actual=push_pending,
            expected=0,
        )
    return {
        "interpretation_ok": not failures,
        "strict_failure_count": len(failures),
        "strict_failures": failures,
    }


def summarize_run(
    run_dir: Path,
    *,
    explicit_judges: frozenset[tuple[str, str]] | None = None,
    allow_legacy_persistence: bool = False,
) -> dict:
    run_id = run_dir.name
    meta_path = run_dir / "run.meta"
    meta = {}
    has_run_meta = meta_path.exists()
    run_meta_parse_error = False
    judge_count_error = None
    judge_count = None
    contract_errors: list[str] = []
    declared_roster: list[str] | None = None
    declared_scenarios: list[str] | None = None
    declared_reps: int | None = None
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
        except json.JSONDecodeError:
            run_meta_parse_error = True
            meta = {"_parse_error": True}
    schema_version = meta.get("schema_version") if isinstance(meta, dict) else None
    modern_markers = {
        "models", "models_sha256", "models_count", "scenarios", "scenarios_sha256",
        "scenario_ids", "persist_mode", "judge_identities",
    }
    has_modern_markers = bool(modern_markers & set(meta)) if isinstance(meta, dict) else False
    modern_contract = schema_version == 2 and not isinstance(schema_version, bool)
    if has_modern_markers and not modern_contract:
        contract_errors.append(
            "run.meta with modern contract fields requires schema_version=2"
        )
    if has_run_meta and not run_meta_parse_error:
        try:
            judge_count = analysis_metrics.metadata_judge_count(meta)
        except ValueError as exc:
            judge_count_error = str(exc)
    if modern_contract and not run_meta_parse_error:
        try:
            root = repo_root_for_run(run_dir)
            models_count = strict_positive_int(meta.get("models_count"), "models_count")
            expect = strict_positive_int(meta.get("expect"), "expect")
            scenario_count = strict_positive_int(meta.get("scenario_count"), "scenario_count")
            declared_reps = strict_positive_int(meta.get("reps"), "reps")
            persistence_mode = meta.get("persist_mode")
            legacy_persistence = allow_legacy_persistence and persistence_mode is None
            if persistence_mode not in {"git-push", "local-files"} and not legacy_persistence:
                contract_errors.append(
                    "run.meta persist_mode must be git-push or local-files"
                )
            roster_path = safe_contract_file(
                root, meta.get("models"), meta.get("models_sha256"), "models"
            )
            scenario_path = safe_contract_file(
                root, meta.get("scenarios"), meta.get("scenarios_sha256"), "scenarios"
            )
            declared_roster = [
                line.strip()
                for line in roster_path.read_text().splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            ]
            if (
                len(declared_roster) != models_count
                or len(declared_roster) != expect
                or len(declared_roster) != len(set(declared_roster))
            ):
                raise ValueError("run.meta model counts differ from unique roster")
            scenario_payload = json.loads(scenario_path.read_text())
            scenario_rows = scenario_payload.get("scenarios") if isinstance(scenario_payload, dict) else None
            if not isinstance(scenario_rows, list):
                raise ValueError("scenario contract lacks scenarios list")
            declared_scenarios = [
                row.get("id") for row in scenario_rows if isinstance(row, dict)
            ]
            if (
                len(declared_scenarios) != len(scenario_rows)
                or len(declared_scenarios) != scenario_count
                or any(not isinstance(value, str) or not value for value in declared_scenarios)
                or len(declared_scenarios) != len(set(declared_scenarios))
                or meta.get("scenario_ids") != declared_scenarios
            ):
                raise ValueError("run.meta scenario domain differs from ordered scenario contract")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            contract_errors.append(str(exc))
    result_paths = sorted((run_dir / "_mirror").glob("results.*.jsonl"))
    if not result_paths:
        result_paths = sorted(run_dir.glob("results.*.jsonl"))
    if not result_paths:
        result_paths = sorted(run_dir.glob("results.*.jsonl.gz"))
    if not result_paths:
        result_paths = sorted(run_dir.glob("*.results.jsonl.gz"))
    rows = []
    parse_errors = 0
    for path in result_paths:
        for row in read_jsonl(path):
            if row.get("_parse_error"):
                parse_errors += 1
            else:
                rows.append(row)
    judged = []
    judge_parse_errors = 0
    for path in sorted(run_dir.glob("judged.*.jsonl")):
        for row in read_jsonl(path):
            if row.get("_parse_error"):
                judge_parse_errors += 1
            else:
                judged.append(row)
    judge_tuple_counts = Counter(
        (
            row.get("model"),
            row.get("scenario"),
            row.get("rep"),
            row.get("memory_context") or row.get("env.memory_context") or "none",
            row.get("inference_strategy") or row.get("env.inference_strategy") or "baseline",
            row.get("judge_backend") or "unknown",
            row.get("judge_model"),
        )
        for row in judged
    )
    judge_duplicate_examples = [
        {
            "count": count,
            "model": key[0],
            "scenario": key[1],
            "rep": key[2],
            "memory_context": key[3],
            "inference_strategy": key[4],
            "judge_backend": key[5],
            "judge_model": key[6],
        }
        for key, count in sorted(judge_tuple_counts.items())
        if count > 1
    ]
    judge_duplicates = sum(count - 1 for count in judge_tuple_counts.values() if count > 1)
    judge_attempts_by_key: dict[tuple, list[dict]] = defaultdict(list)
    for row in judged:
        key = (
            row.get("model"),
            row.get("scenario"),
            row.get("rep"),
            row.get("memory_context") or row.get("env.memory_context") or "none",
            row.get("inference_strategy") or row.get("env.inference_strategy") or "baseline",
            row.get("judge_backend") or "unknown",
            row.get("judge_model"),
        )
        judge_attempts_by_key[key].append(row)
    successful_attempts = {
        key: [row for row in attempts if analysis_metrics.judgement_success(row)]
        for key, attempts in judge_attempts_by_key.items()
    }
    metadata_judges = None
    judge_metadata_error = None
    try:
        metadata_judges = analysis_metrics.metadata_judge_identities(meta)
    except ValueError as exc:
        judge_metadata_error = str(exc)
    judge_domain_conflict = (
        metadata_judges is not None
        and explicit_judges is not None
        and metadata_judges != explicit_judges
    )
    declared_judges = metadata_judges if metadata_judges is not None else explicit_judges
    result_join_keys = {
        (
            row.get("model"), row.get("scenario"), row.get("rep"),
            row.get("env.memory_context") or "none",
            row.get("env.inference_strategy") or "baseline",
        )
        for row in rows
    }
    expected_judge_keys = {
        (*result_key, backend, model)
        for result_key in result_join_keys
        for backend, model in (declared_judges or frozenset())
    }
    observed_judge_keys = set(judge_attempts_by_key)
    extra_judge_keys = observed_judge_keys - expected_judge_keys if declared_judges else set()
    missing_judge_keys = expected_judge_keys - observed_judge_keys if declared_judges else set()
    domain_keys = expected_judge_keys if declared_judges else observed_judge_keys
    judge_canonical_successes = sum(len(successful_attempts.get(key, [])) == 1 for key in domain_keys)
    judge_missing_success_tuples = sum(not successful_attempts.get(key) for key in domain_keys)
    judge_competing_success_tuples = sum(len(successful_attempts.get(key, [])) > 1 for key in domain_keys)
    judge_retry_attempts = sum(
        len(all_attempts) - 1
        for key, all_attempts in judge_attempts_by_key.items()
        if len(successful_attempts[key]) == 1
    )
    judge_unclassified_failures = sum(
        1
        for attempts in judge_attempts_by_key.values()
        for row in attempts
        if not analysis_metrics.judgement_success(row) and not classified_judge_retry(row)
    )
    keys_seen = set().union(*(row.keys() for row in rows)) if rows else set()
    missing_counts = Counter()
    for row in rows:
        for key in keys_seen:
            if key not in row:
                missing_counts[key] += 1
    tuple_counts = Counter((row.get("model"), row.get("scenario"), row.get("rep"), row.get("env.memory_context") or "none", row.get("env.inference_strategy") or "baseline") for row in rows)
    duplicates = sum(count - 1 for count in tuple_counts.values() if count > 1)
    result_domain_missing = 0
    result_domain_extra = 0
    persistence_domain_errors = 0
    if declared_roster is not None and declared_scenarios is not None and declared_reps is not None:
        expected_result_domain = {
            (model, scenario, rep)
            for model in declared_roster
            for scenario in declared_scenarios
            for rep in range(declared_reps)
        }
        actual_result_domain = set()
        for row in rows:
            rep = row.get("rep")
            if isinstance(rep, bool) or not isinstance(rep, int):
                result_domain_extra += 1
                continue
            actual_result_domain.add((str(row.get("model")), str(row.get("scenario")), rep))
        result_domain_missing = len(expected_result_domain - actual_result_domain)
        result_domain_extra += len(actual_result_domain - expected_result_domain)
        if modern_contract and not (
            allow_legacy_persistence and meta.get("persist_mode") is None
        ):
            committed = [
                line.strip()
                for line in (run_dir / ".committed").read_text().splitlines()
                if line.strip()
            ] if (run_dir / ".committed").is_file() and not (run_dir / ".committed").is_symlink() else []
            done_paths = sorted((run_dir / "_mirror").glob("results.*.jsonl.done"))
            done_rows = []
            done_parse_errors = 0
            if len(done_paths) == 1 and not done_paths[0].is_symlink():
                parsed_done = read_jsonl(done_paths[0])
                done_parse_errors = sum(bool(row.get("_parse_error")) for row in parsed_done)
                done_rows = [row for row in parsed_done if not row.get("_parse_error")]
            done_models = [row.get("model") for row in done_rows]
            expected_units = len(declared_scenarios) * declared_reps
            if (
                len(done_paths) != 1
                or done_parse_errors
                or len(committed) != len(set(committed))
                or set(committed) != set(declared_roster)
                or len(done_models) != len(set(done_models))
                or set(done_models) != set(declared_roster)
                or any(
                    isinstance(row.get("units"), bool)
                    or not isinstance(row.get("units"), int)
                    or row.get("units") != expected_units
                    for row in done_rows
                )
            ):
                persistence_domain_errors = 1
    finish_counts = Counter(((row.get("gen_ai.response.finish_reasons") or [None])[0]) or "unknown" for row in rows)
    dnf_rows = [row for row in rows if row.get("dnf") or str(((row.get("gen_ai.response.finish_reasons") or [None])[0]) or "").startswith("DNF")]
    length_rows = [row for row in rows if "length" in str(((row.get("gen_ai.response.finish_reasons") or [None])[0]) or "").lower()]
    zero_stalls = [row for row in rows if ((row.get("gen_ai.response.finish_reasons") or [None])[0]) == "DNF:stall" and not row.get("gen_ai.usage.output_tokens") and not row.get("progress_trace")]
    by_model: dict[str, dict] = {}
    by_scenario: dict[str, dict] = {}
    by_memory: dict[str, dict] = {}
    by_strategy: dict[str, dict] = {}
    for row in rows:
        is_dnf = row in dnf_rows
        inc_bucket(by_model, row.get("model"), dnf=is_dnf)
        inc_bucket(by_scenario, row.get("scenario"), dnf=is_dnf)
        inc_bucket(by_memory, row.get("env.memory_context") or "none", dnf=is_dnf)
        inc_bucket(by_strategy, row.get("env.inference_strategy") or "baseline", dnf=is_dnf)
    no_answer_judgements = [row for row in judged if is_deterministic_no_answer_judge(row)]
    judge_response_parse_failures = [
        row for row in judged
        if row.get("score") is None
        and (
            row.get("evidence") == "parse_error"
            or "judge response could not be parsed" in (row.get("criteria_missed") or [])
        )
    ]
    judge_unresolved_parse_failures = [
        row
        for key, attempts in judge_attempts_by_key.items()
        if not successful_attempts[key]
        for row in attempts
        if row in judge_response_parse_failures
    ]
    canonical_success_rows = [
        attempts[0]
        for key, attempts in successful_attempts.items()
        if key in domain_keys and len(attempts) == 1
    ]
    judge_missing_evidence = [row for row in canonical_success_rows if not row.get("evidence")]
    judge_missing_criteria = [
        row for row in canonical_success_rows
        if "criteria_met" not in row or "criteria_missed" not in row
    ]
    judge_empty = [row for row in judged if row.get("verdict") == "empty" and not is_deterministic_no_answer_judge(row)]
    usage_by_judge: dict[str, dict] = defaultdict(lambda: {"calls": 0, "tokens_in": 0, "tokens_out": 0, "cache_read": 0, "cache_write": 0, "ai_credits": 0.0})
    for row in judged:
        usage = row.get("usage") or {}
        entry = usage_by_judge[analysis_metrics.judge_identity_label(row)]
        entry["calls"] += 1
        for key in ("tokens_in", "tokens_out", "cache_read", "cache_write"):
            entry[key] += int(usage.get(key) or 0)
        entry["ai_credits"] += float(usage.get("ai_credits") or 0)
    def optional_positive_int(*keys, default=None):
        for key in keys:
            value = meta.get(key)
            if value is not None:
                try:
                    return strict_positive_int(value, key)
                except ValueError as exc:
                    contract_errors.append(str(exc))
                    return None
        return default

    expected_models = optional_positive_int("expect", "models_count")
    scenario_count = optional_positive_int("scenario_count")
    reps = optional_positive_int("reps", default=5 if not modern_contract else None)
    expected_rows = (
        expected_models * scenario_count * reps
        if expected_models and scenario_count and reps
        else None
    )
    expected_judged = (
        expected_rows * judge_count
        if expected_rows and judge_count is not None and meta.get("judge_expected", True) is not False
        else None
    )
    report = {
        "run_id": run_id,
        "has_run_meta": has_run_meta,
        "run_meta_parse_error": run_meta_parse_error,
        "legacy_persistence_opt_in": bool(
            allow_legacy_persistence and meta.get("persist_mode") is None
        ),
        "result_file_count": len(result_paths),
        "meta": {
            "model_set": meta.get("model_set"),
            "scenario_set": meta.get("scenario_set"),
            "memory_context": meta.get("memory_context") or "none",
            "inference_strategy": meta.get("inference_strategy") or "baseline",
            "timeout_policy_id": meta.get("timeout_policy_id"),
            "judges": judge_count,
        },
        "rows": len(rows),
        "expected_rows": expected_rows,
        "judged_rows": len(judged),
        "expected_judged_rows": expected_judged,
        "parse_errors": parse_errors,
        "judge_parse_errors": judge_parse_errors,
        "judge_unique_tuples": len(judge_tuple_counts),
        "judge_duplicate_tuples": judge_duplicates,
        "judge_duplicate_examples": judge_duplicate_examples[:10],
        "judge_canonical_successes": judge_canonical_successes,
        "judge_retry_attempts": judge_retry_attempts,
        "judge_unclassified_failures": judge_unclassified_failures,
        "judge_missing_success_tuples": judge_missing_success_tuples,
        "judge_competing_success_tuples": judge_competing_success_tuples,
        "judge_unresolved_parse_failures": len(judge_unresolved_parse_failures),
        "judge_domain_declared": declared_judges is not None,
        "judge_domain_conflict": judge_domain_conflict,
        "judge_metadata_error": judge_metadata_error,
        "judge_count_error": judge_count_error,
        "metadata_judges": sorted(
            f"{backend}:{model}" for backend, model in (metadata_judges or frozenset())
        ),
        "explicit_judges": sorted(
            f"{backend}:{model}" for backend, model in (explicit_judges or frozenset())
        ),
        "judge_expected_identities": sorted(
            f"{backend}:{model}" for backend, model in (declared_judges or frozenset())
        ),
        "judge_missing_keys": len(missing_judge_keys),
        "judge_extra_keys": len(extra_judge_keys),
        "duplicate_result_tuples": duplicates,
        "contract_error_count": len(contract_errors),
        "contract_errors": contract_errors,
        "result_domain_missing": result_domain_missing,
        "result_domain_extra": result_domain_extra,
        "persistence_domain_errors": persistence_domain_errors,
        "schema_field_count": len(keys_seen),
        "schema_missing_fields": dict(missing_counts),
        "dnf": len(dnf_rows),
        "dnf_rate": pct(len(dnf_rows), len(rows)),
        "length": len(length_rows),
        "length_rate": pct(len(length_rows), len(rows)),
        "zero_output_stalls": len(zero_stalls),
        "zero_output_stall_rate": pct(len(zero_stalls), len(rows)),
        "finish_reasons": dict(finish_counts),
        "dnf_by_model": compact_bucket(by_model)[:20],
        "dnf_by_scenario": compact_bucket(by_scenario)[:20],
        "dnf_by_memory_context": compact_bucket(by_memory),
        "dnf_by_inference_strategy": compact_bucket(by_strategy),
        "judge_empty": len(judge_empty),
        "empty_answer_judgements": len(no_answer_judgements),
        "judge_response_parse_failures": len(judge_response_parse_failures),
        "judge_evidence_missing": len(judge_missing_evidence),
        "judge_criteria_missing": len(judge_missing_criteria),
        "usage_by_judge": {judge: finalize_usage(dict(usage)) for judge, usage in usage_by_judge.items()},
        "persistence": {
            "committed_models": count_lines(run_dir / ".committed"),
            "push_pending": count_lines(run_dir / ".push-pending"),
        },
    }
    report.update(evaluate_interpretation(report))
    return report


def print_text(reports: list[dict]) -> None:
    for report in reports:
        meta = report["meta"]
        print(f"== {report['run_id']} ==")
        print(f"scope: {meta.get('model_set')} x {meta.get('scenario_set')} x {meta.get('memory_context')} x {meta.get('inference_strategy')}")
        expected = f"/{report['expected_rows']}" if report.get("expected_rows") else ""
        expected_j = f"/{report['expected_judged_rows']}" if report.get("expected_judged_rows") else ""
        print(
            f"rows: {report['rows']}{expected}; "
            f"judged: {report['judge_canonical_successes']}{expected_j} canonical "
            f"from {report['judged_rows']} attempts; fields: {report['schema_field_count']}"
        )
        print(f"run_meta={int(report['has_run_meta'])}; result_files={report['result_file_count']}")
        gate = "PASS" if report["interpretation_ok"] else "FAIL"
        print(f"interpretation: {gate}; strict_failures={report['strict_failure_count']}")
        for item in report["strict_failures"][:5]:
            expected_value = f" expected={item['expected']}" if "expected" in item else ""
            actual_value = f" actual={item['actual']}" if "actual" in item else ""
            print(f"  strict failure: {item['code']} - {item['message']}{actual_value}{expected_value}")
        print(f"parse_errors={report['parse_errors']} duplicate_tuples={report['duplicate_result_tuples']} missing_fields={len(report['schema_missing_fields'])}")
        print(f"reliability: DNF {report['dnf']}/{report['rows']} ({report['dnf_rate']}%) · length {report['length']} ({report['length_rate']}%) · zero-output stalls {report['zero_output_stalls']} ({report['zero_output_stall_rate']}%)")
        print(
            f"judge: empty={report['judge_empty']} "
            f"no_answer={report.get('empty_answer_judgements', 0)} "
            f"parse_failures={report.get('judge_response_parse_failures', 0)} "
            f"evidence_missing={report['judge_evidence_missing']} "
            f"criteria_missing={report['judge_criteria_missing']} "
            f"retry_attempts={report['judge_retry_attempts']} "
            f"missing_success={report['judge_missing_success_tuples']} "
            f"competing_success={report['judge_competing_success_tuples']}"
        )
        if not report["judge_domain_declared"]:
            print("  judge domain: UNDECLARED (pass --judge BACKEND:MODEL for legacy runs)")
        if report["judge_duplicate_examples"]:
            for item in report["judge_duplicate_examples"][:5]:
                print(
                    "  multiple judge attempts: "
                    f"count={item['count']} model={item['model']} "
                    f"scenario={item['scenario']} rep={item['rep']} "
                    f"memory={item['memory_context']} strategy={item['inference_strategy']} "
                    f"judge={item['judge_model']}"
                )
        if report["dnf_by_model"]:
            top = ", ".join(f"{item['id']}={item['dnf']}" for item in report["dnf_by_model"][:5] if item["dnf"])
            print(f"top DNF models: {top or 'none'}")
        if report["dnf_by_inference_strategy"]:
            strat = ", ".join(f"{item['id']}={item['dnf']}/{item['rows']}" for item in report["dnf_by_inference_strategy"])
            print(f"strategy DNF: {strat}")
        if report["usage_by_judge"]:
            for judge, usage in sorted(report["usage_by_judge"].items()):
                print(
                    f"judge usage {judge}: calls={usage['calls']} "
                    f"in={usage['tokens_in']} out={usage['tokens_out']} "
                    f"cache_read={usage['cache_read']} ({usage['cache_read_pct']}%) "
                    f"cache_write={usage['cache_write']} ({usage['cache_write_pct']}%) "
                    f"uncached_in={usage['uncached_input_tokens']} "
                    f"credits={round(usage['ai_credits'], 2)}"
                )
        print()


def print_markdown(reports: list[dict]) -> None:
    for report in reports:
        meta = report["meta"]
        expected = f"/{report['expected_rows']}" if report.get("expected_rows") else ""
        expected_j = f"/{report['expected_judged_rows']}" if report.get("expected_judged_rows") else ""
        gate = "PASS" if report["interpretation_ok"] else "FAIL"
        print(f"## {report['run_id']}")
        print()
        print(f"Scope: `{meta.get('model_set')}` x `{meta.get('scenario_set')}` x `{meta.get('memory_context')}` x `{meta.get('inference_strategy')}`")
        print()
        print("### Interpretation Gate")
        print()
        print(f"**{gate}** (`strict_failures={report['strict_failure_count']}`)")
        print()
        if report["strict_failures"]:
            print("| Code | Actual | Expected | Finding |")
            print("|---|---:|---:|---|")
            for item in report["strict_failures"]:
                actual = item.get("actual", "")
                expected_value = item.get("expected", "")
                print(f"| `{item['code']}` | {actual} | {expected_value} | {item['message']} |")
            print()
        print("### Structural Summary")
        print()
        print("| Signal | Value |")
        print("|---|---:|")
        print(f"| Inference rows | {report['rows']}{expected} |")
        print(f"| Raw judge attempts | {report['judged_rows']} |")
        print(f"| Canonical successful judgements | {report['judge_canonical_successes']}{expected_j} |")
        print(f"| Judge retry attempts | {report['judge_retry_attempts']} |")
        print(f"| Judge tuples missing success | {report['judge_missing_success_tuples']} |")
        print(f"| Judge tuples with competing successes | {report['judge_competing_success_tuples']} |")
        print(f"| Run metadata present | {report['has_run_meta']} |")
        print(f"| Result files | {report['result_file_count']} |")
        print(f"| Result parse errors | {report['parse_errors']} |")
        print(f"| Judge parse errors | {report['judge_parse_errors']} |")
        print(f"| Duplicate inference tuples | {report['duplicate_result_tuples']} |")
        print(f"| Duplicate judge tuples | {report['judge_duplicate_tuples']} |")
        print(f"| Judge empty rows | {report['judge_empty']} |")
        print(f"| No-answer judgements | {report.get('empty_answer_judgements', 0)} |")
        print(f"| Judge response parse failures | {report.get('judge_response_parse_failures', 0)} |")
        print(f"| Judge evidence missing | {report['judge_evidence_missing']} |")
        print(f"| Judge criteria missing | {report['judge_criteria_missing']} |")
        print(f"| Push pending markers | {report['persistence']['push_pending']} |")
        print()
        print("### Reliability")
        print()
        print("| Signal | Value |")
        print("|---|---:|")
        print(f"| DNF | {report['dnf']}/{report['rows']} ({report['dnf_rate']}%) |")
        print(f"| Length finishes | {report['length']} ({report['length_rate']}%) |")
        print(f"| Zero-output stalls | {report['zero_output_stalls']} ({report['zero_output_stall_rate']}%) |")
        print()
        if report["judge_duplicate_examples"]:
            print("### Multiple Judge Attempt Examples")
            print()
            print("| Count | Model | Scenario | Rep | Memory | Strategy | Judge |")
            print("|---:|---|---|---:|---|---|---|")
            for item in report["judge_duplicate_examples"][:10]:
                print(
                    f"| {item['count']} | `{item['model']}` | `{item['scenario']}` | {item['rep']} | "
                    f"`{item['memory_context']}` | `{item['inference_strategy']}` | `{item['judge_model']}` |"
                )
            print()
        if report["dnf_by_inference_strategy"]:
            print("### Strategy DNF")
            print()
            print("| Strategy | DNF | Rows | Rate |")
            print("|---|---:|---:|---:|")
            for item in report["dnf_by_inference_strategy"]:
                print(f"| `{item['id']}` | {item['dnf']} | {item['rows']} | {item['dnf_rate']}% |")
            print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="+", help="run ids or data/runs/<id> directories")
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    output_group.add_argument("--markdown", action="store_true", help="emit review-ready Markdown")
    parser.add_argument("--strict", action="store_true", help="exit non-zero when structural interpretation gates fail")
    parser.add_argument("--judge", action="append", default=[], metavar="BACKEND:MODEL",
                        help="declared judge identity for legacy run.meta without judge_identities")
    parser.add_argument(
        "--allow-legacy-persistence",
        action="store_true",
        help="explicitly audit a historical schema-v2 run that predates persist_mode and done/committed markers",
    )
    args = parser.parse_args()
    explicit_judges = None
    if args.judge:
        parsed = set()
        for value in args.judge:
            backend, separator, model = value.partition(":")
            if not separator or not backend or not model:
                parser.error(f"invalid --judge {value!r}; expected BACKEND:MODEL")
            parsed.add((backend, model))
        explicit_judges = frozenset(parsed)
    reports = [
        summarize_run(
            resolve_run(item),
            explicit_judges=explicit_judges,
            allow_legacy_persistence=args.allow_legacy_persistence,
        )
        for item in args.runs
    ]
    if args.json:
        print(json.dumps({"runs": reports}, indent=2, sort_keys=True))
    elif args.markdown:
        print_markdown(reports)
    else:
        print_text(reports)
    if args.strict and any(not report["interpretation_ok"] for report in reports):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
