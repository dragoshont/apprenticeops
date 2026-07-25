#!/usr/bin/env python3
"""Build canonical analysis v1 snapshots from a locked completed-run bundle.

WHY A SECOND BUILDER. `scripts/migrate-analysis-v1.py` normalizes the frozen
paper lane *in place*, and most of its work is resolving per-row provenance
across two collection batches whose condition identity is incomplete. A promoted
completed run needs none of that: it is a single batch, every row carries
`condition_identity_incomplete=false`, and the environment fields are constant
across the whole run. So this builder derives the same canonical schema directly
from the locked bundle, and asserts that constancy instead of inferring it.

WHAT IT DOES NOT DO. It never writes into the frozen lane. The 94-model frozen
evidence stays intact and citable; the completed run gets its own lane
directory. Nothing here changes `data/analysis-manifest.json` or any claim
status - producing the snapshots and locking a claim are deliberately separate
steps.

Usage:
  scripts/build-analysis-v1-from-bundle.py --bundle <path> [--out <dir>]
  scripts/build-analysis-v1-from-bundle.py --bundle <path> --check
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODEL_LOCK = REPO / "data/models.lock.jsonl"

# Frozen-lane artifacts this builder must never overwrite.
FROZEN_ARTIFACTS = {
    REPO / "data/snapshots/results_snapshot.csv",
    REPO / "data/snapshots/judged_snapshot.csv",
    REPO / "data/snapshots/judged_snapshot.det.csv",
    REPO / "data/snapshots/judge_pair_provenance.csv",
    REPO / "data/site/judge_pairs.csv",
    REPO / "data/analysis-manifest.json",
}

# Canonical analysis v1 schema. Kept byte-identical to the frozen lane so the
# public notebooks can consume either lane unchanged; `--check` proves it.
RESULT_COLUMNS = [
    "analysis_schema_version", "model", "runtime_adapter", "parameter_tier",
    "legacy_footprint_bracket", "collection_batch", "cpu_frequency_regime",
    "power_source", "energy_analysis_scope", "scenario", "rep", "det_score",
    "decode_tokens_per_s", "prefill_tokens_per_s", "wall_s",
    "membw_peak_mb_s", "energy_wh", "parameter_count",
    "parameter_size_label", "quantization", "artifact_size_bytes",
    "expert_count", "expert_used_count", "dnf", "finish_reason",
]
JUDGED_COLUMNS = [
    "analysis_schema_version", "model", "runtime_adapter", "parameter_tier",
    "legacy_footprint_bracket", "collection_batch", "cpu_frequency_regime",
    "scenario", "rep", "judge_score",
]
JUDGE_PAIR_COLUMNS = [
    "analysis_schema_version", "model", "scenario", "rep",
    "claude_score", "gpt_score",
]

# Bundle field -> canonical column.
RESULT_SOURCE = {
    "model": "model",
    "runtime_adapter": "adapter",
    "legacy_footprint_bracket": "bracket",
    "power_source": "power.source",
    "scenario": "scenario",
    "rep": "rep",
    "det_score": "det_score",
    "decode_tokens_per_s": "decode_tok_s",
    "prefill_tokens_per_s": "prefill_tok_s",
    "wall_s": "wall_s",
    "membw_peak_mb_s": "membw.peak_mb_s",
    "energy_wh": "power.energy_wh",
    "parameter_count": "ollama.parameter_count",
    "parameter_size_label": "ollama.parameter_size",
    "quantization": "ollama.quantization",
    "artifact_size_bytes": "ollama.size_bytes",
    "expert_count": "ollama.expert_count",
    "expert_used_count": "ollama.expert_used_count",
    "dnf": "dnf",
}

# Environment fields that MUST be constant for the run to be a single condition.
CONSTANT_ENV = [
    "env.inference_runtime", "env.inference_strategy", "env.memory_context",
    "env.scenario_set", "env.scenarios_sha", "env.ollama_version",
    "env.cpu_governor", "env.cpu_no_turbo", "env.cpu_max_perf_pct",
    "env.cpu_min_perf_pct", "env.rapl_domain", "env.host", "env.run_id",
    "prompt.template_sha256", "evaluation_policy", "adapter", "power.source",
]

CONTROLLED_POWER_SOURCE = "rapl:package-0"


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_bundle_file(bundle: Path, relative: str) -> Path:
    """Return a bundle file only after its hash matches the bundle manifest."""
    manifest_path = bundle / "bundle-manifest.json"
    if not manifest_path.exists():
        fail(f"not a locked bundle (no bundle-manifest.json): {bundle}")
    manifest = json.loads(manifest_path.read_text())
    expected = (manifest.get("source_sha256") or {}).get(relative)
    if not expected:
        fail(f"bundle manifest does not bind {relative}")
    path = bundle / relative
    if not path.exists():
        fail(f"missing bundle file: {path}")
    observed = sha256(path)
    if observed != expected:
        fail(f"{relative} hash mismatch\n  expected {expected}\n  observed {observed}")
    return path


def load_tiers() -> dict[str, str]:
    tiers: dict[str, str] = {}
    with MODEL_LOCK.open() as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                tiers[row["model_id"]] = row.get("tier") or ""
    return tiers


def read_jsonl_gz(path: Path):
    with gzip.open(path, "rt") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def cell_sort_key(row: dict[str, object]) -> tuple[str, str, int]:
    return (str(row["model"]), str(row["scenario"]), int(row["rep"]))


def value(raw: object) -> str:
    """Deterministic CSV rendering; None and NaN become the empty string."""
    if raw is None:
        return ""
    if isinstance(raw, bool):
        return str(raw)
    if isinstance(raw, float) and raw != raw:  # NaN
        return ""
    return str(raw)


def build(bundle: Path, out_dir: Path, write: bool) -> dict[str, object]:
    results_path = verify_bundle_file(bundle, "canonical/results.jsonl.gz")
    judged_path = verify_bundle_file(bundle, "canonical/judged.jsonl.gz")
    manifest = json.loads((bundle / "bundle-manifest.json").read_text())
    tiers = load_tiers()

    constants: dict[str, set[str]] = defaultdict(set)
    incomplete = 0
    results: list[dict[str, object]] = []
    missing_tier: set[str] = set()

    for row in read_jsonl_gz(results_path):
        for key in CONSTANT_ENV:
            constants[key].add(value(row.get(key)))
        if row.get("condition_identity_incomplete"):
            incomplete += 1
        model = str(row.get("model"))
        if model not in tiers:
            missing_tier.add(model)
        power_source = value(row.get("power.source"))
        record = {column: value(row.get(source)) for column, source in RESULT_SOURCE.items()}
        record["analysis_schema_version"] = "1"
        record["runtime_adapter"] = record["runtime_adapter"] or "ollama"
        record["parameter_tier"] = tiers.get(model, "")
        record["collection_batch"] = str(manifest["source_id"])
        record["energy_analysis_scope"] = (
            "controlled_three_axis"
            if power_source == CONTROLLED_POWER_SOURCE
            else "descriptive_only"
        )
        finish = row.get("gen_ai.response.finish_reasons") or [None]
        record["finish_reason"] = value(finish[0] if isinstance(finish, list) else finish)
        results.append(record)

    if incomplete:
        fail(f"{incomplete} rows carry condition_identity_incomplete=true; "
             "this bundle is not a single canonical condition")
    if missing_tier:
        fail(f"{len(missing_tier)} models absent from data/models.lock.jsonl, "
             f"e.g. {sorted(missing_tier)[:3]}")
    for key in CONSTANT_ENV:
        if len(constants[key]) != 1:
            fail(f"{key} is not constant across the run ({len(constants[key])} values); "
                 "conditions are not identical")

    governor = next(iter(constants["env.cpu_governor"]))
    no_turbo = next(iter(constants["env.cpu_no_turbo"]))
    max_pct = next(iter(constants["env.cpu_max_perf_pct"]))
    min_pct = next(iter(constants["env.cpu_min_perf_pct"]))
    regime = (
        f"governor_{governor}"
        f"_turbo_{'off' if str(no_turbo) == '1' else 'on'}"
        f"_perf_pct_{min_pct}_{max_pct}"
    )
    for record in results:
        record["cpu_frequency_regime"] = regime

    # Judged: collapse per-judge rows to the two-judge consensus mean, matching
    # the frozen lane's judge_score semantics (verified: mean, not max/min).
    per_cell: dict[tuple[str, str, int], dict[str, float]] = defaultdict(dict)
    judges: Counter[str] = Counter()
    for row in read_jsonl_gz(judged_path):
        key = (str(row["model"]), str(row["scenario"]), int(row["rep"]))
        judge = str(row.get("judge_model"))
        judges[judge] += 1
        score = row.get("score")
        if score is None:
            continue
        per_cell[key][judge] = float(score)

    if len(judges) != 2:
        fail(f"expected exactly 2 judges, found {sorted(judges)}")
    claude_judge = next((j for j in judges if j.startswith("claude")), None)
    gpt_judge = next((j for j in judges if j.startswith("gpt")), None)
    if not claude_judge or not gpt_judge:
        fail(f"cannot identify a claude/gpt judge pair in {sorted(judges)}")

    identity = {(r["model"], r["scenario"], int(r["rep"])): r for r in results}

    judged_rows: list[dict[str, object]] = []
    pair_rows: list[dict[str, object]] = []
    for key, scores in per_cell.items():
        base = identity.get(key)
        if base is None:
            fail(f"judged cell has no primary row: {key}")
        mean = sum(scores.values()) / len(scores)
        judged_rows.append({
            "analysis_schema_version": "1",
            "model": base["model"],
            "runtime_adapter": base["runtime_adapter"],
            "parameter_tier": base["parameter_tier"],
            "legacy_footprint_bracket": base["legacy_footprint_bracket"],
            "collection_batch": base["collection_batch"],
            "cpu_frequency_regime": base["cpu_frequency_regime"],
            "scenario": base["scenario"],
            "rep": base["rep"],
            "judge_score": mean,
        })
        if claude_judge in scores and gpt_judge in scores:
            pair_rows.append({
                "analysis_schema_version": "1",
                "model": base["model"],
                "scenario": base["scenario"],
                "rep": base["rep"],
                "claude_score": scores[claude_judge],
                "gpt_score": scores[gpt_judge],
            })

    results.sort(key=cell_sort_key)
    judged_rows.sort(key=cell_sort_key)
    pair_rows.sort(key=cell_sort_key)

    summary = {
        "run_id": manifest["source_id"],
        "bundle_id": manifest["bundle_id"],
        "evaluation_policy": manifest["evaluation_policy"],
        "judges": {"claude": claude_judge, "gpt": gpt_judge},
        "collection_batch": str(manifest["source_id"]),
        "cpu_frequency_regime": regime,
        "power_source": next(iter(constants["power.source"])),
        "energy_analysis_scope": sorted({r["energy_analysis_scope"] for r in results}),
        "condition_identity_incomplete": 0,
        "counts": {
            "results": len(results),
            "judged_cells": len(judged_rows),
            "complete_judge_pairs": len(pair_rows),
            "models": len({r["model"] for r in results}),
            "scenarios": len({r["scenario"] for r in results}),
        },
        "constant_environment": {k: sorted(v)[0] for k, v in sorted(constants.items())},
    }

    if not write:
        return summary

    for target in (out_dir / "results_snapshot.csv",
                   out_dir / "judged_snapshot.csv",
                   out_dir / "judge_pairs.csv"):
        if target.resolve() in {p.resolve() for p in FROZEN_ARTIFACTS if p.exists()}:
            fail(f"refusing to overwrite frozen-lane artifact: {target}")

    out_dir.mkdir(parents=True, exist_ok=True)
    for name, columns, rows in (
        ("results_snapshot.csv", RESULT_COLUMNS, results),
        ("judged_snapshot.csv", JUDGED_COLUMNS, judged_rows),
        ("judge_pairs.csv", JUDGE_PAIR_COLUMNS, pair_rows),
    ):
        path = out_dir / name
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            writer.writerows([{c: row.get(c, "") for c in columns} for row in rows])
        summary.setdefault("artifact_sha256", {})[name] = sha256(path)

    (out_dir / "lane.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def check_schema_matches_frozen() -> None:
    """The lane is only drop-in if its headers equal the frozen lane's."""
    pairs = [
        (REPO / "data/snapshots/results_snapshot.csv", RESULT_COLUMNS),
        (REPO / "data/snapshots/judged_snapshot.csv", JUDGED_COLUMNS),
        (REPO / "data/site/judge_pairs.csv", JUDGE_PAIR_COLUMNS),
    ]
    for path, columns in pairs:
        if not path.exists():
            continue
        with path.open(newline="") as handle:
            observed = next(csv.reader(handle), [])
        if observed != columns:
            fail(f"schema drift vs frozen lane in {path.relative_to(REPO)}\n"
                 f"  frozen  : {observed}\n  builder : {columns}")
    print("schema check passed: builder emits the frozen lane's canonical v1 headers")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True, help="locked completed-run bundle directory")
    parser.add_argument("--out", default="", help="lane output directory")
    parser.add_argument("--check", action="store_true",
                        help="validate schema and bundle without writing")
    args = parser.parse_args()

    bundle = Path(args.bundle)
    if not bundle.is_absolute():
        bundle = REPO / bundle
    if not bundle.is_dir():
        fail(f"bundle directory not found: {bundle}")

    check_schema_matches_frozen()
    manifest = json.loads((bundle / "bundle-manifest.json").read_text())
    out_dir = Path(args.out) if args.out else REPO / "data/snapshots" / str(manifest["source_id"])
    if not out_dir.is_absolute():
        out_dir = REPO / out_dir

    summary = build(bundle, out_dir, write=not args.check)
    print(json.dumps(summary, indent=2))
    if args.check:
        print("\ncheck only: nothing written")
    else:
        print(f"\nwrote lane -> {out_dir.relative_to(REPO)}")


if __name__ == "__main__":
    main()
