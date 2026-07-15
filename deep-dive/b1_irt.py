"""B1 — 2-PL Item Response Theory over the ops scenarios.

Persons = models, items = scenarios, response = deterministic success (det>=0.5),
5 reps per cell. Fits a 2-parameter logistic (item difficulty b, discrimination a,
model ability theta) by joint maximum likelihood, then reports Fisher information
per scenario -> which scenarios to keep or prune (tinyBenchmarks; Maia Polo 2024).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression

from ceops_data import REPO, load_runs

SUCCESS = 0.5  # det_score threshold for "correct"


def main() -> None:
    df = load_runs().dropna(subset=["det_score"]).copy()
    df["y"] = (df["det_score"] >= SUCCESS).astype(int)
    models = sorted(df["model"].unique())
    scen = sorted(df["scenario"].unique())
    mi = {m: i for i, m in enumerate(models)}
    si = {s: i for i, s in enumerate(scen)}
    df["mi"] = df["model"].map(mi)
    df["si"] = df["scenario"].map(si)
    Y = df["y"].values
    MI = df["mi"].values
    SI = df["si"].values
    n_m, n_s = len(models), len(scen)

    # init
    theta = np.array([stats.norm.ppf(np.clip(df[df.mi == i]["y"].mean(), .02, .98)) for i in range(n_m)])
    theta = (theta - theta.mean()) / theta.std()
    a = np.ones(n_s)
    b = np.array([-stats.norm.ppf(np.clip(df[df.si == j]["y"].mean(), .02, .98)) for j in range(n_s)])

    for it in range(30):
        # item step: logistic y ~ theta per scenario -> slope=a_s, intercept=-a_s*b_s
        for j in range(n_s):
            m = SI == j
            x = theta[MI[m]].reshape(-1, 1)
            yy = Y[m]
            if yy.min() == yy.max():
                continue
            lr = LogisticRegression(C=1e6, solver="lbfgs", max_iter=200).fit(x, yy)
            a[j] = max(lr.coef_[0, 0], 0.05)
            b[j] = -lr.intercept_[0] / a[j]
        # person step: 1-D Newton for theta_m given a,b
        for i in range(n_m):
            m = MI == i
            aj = a[SI[m]]
            bj = b[SI[m]]
            yy = Y[m]
            for _ in range(25):
                p = 1 / (1 + np.exp(-aj * (theta[i] - bj)))
                grad = np.sum(aj * (yy - p))
                hess = -np.sum(aj ** 2 * p * (1 - p)) - 1e-6
                step = grad / hess
                theta[i] -= step
                if abs(step) < 1e-6:
                    break
        # identify: standardize theta, rescale a,b
        mu, sd = theta.mean(), theta.std()
        theta = (theta - mu) / sd
        b = (b - mu) / sd
        a = a * sd

    S = pd.DataFrame({"scenario": scen, "class": [df[df.si == j]["scenario_class"].iloc[0] for j in range(n_s)],
                      "difficulty_b": b, "discrimination_a": a})
    # Fisher information at the mean ability (theta=0): I = a^2 * p*(1-p)
    p0 = 1 / (1 + np.exp(-a * (0 - b)))
    S["info_at_0"] = a ** 2 * p0 * (1 - p0)
    S = S.sort_values("discrimination_a", ascending=False)
    print("=== 2-PL IRT item parameters (sorted by discrimination) ===")
    print(S.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # validate discrimination vs the A4 correlation proxy
    ms = df.groupby(["model", "scenario"])["judge_score"].mean().unstack("scenario")
    ability_proxy = ms.mean(axis=1)
    proxy = {s: stats.pearsonr(ms[s], ability_proxy)[0] for s in ms.columns}
    S["a4_proxy"] = S["scenario"].map(proxy)
    r = stats.spearmanr(S["discrimination_a"], S["a4_proxy"]).correlation
    print(f"\nvalidation: IRT discrimination vs A4 correlation-proxy: Spearman={r:.3f}")

    # model ability ranking
    A = pd.DataFrame({"model": models, "theta": theta}).sort_values("theta", ascending=False)
    print("\n=== top / bottom model ability (theta) ===")
    print(A.head(6).to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print(A.tail(4).to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    # tinyBenchmarks-style: total information from top-k scenarios
    tot = S["info_at_0"].sum()
    cum = S.sort_values("info_at_0", ascending=False)["info_at_0"].cumsum() / tot
    k80 = int((cum < 0.8).sum() + 1)
    print(f"\n=== scenario information ===")
    print(f"most informative: {S.sort_values('info_at_0', ascending=False).iloc[0]['scenario']}")
    print(f"least informative: {S.sort_values('info_at_0').iloc[0]['scenario']}")
    print(f"{k80} of {n_s} scenarios carry 80% of the Fisher information at mean ability "
          f"-> the set could be pruned/rebalanced")

    S.to_csv(REPO / "deep-dive" / "out" / "b1_irt.csv", index=False)
    print("\nsaved out/b1_irt.csv")


if __name__ == "__main__":
    main()
