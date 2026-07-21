"""Reasoning-budget re-run — PRIMARY competing-risks / ITT analysis (no judging).

Implements the *primary* half of deep-dive/reasoning-budget-reanalysis-plan.md against the
completed standalone run `reasoning-budget-v1v2-nocap-20260717-112750` (14 models x 20
scenarios x 5 reps = 1400 assigned cells; envelope max_tokens=4096, timeout=600s).

The primary outcome is COMPLETION — "did the model deliver a judgeable answer within the
envelope?" — which is intention-to-treat by construction (every assigned cell counts; a
`dnf` is the competing timeout event, scored as did-not-complete, never dropped). This half
needs NO judge scores, so it is computable now. The secondary conditional-quality (with
Manski/Lee bounds) waits for the 2-judge pass.

Standalone per AGENTS lesson 8: never spliced into the 152 run.
Run:  ./deep-dive/.venv/bin/python deep-dive/reasoning_budget_reanalysis.py
"""
from __future__ import annotations

import math
import pathlib

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
CSV = HERE / "reasoning-budget" / "primary-cells.csv"
RID = "reasoning-budget-v1v2-nocap-20260717-112750"

# Matched thinking-vs-instruct pairs (same lineage; pair_id was not emitted by the run).
PAIRS = [
    ("qwen3-4b Q4", "qwen3:4b-thinking-2507-q4_K_M", "qwen3:4b-instruct-2507-q4_K_M"),
    ("qwen3-4b Q8", "qwen3:4b-thinking-2507-q8_0", "qwen3:4b-instruct-2507-q8_0"),
    ("exaone 7.8b", "exaone-deep:7.8b", "exaone3.5:7.8b"),
    ("phi4-mini", "phi4-mini-reasoning", "phi4-mini"),
]


def _mode(m: str) -> str:
    ml = m.lower()
    if "instruct" in ml:
        return "instruct"
    if any(k in ml for k in ("thinking", "reasoning", "-deep", "smallthinker")):
        return "thinking"
    if ml.startswith("qwen3:4b"):  # base qwen3 emits chain-of-thought by default
        return "thinking"
    return "base"  # codegemma, phi4-mini, exaone3.5, starcoder2, qwen2.5 (non-CoT)


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main() -> None:
    df = pd.read_csv(CSV)
    for c in ["wall_s", "think_s", "decode_s", "output_tokens", "timeout_s"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["mode"] = df["model"].map(_mode)
    df["completed"] = df["dnf"] == 0

    print(f"=== Reasoning-budget re-run \u2014 PRIMARY competing-risks analysis (judged=NO) ===")
    print(f"run: {RID}")
    tmo = int(df['timeout_s'].dropna().mode().iloc[0]); mtok = int(df['max_tokens'].dropna().mode().iloc[0])
    print(f"envelope: max_tokens={mtok}, timeout={tmo}s | cells={len(df)} "
          f"({df.model.nunique()} models x {df.scenario.nunique()} scenarios x {df.rep.nunique()} reps)\n")

    # ---- per-model completion (ITT) ----
    rows = []
    for m, g in df.groupby("model"):
        n = len(g); comp = int(g["completed"].sum())
        lo, hi = _wilson(comp, n)
        dnf_g = g[~g["completed"]]
        fr = dnf_g["finish_reason"].value_counts()
        rows.append({
            "model": m, "mode": g["mode"].iloc[0], "n": n,
            "complete%": round(100 * comp / n),
            "wilson95": f"[{100*lo:.0f}-{100*hi:.0f}]",
            "dnf%": round(100 * (n - comp) / n),
            "dnf_reason": (fr.index[0] if len(fr) else "-"),
            "medWall_s": round(g["wall_s"].median()),
            "wall_hit%": round(100 * (g["wall_s"] >= tmo - 5).mean()),
            "medThink_s": (round(g["think_s"].median()) if g["think_s"].notna().any() else None),
        })
    tab = pd.DataFrame(rows).sort_values(["complete%", "model"])
    pd.set_option("display.width", 200); pd.set_option("display.max_columns", 20)
    print("--- per-model completion (ITT; DNF = did-not-complete within envelope) ---")
    print(tab.to_string(index=False))

    # ---- matched thinking-vs-instruct pairs (lineage-level, lesson 5) ----
    print("\n--- matched thinking-vs-instruct pairs (same lineage) ---")
    pr = []
    comp_by_model = df.groupby("model")["completed"].mean() * 100
    for label, think_m, inst_m in PAIRS:
        if think_m in comp_by_model and inst_m in comp_by_model:
            t, i = comp_by_model[think_m], comp_by_model[inst_m]
            pr.append({"lineage": label, "thinking_complete%": round(t), "instruct_complete%": round(i),
                       "gap_pp": round(t - i)})
    prdf = pd.DataFrame(pr)
    print(prdf.to_string(index=False))
    print(f"mean within-lineage completion gap (thinking \u2212 instruct): {prdf['gap_pp'].mean():.0f} pp")

    # ---- mode summary (descriptive; n=14, estimation not NHST) ----
    print("\n--- mode summary (cell-level completion; descriptive) ---")
    ms = df.groupby("mode").agg(models=("model", "nunique"), cells=("model", "size"),
                                complete_pct=("completed", lambda s: round(100 * s.mean())),
                                med_wall_s=("wall_s", lambda s: round(s.median()))).reset_index()
    print(ms.to_string(index=False))

    # ---- headline ----
    thinking = df[df["mode"] == "thinking"]
    th_worst = tab[tab["mode"] == "thinking"]["dnf%"].max()
    th_best = tab[tab["mode"] == "thinking"]["dnf%"].min()
    inst_dnf = round(100 * (1 - df[df["mode"] == "instruct"]["completed"].mean()))
    print("\n=== HEADLINE (primary, selection-free) ===")
    print(f"At {mtok} tok / {tmo}s, verbose reasoning lineages fail to COMPLETE {th_best}-{th_worst}% of")
    print(f"assigned cells (instruct \u2248 {inst_dnf}% DNF). The completion deficit is the primary outcome;")
    print("it worsens finding 17 (a generous budget does not rescue completion). Conditional")
    print("quality on completed cells (with Manski/Lee bounds) is PENDING the 2-judge pass.")

    out = HERE / "reasoning-budget" / "primary-summary.csv"
    tab.to_csv(out, index=False)
    print(f"\nsaved {out.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
