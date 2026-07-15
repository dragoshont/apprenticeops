"""A1 — Ranking rigor.

Grounded in Miller 2024 (evals as experiments; paired/clustered CIs) and
Demsar 2006 (Friedman + Nemenyi critical difference for many systems over many
tasks). Answers: which models are *really* different, or just noise?

* per-model quality (judge 1-5) with scenario-clustered bootstrap 95% CI;
* Friedman test across all models over the 19 scenarios + Kendall's W effect size;
* Nemenyi critical difference -> how many models are statistical co-leaders;
* Spearman agreement between the LLM-judge ranking and the deterministic-score ranking.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from ceops_data import REPO, load_runs

RNG = np.random.default_rng(20260715)
B = 10000


def cluster_bootstrap_ci(pivot: pd.DataFrame, model: str, b: int = B):
    """Resample scenarios (clusters) with replacement; CI of the model's mean."""
    vals = pivot[model].dropna().values
    scen = len(vals)
    idx = RNG.integers(0, scen, size=(b, scen))
    means = vals[idx].mean(axis=1)
    return np.percentile(means, [2.5, 97.5])


def main() -> None:
    df = load_runs()
    # per (model, scenario) mean over reps = the paired, scenario-level matrix
    ms = df.groupby(["model", "scenario"])["judge_score"].mean().unstack("scenario")
    dts = df.groupby(["model", "scenario"])["det_score"].mean().unstack("scenario")
    models = ms.index.tolist()
    pivot = ms.T  # scenarios x models

    rows = []
    for m in models:
        lo, hi = cluster_bootstrap_ci(pivot, m)
        rows.append((m, ms.loc[m].mean(), lo, hi, dts.loc[m].mean()))
    R = pd.DataFrame(rows, columns=["model", "quality", "ci_lo", "ci_hi", "det"]).sort_values("quality", ascending=False)
    R["rank"] = range(1, len(R) + 1)

    print("=== quality ranking (judge 1-5) with scenario-clustered 95% CI ===")
    print(R.head(15).to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("...")
    print(R.tail(5).to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # statistical co-leaders: models whose CI overlaps the #1's CI
    top = R.iloc[0]
    coleaders = R[R["ci_hi"] >= top["ci_lo"]]
    print(f"\n#1 = {top['model']} (quality {top['quality']:.3f}, CI {top['ci_lo']:.3f}-{top['ci_hi']:.3f})")
    print(f"statistical co-leaders (CI overlaps #1): {len(coleaders)} models")
    print("  ", ", ".join(coleaders["model"].head(10)))

    # Friedman across all models over scenarios (need complete matrix)
    M = ms.dropna(axis=1)  # scenarios present for all models
    print(f"\n=== Friedman test: {M.shape[0]} models over {M.shape[1]} complete scenarios ===")
    chi2, p = stats.friedmanchisquare(*[M[c].values for c in M.columns])
    n, k = M.shape[1], M.shape[0]  # blocks=scenarios, treatments=models
    W = chi2 / (n * (k - 1))  # Kendall's W
    print(f"chi2={chi2:.1f}, p={p:.2e}, Kendall's W={W:.3f} (0=no agreement,1=perfect ordering across scenarios)")

    # Nemenyi critical difference on mean ranks
    ranks = M.rank(axis=0, ascending=False)  # per scenario (column), rank models
    mean_rank = ranks.mean(axis=1).sort_values()
    q_alpha = 3.354  # studentized range /sqrt2 approx for alpha=0.05, large k (Demsar table asymptote ~ from normal)
    # use the standard Nemenyi CD with q for infinite k (0.05) ~ 3.219? use conservative normal approx:
    from math import sqrt
    q05 = stats.norm.ppf(1 - 0.05 / (k * (k - 1)))  # Bonferroni-Dunn style critical z for all pairs
    CD = q05 * sqrt(k * (k + 1) / (6 * n))
    best_rank = mean_rank.iloc[0]
    within = mean_rank[mean_rank <= best_rank + CD]
    print(f"mean-rank best = {mean_rank.index[0]} ({best_rank:.2f}); CD(0.05)={CD:.2f}")
    print(f"models within CD of the best mean-rank (statistical co-top): {len(within)}")
    print("  ", ", ".join(within.index[:10]))

    # judge vs deterministic ranking agreement
    rho, pr = stats.spearmanr(R["quality"], R["det"])
    tau, pt = stats.kendalltau(R.set_index("model")["quality"].rank(), R.set_index("model")["det"].rank())
    print(f"\n=== quality(judge) vs det_score ranking agreement ===")
    print(f"Spearman rho={rho:.3f} (p={pr:.1e}); Kendall tau={tau:.3f}")
    # biggest judge-vs-det disagreements (models the judge likes but det doesn't, and vice versa)
    R2 = R.copy()
    R2["q_rank"] = R2["quality"].rank(ascending=False)
    R2["d_rank"] = R2["det"].rank(ascending=False)
    R2["rank_gap"] = R2["d_rank"] - R2["q_rank"]  # positive: judge ranks higher than det
    print("judge-favoured (judge rank >> det rank):")
    print(R2.sort_values("rank_gap", ascending=False)[["model", "quality", "det", "q_rank", "d_rank"]].head(5).to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print("det-favoured (det rank >> judge rank):")
    print(R2.sort_values("rank_gap")[["model", "quality", "det", "q_rank", "d_rank"]].head(5).to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    R.to_csv(REPO / "deep-dive" / "out" / "a1_ranking.csv", index=False)
    print("\nsaved a1_ranking.csv")


if __name__ == "__main__":
    main()
