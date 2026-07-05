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
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
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
    if report.get("expected_judged_rows") is not None and report["judged_rows"] != report["expected_judged_rows"]:
        add_strict_failure(
            failures,
            "judged-row-count-mismatch",
            "judged row count does not match run metadata",
            actual=report["judged_rows"],
            expected=report["expected_judged_rows"],
        )
    for field, code, message in (
        ("parse_errors", "result-parse-errors", "inference result JSONL contains parse errors"),
        ("judge_parse_errors", "judge-parse-errors", "judged JSONL contains parse errors"),
        ("duplicate_result_tuples", "duplicate-result-tuples", "duplicate inference tuples were found"),
        ("judge_duplicate_tuples", "duplicate-judge-tuples", "duplicate judged tuples were found"),
        ("judge_empty", "empty-judge-rows", "judge backend produced empty verdict rows"),
        ("judge_response_parse_failures", "judge-response-parse-failures", "judge responses could not be parsed"),
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


def summarize_run(run_dir: Path) -> dict:
    run_id = run_dir.name
    meta_path = run_dir / "run.meta"
    meta = {}
    has_run_meta = meta_path.exists()
    run_meta_parse_error = False
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
        except json.JSONDecodeError:
            run_meta_parse_error = True
            meta = {"_parse_error": True}
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
            "judge_model": key[5],
        }
        for key, count in sorted(judge_tuple_counts.items())
        if count > 1
    ]
    judge_duplicates = sum(count - 1 for count in judge_tuple_counts.values() if count > 1)
    keys_seen = set().union(*(row.keys() for row in rows)) if rows else set()
    missing_counts = Counter()
    for row in rows:
        for key in keys_seen:
            if key not in row:
                missing_counts[key] += 1
    tuple_counts = Counter((row.get("model"), row.get("scenario"), row.get("rep"), row.get("env.memory_context") or "none", row.get("env.inference_strategy") or "baseline") for row in rows)
    duplicates = sum(count - 1 for count in tuple_counts.values() if count > 1)
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
    judge_missing_evidence = [row for row in judged if not row.get("evidence")]
    judge_missing_criteria = [row for row in judged if "criteria_met" not in row or "criteria_missed" not in row]
    judge_empty = [row for row in judged if row.get("verdict") == "empty" and not is_deterministic_no_answer_judge(row)]
    usage_by_judge: dict[str, dict] = defaultdict(lambda: {"calls": 0, "tokens_in": 0, "tokens_out": 0, "cache_read": 0, "cache_write": 0, "ai_credits": 0.0})
    for row in judged:
        usage = row.get("usage") or {}
        entry = usage_by_judge[row.get("judge_model") or "unknown"]
        entry["calls"] += 1
        for key in ("tokens_in", "tokens_out", "cache_read", "cache_write"):
            entry[key] += int(usage.get(key) or 0)
        entry["ai_credits"] += float(usage.get("ai_credits") or 0)
    expected_models = int(meta.get("expect") or meta.get("models_count") or 0)
    scenario_count = int(meta.get("scenario_count") or 0)
    reps = int(meta.get("reps") or 5)
    judges = int(meta.get("judges") or 2)
    expected_rows = expected_models * scenario_count * reps if expected_models and scenario_count else None
    expected_judged = expected_rows * judges if expected_rows and meta.get("judge_expected", True) is not False else None
    report = {
        "run_id": run_id,
        "has_run_meta": has_run_meta,
        "run_meta_parse_error": run_meta_parse_error,
        "result_file_count": len(result_paths),
        "meta": {
            "model_set": meta.get("model_set"),
            "scenario_set": meta.get("scenario_set"),
            "memory_context": meta.get("memory_context") or "none",
            "inference_strategy": meta.get("inference_strategy") or "baseline",
            "timeout_policy_id": meta.get("timeout_policy_id"),
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
        "duplicate_result_tuples": duplicates,
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
        print(f"rows: {report['rows']}{expected}; judged: {report['judged_rows']}{expected_j}; fields: {report['schema_field_count']}")
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
            f"duplicate_tuples={report['judge_duplicate_tuples']}"
        )
        if report["judge_duplicate_examples"]:
            for item in report["judge_duplicate_examples"][:5]:
                print(
                    "  duplicate judge tuple: "
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
        print(f"| Judged rows | {report['judged_rows']}{expected_j} |")
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
            print("### Duplicate Judge Examples")
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
    args = parser.parse_args()
    reports = [summarize_run(resolve_run(item)) for item in args.runs]
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
