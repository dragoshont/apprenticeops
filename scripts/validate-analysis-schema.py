#!/usr/bin/env python3
"""Validate canonical analysis v1 artifacts and their locked manifest."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import analysis_metrics  # noqa: E402

SCHEMA = REPO / "data/analysis.schema.json"
MANIFEST = REPO / "data/analysis-manifest.json"
ARTIFACTS = {
    "paper_results_snapshot_csv": ["data/snapshots/results_snapshot.csv"],
    "paper_judged_snapshot_csv": [
        "data/snapshots/judged_snapshot.csv",
        "data/snapshots/judged_snapshot.det.csv",
    ],
    "site_models_csv": ["data/site/models.csv"],
    "site_controlled_models_csv": ["data/site/controlled_models.csv"],
    "site_pareto_csv": ["data/site/pareto.csv"],
    "site_quality_safety_pareto_csv": ["data/site/quality_safety_pareto.csv"],
    "site_axis_quality_csv": ["data/site/axis_quality.csv"],
    "site_axis_safety_csv": [
        "data/site/axis_safety_arm.csv",
        "data/site/axis_safety_bracket.csv",
    ],
    "site_axis_energy_csv": ["data/site/axis_energy.csv"],
    "site_judge_pairs_csv": ["data/site/judge_pairs.csv"],
    "judge_pair_provenance_csv": ["data/snapshots/judge_pair_provenance.csv"],
    "site_summary_json": ["data/site/summary.json"],
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    value.update(path.read_bytes())
    return value.hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def columns(path: Path) -> list[str]:
    with path.open(newline="") as handle:
        return next(csv.reader(handle), [])


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    schema = analysis_metrics.load_analysis_schema(str(SCHEMA))
    if not MANIFEST.exists():
        fail("missing data/analysis-manifest.json")
    manifest = json.loads(MANIFEST.read_text())
    errors = analysis_metrics.validate_analysis_manifest(manifest, claim_bearing=True)
    if errors:
        fail("; ".join(errors))
    for relative, expected in (manifest.get("source_sha256") or {}).items():
        path = REPO / relative
        if not path.exists() or digest(path) != expected:
            fail(f"manifest source hash mismatch: {relative}")
    checked = 0
    for contract, paths in ARTIFACTS.items():
        for relative in paths:
            path = REPO / relative
            if not path.exists():
                fail(f"missing analysis artifact: {relative}")
            if path.suffix == ".json":
                payload = json.loads(path.read_text())
                observed = list(payload.keys())
                if payload.get("analysis_schema_version") != analysis_metrics.ANALYSIS_SCHEMA_VERSION:
                    fail(f"{relative}: analysis_schema_version is not 1")
                if contract == "site_summary_json":
                    if payload.get("source_id") != manifest.get("source_id"):
                        fail(f"{relative}: source_id does not match analysis manifest")
                    if payload.get("claim_status") != manifest.get("claim_status"):
                        fail(f"{relative}: claim_status does not match analysis manifest")
            else:
                observed = columns(path)
                rows = csv_rows(path)
                versions = {row.get("analysis_schema_version") for row in rows}
                if versions != {str(analysis_metrics.ANALYSIS_SCHEMA_VERSION)}:
                    fail(f"{relative}: row analysis_schema_version values are {sorted(versions)}")
            errors = analysis_metrics.validate_artifact_columns(schema, contract, observed)
            if errors:
                fail(f"{relative}: {'; '.join(errors)}")
            checked += 1
    print(f"analysis schema v1 artifacts passed: {checked}")


if __name__ == "__main__":
    main()