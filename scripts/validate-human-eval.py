#!/usr/bin/env python3
"""Validate committed human-eval packet structure."""

from __future__ import annotations

import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PACKET = REPO / "data" / "human_eval" / "external-v1-spread10-baseline-clean-20260703-164337"


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def main() -> None:
    sheet = PACKET / "sheet.md"
    scores = PACKET / "scores.csv"
    key_path = PACKET / "key.json"
    for path in (sheet, scores, key_path):
        if not path.exists() or path.stat().st_size == 0:
            fail(f"missing or empty human eval artifact: {path.relative_to(REPO)}")
    key = json.loads(key_path.read_text())
    items = key.get("items") or []
    if len(items) != 45:
        fail(f"expected 45 human eval items, found {len(items)}")
    row_ids = [item["row_id"] for item in items]
    if len(row_ids) != len(set(row_ids)):
        fail("human eval key contains duplicate row ids")
    score_rows = list(csv.DictReader(scores.open()))
    if [row["row_id"] for row in score_rows] != row_ids:
        fail("scores.csv row ids must match key order")
    invalid_scores = [row for row in score_rows if row.get("human_score") and row["human_score"] not in {"1", "2", "3", "4", "5"}]
    if invalid_scores:
        fail(f"invalid human scores: {invalid_scores[:3]}")
    sheet_text = sheet.read_text()
    missing = [row_id for row_id in row_ids if row_id not in sheet_text]
    if missing:
        fail(f"sheet missing row ids: {missing[:5]}")
    print(f"human eval validation passed: packet={PACKET.relative_to(REPO)} items={len(items)} scored={sum(bool(row.get('human_score')) for row in score_rows)}")


if __name__ == "__main__":
    main()