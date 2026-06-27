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
        with path.open(errors="ignore") as handle:
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


def summarize_run(run_dir: Path) -> dict:
    run_id = run_dir.name
    meta_path = run_dir / "run.meta"
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
        except json.JSONDecodeError:
            meta = {"_parse_error": True}
    result_paths = sorted((run_dir / "_mirror").glob("results.*.jsonl"))
    if not result_paths:
        result_paths = sorted(run_dir.glob("results.*.jsonl"))
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
    judge_missing_evidence = [row for row in judged if not row.get("evidence")]
    judge_missing_criteria = [row for row in judged if "criteria_met" not in row or "criteria_missed" not in row]
    judge_empty = [row for row in judged if row.get("verdict") == "empty"]
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
    return {
        "run_id": run_id,
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
        "judge_evidence_missing": len(judge_missing_evidence),
        "judge_criteria_missing": len(judge_missing_criteria),
        "usage_by_judge": dict(usage_by_judge),
        "persistence": {
            "committed_models": count_lines(run_dir / ".committed"),
            "push_pending": count_lines(run_dir / ".push-pending"),
        },
    }


def print_text(reports: list[dict]) -> None:
    for report in reports:
        meta = report["meta"]
        print(f"== {report['run_id']} ==")
        print(f"scope: {meta.get('model_set')} x {meta.get('scenario_set')} x {meta.get('memory_context')} x {meta.get('inference_strategy')}")
        expected = f"/{report['expected_rows']}" if report.get("expected_rows") else ""
        expected_j = f"/{report['expected_judged_rows']}" if report.get("expected_judged_rows") else ""
        print(f"rows: {report['rows']}{expected}; judged: {report['judged_rows']}{expected_j}; fields: {report['schema_field_count']}")
        print(f"parse_errors={report['parse_errors']} duplicate_tuples={report['duplicate_result_tuples']} missing_fields={len(report['schema_missing_fields'])}")
        print(f"reliability: DNF {report['dnf']}/{report['rows']} ({report['dnf_rate']}%) · length {report['length']} ({report['length_rate']}%) · zero-output stalls {report['zero_output_stalls']} ({report['zero_output_stall_rate']}%)")
        print(f"judge: empty={report['judge_empty']} evidence_missing={report['judge_evidence_missing']} criteria_missing={report['judge_criteria_missing']}")
        if report["dnf_by_model"]:
            top = ", ".join(f"{item['id']}={item['dnf']}" for item in report["dnf_by_model"][:5] if item["dnf"])
            print(f"top DNF models: {top or 'none'}")
        if report["dnf_by_inference_strategy"]:
            strat = ", ".join(f"{item['id']}={item['dnf']}/{item['rows']}" for item in report["dnf_by_inference_strategy"])
            print(f"strategy DNF: {strat}")
        if report["usage_by_judge"]:
            for judge, usage in sorted(report["usage_by_judge"].items()):
                print(f"judge usage {judge}: calls={usage['calls']} in={usage['tokens_in']} out={usage['tokens_out']} credits={round(usage['ai_credits'], 2)}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="+", help="run ids or data/runs/<id> directories")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()
    reports = [summarize_run(resolve_run(item)) for item in args.runs]
    if args.json:
        print(json.dumps({"runs": reports}, indent=2, sort_keys=True))
    else:
        print_text(reports)


if __name__ == "__main__":
    main()
