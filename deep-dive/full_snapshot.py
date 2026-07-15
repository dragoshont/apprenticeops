"""Emit the tracked, portable, claim-locked reproduction artifacts for the 152-model
full run from the durable locked bundle.

The heavy raw run (`.tmp/completed-run-intake/...`, ~1.1 GB) and the promoted, hash-
bound locked bundle (`data/completed-runs/<run>-<bundle_id>/`, ~433 MB) are BOTH
gitignored by design. This script derives two compact, tracked CSVs that ARE the
serialized `full_data._load_results()` / `_load_judged()` frames, so a fresh clone with
neither heavy artifact can still recompute every 152-run number (`full_data.py` falls
back to them). It also writes a tracked claim-lock manifest that binds the canonical
bundle inputs and the two CSVs by sha256, mirroring `data/analysis-manifest.json` (the
94-model pattern). Nothing here re-judges or recomputes bundle hashes — it reuses the
pipeline's own `bundle-manifest.json` / `gate-report.json`.

Run: `deep-dive/.venv/bin/python deep-dive/full_snapshot.py`
"""

from __future__ import annotations

import hashlib
import json

import full_data as F


def _sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    canon = F.LOCKED / "canonical"
    if not (canon / "results.jsonl.gz").exists():
        raise SystemExit(f"locked bundle not found at {F.LOCKED} — cannot generate a "
                         "trustworthy snapshot from an ephemeral/absent source.")

    # --- compact tracked snapshots = the exact loader frames, deterministically ordered ---
    res = F._load_results().sort_values(["model", "scenario", "rep"], kind="stable")
    jud = F._load_judged().sort_values(["model", "scenario", "rep", "judge_model"], kind="stable")
    F._SNAP_RESULTS.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(F._SNAP_RESULTS, index=False)
    jud.to_csv(F._SNAP_JUDGED, index=False)
    print(f"results snapshot: {len(res):,} rows -> {F._SNAP_RESULTS.relative_to(F.REPO)}")
    print(f"judged  snapshot: {len(jud):,} rows -> {F._SNAP_JUDGED.relative_to(F.REPO)}")

    # --- claim-lock manifest (reuses the bundle's own computed hashes; no recompute) ---
    bundle_manifest = json.loads((F.LOCKED / "bundle-manifest.json").read_text())
    gate = json.loads((F.LOCKED / "gate-report.json").read_text())
    bsha = bundle_manifest.get("source_sha256", {})
    rel_res = str(F._SNAP_RESULTS.relative_to(F.REPO))
    rel_jud = str(F._SNAP_JUDGED.relative_to(F.REPO))

    manifest = {
        "analysis_schema_version": bundle_manifest.get("analysis_schema_version", 1),
        "source_kind": "completed_run",
        "source_id": F.RUN_ID,
        "bundle_id": bundle_manifest.get("bundle_id"),
        "bundle_path": str(F.LOCKED.relative_to(F.REPO)),
        "bundle_state": bundle_manifest.get("bundle_state"),
        "claim_status": bundle_manifest.get("claim_status", "provisional"),
        "gate_passed": bool(gate.get("passed")),
        "evaluation_policy": bundle_manifest.get("evaluation_policy"),
        "judges": ["claude-opus-4.6", "gpt-5.4"],
        "scenario_set": "core-current",
        "expected": bundle_manifest.get("expected"),
        "observed": bundle_manifest.get("observed"),
        "source_sha256": {
            "canonical/results.jsonl.gz": bsha.get("canonical/results.jsonl.gz"),
            "canonical/judged.jsonl.gz": bsha.get("canonical/judged.jsonl.gz"),
            rel_res: _sha256(F._SNAP_RESULTS),
            rel_jud: _sha256(F._SNAP_JUDGED),
        },
        "portable_reproduction": (
            "The heavy raw run is the content-addressed locked bundle "
            f"{F.LOCKED.relative_to(F.REPO)}/ (gitignored by design, ~433 MB). The two "
            "tracked snapshots above are the compact, offline-reproducible derivation that "
            "deep-dive/full_data.py falls back to when the bundle is absent; deep-dive/"
            "full_ab.py + full_*.py recompute every 152-run number from them."
        ),
        "provenance_note": (
            "Standalone 152-model study. Do NOT cross-join with the frozen 94-model "
            "snapshot (data/analysis-manifest.json / paper-94-model-corrected-v1): different "
            "judge pair (claude-opus-4.8 + gpt-5.5) and only 12/20 shared scenario ids. "
            "claim_status is provisional; promotion to a paper-final claim is a separate "
            "human decision."
        ),
    }
    out = F.REPO / "data" / f"analysis-manifest.{F.RUN_ID}.json"
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"claim-lock manifest -> {out.relative_to(F.REPO)} "
          f"(claim_status={manifest['claim_status']}, gate_passed={manifest['gate_passed']})")


if __name__ == "__main__":
    main()
