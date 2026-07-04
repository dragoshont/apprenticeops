#!/usr/bin/env python3
"""Validate the ApprenticeOps model lock against the <=5B thesis boundary."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROSTER = REPO / "data" / "models.txt"
LOCK = REPO / "data" / "models.lock.jsonl"
SCHEMA = REPO / "data" / "model.schema.json"

REQUIRED = {
    "model_id",
    "publisher",
    "family",
    "params_b",
    "tier",
    "architecture",
    "training_type",
    "quantization",
    "runtime",
    "artifact_size_gb",
    "source_url",
    "license",
    "ollama_digest",
    "gguf_sha256",
    "context_length",
    "included",
    "track",
    "exclusion_reason",
    "downloaded_at",
    "metadata_status",
    "roster_bracket",
    "legacy_bracket",
    "measured_snapshot",
    "notes",
}


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def roster_models() -> list[str]:
    models: list[str] = []
    for raw in ROSTER.read_text().splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            models.append(line)
    return models


def load_lock() -> list[dict]:
    rows: list[dict] = []
    for line_number, raw in enumerate(LOCK.read_text().splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            rows.append(json.loads(raw))
        except json.JSONDecodeError as exc:
            fail(f"invalid JSON on models.lock.jsonl line {line_number}: {exc}")
    return rows


def tier_for(params_b: float | None) -> str | None:
    if params_b is None or params_b <= 0:
        return None
    if params_b <= 1:
        return "T1"
    if params_b <= 2:
        return "T2"
    if params_b <= 3:
        return "T3"
    if params_b <= 4:
        return "T4"
    if params_b <= 5:
        return "T5"
    return None


def validate_schema_shell() -> None:
    schema = json.loads(SCHEMA.read_text())
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        fail("model schema must declare JSON Schema draft 2020-12")
    if schema.get("additionalProperties") is not False:
        fail("model schema must reject unknown top-level fields")
    if set(schema.get("required") or []) != REQUIRED:
        fail("model schema required fields do not match validator REQUIRED set")


def validate() -> None:
    validate_schema_shell()
    roster = roster_models()
    rows = load_lock()
    ids = [row.get("model_id") for row in rows]
    if len(ids) != len(set(ids)):
        duplicates = [model for model, count in Counter(ids).items() if count > 1]
        fail(f"models.lock.jsonl contains duplicate model ids: {duplicates}")
    if set(ids) != set(roster):
        missing = sorted(set(roster) - set(ids))
        extra = sorted(set(ids) - set(roster))
        fail(f"model lock does not match roster: missing={missing[:10]} extra={extra[:10]}")
    if len(rows) != len(roster):
        fail(f"model lock row count {len(rows)} != roster count {len(roster)}")

    included = 0
    excluded = 0
    unknown_params = 0
    above_5b = 0
    by_tier: Counter[str] = Counter()
    for row in rows:
        model_id = row["model_id"]
        missing = REQUIRED - set(row)
        extra = set(row) - REQUIRED
        if missing or extra:
            fail(f"{model_id} field mismatch: missing={sorted(missing)} extra={sorted(extra)}")
        params_b = row["params_b"]
        if params_b is None:
            unknown_params += 1
        elif not isinstance(params_b, (int, float)) or params_b <= 0:
            fail(f"{model_id} params_b must be positive or null")
        expected_tier = tier_for(params_b)
        if row["tier"] != expected_tier:
            fail(f"{model_id} tier {row['tier']} does not match params_b={params_b} expected={expected_tier}")
        if row["included"]:
            included += 1
            if params_b is None:
                fail(f"{model_id} is included but params_b is unknown")
            if params_b > 5:
                fail(f"{model_id} is included but exceeds 5B parameters: {params_b}")
            if row["exclusion_reason"] is not None:
                fail(f"{model_id} is included but has exclusion_reason={row['exclusion_reason']}")
            if "thesis_5b_candidate" not in row["track"]:
                fail(f"{model_id} is included but missing thesis_5b_candidate track")
            by_tier[row["tier"]] += 1
        else:
            excluded += 1
            if not row["exclusion_reason"]:
                fail(f"{model_id} is excluded but lacks exclusion_reason")
        if params_b is not None and params_b > 5:
            above_5b += 1
            if row["included"]:
                fail(f"{model_id} exceeds 5B and must not be included")

    target_status = "met" if included >= 150 else "not_met"
    if included < 150:
        fail(f"thesis_5b_candidate count {included} is below the 150+ target")
    print(
        "model lock validation passed: "
        f"rows={len(rows)} included_thesis_5b={included} excluded={excluded} "
        f"above_5b_excluded={above_5b} unknown_params={unknown_params} "
        f"tiers={dict(sorted(by_tier.items()))} target_150_status={target_status}"
    )


if __name__ == "__main__":
    validate()