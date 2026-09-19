#!/usr/bin/env python3
"""Validate Phase 3 external candidate scenarios.

This gate is intentionally separate from scripts/validate-scenarios.py because
external candidates must not become part of the locked Core catalog by accident.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import run  # noqa: E402

CORE = REPO / "data" / "scenarios.json"
LIFECYCLE_SCHEMA = REPO / "data" / "scenario-lifecycle.schema.json"

CANDIDATE_FILES = [
    {
        "path": REPO / "data" / "scenarios.external-candidates-v0.json",
        "scenario_set": "external-candidates-v0",
        "phase": "phase3",
        "count": 8,
        "require_lifecycle": False,
    },
    {
        "path": REPO / "data" / "scenarios.external-candidates-v1.json",
        "scenario_set": "external-candidates-v1",
        "phase": "phase6",
        "count": 9,
        "require_lifecycle": True,
    },
]

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
    "contamination_review",
    "sources",
    "negative_control",
    "adversarial_fixtures",
}

SECRET_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"sk-live-[A-Za-z0-9_\-]{8,}",
        r"sk-[A-Za-z0-9_\-]{16,}",
        r"ghp_[A-Za-z0-9_]{16,}",
        r"AKIA[0-9A-Z]{16}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    )
]


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def schema_enum(schema: dict, *path: str) -> set[str]:
    node = schema
    for part in path:
        node = node[part]
    return set(node["enum"])


def validate_external_metadata(scenario: dict, expected_phase: str) -> None:
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
    if meta["phase"] != expected_phase:
        fail(f"{scenario_id} must be marked {expected_phase}")
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
    review = meta["contamination_review"]
    if not isinstance(review, dict):
        fail(f"{scenario_id} contamination_review must be an object")
    if review.get("review_type") != "manual-pattern-synthesis":
        fail(f"{scenario_id} contamination_review must record manual-pattern-synthesis")
    if review.get("source_rows_read") is not False:
        fail(f"{scenario_id} contamination_review must say source_rows_read=false")
    if review.get("verdict") != "no-row-derived-content":
        fail(f"{scenario_id} contamination_review must have no-row-derived-content verdict")
    if not isinstance(meta["sources"], list) or not meta["sources"]:
        fail(f"{scenario_id} must list at least one source")
    for source in meta["sources"]:
        if not source.get("id") or not source.get("use") or not source.get("source_file_sha256"):
            fail(f"{scenario_id} has incomplete source trace: {source}")
        if len(source["source_file_sha256"]) != 64:
            fail(f"{scenario_id} has invalid source hash: {source}")
    fixtures = meta["adversarial_fixtures"]
    if not isinstance(fixtures, list) or len(fixtures) < 2:
        fail(f"{scenario_id} must include at least two adversarial fixtures")
    for fixture in fixtures:
        if not fixture.get("name") or not fixture.get("answer"):
            fail(f"{scenario_id} has incomplete adversarial fixture: {fixture}")
        if not isinstance(fixture.get("max_passed"), int):
            fail(f"{scenario_id} fixture {fixture.get('name')} must set max_passed")


def validate_lifecycle_metadata(scenario: dict, schema: dict) -> None:
    scenario_id = scenario.get("id", "<missing>")
    lifecycle = scenario.get("lifecycle")
    if not isinstance(lifecycle, dict):
        fail(f"{scenario_id} must include lifecycle metadata")

    required = set(schema["required"])
    missing = required - set(lifecycle)
    extra = set(lifecycle) - set(schema["properties"])
    if missing:
        fail(f"{scenario_id} lifecycle missing fields: {sorted(missing)}")
    if extra:
        fail(f"{scenario_id} lifecycle has unknown fields: {sorted(extra)}")
    if lifecycle.get("schema_version") != 1:
        fail(f"{scenario_id} lifecycle schema_version must be 1")

    properties = schema["properties"]
    object_meta = lifecycle["operational_object"]
    if object_meta.get("kind") not in schema_enum(schema, "properties", "operational_object", "properties", "kind"):
        fail(f"{scenario_id} lifecycle operational_object.kind is invalid")
    if not object_meta.get("name"):
        fail(f"{scenario_id} lifecycle operational_object.name is required")

    lifecycle_values = lifecycle["task_lifecycle"]
    allowed_lifecycle = schema_enum(schema, "properties", "task_lifecycle", "items")
    if not isinstance(lifecycle_values, list) or not lifecycle_values:
        fail(f"{scenario_id} lifecycle task_lifecycle must be a non-empty list")
    if len(lifecycle_values) != len(set(lifecycle_values)):
        fail(f"{scenario_id} lifecycle task_lifecycle contains duplicates")
    if any(value not in allowed_lifecycle for value in lifecycle_values):
        fail(f"{scenario_id} lifecycle task_lifecycle contains invalid values: {lifecycle_values}")

    fault = lifecycle["fault_model"]
    if fault.get("category") not in schema_enum(schema, "properties", "fault_model", "properties", "category"):
        fail(f"{scenario_id} lifecycle fault_model.category is invalid")
    if not fault.get("manifestation"):
        fail(f"{scenario_id} lifecycle fault_model.manifestation is required")

    evidence = lifecycle["workload_evidence"]
    channels = evidence.get("channels")
    allowed_channels = schema_enum(schema, "properties", "workload_evidence", "properties", "channels", "items")
    if not isinstance(channels, list) or not channels:
        fail(f"{scenario_id} lifecycle workload_evidence.channels must be non-empty")
    if len(channels) != len(set(channels)):
        fail(f"{scenario_id} lifecycle workload_evidence.channels contains duplicates")
    if any(channel not in allowed_channels for channel in channels):
        fail(f"{scenario_id} lifecycle workload_evidence.channels contains invalid values: {channels}")
    if evidence.get("source_quality") not in schema_enum(schema, "properties", "workload_evidence", "properties", "source_quality"):
        fail(f"{scenario_id} lifecycle workload_evidence.source_quality is invalid")

    action_surface = lifecycle["action_surface"]
    if action_surface.get("mode") not in schema_enum(schema, "properties", "action_surface", "properties", "mode"):
        fail(f"{scenario_id} lifecycle action_surface.mode is invalid")
    if action_surface.get("destructive_risk") not in schema_enum(schema, "properties", "action_surface", "properties", "destructive_risk"):
        fail(f"{scenario_id} lifecycle action_surface.destructive_risk is invalid")

    evaluator = lifecycle["evaluator_shape"]
    for key in ("deterministic_checks", "judge_rubric"):
        if not isinstance(evaluator.get(key), bool):
            fail(f"{scenario_id} lifecycle evaluator_shape.{key} must be boolean")

    if lifecycle["promotion_status"] not in schema_enum(schema, "properties", "promotion_status"):
        fail(f"{scenario_id} lifecycle promotion_status is invalid")

    source_trace = lifecycle["source_trace"]
    if source_trace.get("use") not in schema_enum(schema, "properties", "source_trace", "properties", "use"):
        fail(f"{scenario_id} lifecycle source_trace.use is invalid")
    if source_trace.get("row_status") not in schema_enum(schema, "properties", "source_trace", "properties", "row_status"):
        fail(f"{scenario_id} lifecycle source_trace.row_status is invalid")


def validate_no_live_secret_patterns(scenario: dict) -> None:
    scenario_id = scenario["id"]
    payload = json.dumps(scenario, sort_keys=True)
    for pattern in SECRET_PATTERNS:
        if pattern.search(payload):
            fail(f"{scenario_id} contains live-looking secret pattern: {pattern.pattern}")


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

    for fixture in scenario["external_candidate"]["adversarial_fixtures"]:
        passed, _, details = run.run_checks(fixture["answer"], checks)
        if passed > fixture["max_passed"]:
            fail(
                f"adversarial fixture {fixture['name']} passed too many checks "
                f"for {scenario_id}: {passed}>{fixture['max_passed']} {details}"
            )
        for expected_failure in fixture.get("must_fail", []):
            matching = [
                detail for detail in details
                if expected_failure.lower() in detail["desc"].lower()
            ]
            if not matching:
                fail(
                    f"adversarial fixture {fixture['name']} for {scenario_id} "
                    f"references unknown expected failure: {expected_failure!r}"
                )
            if any(detail["pass"] for detail in matching):
                fail(
                    f"adversarial fixture {fixture['name']} for {scenario_id} "
                    f"unexpectedly passed required-failure check {expected_failure!r}: {details}"
                )


def main() -> None:
    lifecycle_schema = load_json(LIFECYCLE_SCHEMA)
    core_data = load_json(CORE)
    core_ids = {scenario["id"] for scenario in core_data["scenarios"]}
    summaries = []
    for candidate_file in CANDIDATE_FILES:
        candidate_data = load_json(candidate_file["path"])
        meta = candidate_data.get("_meta") or {}
        if meta.get("scenario_set") != candidate_file["scenario_set"]:
            fail(f"{candidate_file['path'].name} has wrong scenario_set metadata")
        if meta.get("phase") != candidate_file["phase"]:
            fail(f"{candidate_file['path'].name} has wrong phase metadata")
        scenarios = candidate_data.get("scenarios")
        if not isinstance(scenarios, list):
            fail(f"{candidate_file['path'].name} must contain a scenarios list")
        if len(scenarios) != candidate_file["count"]:
            fail(f"{candidate_file['path'].name} expected {candidate_file['count']} scenarios, found {len(scenarios)}")

        ids = [scenario.get("id") for scenario in scenarios]
        if len(ids) != len(set(ids)):
            fail(f"{candidate_file['path'].name} contains duplicate scenario ids")
        overlap = sorted(core_ids & set(ids))
        if overlap:
            fail(f"{candidate_file['path'].name} overlaps Core ids: {overlap}")

        for scenario in scenarios:
            validate_external_metadata(scenario, candidate_file["phase"])
            if candidate_file["require_lifecycle"]:
                validate_lifecycle_metadata(scenario, lifecycle_schema)
            validate_no_live_secret_patterns(scenario)
            validate_checks(scenario)
        summaries.append(f"{candidate_file['scenario_set']}={len(scenarios)}")

    print(
        "external candidate validation passed: "
        f"{', '.join(summaries)}, no Core overlap, no live-looking secrets, "
        "gold checks pass, negative controls and adversarial fixtures fail as expected"
    )


if __name__ == "__main__":
    main()