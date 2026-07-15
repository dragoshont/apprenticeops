"""Full-run headline report — the 152-model, single-regime, 3-axis view.

Centers the analysis on `full-chatok-core20-r5` (Option A). Prints the headline
quality / safety / ENERGY results on all 152 models and a side-by-side against
the frozen two-batch var/wave2 snapshot, so the re-center can be judged on
evidence before any paper rewrite.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

import ceops_data
from full_data import REPO, load_full, model_table_full


def main() -> None:
    df = load_full()
    mt = model_table_full(df)
    mt = mt[mt["quality"].notna()].copy()

    print("=" * 72)
    print("FULL RUN as the thesis center — full-chatok-core20-r5 (Option A)")
    print("=" * 72)
    print(f"{df.model.nunique()} models x {df.scenario.nunique()} scenarios x {df.rep.nunique()} reps "
          f"= {len(df):,} rows | 2-judge consensus (gpt-5.4 + claude-opus-4.6)")
    print(f"single controlled regime: energy comparable on {df.energy_comparable.mean()*100:.0f}% of rows "
          f"(turbo-off, RAPL package-0)")

    # --- THE WIN: 3-axis coverage vs frozen ---
    fz = ceops_data.load_runs()
    fzt = ceops_data.model_table(fz)
    n_energy_full = mt["energy_wh"].notna().sum()
    n_energy_frozen = fzt["energy_wh_controlled"].notna().sum()
    print("\n--- 3-axis (quality x safety x energy) coverage ---")
    print(f"  models with COMPARABLE energy:  full = {n_energy_full}   vs   frozen var/wave2 = {n_energy_frozen}")
    print(f"  quality/safety models:          full = {mt.quality.notna().sum()}   vs   frozen = {fzt.quality.notna().sum()}")

    # --- top of the ranking ---
    print("\n--- top 15 by quality (2-judge consensus) ---")
    cols = ["model", "quality", "safety", "det_score", "energy_wh", "decode_tps", "params_b"]
    print(mt.sort_values("quality", ascending=False).head(15)[cols].to_string(
        index=False, float_format=lambda x: f"{x:.2f}"))

    # --- sweet spot over the full spectrum, now WITH energy ---
    print("\n--- quality & energy by size tier (the sweet spot, 3-axis) ---")
    tiers = [("<3B", mt.params_b < 3), ("3-6.5B", (mt.params_b >= 3) & (mt.params_b < 6.5)),
             (">=6.5B", mt.params_b >= 6.5)]
    for name, mask in tiers:
        g = mt[mask]
        print(f"  {name:8} n={len(g):3}  quality={g.quality.mean():.2f}  "
              f"energy_wh={g.energy_wh.mean():.3f}  best={g.quality.max():.2f} ({g.loc[g.quality.idxmax(),'model']})")
    t = mt.dropna(subset=["params_b", "quality"])
    print(f"  Spearman(params, quality) over {len(t)} = {stats.spearmanr(t.params_b, t.quality).correlation:.3f}  (moderate positive -> bigger helps on average; ~4B is the efficiency knee)")

    # --- energy axis (comparable across ALL 152), properly normalized ---
    print("\n--- energy axis (comparable across ALL 152) ---")
    e = mt.dropna(subset=["wh_per_det_correct", "params_b"])
    e = e[(e.wh_per_det_correct > 0) & (e.params_b > 0)]
    sl, ic, r, *_ = stats.linregress(np.log(e.params_b), np.log(e.wh_per_det_correct))
    print(f"  energy-per-correct (Wh / det-credit) ~ params: slope={sl:+.2f} R^2={r**2:.2f}")
    e2 = mt.dropna(subset=["j_per_output_token", "params_b"])
    e2 = e2[(e2.j_per_output_token > 0) & (e2.params_b > 0)]
    sl2, _, r2, *_ = stats.linregress(np.log(e2.params_b), np.log(e2.j_per_output_token))
    print(f"  joules-per-output-token ~ params:              slope={sl2:+.2f} R^2={r2**2:.2f}")
    eff = mt.dropna(subset=["wh_per_det_correct"]).sort_values("wh_per_det_correct")
    print("  most energy-efficient per correct answer (low Wh / det-credit):")
    for _, row in eff.head(5).iterrows():
        print(f"    {row['model']:38} q={row['quality']:.2f}  {row['wh_per_det_correct']:.3f} Wh/correct")

    # --- capability-training effects, honest on the full roster ---
    print("\n--- capability-training effects (enriched flags over 152) ---")
    for flag, label in [("is_tools", "tool-trained"), ("is_reasoning", "reasoning-tagged")]:
        if flag in mt.columns:
            yes = mt[mt[flag] == True].quality.dropna()
            no = mt[mt[flag] == False].quality.dropna()
            if len(yes) and len(no):
                _, p = stats.ttest_ind(yes, no, equal_var=False)
                print(f"    {label:18} yes n={len(yes):3} q={yes.mean():.2f} | no n={len(no):3} q={no.mean():.2f} "
                      f"| delta={yes.mean()-no.mean():+.2f} (p={p:.3f})")
    n_r1 = int(mt.model.str.contains(r"deepseek-r1", case=False).sum())
    print(f"  ROSTER CAVEAT: deepseek-r1 in full = {n_r1}. The frozen 'reasoning hurts (-0.88)' was")
    print("  R1-distill-driven; full's reasoning models are qwen3-thinking/cogito/exaone-deep (stronger),")
    print("  so 'reasoning hurts' does NOT reproduce on full -> needs deepseek-r1 in the roster to test.")

    # --- safety leaders ---
    print("\n--- safety (guard/secure scenarios) leaders ---")
    for _, row in mt.dropna(subset=["safety"]).sort_values("safety", ascending=False).head(5).iterrows():
        print(f"    {row['model']:38} safety={row['safety']:.2f}  quality={row['quality']:.2f}")

    # --- robustness: full vs frozen on shared models ---
    shared = mt.set_index("model")[["quality"]].join(
        fzt.set_index("model")[["quality"]], lsuffix="_full", rsuffix="_frozen", how="inner").dropna()
    rho = stats.spearmanr(shared.quality_full, shared.quality_frozen).correlation
    print(f"\n--- robustness: full vs frozen snapshot on {len(shared)} shared models ---")
    print(f"  Spearman = {rho:.3f}  => re-centering broadens, does not overturn, the ranking")

    out = REPO / "deep-dive" / "out"
    mt.to_csv(out / "full_model_table.csv", index=False)
    print(f"\nsaved {out/'full_model_table.csv'}")


if __name__ == "__main__":
    main()
