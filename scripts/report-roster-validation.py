#!/usr/bin/env python3
"""Summarize JSONL produced by scripts/validate-roster-models.py."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def read_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for raw in path.read_text(errors="ignore").splitlines():
        if not raw.strip():
            continue
        try:
            rows.append(json.loads(raw))
        except json.JSONDecodeError:
            rows.append({"overall_status": "fail", "overall_reason": "parse_error", "raw": raw[:200]})
    return rows


def pct(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 2) if denominator else 0.0


def summarize(rows: list[dict]) -> dict:
    status = Counter(str(row.get("overall_status") or "unknown") for row in rows)
    reason = Counter(str(row.get("overall_reason") or "unknown") for row in rows)
    family = defaultdict(Counter)
    bracket = defaultdict(Counter)
    historical_high_dnf = []
    historical_high_length = []
    failures = []
    warnings = []
    for row in rows:
        state = str(row.get("overall_status") or "unknown")
        family[str(row.get("lock.family") or "unknown")][state] += 1
        bracket[str(row.get("roster_bracket") or "unknown")][state] += 1
        if state == "fail":
            failures.append(row)
        elif state == "warn":
            warnings.append(row)
        hist_dnf = row.get("historical.dnf_rate")
        hist_length = row.get("historical.length_rate")
        if isinstance(hist_dnf, (int, float)) and hist_dnf >= 0.25:
            historical_high_dnf.append(row)
        if isinstance(hist_length, (int, float)) and hist_length >= 0.25:
            historical_high_length.append(row)
    return {
        "rows": len(rows),
        "status": dict(status),
        "reasons": dict(reason),
        "failure_rate_pct": pct(status.get("fail", 0), len(rows)),
        "warn_rate_pct": pct(status.get("warn", 0), len(rows)),
        "failures": failures,
        "warnings": warnings,
        "historical_high_dnf": historical_high_dnf,
        "historical_high_length": historical_high_length,
        "family": {key: dict(value) for key, value in sorted(family.items())},
        "bracket": {key: dict(value) for key, value in sorted(bracket.items())},
    }


def row_line(row: dict) -> str:
    findings = row.get("findings") or []
    if isinstance(findings, list):
        finding_text = "; ".join(str(item) for item in findings[:3])
    else:
        finding_text = str(findings)
    return (
        f"- {row.get('model')} [{row.get('roster_bracket') or 'unknown'}] "
        f"{row.get('overall_status')} / {row.get('overall_reason')}"
        f"; chat_chars={row.get('chat.output_chars')} generate_chars={row.get('generate.output_chars')}"
        f"; hist_dnf={row.get('historical.dnf_rate')} hist_length={row.get('historical.length_rate')}"
        + (f"; {finding_text}" if finding_text else "")
    )


def print_text(report: dict, *, limit: int) -> None:
    print(f"rows: {report['rows']}")
    print(f"status: {report['status']}")
    print(f"reasons: {report['reasons']}")
    print(f"failure_rate_pct={report['failure_rate_pct']} warn_rate_pct={report['warn_rate_pct']}")
    if report["failures"]:
        print("\nFailures")
        for row in report["failures"][:limit]:
            print(row_line(row))
    if report["warnings"]:
        print("\nWarnings")
        for row in report["warnings"][:limit]:
            print(row_line(row))
    if report["historical_high_dnf"]:
        print("\nHistorical High DNF (>=25%)")
        for row in report["historical_high_dnf"][:limit]:
            print(row_line(row))
    if report["historical_high_length"]:
        print("\nHistorical High Length (>=25%)")
        for row in report["historical_high_length"][:limit]:
            print(row_line(row))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()
    report = summarize(read_rows(args.path))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text(report, limit=args.limit)


if __name__ == "__main__":
    main()