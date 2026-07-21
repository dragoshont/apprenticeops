"""Prototype: per-concept error analysis of the EXISTING 152 run (no re-run, no grounding).

Answers one question for the paper: does re-grouping the already-judged 15,200 rows
by ops *concept* (the data/concepts/ nodes on branch its-knowledge-capture) reveal a
signal the per-scenario/per-class view doesn't already give? Leakage-free: this reads
existing model OUTPUTS post-hoc; it never injects a node as grounding.

Run:  ./deep-dive/.venv/bin/python deep-dive/concept_error_analysis.py
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
import full_data as fd  # noqa: E402

BRANCH = "its-knowledge-capture"


def load_nodes() -> list[dict]:
    """Read the concept nodes from the working tree if present, else straight from the
    branch (no checkout) so this runs on main where data/concepts/ does not exist. The
    nodes live on the additive, possibly-unmerged branch its-knowledge-capture; if
    neither source is available (e.g. a GitHub clone that never received the branch),
    exit with guidance rather than a raw traceback."""
    local = REPO / "data" / "concepts" / "nodes"
    if local.exists():
        return [json.loads(p.read_text()) for p in sorted(local.glob("*.json"))]
    try:
        names = subprocess.check_output(
            ["git", "-C", str(REPO), "ls-tree", "-r", "--name-only", BRANCH, "data/concepts/nodes/"],
            text=True, stderr=subprocess.DEVNULL).split()
    except subprocess.CalledProcessError:
        names = []
    nodes = [json.loads(subprocess.check_output(["git", "-C", str(REPO), "show", f"{BRANCH}:{n}"], text=True))
             for n in names if n.endswith(".json")]
    if not nodes:
        sys.exit(f"concept nodes not found: neither {local} nor branch '{BRANCH}' is present here. "
                 "Check out/merge the concept branch (its-knowledge-capture) or restore data/concepts/.")
    return nodes


def main() -> None:
    nodes = load_nodes()
    scen2concept: dict[str, list[str]] = {}
    titles: dict[str, str] = {}
    for nd in nodes:
        titles[nd["id"]] = nd["title"]
        for s in nd.get("scenarios", []):
            scen2concept.setdefault(s, []).append(nd["id"])

    df = fd.load_full()
    df["params_b"] = pd.to_numeric(df["params_b"], errors="coerce")
    lo, hi = df["judge_score"].min(), df["judge_score"].max()
    mid = (lo + hi) / 2

    df["concepts"] = df["scenario"].map(scen2concept)
    covered = df[df["concepts"].notna()].copy()
    ex = covered.explode("concepts").rename(columns={"concepts": "concept"})

    print(f"scale judge_score {lo:.0f}..{hi:.0f} (fail = < {mid:.1f}); overall mean {df.judge_score.mean():.2f}")
    print(f"coverage: {covered.scenario.nunique()}/{df.scenario.nunique()} scenarios, "
          f"{len(covered)}/{len(df)} rows ({len(covered) / len(df) * 100:.0f}%), {len(nodes)} concepts\n")

    def cstats(g: pd.DataFrame) -> pd.Series:
        per_scen = g.groupby("scenario")["judge_score"].mean()
        small = g[g.params_b <= 5]
        return pd.Series({
            "n_scen": g["scenario"].nunique(),
            "n_rows": len(g),
            "q_all": g["judge_score"].mean(),
            "q_small": small["judge_score"].mean(),
            "q_large": g[g.params_b > 5]["judge_score"].mean(),
            "det": g["det_score"].mean(),
            "fail_small": (small["judge_score"] < mid).mean(),
            "scen_spread": per_scen.max() - per_scen.min(),
        })

    tab = ex.groupby("concept").apply(cstats, include_groups=False)
    tab.insert(0, "title", tab.index.map(titles))
    tab = tab.sort_values("q_small")
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 20)
    print("=== per-concept, small-model quality worst-first ===")
    print(tab.round(2).to_string())

    spread_small = tab["q_small"].max() - tab["q_small"].min()
    print(f"\nconcept-level small-model quality spread: {spread_small:.2f} on a {lo:.0f}-{hi:.0f} scale")

    print("\n=== concept x size (mean quality) ===")
    df["size_cut"] = pd.cut(df["params_b"], [0, 5, 14, 999], labels=["<=5B", "5-14B", ">14B"])
    ex["size_cut"] = pd.cut(ex["params_b"], [0, 5, 14, 999], labels=["<=5B", "5-14B", ">14B"])
    print(ex.pivot_table(index="concept", columns="size_cut", values="judge_score",
                         aggfunc="mean", observed=True).round(2).to_string())

    print("\n=== scenario-classes each concept spans (cross-class value) ===")
    for c in tab.index:
        classes = sorted(ex[ex.concept == c]["scenario_class"].dropna().unique())
        print(f"  {c}: {len(classes)} class(es) {classes}")

    print(f"\nsmall (<=5B) worst concept: {tab['q_small'].idxmin()} ({tab['q_small'].min():.2f}); "
          f"best: {tab['q_small'].idxmax()} ({tab['q_small'].max():.2f})")
    print(f"large (>5B)  worst concept: {tab['q_large'].idxmin()} ({tab['q_large'].min():.2f})")


if __name__ == "__main__":
    main()
