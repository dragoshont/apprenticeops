"""A2 — Efficiency frontiers (the core "punch above weight" analysis).

Grounded in Luccioni 2024 (compare energy controlling for parameters) and the
SLM survey (capability x latency x memory x size for on-device models).

* efficiency leaderboards: quality per GB / per B-param / per second (all 95),
  and quality per Wh (controlled 25);
* 2-axis Pareto frontiers (maximise quality, minimise cost) with dominated counts;
* energy/quality residualised on size (efficiency *beyond* what size buys);
* diminishing-returns knee of quality vs parameters.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

from ceops_data import REPO, load_runs, model_table

FIG = REPO / "deep-dive" / "figures"


def pareto_mask(quality: np.ndarray, cost: np.ndarray) -> np.ndarray:
    """True where a point is Pareto-optimal: maximise quality, minimise cost."""
    order = np.lexsort((cost, -quality))  # high quality first, then low cost
    best_cost = np.inf
    keep = np.zeros(len(quality), dtype=bool)
    for i in order:
        if cost[i] <= best_cost:
            keep[i] = True
            best_cost = cost[i]
    return keep


def frontier_report(mt: pd.DataFrame, qcol: str, ccol: str, name: str, lo_is_better=True):
    sub = mt.dropna(subset=[qcol, ccol]).copy()
    cost = sub[ccol].values if lo_is_better else -sub[ccol].values
    mask = pareto_mask(sub[qcol].values, cost)
    sub["pareto"] = mask
    front = sub[sub.pareto].sort_values(qcol, ascending=False)
    print(f"\n=== {name}: {mask.sum()}/{len(sub)} Pareto-optimal ({100*mask.sum()/len(sub):.0f}% frontier) ===")
    print(front[["model", qcol, ccol]].to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    return sub


def main() -> None:
    df = load_runs()
    mt = model_table(df)

    # ---- efficiency leaderboards ----
    def top(col, n=8, asc=False, need=None):
        s = mt.dropna(subset=[col] + ([need] if need else []))
        return s.sort_values(col, ascending=asc)[["model", col, "quality", "size_gb", "params_b"]].head(n)

    print("=== quality per GB (all models) ===")
    print(top("quality_per_gb").to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("\n=== quality per second (throughput-adjusted quality) ===")
    print(top("quality_per_sec").to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("\n=== quality per Wh (controlled-energy 25) ===")
    print(mt.dropna(subset=["quality_per_wh_controlled"]).sort_values("quality_per_wh_controlled", ascending=False)[
        ["model", "quality_per_wh_controlled", "quality", "energy_wh_controlled", "size_gb"]].head(8).to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # ---- Pareto frontiers ----
    frontier_report(mt, "quality", "size_gb", "Quality vs size (GB)")
    frontier_report(mt, "quality", "wall_s", "Quality vs latency (wall_s)")
    en = frontier_report(mt.dropna(subset=["energy_wh_controlled"]), "quality", "energy_wh_controlled", "Quality vs energy (controlled 25)")

    # 3-axis Pareto on controlled set (quality up, safety up, energy down) -> matches site's 7/24
    c = mt.dropna(subset=["energy_wh_controlled", "safety", "quality"]).copy()
    Q, S, E = c["quality"].values, c["safety"].values, c["energy_wh_controlled"].values
    dom = np.zeros(len(c), dtype=bool)
    for i in range(len(c)):
        dom[i] = np.any((Q >= Q[i]) & (S >= S[i]) & (E <= E[i]) & ((Q > Q[i]) | (S > S[i]) | (E < E[i])))
    c["pareto3"] = ~dom
    print(f"\n=== 3-axis Pareto (quality up, safety up, energy down), controlled {len(c)} ===")
    print(f"Pareto-optimal: {int(c.pareto3.sum())}  |  dominated: {int((~c.pareto3).sum())}")
    print(c[c.pareto3].sort_values("quality", ascending=False)[["model", "quality", "safety", "energy_wh_controlled"]].to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # ---- energy controlling for size (Luccioni) ----
    e = mt.dropna(subset=["energy_wh_controlled", "size_gb", "quality"]).copy()
    lr = stats.linregress(np.log(e["size_gb"]), np.log(e["energy_wh_controlled"]))
    e["log_energy_resid"] = np.log(e["energy_wh_controlled"]) - (lr.intercept + lr.slope * np.log(e["size_gb"]))
    print(f"\n=== energy ~ size scaling (log-log): slope={lr.slope:.2f}, R^2={lr.rvalue**2:.2f} ===")
    print("most energy-EFFICIENT beyond size (negative residual):")
    print(e.sort_values("log_energy_resid")[["model", "size_gb", "energy_wh_controlled", "quality", "log_energy_resid"]].head(5).to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("most energy-HUNGRY beyond size (positive residual):")
    print(e.sort_values("log_energy_resid", ascending=False)[["model", "size_gb", "energy_wh_controlled", "quality", "log_energy_resid"]].head(5).to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # ---- quality vs params knee ----
    k = mt.dropna(subset=["quality", "params_b"]).copy()
    rho = stats.spearmanr(k["params_b"], k["quality"]).correlation
    # log fit
    lr2 = stats.linregress(np.log(k["params_b"]), k["quality"])
    print(f"\n=== quality vs params ===")
    print(f"Spearman(params, quality)={rho:.3f}; quality ~ a + b*ln(params): b={lr2.slope:.2f} pts/e-fold, R^2={lr2.rvalue**2:.2f}")

    # ---- figure: quality-energy + quality-size Pareto ----
    fig, ax = plt.subplots(1, 2, figsize=(12, 5))
    ax[0].scatter(en["energy_wh_controlled"], en["quality"], c=np.where(en.pareto, "crimson", "gray"), s=28)
    for _, r in en[en.pareto].iterrows():
        ax[0].annotate(r["model"].split("/")[-1][:16], (r["energy_wh_controlled"], r["quality"]), fontsize=6)
    ax[0].set(xlabel="energy per answer (Wh, controlled)", ylabel="quality (judge 1-5)", title="Quality vs energy (controlled 25)")
    allm = mt.dropna(subset=["quality", "size_gb"])
    pm = pareto_mask(allm["quality"].values, allm["size_gb"].values)
    ax[1].scatter(allm["size_gb"], allm["quality"], c=np.where(pm, "crimson", "gray"), s=22)
    ax[1].set(xlabel="model size (GB)", ylabel="quality (judge 1-5)", title="Quality vs size (all 95)")
    fig.tight_layout()
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "a2_efficiency_frontiers.png", dpi=130)
    print(f"\nsaved figure {FIG/'a2_efficiency_frontiers.png'}")


if __name__ == "__main__":
    main()
