"""A4 — Capability structure: scenario difficulty, discrimination, and safety.

* scenario difficulty (mean quality) and *discrimination* (how well a scenario
  separates strong from weak models -- a lightweight IRT-style proxy: correlation
  of per-scenario score with overall model ability);
* per scenario-class winners by family;
* safety deep-dive: who refuses destructive/insecure actions (guard + 5 secure).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from ceops_data import REPO, load_runs

def main() -> None:
    df = load_runs()
    # per (model, scenario) mean
    ms = df.groupby(["model", "scenario"])["judge_score"].mean().unstack("scenario")
    ability = ms.mean(axis=1)  # overall model ability

    sc_class = df.drop_duplicates("scenario").set_index("scenario")["scenario_class"]

    rows = []
    for s in ms.columns:
        col = ms[s]
        diff = col.mean()  # difficulty (higher = easier)
        disc = stats.pearsonr(col, ability)[0]  # discrimination proxy
        spread = col.std()
        rows.append((s, sc_class.get(s, "?"), diff, spread, disc))
    S = pd.DataFrame(rows, columns=["scenario", "class", "mean_quality", "spread", "discrimination"]).sort_values("discrimination", ascending=False)
    print("=== scenario discrimination (how well it separates strong/weak models) ===")
    print(S.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print(f"\nmost discriminative: {S.iloc[0]['scenario']} (r={S.iloc[0]['discrimination']:.2f})")
    print(f"least discriminative: {S.iloc[-1]['scenario']} (r={S.iloc[-1]['discrimination']:.2f}) -- near-redundant / everyone similar")
    print(f"hardest (lowest mean quality): {S.sort_values('mean_quality').iloc[0]['scenario']} ({S.sort_values('mean_quality').iloc[0]['mean_quality']:.2f})")
    print(f"easiest: {S.sort_values('mean_quality').iloc[-1]['scenario']} ({S.sort_values('mean_quality').iloc[-1]['mean_quality']:.2f})")

    # per scenario-class: family means (who wins which ops verb)
    dfm = df.merge(df.groupby('model')['judge_score'].mean().rename('ability'), on='model')
    print("\n=== mean quality by scenario-class x top families ===")
    piv = df.pivot_table(index="family", columns="scenario_class", values="judge_score", aggfunc="mean")
    keep_fam = df.groupby("family")["model"].nunique()
    piv = piv.loc[keep_fam[keep_fam >= 3].index]
    piv["ALL"] = piv.mean(axis=1)
    piv = piv.sort_values("ALL", ascending=False)
    print(piv.round(2).to_string())

    # safety deep-dive: per-model safety, and the destructive-guard scenario specifically
    saf = df[df.is_safety].groupby("model")["judge_score"].mean().sort_values(ascending=False)
    print("\n=== safest models (mean judge on 6 safety scenarios) ===")
    print(saf.head(8).to_string(float_format=lambda x: f"{x:.2f}"))
    print("=== least safe ===")
    print(saf.tail(6).to_string(float_format=lambda x: f"{x:.2f}"))

    # guard-08-destructive specifically: does the model avoid the destructive action?
    guard = df[df.scenario.eq("guard-08-destructive")].groupby("model")["det_score"].mean().sort_values()
    print(f"\n=== guard-08-destructive det_score (0=took destructive action / failed, 1=correctly refused) ===")
    print(f"models that FAILED the destructive-guard (det<0.5): {(guard<0.5).sum()}/{len(guard)}")
    print("worst (most likely to take destructive action):")
    print(guard.head(8).to_string(float_format=lambda x: f"{x:.2f}"))

    # safety vs quality: are the best models also safe? (correlation)
    q = df.groupby("model")["judge_score"].mean()
    both = pd.concat([q.rename("quality"), saf.rename("safety")], axis=1).dropna()
    r = stats.pearsonr(both["quality"], both["safety"])[0]
    print(f"\n=== safety vs quality correlation across models: r={r:.3f} ===")
    # models with biggest safety deficit relative to quality
    both["gap"] = both["safety"] - both["quality"]
    print("quality>>safety (capable but comparatively UNsafe):")
    print(both.sort_values("gap").head(5).to_string(float_format=lambda x: f"{x:.2f}"))

    S.to_csv(REPO / "deep-dive" / "out" / "a4_scenarios.csv", index=False)
    print("\nsaved a4_scenarios.csv")


if __name__ == "__main__":
    main()
