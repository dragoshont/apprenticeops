#!/usr/bin/env python3
"""Validate committed human-eval packet structure."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PACKETS = {
    "external-v1-spread10-baseline-clean-20260703-164337": {
        "items": 45,
        "judges": {"claude-opus-4.6", "gpt-5.4"},
    },
    "paper-94-model-corrected-v1": {
        "items": 50,
        "judges": {"claude-opus-4.8", "gpt-5.5"},
        "source_kind": "frozen_snapshot",
        "sources": {
            "data/raw/outputs.var.tar.gz",
            "data/raw/outputs.wave2.tar.gz",
            "data/scenarios.json",
            "data/site/judge_pairs.csv",
            "data/snapshots/judge_pair_provenance.csv",
            "data/snapshots/results_snapshot.csv",
        },
        "evaluation_policy": (
            "deterministic-checks-v1|judges:"
            "copilot:claude-opus-4.8+copilot:gpt-5.5"
        ),
    },
}


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_packet(packet_id: str, contract: dict) -> int:
    packet = REPO / "data" / "human_eval" / packet_id
    sheet = packet / "sheet.md"
    scores = packet / "scores.csv"
    key_path = packet / "key.json"
    for path in (sheet, scores, key_path):
        if not path.exists() or path.stat().st_size == 0:
            fail(f"missing or empty human eval artifact: {path.relative_to(REPO)}")
    key = json.loads(key_path.read_text())
    source_id = key.get("source_id") or key.get("run_id")
    if source_id != packet_id:
        fail(f"human eval packet source id changed: {source_id!r} != {packet_id!r}")
    items = key.get("items") or []
    if len(items) != contract["items"]:
        fail(f"expected {contract['items']} human eval items in {packet_id}, found {len(items)}")
    row_ids = [item["row_id"] for item in items]
    if len(row_ids) != len(set(row_ids)):
        fail("human eval key contains duplicate row ids")
    score_rows = list(csv.DictReader(scores.open()))
    if [row["row_id"] for row in score_rows] != row_ids:
        fail("scores.csv row ids must match key order")
    invalid_scores = [row for row in score_rows if row.get("human_score") and row["human_score"] not in {"1", "2", "3", "4", "5"}]
    if invalid_scores:
        fail(f"invalid human scores: {invalid_scores[:3]}")
    scored = sum(bool(row.get("human_score")) for row in score_rows)
    if scored not in {0, len(items)}:
        fail(f"{packet_id} must be fully blank or fully scored, found {scored}/{len(items)}")
    sheet_text = sheet.read_text()
    missing = [row_id for row_id in row_ids if row_id not in sheet_text]
    if missing:
        fail(f"sheet missing row ids: {missing[:5]}")
    expected_judges = contract["judges"]
    for item in items:
        judge_scores = item.get("judge_scores") or {}
        if set(judge_scores) != expected_judges:
            fail(f"{packet_id} {item['row_id']} judge identities changed: {sorted(judge_scores)}")
        if any(not isinstance(value, (int, float)) or not 1 <= float(value) <= 5 for value in judge_scores.values()):
            fail(f"{packet_id} {item['row_id']} contains invalid hidden judge scores")
    if contract.get("source_kind"):
        if key.get("source_kind") != contract["source_kind"]:
            fail(f"{packet_id} source_kind changed")
        if key.get("evaluation_policy") != contract["evaluation_policy"]:
            fail(f"{packet_id} evaluation policy changed")
        manifest_path = REPO / "data/analysis-manifest.json"
        if key.get("analysis_manifest_sha256") != sha256(manifest_path):
            fail(f"{packet_id} analysis manifest hash changed")
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("source_id") != packet_id or manifest.get("claim_status") != "locked":
            fail(f"{packet_id} does not point to the locked paper manifest")
        packet_sources = key.get("source_sha256") or {}
        if set(packet_sources) != contract["sources"]:
            fail(
                f"{packet_id} source set changed: "
                f"{sorted(set(packet_sources) ^ contract['sources'])}"
            )
        for relative, expected in packet_sources.items():
            if manifest.get("source_sha256", {}).get(relative) != expected:
                fail(f"{packet_id} source is not in the locked manifest: {relative}")
            if sha256(REPO / relative) != expected:
                fail(f"{packet_id} source hash changed: {relative}")
    agreement_path = packet / "agreement.json"
    if scored == len(items) and not agreement_path.exists():
        fail(f"{packet_id} is fully scored but agreement.json is missing")
    if scored == 0 and agreement_path.exists():
        fail(f"{packet_id} is blank but agreement.json exists")
    if agreement_path.exists():
        agreement = json.loads(agreement_path.read_text())
        if agreement.get("source_id") != packet_id:
            fail(f"{packet_id} agreement source id changed")
        if agreement.get("key_sha256") != sha256(key_path):
            fail(f"{packet_id} agreement key hash changed")
        if agreement.get("scores_sha256") != sha256(scores):
            fail(f"{packet_id} agreement score hash changed")
        if agreement.get("items_scored") != len(items) or agreement.get("items_total") != len(items):
            fail(f"{packet_id} agreement is incomplete")
        if set(agreement.get("judge_reports") or {}) != expected_judges:
            fail(f"{packet_id} agreement judge identities changed")
        if agreement.get("human_raters") != 1 or agreement.get("single_rater_limitation") is not True:
            fail(f"{packet_id} agreement must retain the single-rater limitation")
    print(
        f"human eval validation passed: packet={packet.relative_to(REPO)} "
        f"items={len(items)} scored={scored}"
    )
    return scored


def main() -> None:
    for packet_id, contract in PACKETS.items():
        validate_packet(packet_id, contract)


if __name__ == "__main__":
    main()