#!/usr/bin/env python3
"""Fail closed when current ApprenticeOps claims drift from analysis schema v1."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SURFACES = {
    relative: (REPO / relative).read_text(errors="replace")
    for relative in [
        "README.md",
        "REVIEWER.md",
        "docs/ANALYSIS.md",
        "docs/PAPER.md",
        "docs/TAXONOMY.md",
        "docs/analysis/index.qmd",
        "docs/analysis/_evidence-lock.md",
        "scripts/write-portal-build.py",
        "docs/analysis/judge_comparison.ipynb",
        "docs/analysis/reviewers.qmd",
        "docs/analysis/research-updates.qmd",
        "docs/analysis/paper.qmd",
        "docs/analysis/reviewer.ipynb",
    ]
}


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def csv_rows(relative: str) -> list[dict[str, str]]:
    with (REPO / relative).open(newline="") as handle:
        return list(csv.DictReader(handle))


def require_pattern(relative: str, pattern: str) -> None:
    if not re.search(pattern, SURFACES[relative], re.I | re.S):
        fail(f"{relative}: missing canonical claim pattern: {pattern}")


def main() -> None:
    summary = json.loads((REPO / "data/site/summary.json").read_text())
    if summary.get("analysis_schema_version") != 1 or summary.get("claim_status") != "locked":
        fail("public claims require a locked analysis schema v1 summary")
    if summary.get("energy_cross_batch_comparison_allowed") is not False:
        fail("cross-batch energy comparison must remain forbidden")

    expected = {
        "breadth_model_count": 94,
        "breadth_quality_safety_pareto_count": 2,
        "controlled_model_count": 24,
        "controlled_three_axis_pareto_count": 7,
        "controlled_three_axis_dominated_count": 17,
        "controlled_three_axis_pick": "qwen3:4b-instruct-2507-q4_K_M",
        "quality_4_5gb_minus_3_4b_ci_low_points": 1.9,
        "quality_4_5gb_minus_3_4b_ci_high_points": 7.4,
        "safety_instruct_minus_reasoning_ci_low_points": 15.2,
        "safety_instruct_minus_reasoning_ci_high_points": 32.5,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            fail(f"summary {key}={summary.get(key)!r}; expected {value!r}")

    breadth = csv_rows("data/site/models.csv")
    controlled = csv_rows("data/site/controlled_models.csv")
    controlled_front = csv_rows("data/site/pareto.csv")
    breadth_front = csv_rows("data/site/quality_safety_pareto.csv")
    if "mean_energy_wh_per_answer" in (breadth[0] if breadth else {}):
        fail("94-model breadth export must not contain energy")
    if len(breadth) != 94 or len(controlled) != 24 or len(controlled_front) != 7 or len(breadth_front) != 2:
        fail("model/front export populations drifted")
    if {row["analysis_scope"] for row in controlled} != {
        summary["controlled_analysis_scope"]
    }:
        fail("controlled model export mixes analysis scopes")
    if {row["collection_batch"] for row in controlled} != {"var"}:
        fail("controlled model export mixes collection batches")
    if {row["cpu_frequency_regime"] for row in controlled} != {"base_clock_1700_turbo_off"}:
        fail("controlled model export mixes CPU-frequency regimes")
    if {row["power_source"] for row in controlled} != {"rapl:package-0"}:
        fail("controlled model export mixes power sources")

    expected_front = {row["model"] for row in controlled if row["three_axis_pareto"] == "True"}
    if {row["model"] for row in controlled_front} != expected_front:
        fail("controlled Pareto table disagrees with controlled model flags")
    expected_breadth_front = {
        row["model"] for row in breadth if row["quality_safety_pareto"] == "True"
    }
    if {row["model"] for row in breadth_front} != expected_breadth_front:
        fail("quality-safety Pareto table disagrees with breadth model flags")

    required_by_surface = {
        "README.md": [r"7 of 24", r"quality-safety front contains \*\*2 of 94 models", r"12-of-94.*withdrawn"],
        "REVIEWER.md": [r"7-of-24", r"2-of-94", r"12-of-94.*withdrawn"],
        "docs/ANALYSIS.md": [r"7 of 24", r"2 of 94", r"12-of-94.*withdrawn"],
        "docs/PAPER.md": [r"7 of 24", r"quality-safety.*2 models", r"12-of-94.*withdrawn"],
        "docs/TAXONOMY.md": [r"data/scenarios\.json` now has \*\*33\*\*", r"Core selection contains 20"],
        "docs/analysis/index.qmd": [r"7 of 24", r"quality-safety front contains \*\*2", r"(?:withdr(?:aw|ew|awn).*12-of-94|12-of-94.*withdr(?:aw|ew|awn))"],
        "docs/analysis/_evidence-lock.md": [r"analysis schema `v1`", r"7 of 24", r"2\s*\n?of 94"],
        "scripts/write-portal-build.py": [r"Evidence lock:", r"controlled_front", r"breadth_front"],
        "docs/analysis/judge_comparison.ipynb": [r"8,909", r"hash-bound raw verdict rows"],
        "docs/analysis/reviewers.qmd": [r"7 of 24", r"2 of 94", r"n=120"],
        "docs/analysis/research-updates.qmd": [r"Candidate evidence, not paper claims", r"zero promotions"],
        "docs/analysis/paper.qmd": [r"7 of 24", r"quality-safety front contains \*\*2 models", r"12-of-94.*withdraw"],
        "docs/analysis/reviewer.ipynb": [r"7 of 24", r"controlled_three_axis", r"CONTROLLED_ROWS"],
    }
    for relative, patterns in required_by_surface.items():
        for pattern in patterns:
            require_pattern(relative, pattern)

    combined = "\n".join(SURFACES.values())
    forbidden = {
        "active 12-of-94 Pareto claim": r"12 of 94 models are Pareto-optimal",
        "active 82-dominated claim": r"other 82 are dominated",
        "old row-bootstrap quality interval": r"\[31\.5,\s*32\.9\]",
        "old row-bootstrap safety interval": r"\[70\.3,\s*72\.4\]",
        "marginal-CI significance claim": r"CIs are nowhere near overlapping",
        "difficulty-as-validated claim": r"difficulty.{0,80}validated empirically",
        "GB doctoral boundary": r"CPU-only,\s*≤\s*5\s*GB",
        "retired summary key": r"quality_knee_bracket",
        "stale taxonomy count": r"data/scenarios\.json` now has 27",
        "stale reviewer safety count": r"n\s*=\s*60|n=60",
    }
    for label, pattern in forbidden.items():
        if re.search(pattern, combined, re.I | re.S):
            fail(f"forbidden {label} found: {pattern}")

    for row in controlled_front:
        for relative in ("docs/analysis/index.qmd", "docs/analysis/paper.qmd"):
            if row["model"] not in SURFACES[relative]:
                fail(f"{relative}: controlled front omits {row['model']}")
    for row in breadth_front:
        if row["model"] not in SURFACES["docs/analysis/paper.qmd"]:
            fail(f"paper omits breadth-front model {row['model']}")

    print(f"paper claim audit passed: surfaces={len(SURFACES)}")


if __name__ == "__main__":
    main()