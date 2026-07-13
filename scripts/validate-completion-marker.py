#!/usr/bin/env python3
"""Validate producer completion records and emit a canonical process snapshot."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def roster_models(path: Path) -> list[str]:
    models = [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not models or len(models) != len(set(models)):
        raise ValueError("roster must contain unique models")
    return models


def scenario_count(path: Path) -> int:
    value = json.loads(path.read_text())
    rows = value.get("scenarios") if isinstance(value, dict) else None
    if not isinstance(rows, list) or not rows:
        raise ValueError("scenario contract lacks a non-empty scenarios list")
    return len(rows)


def validate(roster_path: Path, done_path: Path, scenarios_path: Path, reps: int) -> list[dict]:
    if isinstance(reps, bool) or not isinstance(reps, int) or reps <= 0:
        raise ValueError("repetitions must be a positive integer")
    roster = roster_models(roster_path)
    expected_units = scenario_count(scenarios_path) * reps
    seen = set()
    records = []
    for line_number, raw in enumerate(done_path.read_text().splitlines(), 1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"done marker line {line_number} is invalid JSON") from exc
        if not isinstance(row, dict) or set(row) != {"model", "bracket", "ts", "units"}:
            raise ValueError(f"done marker line {line_number} has invalid fields")
        model = row.get("model")
        bracket = row.get("bracket")
        timestamp = row.get("ts")
        units = row.get("units")
        if not isinstance(model, str) or model not in roster:
            raise ValueError(f"done marker line {line_number} has a model outside the roster")
        if model in seen:
            raise ValueError(f"done marker line {line_number} duplicates model {model}")
        if not isinstance(bracket, str) or not bracket.strip():
            raise ValueError(f"done marker line {line_number} has an invalid bracket")
        if (
            isinstance(timestamp, bool)
            or not isinstance(timestamp, (int, float))
            or not math.isfinite(timestamp)
            or timestamp <= 0
        ):
            raise ValueError(f"done marker line {line_number} has an invalid timestamp")
        if isinstance(units, bool) or not isinstance(units, int) or units != expected_units:
            raise ValueError(f"done marker line {line_number} has invalid units")
        seen.add(model)
        records.append({"model": model, "units": units})
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roster", required=True, type=Path)
    parser.add_argument("--done", required=True, type=Path)
    parser.add_argument("--scenarios", required=True, type=Path)
    parser.add_argument("--reps", required=True, type=int)
    args = parser.parse_args()
    try:
        records = validate(args.roster, args.done, args.scenarios, args.reps)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc
    for row in records:
        print(json.dumps(row, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
