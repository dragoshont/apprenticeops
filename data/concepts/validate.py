#!/usr/bin/env python3
"""Validate ApprenticeOps concept nodes (stdlib only, no pytest/pyyaml/jsonschema).

Checks:
  1. Schema-ish : required fields present, kind in enum, sources non-empty.
  2. Provenance : every sources[].access file exists on disk (owned artifact).
  3. Scenarios  : every scenarios[] id exists in data/scenarios.json.
  4. Graph      : no duplicate ids, prerequisites resolve, no cycles.

Run from the repo root:
    python3 data/concepts/validate.py
Exits non-zero on any problem.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]  # data/knowledge -> repo root
NODES_DIR = HERE / "nodes"
SCENARIOS = REPO_ROOT / "data" / "scenarios.json"

REQUIRED = ["id", "title", "kind", "one_line", "sources", "captured"]
KINDS = {"concept", "algorithm", "technique", "pitfall"}


def _scenario_ids() -> set[str]:
    data = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("scenarios", [])
    return {s["id"] for s in items}


def _topo_check(nodes: dict[str, dict], errors: list[str]) -> None:
    for nid, node in nodes.items():
        for pre in node.get("prerequisites", []) or []:
            if pre not in nodes:
                errors.append(f"{nid}: prerequisite not found: {pre}")
    state: dict[str, int] = {nid: 0 for nid in nodes}

    def visit(nid: str, stack: tuple[str, ...]) -> None:
        if state.get(nid, 2) == 2:
            return
        if state[nid] == 1:
            errors.append("cycle: " + " -> ".join((*stack, nid)))
            return
        state[nid] = 1
        for pre in nodes[nid].get("prerequisites", []) or []:
            if pre in nodes:
                visit(pre, (*stack, nid))
        state[nid] = 2

    for nid in sorted(nodes):
        visit(nid, ())


def validate() -> list[str]:
    errors: list[str] = []
    paths = sorted(NODES_DIR.glob("*.json"))
    if not paths:
        return [f"no *.json nodes in {NODES_DIR}"]

    scenario_ids = _scenario_ids()
    nodes: dict[str, dict] = {}

    for path in paths:
        node = json.loads(path.read_text(encoding="utf-8"))
        name = path.name
        for key in REQUIRED:
            if key not in node:
                errors.append(f"{name}: missing required field '{key}'")
        if node.get("kind") not in KINDS:
            errors.append(f"{name}: kind '{node.get('kind')}' not in {sorted(KINDS)}")
        srcs = node.get("sources") or []
        if not srcs:
            errors.append(f"{name}: sources must be non-empty (provenance)")
        for i, src in enumerate(srcs):
            access = src.get("access")
            if access and not (REPO_ROOT / access).exists():
                errors.append(f"{name}: provenance: sources[{i}].access not found: {access}")
        for sid in node.get("scenarios", []) or []:
            if sid not in scenario_ids:
                errors.append(f"{name}: scenarios[] unknown id: {sid}")
        nid = node.get("id")
        if nid in nodes:
            errors.append(f"{name}: duplicate node id: {nid}")
        elif nid:
            nodes[nid] = node

    _topo_check(nodes, errors)
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print(f"FAIL - {len(errors)} problem(s):")
        for e in errors:
            print(f"  - {e}")
        return 1
    n = len(list(NODES_DIR.glob("*.json")))
    print(f"OK - {n} node(s) valid: fields + provenance + scenarios + graph.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
