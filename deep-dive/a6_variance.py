"""A6 — Variance, reproducibility, and failure structure.

* per-model rep-to-rep stability (temp 0.7, 5 reps);
* variance decomposition of judge_score: model vs scenario vs interaction vs rep
  (is the benchmark measuring the model or the task?);
* split-half rank reproducibility;
* DNF/timeout concentration and truncation by model/scenario.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from ceops_data import REPO, load_runs


def main() -> None:
    df = load_runs()

    # ---- rep stability ----
    rep_sd = df.groupby(["model", "scenario"])["judge_score"].std().groupby("model").mean()
    print("=== rep-to-rep stability (mean within-(model,scenario) SD of judge_score) ===")
    print("most STABLE models:")
    print(rep_sd.sort_values().head(5).to_string(float_format=lambda x: f"{x:.3f}"))
    print("most STOCHASTIC models:")
    print(rep_sd.sort_values(ascending=False).head(5).to_string(float_format=lambda x: f"{x:.3f}"))
    print(f"overall mean within-cell SD: {rep_sd.mean():.3f} (on a 1-5 scale)")

    # ---- variance decomposition (type-I SS: model, scenario, interaction, residual) ----
    d = df.dropna(subset=["judge_score"]).copy()
    gm = d.judge_score.mean()
    sst = ((d.judge_score - gm) ** 2).sum()
    mm = d.groupby("model")["judge_score"].transform("mean")
    sm = d.groupby("scenario")["judge_score"].transform("mean")
    ss_model = ((mm - gm) ** 2).sum()
    ss_scen = ((sm - gm) ** 2).sum()
    cell = d.groupby(["model", "scenario"])["judge_score"].transform("mean")
    ss_inter = ((cell - mm - sm + gm) ** 2).sum()
    ss_resid = ((d.judge_score - cell) ** 2).sum()  # rep-level (irreducible)
    print("\n=== variance decomposition of judge_score ===")
    for name, ss in [("model (who)", ss_model), ("scenario (task)", ss_scen),
                     ("model x scenario (specialisation)", ss_inter), ("rep (noise)", ss_resid)]:
        print(f"  {name:34} {100*ss/sst:5.1f}%")
    print("  -> 'model' = how much variance is the model identity; 'scenario' = task difficulty;")
    print("     'interaction' = models having different strengths; 'rep' = irreducible sampling noise")

    # ---- split-half reproducibility ----
    a = df[df.rep.isin([0, 1, 2])].groupby("model")["judge_score"].mean()
    b = df[df.rep.isin([3, 4])].groupby("model")["judge_score"].mean()
    both = pd.concat([a, b], axis=1).dropna()
    sh = stats.spearmanr(both.iloc[:, 0], both.iloc[:, 1])[0]
    print(f"\n=== split-half rank reproducibility (reps 0-2 vs 3-4): Spearman={sh:.3f} ===")

    # ---- failures ----
    print("\n=== DNF / timeout concentration ===")
    print(f"overall DNF rate: {df.dnf_bool.mean():.1%}")
    dnf_scen = df.groupby("scenario")["dnf_bool"].mean().sort_values(ascending=False)
    print("scenarios with most DNF (timeout/error):")
    print(dnf_scen.head(5).to_string(float_format=lambda x: f"{x:.1%}"))
    dnf_model = df.groupby("model")["dnf_bool"].mean().sort_values(ascending=False)
    print("models with most DNF:")
    print(dnf_model[dnf_model > 0].head(6).to_string(float_format=lambda x: f"{x:.1%}"))

    print("\n=== truncation (finish_reason=length) ===")
    print(f"overall truncation rate: {df.truncated.mean():.1%}")
    tr_model = df.groupby("model")["truncated"].mean().sort_values(ascending=False)
    print("models that most often run to the token cap (verbose / non-terminating):")
    print(tr_model.head(6).to_string(float_format=lambda x: f"{x:.1%}"))
    # does truncation hurt quality?
    tq = df.groupby("truncated")["judge_score"].mean()
    print(f"quality when truncated={tq.get(True, float('nan')):.2f} vs not={tq.get(False, float('nan')):.2f}")


if __name__ == "__main__":
    main()
