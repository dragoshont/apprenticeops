#!/usr/bin/env python3
"""Normalize the frozen ApprenticeOps analysis bundle to canonical schema v1.

This is a deterministic metadata/column migration over committed snapshots. It
does not read the active run and does not recompute model outputs or judge scores.
The notebook subsequently regenerates public exports from these snapshots.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "data/snapshots/results_snapshot.csv"
JUDGED = REPO / "data/snapshots/judged_snapshot.csv"
JUDGED_DET = REPO / "data/snapshots/judged_snapshot.det.csv"
MODEL_LOCK = REPO / "data/models.lock.jsonl"
MANIFEST = REPO / "data/analysis-manifest.json"
RAW_RESULTS = {
    "var": REPO / "data/raw/results.var.jsonl.gz",
    "wave2": REPO / "data/raw/results.wave2.jsonl.gz",
}
RAW_OUTPUTS = {
    "var": REPO / "data/raw/outputs.var.tar.gz",
    "wave2": REPO / "data/raw/outputs.wave2.tar.gz",
}
SCENARIOS = REPO / "data/scenarios.json"
RAW_JUDGEMENTS = [
    REPO / "data/raw/judged.var.claude.jsonl.gz",
    REPO / "data/raw/judged.var.gpt55.jsonl.gz",
    REPO / "data/raw/judged.det.jsonl.gz",
    REPO / "data/raw/judged.det.gpt55.jsonl.gz",
    REPO / "data/raw/judged.wave2.jsonl.gz",
]
JUDGE_PAIRS = REPO / "data/site/judge_pairs.csv"
JUDGE_PAIR_PROVENANCE = REPO / "data/snapshots/judge_pair_provenance.csv"
CPU_FREQUENCY_REGIMES = {
    "var": "base_clock_1700_turbo_off",
    "wave2": "dynamic_above_base_turbo_on",
}

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
RENAMES = {
    "adapter": "runtime_adapter",
    "bracket": "legacy_footprint_bracket",
    "decode_tok_s": "decode_tokens_per_s",
    "prefill_tok_s": "prefill_tokens_per_s",
    "param_count": "parameter_count",
    "param_size": "parameter_size_label",
    "quant": "quantization",
    "size_bytes": "artifact_size_bytes",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_tiers() -> dict[str, str | None]:
    tiers = {}
    with MODEL_LOCK.open() as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                tiers[row["model_id"]] = row.get("tier")
    return tiers


def _number(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _same_number(left: object, right: object) -> bool:
    left_number, right_number = _number(left), _number(right)
    if left_number is None or right_number is None:
        return left_number is None and right_number is None
    return math.isclose(left_number, right_number, rel_tol=0.0, abs_tol=1e-12)


def load_raw_lineage() -> dict[tuple[str, str, str], list[dict[str, object]]]:
    lineage: dict[tuple[str, str, str], list[dict[str, object]]] = {}
    for batch, path in RAW_RESULTS.items():
        if not path.exists():
            raise SystemExit(f"missing raw lineage source: {path.relative_to(REPO)}")
        with gzip.open(path, "rt") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("fatal") or row.get("scenario") is None or row.get("rep") is None:
                    continue
                key = (str(row.get("model")), str(row.get("scenario")), str(row.get("rep")))
                lineage.setdefault(key, []).append({
                    "collection_batch": batch,
                    "cpu_frequency_regime": CPU_FREQUENCY_REGIMES[batch],
                    "power_source": row.get("power.source") or "",
                    "energy_wh": row.get("power.energy_wh"),
                    "det_score": row.get("det_score"),
                    "finish_reason": (row.get("gen_ai.response.finish_reasons") or [None])[0],
                })
    return lineage


def resolve_result_lineage(
    row: dict[str, str],
    lineage: dict[tuple[str, str, str], list[dict[str, object]]],
) -> dict[str, object]:
    key = (str(row.get("model")), str(row.get("scenario")), str(row.get("rep")))
    candidates = lineage.get(key, [])
    matches = [
        candidate
        for candidate in candidates
        if _same_number(row.get("energy_wh"), candidate.get("energy_wh"))
        and _same_number(row.get("det_score"), candidate.get("det_score"))
        and str(row.get("finish_reason") or "") == str(candidate.get("finish_reason") or "")
    ]
    unique = {
        (
            str(candidate["collection_batch"]),
            str(candidate["cpu_frequency_regime"]),
            str(candidate["power_source"]),
        )
        for candidate in matches
    }
    if len(unique) != 1:
        raise SystemExit(
            "cannot resolve unique raw lineage for "
            f"{key}: matches={sorted(unique)} candidates={len(candidates)}"
        )
    collection_batch, cpu_frequency_regime, power_source = next(iter(unique))
    return {
        "collection_batch": collection_batch,
        "cpu_frequency_regime": cpu_frequency_regime,
        "power_source": power_source,
        "energy_analysis_scope": (
            "controlled_three_axis"
            if collection_batch == "var" and power_source == "rapl:package-0"
            else "descriptive_only"
        ),
    }


def normalize_results(
    path: Path,
    columns: list[str],
    tiers: dict[str, str | None],
    lineage: dict[tuple[str, str, str], list[dict[str, object]]],
) -> tuple[int, dict[tuple[str, str, str], dict[str, object]]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    normalized = []
    resolved: dict[tuple[str, str, str], dict[str, object]] = {}
    for source in rows:
        row = dict(source)
        for old, new in RENAMES.items():
            if old in row and new not in row:
                row[new] = row[old]
        row["analysis_schema_version"] = "1"
        row["runtime_adapter"] = row.get("runtime_adapter") or "ollama"
        row["parameter_tier"] = tiers.get(row.get("model")) or ""
        provenance = resolve_result_lineage(row, lineage)
        row.update(provenance)
        key = (str(row.get("model")), str(row.get("scenario")), str(row.get("rep")))
        resolved[key] = provenance
        normalized.append({column: row.get(column, "") for column in columns})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(normalized)
    return len(normalized), resolved


def normalize_judged(
    path: Path,
    columns: list[str],
    tiers: dict[str, str | None],
    resolved: dict[tuple[str, str, str], dict[str, object]],
) -> int:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    normalized = []
    model_provenance: dict[str, dict[str, object]] = {}
    for (model, _scenario, _rep), provenance in resolved.items():
        current = model_provenance.get(model)
        if current is not None and current["collection_batch"] != provenance["collection_batch"]:
            raise SystemExit(f"model spans multiple canonical batches: {model}")
        model_provenance[model] = provenance
    for source in rows:
        row = dict(source)
        for old, new in RENAMES.items():
            if old in row and new not in row:
                row[new] = row[old]
        row["analysis_schema_version"] = "1"
        row["runtime_adapter"] = row.get("runtime_adapter") or "ollama"
        row["parameter_tier"] = tiers.get(row.get("model")) or ""
        key = (str(row.get("model")), str(row.get("scenario")), str(row.get("rep")))
        provenance = resolved.get(key) or model_provenance.get(str(row.get("model")))
        if provenance is None:
            raise SystemExit(f"cannot resolve judged lineage for {key}")
        row["collection_batch"] = provenance["collection_batch"]
        row["cpu_frequency_regime"] = provenance["cpu_frequency_regime"]
        normalized.append({column: row.get(column, "") for column in columns})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(normalized)
    return len(normalized)


def write_manifest() -> None:
    sources = [
        *RAW_RESULTS.values(),
        *RAW_OUTPUTS.values(),
        *RAW_JUDGEMENTS,
        SCENARIOS,
        MODEL_LOCK,
        RESULTS,
        JUDGED,
        JUDGED_DET,
        JUDGE_PAIRS,
        JUDGE_PAIR_PROVENANCE,
    ]

    def source_name(path: Path) -> str:
        try:
            return str(path.relative_to(REPO))
        except ValueError:
            return path.name

    manifest = {
        "analysis_schema_version": 1,
        "source_kind": "frozen_snapshot",
        "source_id": "paper-94-model-corrected-v1",
        "source_sha256": {source_name(path): sha256(path) for path in sources},
        "claim_status": "locked",
        "provenance_note": (
            "Raw result rows, answer archives, scenario semantics, and per-judge "
            "verdict rows for both collection batches are committed and hash-bound. "
            "The paper-era rows predate complete canonical condition identity, so "
            "judge_pair_provenance.csv marks "
            "condition_identity_incomplete=1 and supplies a frozen provenance key; "
            "it must not be reused for cross-run joins."
        ),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate headers without writing")
    args = parser.parse_args()
    tiers = load_tiers()
    expected = [(RESULTS, RESULT_COLUMNS), (JUDGED, JUDGED_COLUMNS), (JUDGED_DET, JUDGED_COLUMNS)]
    if args.check:
        for path, columns in expected:
            with path.open(newline="") as handle:
                observed = next(csv.reader(handle), [])
            if observed != columns:
                raise SystemExit(f"{path.relative_to(REPO)} is not canonical v1")
        print("analysis snapshot v1 headers passed")
        return
    lineage = load_raw_lineage()
    result_count, resolved = normalize_results(RESULTS, RESULT_COLUMNS, tiers, lineage)
    counts = [
        result_count,
        normalize_judged(JUDGED, JUDGED_COLUMNS, tiers, resolved),
        normalize_judged(JUDGED_DET, JUDGED_COLUMNS, tiers, resolved),
    ]
    write_manifest()
    print(f"migrated analysis snapshots to v1: results={counts[0]} judged={counts[1]} det={counts[2]}")


if __name__ == "__main__":
    main()