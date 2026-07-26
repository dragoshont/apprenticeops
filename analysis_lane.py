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
FROZEN_BRACKET_ORDER = ("0-1B", "1-2B", "2-3B", "3-4B", "4-5GB")
TIER_ORDER = ("T1", "T2", "T3", "T4", "T5")


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
    #: Ordered categories of `grouping_axis`, low to high.
    grouping_order: tuple[str, ...]
    notes: tuple[str, ...] = field(default=())

    @property
    def is_frozen(self) -> bool:
        return self.source_kind == "frozen_snapshot"

    @property
    def site_dir(self) -> Path:
        """Where this lane's website exports belong.

        Only the lane that currently holds the claim writes to `data/site`.
        Any other lane exports beside it under its own id, so re-running a
        non-claim lane can never overwrite the published artifacts.
        """
        if self.holds_claim:
            return REPO / "data" / "site"
        # Deliberately OUTSIDE data/site: the site build compares that directory
        # against the committed bundle, so a lane exporting into it would be
        # reported as unexpected content and weaken the gate.
        return REPO / "data" / "site-lanes" / self.lane_id

    @property
    def manifest_path(self) -> Path:
        """The manifest describing this lane."""
        sidecar = REPO / "data" / f"analysis-manifest.{self.lane_id}.json"
        return sidecar if sidecar.exists() else MANIFEST

    @property
    def holds_claim(self) -> bool:
        if not MANIFEST.exists():
            return self.is_frozen
        manifest = json.loads(MANIFEST.read_text())
        return manifest.get("source_id") == self.lane_id

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
        grouping_order=FROZEN_BRACKET_ORDER,
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
        grouping_order=TIER_ORDER,
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
