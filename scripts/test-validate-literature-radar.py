#!/usr/bin/env python3
"""Focused attacks for the ApprenticeOps research-radar validator."""
from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "validate-literature-radar.py"
SPEC = importlib.util.spec_from_file_location("validate_literature_radar", SCRIPT)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)

SCAN_ID = "radar-20260713-test"
VERSION_ID = "arxiv:2504.12285@arxiv-v2"
CLAIM_ID = "arxiv:2504.12285#cpu-runtime"
CLAIM_VERSION_ID = f"{CLAIM_ID}@{VERSION_ID}"


def base_query(query_id: str, topic: str, family: str = "primary-index", organization: str = "cross-lab") -> dict:
    return {
        "schema": "apprenticeops.radar-query.v1",
        "scan_id": SCAN_ID,
        "query_id": query_id,
        "observed_at": "2026-07-13T20:00:00Z",
        "source_family": family,
        "organization": organization,
        "topic": topic,
        "query": f"{topic} recent primary research",
        "window_start": "2025-01-01",
        "window_end": "2026-07-13",
        "result_count": 1,
        "selected_version_ids": [],
        "notes": "fixture",
    }


def fixture(root: Path) -> dict[str, list[dict]]:
    radar = root / "docs" / "analysis" / "research-radar"
    radar.mkdir(parents=True)
    (radar / "schema.json").write_text((REPO / "docs/analysis/research-radar/schema.json").read_text())
    skill = root / ".github" / "skills" / "literature-radar"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: literature-radar\ndescription: fixture\n---\n")
    agents = root / ".github" / "agents"
    agents.mkdir(parents=True)
    (agents / "research-radar.agent.md").write_text(
        '---\nname: "Research Radar"\ndescription: fixture\nuser-invocable: true\n---\n'
    )
    queries = [base_query(f"q-topic-{index}", topic) for index, topic in enumerate(sorted(validator.TOPICS))]
    for organization in sorted(validator.ORGANIZATIONS):
        queries.append(base_query(f"q-org-{organization}", "small-models", "company-research", organization))
    queries.extend([
        base_query("q-model-code", "specialization", "model-code"),
        base_query("q-reproduction", "evaluation-statistics", "independent-reproduction"),
        base_query("q-social", "small-models", "social-lead"),
    ])
    queries[0]["selected_version_ids"] = [VERSION_ID]
    source = {
        "schema": "apprenticeops.radar-source.v1",
        "scan_id": SCAN_ID,
        "work_id": "arxiv:2504.12285",
        "version_id": VERSION_ID,
        "prior_version_id": None,
        "canonical_url": "https://arxiv.org/abs/2504.12285v2",
        "variants": ["https://github.com/microsoft/BitNet"],
        "title": "BitNet b1.58 2B4T Technical Report",
        "authors_or_orgs": ["Microsoft Research"],
        "first_published": "2025-04-16",
        "observed_at": "2026-07-13T20:00:00Z",
        "revision_id": "arxiv-v2",
        "revision_date": "2025-04-25",
        "revision_hash": None,
        "source_tier": "primary-paper",
        "verification": "abstract-verified",
        "topics": ["small-models", "on-device-systems"],
        "organizations": ["Microsoft"],
        "delta_status": "new",
        "update_kind": "none",
        "changed_claim_version_ids": [],
        "relevance": "Native low-bit CPU runtime candidate.",
        "limitations": "Company report; energy claim needs local measurement.",
        "decision": "promote-candidate",
        "promotion_state": "candidate",
        "promoted_to": None,
    }
    claim = {
        "schema": "apprenticeops.radar-claim.v1",
        "scan_id": SCAN_ID,
        "claim_id": CLAIM_ID,
        "claim_version_id": CLAIM_VERSION_ID,
        "work_id": source["work_id"],
        "version_id": VERSION_ID,
        "claim_text": "The release includes a native CPU inference path.",
        "evidence_scope": "Official technical report and repository.",
        "status": "active",
        "supersedes_claim_version_id": None,
        "changed_from_claim_version_id": None,
        "corroborating_version_ids": [],
        "contradicting_version_ids": [],
        "last_verified_at": "2026-07-13T20:00:00Z",
    }
    scan = {
        "schema": "apprenticeops.radar-scan.v1",
        "scan_id": SCAN_ID,
        "scan_date": "2026-07-13",
        "window_start": "2025-01-01",
        "window_end": "2026-07-13",
        "status": "complete",
        "report_path": "docs/analysis/research-radar/2026-07-13.md",
        "query_ids": [row["query_id"] for row in queries],
        "selected_version_ids": [VERSION_ID],
        "claim_version_ids": [CLAIM_VERSION_ID],
        "canonical_hashes": {path: "a" * 64 for path in validator.CANONICAL_PATHS},
        "notes": "fixture",
    }
    sections = "\n".join(f"## {heading}\n\nfixture" for heading in validator.REPORT_HEADINGS)
    (radar / "2026-07-13.md").write_text(
        f"---\nscan_id: {SCAN_ID}\nwindow_start: 2025-01-01\nwindow_end: 2026-07-13\n---\n\n"
        + sections.replace("## Sources\n\nfixture", f"## Sources\n\n`{VERSION_ID}`")
        + "\n"
    )
    rows = {"queries": queries, "sources": [source], "claims": [claim], "scans": [scan], "promotions": []}
    write_rows(root, rows)
    return rows


def write_rows(root: Path, rows: dict[str, list[dict]]) -> None:
    radar = root / "docs" / "analysis" / "research-radar"
    for kind, filename in validator.RADAR_FILES.items():
        (radar / filename).write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows[kind]))


def assert_rejected(mutate, message: str) -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        rows = fixture(root)
        mutate(rows, root)
        write_rows(root, rows)
        try:
            validator.validate(root, "complete", SCAN_ID, check_canon=False)
        except validator.RadarError as exc:
            assert message in str(exc), str(exc)
        else:
            raise AssertionError(f"attack unexpectedly passed: {message}")


def remove_topic_coverage(rows: dict[str, list[dict]], _root: Path) -> None:
    rows["queries"] = [row for row in rows["queries"] if row["topic"] != "agent-safety"]
    rows["queries"][0]["selected_version_ids"] = [VERSION_ID]
    rows["scans"][0]["query_ids"] = [row["query_id"] for row in rows["queries"]]


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        fixture(root)
        counts = validator.validate(root, "complete", SCAN_ID, check_canon=False)
        assert counts == {"queries": 22, "sources": 1, "claims": 1, "scans": 1, "promotions": 0}

    assert_rejected(lambda rows, _root: rows["queries"].__setitem__(1, copy.deepcopy(rows["queries"][0])), "duplicate query query_id")
    assert_rejected(lambda rows, _root: rows["queries"][0].__setitem__("result_count", True), "non-negative integer")
    assert_rejected(lambda rows, _root: rows["queries"][0].__setitem__("notes", "Seven screened; three selected"), "must not duplicate")
    assert_rejected(remove_topic_coverage, "topic coverage")
    assert_rejected(lambda rows, _root: rows["queries"][0].__setitem__("selected_version_ids", ["arxiv:missing@arxiv-v1"]), "unknown source versions")
    assert_rejected(lambda rows, _root: rows["queries"][0].__setitem__("selected_version_ids", []), "query-selected source inventory")
    assert_rejected(lambda rows, _root: rows["sources"][0].__setitem__("canonical_url", "https://home.hont.ro/private"), "private host")
    assert_rejected(lambda rows, _root: rows["sources"][0].__setitem__("revision_id", "arxiv-v1"), "arXiv source version")
    assert_rejected(lambda rows, _root: rows["claims"][0].__setitem__("claim_version_id", "wrong"), "claim_version_id")
    assert_rejected(lambda rows, _root: rows["claims"][0].__setitem__("changed_from_claim_version_id", CLAIM_VERSION_ID), "self-reference")
    assert_rejected(lambda rows, _root: rows["sources"][0].update(delta_status="updated", update_kind="revision"), "must name changed claims")
    assert_rejected(lambda rows, _root: rows["scans"][0].__setitem__("report_path", None), "must name a report")
    assert_rejected(lambda rows, root: (root / "docs/analysis/research-radar/2026-07-13.md").write_text("---\nscan_id: wrong\n---\n"), "report scan_id")
    assert_rejected(lambda rows, root: (root / ".github/agents/research-radar.agent.md").unlink(), "missing Research Radar agent")
    assert_rejected(lambda rows, _root: rows["promotions"].append({
        "schema": "apprenticeops.radar-promotion.v1", "promotion_id": "p1",
        "scan_id": SCAN_ID, "version_id": VERSION_ID, "approved_by": "human",
        "approved_at": "2026-07-13T20:00:00Z", "targets": ["bib:test"],
    }), "refuses promotion records")
    print("literature radar validator tests passed: 16")


if __name__ == "__main__":
    main()