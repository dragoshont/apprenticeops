"""Build the summary document for a completed-run analysis lane.

WHY THIS IS NOT THE FROZEN SCHEMA. `data/site/summary.json` on the frozen lane is
a PRE-REGISTRATION: it reports a 4-5GB vs 3-4B footprint gate and an
instruct-vs-reasoning safety contrast that were chosen before the data was
examined, and it hardcodes the values those comparisons produced. A completed run
cannot inherit that. Re-pointing those keys at a different grouping axis would
report a pre-registration that never happened, and the reasoning arm does not
even exist on the 152 lane.

So this schema follows three rules:

  1. Nothing is hardcoded. Every number is computed from the lane.
  2. No comparison is presented as pre-registered unless it was. Contrasts
     computed after the fact are labelled `descriptive_not_pre_registered`.
  3. Absences are explained, not omitted. A missing arm carries the reason it is
     missing, because "no reasoning models" and "reasoning models screened out"
     mean very different things to a reader.
"""
from __future__ import annotations

import json
from pathlib import Path

SUMMARY_SCHEMA = "completed_run_v1"
CONTRAST_METHOD = "paired scenario-cluster bootstrap, 10000 samples"
SAFETY_ARMS = ("instruct", "reasoning")


def _quadratic_kappa(left, right, k: int = 5) -> float:
    """Quadratic-weighted Cohen's kappa on a fixed 1..k scale."""
    observed = [[0.0] * k for _ in range(k)]
    for a, b in zip(left, right):
        observed[int(a) - 1][int(b) - 1] += 1
    total = sum(sum(row) for row in observed)
    if not total:
        return float("nan")
    rows = [sum(row) for row in observed]
    cols = [sum(observed[r][c] for r in range(k)) for c in range(k)]
    num = den = 0.0
    for r in range(k):
        for c in range(k):
            weight = (r - c) ** 2 / (k - 1) ** 2
            num += weight * observed[r][c]
            den += weight * rows[r] * cols[c] / total
    return 1 - num / den if den else float("nan")


def judge_agreement(lane) -> dict:
    import pandas as pd

    pairs = pd.read_csv(lane.judge_pairs)
    left, right = pairs["claude_score"], pairs["gpt_score"]
    return {
        "jointly_scored_cells": int(len(pairs)),
        "exact_agreement_pct": round(float((left == right).mean() * 100), 1),
        "within_one_pct": round(float((left - right).abs().le(1).mean() * 100), 1),
        "cross_judge_kappa_quad": round(_quadratic_kappa(left, right), 3),
        "judge_mean_difference": round(float(left.mean() - right.mean()), 3),
    }


def population(results) -> dict:
    """The roster is not the analysis population; say both."""
    tiers = results.groupby("model")["parameter_tier"].first()
    in_population = tiers.notna() & (tiers.astype(str).str.strip() != "")
    return {
        "roster_models": int(len(tiers)),
        "in_population_models": int(in_population.sum()),
        "out_of_population_models": int((~in_population).sum()),
        "population_rule": "data/models.lock.jsonl tier is set (the <=5B doctoral population)",
    }


def roster_screen(faults_path: Path) -> dict:
    """The screen that decided which candidates ran at all.

    Reported with every summary because a roster filtered on an output-shape
    criterion can be correlated with the outcome under study.
    """
    if not faults_path.exists():
        return {"recorded": False}
    screen = json.loads(faults_path.read_text())
    excluded = screen.get("excluded_models", [])
    served = [row for row in excluded if str(row.get("chat_status")) == "200"]
    return {
        "recorded": True,
        "validation_id": screen.get("validation_id"),
        "policy": screen.get("policy"),
        "candidates": screen.get("counts", {}).get("total"),
        "ran": screen.get("counts", {}).get("ok"),
        "excluded": screen.get("counts", {}).get("excluded"),
        "excluded_unservable": len(excluded) - len(served),
        "excluded_despite_serving": len(served),
        "excluded_despite_serving_models": [
            {"model": row["model"], "reason": row.get("overall_reason"),
             "findings": row.get("findings")}
            for row in served
        ],
        "disclosure": (
            "Models excluded despite serving successfully were dropped on an "
            "output-shape criterion (no visible text within the probe budget). "
            "That criterion can be correlated with the phenomenon under study, so "
            "results are conditional on models that emit visible text within budget."
        ),
    }


def conditions(lane, results) -> dict:
    controlled = results[results["energy_analysis_scope"] == "controlled_three_axis"]
    return {
        "collection_batches": int(results["collection_batch"].nunique()),
        "cpu_frequency_regimes": int(results["cpu_frequency_regime"].nunique()),
        "cpu_frequency_regime": sorted(results["cpu_frequency_regime"].unique())[0],
        "analysis_scope": lane.controlled_scope,
        "energy_comparable_rows": int(len(controlled)),
        "energy_comparable_fraction": round(len(controlled) / max(len(results), 1), 4),
        # One batch means there is no cross-batch energy pooling to forbid.
        "cross_batch_energy_pooling_required": bool(results["collection_batch"].nunique() > 1),
    }


def reliability(results) -> dict:
    finish = results["finish_reason"].astype(str)
    dnf = results["dnf"].astype(str).str.lower().isin(("true", "1"))
    return {
        "rows": int(len(results)),
        "dnf_rows": int(dnf.sum()),
        "truncated_rows": int((finish == "length").sum()),
        "note": ("DNF and truncation are outcomes measured under the identical "
                 "condition, not evidence against it."),
    }


def safety_arms(safety_by_arm, screen: dict) -> dict:
    """Report which arms exist, and why one does not.

    `None` means the caller did not compute arms at all, which is different from
    computing them and finding none - the document must not blur the two.
    """
    if safety_by_arm is None:
        return {"arms_computed": False,
                "note": "safety arms were not supplied to the summary builder"}
    present = [arm for arm in SAFETY_ARMS if arm in set(safety_by_arm.index)]
    out = {
        "arms_computed": True,
        "arms_present": present,
        "instruct_vs_reasoning_contrast_available": set(SAFETY_ARMS) <= set(present),
    }
    if "reasoning" not in present:
        dropped = [m["model"] for m in screen.get("excluded_despite_serving_models", [])]
        out["reasoning_arm_absent_reason"] = (
            "No reasoning-family model reached this run. "
            + (f"The chat-compatibility screen excluded {len(dropped)} model(s) that "
               f"served successfully but returned no visible text: {', '.join(dropped)}. "
               if dropped else "")
            + "An instruct-vs-reasoning safety contrast is therefore not available "
              "on this lane and must not be carried over from another lane."
        )
    return out


def quality_by_group(qbrk, grouping_axis: str) -> list[dict]:
    rows = []
    for _, row in qbrk.iterrows():
        rows.append({
            "grouping_kind": grouping_axis,
            "grouping_value": str(row["grouping_value"]),
            "n": int(row["n"]),
            "quality_pct": round(float(row["mean"]) * 100, 1),
            "ci_low_pct": round(float(row["lo"]) * 100, 1),
            "ci_high_pct": round(float(row["hi"]) * 100, 1),
        })
    return rows


def descriptive_contrast(groups: list[dict], grouping_axis: str) -> list[dict]:
    """Top group vs the one below it - explicitly NOT pre-registered."""
    if len(groups) < 2:
        return []
    top, below = groups[-1], groups[-2]
    return [{
        "kind": "quality",
        "grouping_kind": grouping_axis,
        "left": top["grouping_value"],
        "right": below["grouping_value"],
        "points": round(top["quality_pct"] - below["quality_pct"], 1),
        "status": "descriptive_not_pre_registered",
        "note": ("Computed after the data was examined. It carries none of the "
                 "decision weight of a pre-registered gate."),
    }]


def build(lane, results, judged, qbrk, *, faults_path: Path,
          safety_by_arm=None, extra: dict | None = None) -> dict:
    screen = roster_screen(faults_path)
    groups = quality_by_group(qbrk, lane.grouping_axis)
    manifest = json.loads(lane.manifest_path.read_text())
    summary = {
        "analysis_schema_version": 1,
        "summary_schema": SUMMARY_SCHEMA,
        "source_id": manifest.get("source_id", lane.lane_id),
        "source_kind": lane.source_kind,
        "claim_status": manifest.get("claim_status", lane.claim_status),
        "population": population(results),
        "roster_screen": screen,
        "conditions": conditions(lane, results),
        "evaluation": {
            "quality_axis": (f"5-rep x 2-judge consensus "
                             f"({' + '.join(sorted(judged_judges(lane)))})"),
            **judge_agreement(lane),
            "human_validated": False,
            "human_validation_note": (
                "No blind human labels have been scored for this lane; the judge "
                "cutoff and the deterministic safety checks remain un-validated "
                "against a human."),
        },
        "quality_by_group": groups,
        "pre_registered_gates": [],
        "pre_registered_gates_note": (
            "No gate was pre-registered for this lane. The frozen lane's "
            "4-5GB vs 3-4B footprint gate was pre-registered against a different "
            "grouping axis and is not transferable."),
        "descriptive_contrasts": descriptive_contrast(groups, lane.grouping_axis),
        "safety": safety_arms(safety_by_arm, screen),
        "reliability": reliability(results),
        "contrast_interval_method": CONTRAST_METHOD,
    }
    if extra:
        summary.update(extra)
    return summary


def judged_judges(lane) -> list[str]:
    meta = json.loads((lane.results.parent / "lane.json").read_text())
    return list(meta.get("judges", {}).values())
