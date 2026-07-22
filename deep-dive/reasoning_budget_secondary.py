"""Reasoning-budget re-run — SECONDARY conditional-quality analysis (needs the 2-judge pass).

Implements the *secondary* half of reasoning-budget-reanalysis-plan.md: the quality of the
answer GIVEN completion — reported ONLY beside its completion rate and with SELECTION
BOUNDS (Manski, Lee), never as a bare survivor delta. Consumes the 2-judge output
(claude-opus-4.6 + gpt-5.4) produced on `home`, joined to the primary cells.

DNF cells are never dropped: for ITT quality they are floor-scored (Q=1 — the operator got
nothing usable within the envelope); for the thinking-vs-instruct comparison the missingness
is BOUNDED, not assumed ignorable. If the completed-cell "parity" does not survive its
best-case bound, it is a survivorship artifact.

Standalone per AGENTS lesson 8 (never spliced into the 152).
Pull the judged file, then run:
  scp dragos@home.hont.ro:~/apprenticeops-main/judged.reasoning-budget-v1v2.jsonl deep-dive/reasoning-budget/
  ./deep-dive/.venv/bin/python deep-dive/reasoning_budget_secondary.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from reasoning_budget_reanalysis import PAIRS, _mode  # noqa: E402

CELLS = HERE / "reasoning-budget" / "primary-cells.csv"
JUDGED = HERE / "reasoning-budget" / "judged.reasoning-budget-v1v2.jsonl"
JUDGED_GZ = JUDGED.with_suffix(JUDGED.suffix + ".gz")  # committed compact reproduction artifact
SCALE_LO, SCALE_HI = 1.0, 5.0
FLOOR = 1.0  # DNF = no usable answer within the envelope -> task-failure floor


def _open_judged():
    import gzip
    return open(JUDGED) if JUDGED.exists() else gzip.open(JUDGED_GZ, "rt")


def _consensus() -> pd.DataFrame:
    rows = []
    with _open_judged() as f:
        for line in f:
            try:
                r = json.loads(line)
                rows.append({"model": r["model"], "scenario": r["scenario"], "rep": int(r["rep"]),
                             "judge_model": r.get("judge_model"), "score": float(r["score"])})
            except (TypeError, ValueError, KeyError, json.JSONDecodeError):
                continue
    j = pd.DataFrame(rows)
    return j.groupby(["model", "scenario", "rep"]).agg(
        q=("score", "mean"), n_judges=("judge_model", "nunique")).reset_index()


def _manski_assigned_delta(q_comp_think, p_think, q_instruct):
    """Bounds on the ASSIGNED-level quality gap (thinking - instruct) with the unobserved
    (timed-out) thinking cells set to the worst/best of the scale; instruct ~100% complete."""
    lo = (p_think * q_comp_think + (1 - p_think) * SCALE_LO) - q_instruct
    hi = (p_think * q_comp_think + (1 - p_think) * SCALE_HI) - q_instruct
    return lo, hi


def _lee_completed_delta(q_comp_think, instruct_scores, p_keep):
    """Lee bounds on the COMPLETED-cell gap: trim the higher-completing group (instruct) to
    the thinking group's completion rate; instruct's best-kept vs worst-kept p_keep fraction."""
    s = sorted(instruct_scores)
    k = max(1, min(len(s), int(round(len(s) * p_keep))))
    inst_worst_kept = sum(s[:k]) / k      # instruct trimmed to its lowest k -> thinking looks best
    inst_best_kept = sum(s[-k:]) / k       # instruct trimmed to its highest k -> thinking looks worst
    return q_comp_think - inst_best_kept, q_comp_think - inst_worst_kept


def main() -> None:
    if not (JUDGED.exists() or JUDGED_GZ.exists()):
        sys.exit(f"judged file not found: {JUDGED}[.gz]\nPull it once the home pass finishes:\n"
                 "  scp dragos@home.hont.ro:~/apprenticeops-main/judged.reasoning-budget-v1v2.jsonl "
                 f"{JUDGED.parent}/")

    df = pd.read_csv(CELLS)
    df["mode"] = df["model"].map(_mode)
    cons = _consensus()

    comp = df[df.dnf == 0]
    matched = comp.merge(cons, on=["model", "scenario", "rep"], how="left")
    unjudged = int(matched["q"].isna().sum())
    bad2 = int((cons["n_judges"] != 2).sum())
    print(f"=== SECONDARY conditional-quality (scale {SCALE_LO:.0f}-{SCALE_HI:.0f}; DNF floor={FLOOR:.0f}) ===")
    print(f"completed cells={len(comp)} | judged cells={len(cons)} | unjudged completed={unjudged} | "
          f"cells not scored by 2 judges={bad2}")
    if unjudged:
        print(f"  ! PARTIAL: {unjudged} completed cells not yet judged — numbers below are provisional.")

    full = df.merge(cons[["model", "scenario", "rep", "q"]], on=["model", "scenario", "rep"], how="left")
    full["q_itt"] = full["q"].where(full.dnf == 0, FLOOR)

    rows = []
    for mdl, g in full.groupby("model"):
        gc = g[g.dnf == 0]
        rows.append({"model": mdl, "mode": g["mode"].iloc[0], "n": len(g),
                     "complete%": round(100 * (g.dnf == 0).mean()),
                     "condQ": round(gc["q"].mean(), 2) if gc["q"].notna().any() else None,
                     "ITT_Q(DNF=1)": round(g["q_itt"].mean(), 2)})
    tab = pd.DataFrame(rows).sort_values(["mode", "model"])
    pd.set_option("display.width", 200)
    print("\n--- per-model: conditional quality (completed only) vs ITT quality (DNF floored) ---")
    print(tab.to_string(index=False))

    print("\n--- matched pairs: does the completed-cell quality survive the selection? ---")
    for label, tm, im in PAIRS:
        t, i = full[full.model == tm], full[full.model == im]
        tc, ic = t[t.dnf == 0]["q"].dropna(), i[i.dnf == 0]["q"].dropna()
        if tc.empty or ic.empty:
            print(f"{label:12s} (insufficient judged data yet)")
            continue
        p_t = (t.dnf == 0).mean()
        p_i = max((i.dnf == 0).mean(), 1e-9)
        naive = tc.mean() - ic.mean()
        man_lo, man_hi = _manski_assigned_delta(tc.mean(), p_t, ic.mean())
        lee_lo, lee_hi = _lee_completed_delta(tc.mean(), ic.tolist(), min(p_t / p_i, 1.0))
        note = "  <- best case still < 0: thinking worse even ignoring misses" if man_hi < 0 else \
               ("  <- straddles 0: inconclusive from completed cells" if man_lo < 0 < man_hi else "")
        print(f"{label:12s} think {100*p_t:3.0f}% condQ={tc.mean():.2f}  vs instruct condQ={ic.mean():.2f}  "
              f"naive Δ={naive:+.2f}")
        print(f"{'':12s}  Manski assigned-Δ [{man_lo:+.2f}, {man_hi:+.2f}]{note}")
        print(f"{'':12s}  Lee    completed-Δ [{lee_lo:+.2f}, {lee_hi:+.2f}]")

    print("\nRule: report condQ ONLY beside complete% + these bounds; never as a bare survivor")
    print("delta. DNF cells stay scored (ITT), never dropped. Conditional 'parity' that fails")
    print("its Manski best case is a survivorship artifact.")

    if not unjudged:
        out = HERE / "reasoning-budget" / "secondary-summary.csv"
        tab.to_csv(out, index=False)
        print(f"\nsaved {out.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
