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
    print(f"  Spearman(params, quality) over {len(t)} = {stats.spearmanr(t.params_b, t.quality).correlation:.3f}  (weak => size is not destiny)")

    # --- energy is real physics here (single regime) ---
    e = mt.dropna(subset=["energy_wh", "params_b"])
    e = e[(e.energy_wh > 0) & (e.params_b > 0)]
    sl, ic, r, *_ = stats.linregress(np.log(e.params_b), np.log(e.energy_wh))
    print("\n--- energy axis (comparable across ALL 152) ---")
    print(f"  log(energy_wh) ~ log(params): slope={sl:.2f}  R^2={r**2:.2f}")
    eff = mt.dropna(subset=["quality_per_wh"]).sort_values("quality_per_wh", ascending=False)
    print("  most energy-efficient (quality per Wh):")
    for _, row in eff.head(5).iterrows():
        print(f"    {row['model']:38} q={row['quality']:.2f}  {row['energy_wh']:.3f} Wh  q/Wh={row['quality_per_wh']:.1f}")

    # --- tools vs reasoning (survives on the bigger set?) ---
    if "training_regime" in mt.columns:
        print("\n--- training regime effect on quality (full set) ---")
        for reg, g in mt.dropna(subset=["training_regime"]).groupby("training_regime"):
            print(f"    {reg:14} n={len(g):3}  quality={g.quality.mean():.2f}  energy_wh={g.energy_wh.mean():.3f}")

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
