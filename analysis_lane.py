"""Resolve which analysis lane the notebooks, audits and site build should read.

The repository carries two evidence lanes:

  frozen  - the 94-model paper-era snapshots, two collection batches, incomplete
            per-row condition identity, judges claude-opus-4.8 + gpt-5.5.
  <run id> - a promoted completed run, one batch, complete condition identity,
            built by scripts/build-analysis-v1-from-bundle.py.

Both emit identical canonical v1 headers, so consumers differ only in which
files they open and in a few lane-specific labels. Hardcoding the frozen paths
(as the notebooks used to) silently pins every consumer to the 94-model lane, so
resolution happens here instead.

Resolution order:
  1. APPRENTICEOPS_ANALYSIS_LANE - "frozen", a run id, or a lane directory.
  2. data/analysis-manifest.json - whichever lane currently holds the claim.

Nothing in this module flips a claim: it reports the lane, it does not choose
which lane is allowed to make claims.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent
MANIFEST = REPO / "data/analysis-manifest.json"
SNAPSHOTS = REPO / "data/snapshots"
ENV_VAR = "APPRENTICEOPS_ANALYSIS_LANE"

FROZEN_ID = "paper-94-model-corrected-v1"

# The frozen lane's labels are themselves frozen; they are not re-derived.
FROZEN_CONTROLLED_SCOPE = "var_base_clock_1700_turbo_off_package0"


@dataclass(frozen=True)
class Lane:
    """Everything a consumer needs to read one evidence lane."""

    lane_id: str
    source_kind: str
    results: Path
    judged: Path
    judge_pairs: Path
    judged_det: Path | None
    controlled_scope: str
    claim_status: str
    #: Column to group models by. The 152 lane exposes a mixed-unit
    #: `legacy_footprint_bracket` ("4-5B" is parameters, "4-5GB" is disk
    #: footprint), so completed-run lanes group on the clean parameter tier.
    grouping_axis: str
    notes: tuple[str, ...] = field(default=())

    @property
    def is_frozen(self) -> bool:
        return self.source_kind == "frozen_snapshot"

    def describe(self) -> str:
        return (f"lane={self.lane_id} kind={self.source_kind} "
                f"claim_status={self.claim_status} axis={self.grouping_axis}")


def _frozen_lane() -> Lane:
    claim_status = "unknown"
    if MANIFEST.exists():
        manifest = json.loads(MANIFEST.read_text())
        if manifest.get("source_id") == FROZEN_ID:
            claim_status = str(manifest.get("claim_status", "unknown"))
    return Lane(
        lane_id=FROZEN_ID,
        source_kind="frozen_snapshot",
        results=SNAPSHOTS / "results_snapshot.csv",
        judged=SNAPSHOTS / "judged_snapshot.csv",
        judge_pairs=REPO / "data/site/judge_pairs.csv",
        judged_det=SNAPSHOTS / "judged_snapshot.det.csv",
        controlled_scope=FROZEN_CONTROLLED_SCOPE,
        claim_status=claim_status,
        grouping_axis="legacy_footprint_bracket",
        notes=(
            "Two collection batches; only the var batch is energy-comparable.",
            "Rows predate complete canonical condition identity.",
        ),
    )


def _completed_run_lane(directory: Path) -> Lane:
    lane_json = directory / "lane.json"
    if not lane_json.exists():
        raise FileNotFoundError(
            f"{directory} is not a completed-run lane (no lane.json); "
            "build it with scripts/build-analysis-v1-from-bundle.py"
        )
    meta = json.loads(lane_json.read_text())
    claim_status = "provisional"
    if MANIFEST.exists():
        manifest = json.loads(MANIFEST.read_text())
        if manifest.get("source_id") == meta["run_id"]:
            claim_status = str(manifest.get("claim_status", "provisional"))
    return Lane(
        lane_id=str(meta["run_id"]),
        source_kind="completed_run",
        results=directory / "results_snapshot.csv",
        judged=directory / "judged_snapshot.csv",
        judge_pairs=directory / "judge_pairs.csv",
        judged_det=None,
        controlled_scope=f"{meta['collection_batch']}_{meta['cpu_frequency_regime']}",
        claim_status=claim_status,
        grouping_axis="parameter_tier",
        notes=(
            "Single collection batch; every row is energy-comparable.",
            "legacy_footprint_bracket mixes units on this lane "
            "(4-5B is parameters, 4-5GB is disk footprint) - group on "
            "parameter_tier instead.",
        ),
    )


def available_lanes() -> list[str]:
    lanes = [FROZEN_ID]
    if SNAPSHOTS.is_dir():
        lanes.extend(sorted(
            p.name for p in SNAPSHOTS.iterdir()
            if p.is_dir() and (p / "lane.json").exists()
        ))
    return lanes


def resolve(name: str | None = None) -> Lane:
    """Return the lane named, or requested by env, or holding the claim."""
    requested = name or os.environ.get(ENV_VAR) or ""
    requested = requested.strip()

    if not requested:
        if not MANIFEST.exists():
            return _frozen_lane()
        manifest = json.loads(MANIFEST.read_text())
        if manifest.get("source_kind") == "frozen_snapshot":
            return _frozen_lane()
        requested = str(manifest.get("source_id", ""))
        if not requested:
            return _frozen_lane()

    if requested in {"frozen", FROZEN_ID}:
        return _frozen_lane()

    candidate = Path(requested)
    if not candidate.is_absolute():
        candidate = SNAPSHOTS / requested
    if candidate.is_dir():
        return _completed_run_lane(candidate)

    raise FileNotFoundError(
        f"unknown analysis lane {requested!r}; available: {available_lanes()}"
    )


def load(name: str | None = None):
    """Convenience for notebooks: return (lane, results_df, judged_df)."""
    import pandas as pd  # imported lazily so audits stay stdlib-only

    lane = resolve(name)
    return lane, pd.read_csv(lane.results), pd.read_csv(lane.judged)


if __name__ == "__main__":
    for lane_id in available_lanes():
        lane = resolve(lane_id)
        print(lane.describe())
        for note in lane.notes:
            print(f"    - {note}")
