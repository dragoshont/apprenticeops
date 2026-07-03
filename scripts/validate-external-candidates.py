#!/usr/bin/env python3
"""Validate Phase 3 external candidate scenarios.

This gate is intentionally separate from scripts/validate-scenarios.py because
external candidates must not become part of the locked Core catalog by accident.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import run  # noqa: E402

CANDIDATES = REPO / "data" / "scenarios.external-candidates-v0.json"
CORE = REPO / "data" / "scenarios.json"

REQUIRED_SCENARIO_FIELDS = {
    "id",
    "difficulty",
    "class",
    "aiopslab_task",
    "grounding",
    "context",
    "question",
    "gold_answer",
    "deterministic_checks",
    "judge_rubric",
    "max_tokens",
    "timeout_s",
    "external_candidate",
}

REQUIRED_EXTERNAL_FIELDS = {
    "status",
    "phase",
    "pattern_only",
    "copied_source_rows",
    "core_eligible",
    "phase4_required",
    "synthesis_basis",
    "source_rows_used",
    "row_hashes_used",
    "sources",
    "negative_control",
}


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_external_metadata(scenario: dict) -> None:
    scenario_id = scenario.get("id", "<missing>")
    missing = REQUIRED_SCENARIO_FIELDS - set(scenario)
    if missing:
        fail(f"{scenario_id} missing scenario fields: {sorted(missing)}")

    meta = scenario["external_candidate"]
    missing_meta = REQUIRED_EXTERNAL_FIELDS - set(meta)
    if missing_meta:
        fail(f"{scenario_id} missing external metadata fields: {sorted(missing_meta)}")
    if meta["status"] != "candidate-only":
        fail(f"{scenario_id} must remain candidate-only")
    if meta["phase"] != "phase3":
        fail(f"{scenario_id} must be marked phase3")
    if meta["pattern_only"] is not True:
        fail(f"{scenario_id} must be pattern_only=true")
    if meta["copied_source_rows"] is not False:
        fail(f"{scenario_id} must not copy source rows")
    if meta["core_eligible"] is not False:
        fail(f"{scenario_id} must not be Core-eligible")
    if meta["phase4_required"] is not True:
        fail(f"{scenario_id} must require Phase 4 review")
    if meta["synthesis_basis"] != "pattern-family-only":
        fail(f"{scenario_id} must be synthesized from pattern families only")
    if meta["source_rows_used"] != []:
        fail(f"{scenario_id} must not list source rows used")
    if meta["row_hashes_used"] != []:
        fail(f"{scenario_id} must not list row hashes before row-level review")
    if not isinstance(meta["sources"], list) or not meta["sources"]:
        fail(f"{scenario_id} must list at least one source")
    for source in meta["sources"]:
        if not source.get("id") or not source.get("use") or not source.get("source_file_sha256"):
            fail(f"{scenario_id} has incomplete source trace: {source}")
        if len(source["source_file_sha256"]) != 64:
            fail(f"{scenario_id} has invalid source hash: {source}")


def validate_checks(scenario: dict) -> None:
    scenario_id = scenario["id"]
    checks = scenario["deterministic_checks"]
    if not isinstance(checks, list) or len(checks) < 3:
        fail(f"{scenario_id} needs at least three deterministic checks")

    passed, total, details = run.run_checks(scenario["gold_answer"], checks)
    if passed != total:
        failed = [detail for detail in details if not detail["pass"]]
        fail(f"gold answer failed checks for {scenario_id}: {failed}")

    negative = scenario["external_candidate"]["negative_control"]
    bad_passed, bad_total, _ = run.run_checks(negative, checks)
    if bad_passed == bad_total:
        fail(f"negative control unexpectedly passed all checks for {scenario_id}")


def main() -> None:
    candidate_data = load_json(CANDIDATES)
    core_data = load_json(CORE)
    scenarios = candidate_data.get("scenarios")
    if not isinstance(scenarios, list):
        fail("candidate file must contain a scenarios list")

    ids = [scenario.get("id") for scenario in scenarios]
    if len(ids) != len(set(ids)):
        fail("candidate file contains duplicate scenario ids")
    core_ids = {scenario["id"] for scenario in core_data["scenarios"]}
    overlap = sorted(core_ids & set(ids))
    if overlap:
        fail(f"external candidates overlap Core ids: {overlap}")

    for scenario in scenarios:
        validate_external_metadata(scenario)
        validate_checks(scenario)

    print(
        "external candidate validation passed: "
        f"{len(scenarios)} candidates, no Core overlap, gold checks pass, "
        "negative controls fail"
    )


if __name__ == "__main__":
    main()