#!/usr/bin/env python3
"""Generate a field catalog from actual ApprenticeOps JSONL artifacts.

This intentionally uses observed rows as the source of truth for field names and
data types. Descriptions come from data/row-field-descriptions.json using exact
matches first, then prefix matches.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
DEFAULT_DESCRIPTIONS = REPO / "data" / "row-field-descriptions.json"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int) and not isinstance(value, bool):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return type(value).__name__


def describe(name: str, catalog: dict[str, Any], *, sample: bool = False) -> tuple[str, str]:
    exact = catalog.get("exact", {}).get(name)
    if exact:
        return exact.get("category", "uncategorized"), exact.get("description", "")
    key = "sample_prefix" if sample else "prefix"
    for item in catalog.get(key, []):
        prefix = item.get("prefix") or ""
        if name.startswith(prefix):
            return item.get("category", "uncategorized"), item.get("description", "")
    return "uncategorized", "Undocumented observed field. Add an exact or prefix entry to data/row-field-descriptions.json."


def summarize_fields(rows: list[dict[str, Any]], catalog: dict[str, Any], *, sample: bool = False) -> list[dict[str, Any]]:
    fields = sorted(set().union(*(row.keys() for row in rows))) if rows else []
    out = []
    for field in fields:
        values = [row.get(field) for row in rows]
        non_null = [value for value in values if value not in (None, "", [])]
        types = sorted({type_name(value) for value in values if value is not None}) or ["null"]
        category, description = describe(field, catalog, sample=sample)
        out.append({
            "field": field,
            "category": category,
            "types": types,
            "rows": len(rows),
            "non_null": len(non_null),
            "missing": len(rows) - len(non_null),
            "description": description,
        })
    return out


def flatten_samples(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for row in rows:
        for sample in row.get("samples") or []:
            if isinstance(sample, dict):
                samples.append(sample)
    return samples


def markdown_table(title: str, fields: list[dict[str, Any]]) -> str:
    lines = [f"## {title}", "", "| Field | Category | Type(s) | Non-null | Missing | Description |", "|---|---|---|---:|---:|---|"]
    for item in fields:
        types = ", ".join(item["types"])
        desc = str(item["description"]).replace("|", "\\|")
        lines.append(f"| `{item['field']}` | {item['category']} | {types} | {item['non_null']} | {item['missing']} | {desc} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", action="append", type=Path, default=[], help="Raw results JSONL path. May be repeated.")
    parser.add_argument("--judged", action="append", type=Path, default=[], help="Judged JSONL path. May be repeated.")
    parser.add_argument("--run-meta", action="append", type=Path, default=[], help="run.meta JSON path. May be repeated.")
    parser.add_argument("--descriptions", type=Path, default=DEFAULT_DESCRIPTIONS)
    parser.add_argument("--out", type=Path, default=REPO / "docs" / "ROW_FIELD_CATALOG.md")
    parser.add_argument("--json-out", type=Path, default=REPO / "docs" / "row-field-catalog.generated.json")
    parser.add_argument("--run-id", default="manual")
    args = parser.parse_args()

    catalog = json.loads(args.descriptions.read_text(encoding="utf-8"))
    raw_rows = [row for path in args.results for row in load_jsonl(path)]
    judged_rows = [row for path in args.judged for row in load_jsonl(path)]
    meta_rows = [json.loads(path.read_text(encoding="utf-8")) for path in args.run_meta]
    sample_rows = flatten_samples(raw_rows)

    sections = {
        "raw_rows": summarize_fields(raw_rows, catalog),
        "samples": summarize_fields(sample_rows, catalog, sample=True),
        "judged_rows": summarize_fields(judged_rows, catalog),
        "run_meta": summarize_fields(meta_rows, catalog),
    }
    counts = {
        "raw_rows": len(raw_rows),
        "raw_fields": len(sections["raw_rows"]),
        "sample_rows": len(sample_rows),
        "sample_fields": len(sections["samples"]),
        "judged_rows": len(judged_rows),
        "judged_fields": len(sections["judged_rows"]),
        "run_meta_rows": len(meta_rows),
        "run_meta_fields": len(sections["run_meta"]),
    }
    categories = Counter(item["category"] for section in sections.values() for item in section)
    payload = {"run_id": args.run_id, "counts": counts, "categories": dict(sorted(categories.items())), "sections": sections}

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    md = [
        "# ApprenticeOps Row Field Catalog",
        "",
        "Status: generated field catalog. Regenerate with `scripts/generate-row-field-catalog.py` from an actual run artifact.",
        "",
        f"Source run: `{args.run_id}`",
        "",
        "This file is generated from observed JSON artifacts plus `data/row-field-descriptions.json`. If a field is listed as undocumented, update the description map rather than editing this table by hand.",
        "",
        "## Counts",
        "",
        "| Artifact | Rows | Fields |",
        "|---|---:|---:|",
        f"| Raw result rows | {counts['raw_rows']} | {counts['raw_fields']} |",
        f"| `samples[]` entries | {counts['sample_rows']} | {counts['sample_fields']} |",
        f"| Judged rows | {counts['judged_rows']} | {counts['judged_fields']} |",
        f"| `run.meta` rows | {counts['run_meta_rows']} | {counts['run_meta_fields']} |",
        "",
        markdown_table("Raw Result Row Fields", sections["raw_rows"]),
        markdown_table("Sample Fields", sections["samples"]),
        markdown_table("Judged Row Fields", sections["judged_rows"]),
        markdown_table("Run Metadata Fields", sections["run_meta"]),
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(md), encoding="utf-8")


if __name__ == "__main__":
    main()