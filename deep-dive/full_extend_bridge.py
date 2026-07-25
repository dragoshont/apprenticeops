"""94 -> 152 extension bridge — apples-to-apples replication on the shared slice.

Gate 1 of the "can the frozen 94-model corpus be extended to the 152-model run?"
question. The two runs are NOT poolable: they differ in judges (opus-4.8+gpt-5.5 vs
opus-4.6+gpt-5.4), scenarios (only 12 shared), and prompt format (snapshot vs chatok).
So the honest test is REPLICATION on the controlled slice — the SAME models on the SAME
scenarios — asking whether the frozen findings survive the roster growth + protocol change.

This restricts BOTH runs to (shared models) x (shared scenarios) and reports:
  1. quality rank invariance (Spearman/Kendall/Pearson) + judge/format LEVEL shift,
     with the all-scenarios contrast (the looser b6 number) beside it;
  2. safety (deterministic refusal) invariance on the shared safety scenarios,
     with the explicit caveat that the 5 dropped models are the DeepSeek-R1 distills
     + phi:2.7b (the frozen safety driver), so the R1 mechanism CANNOT be re-tested here;
  3. per-claim replication on the shared slice: tool-training, quality-by-bracket,
     and Spearman(params, quality) (the 4B-knee vs "bigger wins" tension).

Standalone + read-only. Never mutates either run bundle. Judges/scenarios/format are
reported, never silently pooled.
Run:  ./deep-dive/.venv/bin/python deep-dive/full_extend_bridge.py
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
from scipy import stats

import ceops_data
import full_data

HERE = pathlib.Path(__file__).resolve().parent
DROPPED_NOTE = "5 frozen-only models (deepseek-r1 distills + phi:2.7b) are NOT in the 152 -> the R1 safety driver cannot be re-tested on the shared slice"


def _permodel(d: pd.DataFrame, col: str) -> pd.Series:
    return d.groupby("model")[col].mean()


def main() -> None:
    d94 = ceops_data.load_runs()
    d152 = full_data.load_full()

    m_shared = sorted(set(d94.model.unique()) & set(d152.model.unique()))
    s_shared = sorted(set(d94.scenario.unique()) & set(d152.scenario.unique()))
    print("=== 94 -> 152 EXTENSION BRIDGE (apples-to-apples replication) ===")
    print(f"shared slice: {len(m_shared)} models x {len(s_shared)} scenarios "
          f"(frozen judges opus-4.8+gpt-5.5 / snapshot fmt  vs  152 judges opus-4.6+gpt-5.4 / chatok fmt)")
    print(f"caveat: {DROPPED_NOTE}\n")

    a = d94[d94.model.isin(m_shared) & d94.scenario.isin(s_shared)].copy()
    b = d152[d152.model.isin(m_shared) & d152.scenario.isin(s_shared)].copy()

    # ---- 1. QUALITY rank invariance on the controlled slice ----
    q = pd.concat([_permodel(a, "judge_score").rename("q94"),
                   _permodel(b, "judge_score").rename("q152")], axis=1).dropna()
    rho = stats.spearmanr(q.q94, q.q152).correlation
    tau = stats.kendalltau(q.q94, q.q152).correlation
    r = stats.pearsonr(q.q94, q.q152)[0]
    diff = q.q152 - q.q94
    print("--- 1. QUALITY invariance (shared models x shared scenarios) ---")
    print(f"n={len(q)}  Spearman={rho:.3f}  Kendall={tau:.3f}  Pearson={r:.3f}")
    print(f"judge/format LEVEL shift (152-94): mean={diff.mean():+.3f}  sd={diff.std():.3f}  "
          f"(rank can hold through a level shift; report both)")
    # contrast: all scenarios each run (the looser, confounded b6 comparison)
    qa_all = _permodel(d94[d94.model.isin(m_shared)], "judge_score")
    qb_all = _permodel(d152[d152.model.isin(m_shared)], "judge_score")
    q_all = pd.concat([qa_all, qb_all], axis=1).dropna()
    q_all.columns = ["a", "b"]
    print(f"contrast (all scenarios each, scenario-confounded): Spearman="
          f"{stats.spearmanr(q_all.a, q_all.b).correlation:.3f}  n={len(q_all)}")
    q["delta"] = diff
    print("biggest RISERS (152 higher):")
    print(q.sort_values("delta", ascending=False).head(4).round(2).to_string())
    print("biggest FALLERS (152 lower):")
    print(q.sort_values("delta").head(4).round(2).to_string())

    # ---- 2. SAFETY (deterministic refusal) invariance ----
    sa, sb = a[a.is_safety.astype(bool)], b[b.is_safety.astype(bool)]
    print(f"\n--- 2. SAFETY (det refusal) invariance | shared safety scenarios: {sorted(sa.scenario.unique())} ---")
    sf = pd.concat([sa.groupby("model")["det_score"].mean().rename("s94"),
                    sb.groupby("model")["det_score"].mean().rename("s152")], axis=1).dropna()
    s_rho = stats.spearmanr(sf.s94, sf.s152).correlation if len(sf) > 2 else float("nan")
    print(f"n={len(sf)}  Spearman={s_rho:.3f}  mean det-safety 94={sf.s94.mean():.3f}  152={sf.s152.mean():.3f}  "
          f"shift={ (sf.s152 - sf.s94).mean():+.3f}")
    print(f"  (the R1 distills that drove the frozen safety gap are NOT here -> this replicates the")
    print("   instruct-model safety level, NOT the reasoning-distill mechanism)")

    # ---- 3. per-claim replication on the shared slice ----
    print("\n--- 3. per-claim replication on the shared slice ---")
    for name, d in [("94 ", a), ("152", b)]:
        tt = d.groupby(d.tools_capable.astype(bool))["judge_score"].mean()
        if True in tt.index and False in tt.index:
            print(f"  [{name}] tool-training quality: tools={tt[True]:.2f}  no-tools={tt[False]:.2f}  "
                  f"delta={tt[True] - tt[False]:+.2f}")
    for name, d in [("94 ", a), ("152", b)]:
        bq = d.groupby("bracket")["judge_score"].mean()
        print(f"  [{name}] quality by bracket: " + "  ".join(f"{k}={v:.2f}" for k, v in bq.items()))
    for name, d in [("94 ", a), ("152", b)]:
        mm = d.groupby("model").agg(qq=("judge_score", "mean"), pp=("params_b", "first")).dropna()
        print(f"  [{name}] Spearman(params, quality) on shared slice = "
              f"{stats.spearmanr(mm.pp, mm.qq).correlation:+.3f}  (frozen '4B knee' vs 'bigger wins' tension)")

    # ---- verdict line ----
    print("\n=== BRIDGE VERDICT ===")
    ok_rank = rho >= 0.9
    print(f"quality rank invariance on the controlled slice: Spearman {rho:.3f} "
          f"-> {'HOLDS (>=0.90): frozen ranking survives the roster+judge+format change' if ok_rank else 'DOES NOT hold'}")
    print("safety mechanism (reasoning-distill): NOT re-testable here (drivers dropped) -> re-run the 5 or re-scope")
    print("This is Gate 1 only. Extension still needs: new-ensemble judge-human validity, <=5B scope,")
    print("multiplicity on 152, and a new analysis lock + independent review (see docs/PAPER_PHASES.md).")

    out = HERE / "out" / "extend_bridge_quality.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    q.round(4).to_csv(out)
    sf.round(4).to_csv(HERE / "out" / "extend_bridge_safety.csv")
    print(f"\nsaved {out.relative_to(HERE.parent)} + extend_bridge_safety.csv")


if __name__ == "__main__":
    main()
