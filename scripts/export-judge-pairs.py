#!/usr/bin/env python3
"""Rebuild the locked two-judge pair table and its frozen provenance sidecar."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VAR_CLAUDE = ROOT / "data/raw/judged.var.claude.jsonl.gz"
VAR_GPT = ROOT / "data/raw/judged.var.gpt55.jsonl.gz"
WAVE2 = ROOT / "data/raw/judged.wave2.jsonl.gz"
RESULTS = ROOT / "data/snapshots/results_snapshot.csv"
OUT = ROOT / "data/site/judge_pairs.csv"
PROVENANCE_OUT = ROOT / "data/snapshots/judge_pair_provenance.csv"

CLAUDE = ("copilot", "claude-opus-4.8")
GPT = ("copilot", "gpt-5.5")
EXPECTED_JUDGES = frozenset({CLAUDE, GPT})
EVALUATION_POLICY = (
    "deterministic-checks-v1|judges:"
    "copilot:claude-opus-4.8+copilot:gpt-5.5"
)
PAIR_FIELDS = [
    "analysis_schema_version", "model", "scenario", "rep",
    "claude_score", "gpt_score",
]
PROVENANCE_FIELDS = [
    "analysis_schema_version", "frozen_pair_key_sha256",
    "condition_identity_incomplete", "model", "runtime_adapter",
    "collection_batch", "cpu_frequency_regime", "power_source",
    "energy_analysis_scope", "scenario", "rep", "evaluation_policy",
    "judge_source_batch", "claude_backend", "claude_model",
    "gpt_backend", "gpt_model",
]


def read_jsonl_gz(path: Path) -> list[dict]:
    with gzip.open(path, "rt") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_judgements(paths: list[Path]) -> dict[tuple[str, str, str], dict[tuple[str, str], int]]:
    grouped: defaultdict[tuple[str, str, str], dict[tuple[str, str], int]] = defaultdict(dict)
    for path in paths:
        for row in read_jsonl_gz(path):
            if row.get("score") is None:
                continue
            key = (str(row["model"]), str(row["scenario"]), str(row.get("rep")))
            judge = (
                str(row.get("judge_backend") or "unknown"),
                str(row.get("judge_model") or "unknown"),
            )
            if judge not in EXPECTED_JUDGES:
                raise ValueError(f"{path}: undeclared judge identity {judge[0]}:{judge[1]}")
            if judge in grouped[key]:
                raise ValueError(f"{path}: duplicate judgement for {key} from {judge}")
            grouped[key][judge] = int(round(float(row["score"])))
    return dict(grouped)


def load_result_provenance() -> tuple[dict[tuple[str, str, str], dict], set[str]]:
    with RESULTS.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_key = {}
    functional_models = set()
    for row in rows:
        key = (row["model"], row["scenario"], row["rep"])
        if key in by_key:
            raise ValueError(f"duplicate frozen result key: {key}")
        by_key[key] = row
        if str(row.get("dnf")).lower() != "true":
            functional_models.add(row["model"])
    return by_key, functional_models


def frozen_pair_hash(row: dict) -> str:
    payload = {
        field: row[field]
        for field in (
            "model", "runtime_adapter", "collection_batch",
            "cpu_frequency_regime", "power_source", "energy_analysis_scope",
            "scenario", "rep", "evaluation_policy",
        )
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_rows() -> tuple[list[dict], list[dict]]:
    first_batch = load_judgements([VAR_CLAUDE, VAR_GPT])
    second_batch = load_judgements([WAVE2])
    combined = dict(first_batch)
    combined.update(second_batch)  # Wave 2 is authoritative for its overlap model.
    result_provenance, functional_models = load_result_provenance()

    pair_rows = []
    provenance_rows = []
    for key in sorted(combined):
        model, scenario, rep = key
        scores = combined[key]
        if model not in functional_models or frozenset(scores) != EXPECTED_JUDGES:
            continue
        result = result_provenance.get(key)
        if result is None:
            raise ValueError(f"judge pair has no frozen result provenance: {key}")
        pair_rows.append({
            "analysis_schema_version": "1",
            "model": model,
            "scenario": scenario,
            "rep": rep,
            "claude_score": str(scores[CLAUDE]),
            "gpt_score": str(scores[GPT]),
        })
        provenance = {
            "analysis_schema_version": "1",
            "condition_identity_incomplete": "1",
            "model": model,
            "runtime_adapter": result["runtime_adapter"],
            "collection_batch": result["collection_batch"],
            "cpu_frequency_regime": result["cpu_frequency_regime"],
            "power_source": result["power_source"],
            "energy_analysis_scope": result["energy_analysis_scope"],
            "scenario": scenario,
            "rep": rep,
            "evaluation_policy": EVALUATION_POLICY,
            "judge_source_batch": "wave2" if key in second_batch else "var",
            "claude_backend": CLAUDE[0],
            "claude_model": CLAUDE[1],
            "gpt_backend": GPT[0],
            "gpt_model": GPT[1],
        }
        provenance["frozen_pair_key_sha256"] = frozen_pair_hash(provenance)
        provenance_rows.append(provenance)

    if len(pair_rows) != 8_909:
        raise ValueError(f"locked pair population changed: {len(pair_rows)} != 8909")
    return pair_rows, provenance_rows


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="compare regenerated rows without writing")
    args = parser.parse_args()
    pairs, provenance = build_rows()
    if args.check:
        if read_csv(OUT) != pairs:
            raise SystemExit(f"{OUT.relative_to(ROOT)} differs from committed raw judge evidence")
        if not PROVENANCE_OUT.exists() or read_csv(PROVENANCE_OUT) != provenance:
            raise SystemExit(f"{PROVENANCE_OUT.relative_to(ROOT)} differs from committed raw judge evidence")
        print(f"judge pair evidence passed: pairs={len(pairs)} provenance={len(provenance)}")
        return
    write_csv(OUT, PAIR_FIELDS, pairs)
    write_csv(PROVENANCE_OUT, PROVENANCE_FIELDS, provenance)
    print(f"wrote {OUT.relative_to(ROOT)} and {PROVENANCE_OUT.relative_to(ROOT)}: {len(pairs)} pairs")


if __name__ == "__main__":
    main()