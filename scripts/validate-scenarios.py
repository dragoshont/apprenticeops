#!/usr/bin/env python3
"""Validate scenario catalogs and the implemented Core 20 additions."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import run  # noqa: E402


NEW_CORE_IDS = [
    "new-external-tool-session-or-credential-degraded",
    "new-backup-restore-drill",
    "new-home-network-wan-dns",
    "new-flux-drift-source-not-ready",
    "new-homeassistant-recorder-or-mqtt",
    "new-linux-oom-or-node-pressure",
]


NEGATIVE_CONTROLS = {
    "new-external-tool-session-or-credential-degraded": (
        "This is an upstream credential/session failure, not a transport/result "
        "delivery problem. Pods are ready and iCloud CalDAV appears in the logs, "
        "so check LibreChat MCP logs and avoid restarting everything."
    ),
    "new-backup-restore-drill": (
        "The backup is trustworthy because restic backup exited 0. Run forget "
        "and prune now, then restore directly to live /srv/appdata."
    ),
    "new-home-network-wan-dns": (
        "The Cloudflare tunnel is the problem. Restart Traefik and redeploy the "
        "photos app even though LAN access works."
    ),
    "new-flux-drift-source-not-ready": (
        "Grafana is the root problem. Just kubectl apply the dashboard manifests "
        "and patch the live deployment now instead of fixing the GitRepository."
    ),
    "new-homeassistant-recorder-or-mqtt": (
        "Home Assistant is completely down because MQTT/Zigbee failed. Delete "
        "home-assistant_v2.db first and restart MQTT."
    ),
    "new-linux-oom-or-node-pressure": (
        "This is node pressure and a scheduler failure. MemoryPressure=False is "
        "the clue; add replicas to fix it and reboot the node."
    ),
}


def load_json(relative_path: str) -> dict:
    return json.loads((REPO / relative_path).read_text())


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def file_sha256(relative_path: str) -> str:
    return hashlib.sha256((REPO / relative_path).read_bytes()).hexdigest()


def validate_scenarios() -> None:
    scenarios = load_json("data/scenarios.json")["scenarios"]
    ids = [scenario["id"] for scenario in scenarios]
    if len(ids) != len(set(ids)):
        fail("data/scenarios.json contains duplicate scenario ids")
    if len(ids) != 33:
        fail(f"expected 33 scenarios, found {len(ids)}")

    by_id = {scenario["id"]: scenario for scenario in scenarios}
    for scenario_id in NEW_CORE_IDS:
        scenario = by_id.get(scenario_id)
        if scenario is None:
            fail(f"missing new Core 20 scenario {scenario_id}")

        passed, total, details = run.run_checks(
            scenario["gold_answer"], scenario["deterministic_checks"]
        )
        if passed != total:
            failed = [detail for detail in details if not detail["pass"]]
            fail(f"gold answer failed checks for {scenario_id}: {failed}")

        negative = NEGATIVE_CONTROLS[scenario_id]
        bad_passed, bad_total, _ = run.run_checks(negative, scenario["deterministic_checks"])
        if bad_passed == bad_total:
            fail(f"negative control unexpectedly passed all checks for {scenario_id}")


def validate_sets_and_manifest() -> None:
    all_scenarios = load_json("data/scenarios.json")["scenarios"]
    all_ids = {scenario["id"] for scenario in all_scenarios}
    core = load_json("data/scenario_sets/core-current.json")["scenarios"]
    extended = load_json("data/scenario_sets/extended.json")["scenarios"]

    core_ids = {scenario["id"] for scenario in core}
    extended_ids = {scenario["id"] for scenario in extended}
    if len(core_ids) != 20:
        fail(f"expected core-current to contain 20 scenarios, found {len(core_ids)}")
    if len(extended_ids) != 13:
        fail(f"expected extended to contain 13 scenarios, found {len(extended_ids)}")
    if not set(NEW_CORE_IDS).issubset(core_ids):
        fail("core-current is missing one or more new Core 20 scenarios")
    if core_ids & extended_ids:
        fail(f"core-current and extended overlap: {sorted(core_ids & extended_ids)}")
    if core_ids | extended_ids != all_ids:
        fail("core-current plus extended does not equal data/scenarios.json")

    matrix_sets = {
        entry["id"]: entry for entry in load_json("data/run-matrix.json")["scenario_sets"]
    }
    matrix = load_json("data/run-matrix.json")
    if set(matrix_sets) != {"core-current", "extended", "all"}:
        fail(f"unexpected scenario_set ids: {sorted(matrix_sets)}")
    if matrix_sets["core-current"]["label"] != "Core 20 - implemented scenarios":
        fail("run matrix core-current label is stale")
    if matrix.get("defaults", {}).get("memory_context") != "none":
        fail("run matrix default memory_context must be none")
    memory_contexts = {entry["id"]: entry for entry in matrix.get("memory_contexts", [])}
    if set(memory_contexts) != {"none", "homelab-okf-v1"}:
        fail(f"unexpected memory_context ids: {sorted(memory_contexts)}")
    if memory_contexts["none"].get("path"):
        fail("memory_context none must not have a path")
    memory_path = memory_contexts["homelab-okf-v1"].get("path")
    if not memory_path or not (REPO / memory_path).exists():
        fail("homelab-okf-v1 memory context path is missing")
    plans = {entry["id"]: entry for entry in matrix.get("experiment_plans", [])}
    plan = plans.get("memory-comparison-v1")
    if not plan:
        fail("missing memory-comparison-v1 experiment plan")
    gate = (plan.get("gate") or "").lower()
    if "verify" not in gate or "phase" not in gate:
        fail("memory-comparison-v1 gate must explicitly require phase verification")
    phases = plan.get("phases") or []
    phase_ids = [phase.get("id") for phase in phases]
    if len(phase_ids) != len(set(phase_ids)) or any(not phase_id for phase_id in phase_ids):
        fail("memory-comparison-v1 phases must have unique non-empty ids")
    if [phase.get("memory_context") for phase in phases] != ["none", "homelab-okf-v1"]:
        fail("memory-comparison-v1 phases must be none -> homelab-okf-v1")
    for phase in phases:
        if not phase.get("gate"):
            fail(f"memory-comparison phase {phase.get('id')} is missing gate text")

    manifest_sets = load_json("data/run-manifest.json")["protocol"]["scenario_sets"]
    expected = {
        "all": ("data/scenarios.json", 33),
        "core-current": ("data/scenario_sets/core-current.json", 20),
        "extended": ("data/scenario_sets/extended.json", 13),
    }
    for scenario_set, (relative_path, count) in expected.items():
        manifest_entry = manifest_sets[scenario_set]
        if manifest_entry["path"] != relative_path:
            fail(f"manifest path mismatch for {scenario_set}")
        if manifest_entry["scenario_count"] != count:
            fail(f"manifest count mismatch for {scenario_set}")
        if manifest_entry["sha256"] != file_sha256(relative_path):
            fail(f"manifest hash mismatch for {scenario_set}")


def main() -> None:
    validate_scenarios()
    validate_sets_and_manifest()
    print("scenario validation passed: all=33 core-current=20 extended=13 memory_contexts=2 plans=1")


if __name__ == "__main__":
    main()