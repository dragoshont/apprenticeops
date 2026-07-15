"""B3 — Partial effects with model-clustered inference.

The A3 group contrasts (tools +0.43, reasoning -0.65) could be confounded: tool
models are also bigger/newer. This fits judge_score on all model-level factors at
once with **scenario fixed effects** (controls task difficulty) and **standard
errors clustered by model** (Miller 2024: the unit of replication is the model,
not the 9,025 runs). A crossed linear mixed model (model+scenario random effects)
is fit as a cross-check.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from ceops_data import load_runs


def main() -> None:
    df = load_runs().dropna(subset=["judge_score"]).copy()
    df["tools"] = df["tools_capable"].astype(str).str.lower().isin(["true", "1"]).astype(int)
    df["moe"] = df["is_moe"].astype(str).str.lower().isin(["true", "1"]).astype(int)
    df["think"] = df["thinking_capable"].astype(str).str.lower().isin(["true", "1"]).astype(int)
    df["regime"] = df["training_regime"].astype(str).replace({"code/math": "code_math"})
    df["quant_grp"] = np.where(df["quant"].astype(str).str.upper().str.startswith("Q4"), "Q4",
                        np.where(df["quant"].astype(str).str.upper().eq("Q8_0"), "Q8", "hi"))
    df["log_params"] = np.log(df["params_b"].clip(lower=0.05))
    df["regime"] = pd.Categorical(df["regime"], categories=["instruct", "code_math", "reasoning"])
    df["quant_grp"] = pd.Categorical(df["quant_grp"], categories=["Q4", "Q8", "hi"])

    mdf = df.dropna(subset=["judge_score", "params_b", "log_params"]).copy()
    mdf = mdf[mdf["regime"].notna() & mdf["quant_grp"].notna()].reset_index(drop=True)
    formula = "judge_score ~ tools + moe + C(regime) + C(quant_grp) + log_params + C(scenario)"
    groups = mdf["model"].astype("category").cat.codes.values
    m = smf.ols(formula, data=mdf).fit(cov_type="cluster", cov_kwds={"groups": groups})

    print("=== OLS judge_score ~ model factors + scenario FE, SE clustered by model ===")
    print(f"n={int(m.nobs)} runs, {df['model'].nunique()} model clusters, R^2={m.rsquared:.3f}\n")
    keep = [p for p in m.params.index if not p.startswith("C(scenario)") and p != "Intercept"]
    tab = pd.DataFrame({
        "coef": m.params[keep],
        "ci_lo": m.conf_int().loc[keep, 0],
        "ci_hi": m.conf_int().loc[keep, 1],
        "p": m.pvalues[keep],
    })
    tab["sig"] = np.where(tab.p < 0.001, "***", np.where(tab.p < 0.01, "**", np.where(tab.p < 0.05, "*", "ns")))
    print(tab.to_string(float_format=lambda x: f"{x:+.3f}"))
    print("\nreading: tools = partial effect of tool-training holding params/regime/quant/scenario fixed.")

    # crossed linear mixed model cross-check (model + scenario random intercepts)
    try:
        agg = mdf.groupby(["model", "scenario"], observed=True).agg(
            judge_score=("judge_score", "mean"), tools=("tools", "first"), moe=("moe", "first"),
            regime=("regime", "first"), quant_grp=("quant_grp", "first"), log_params=("log_params", "first")).reset_index()
        agg["one"] = 1
        vc = {"scenario": "0 + C(scenario)"}
        mm = smf.mixedlm("judge_score ~ tools + moe + C(regime) + C(quant_grp) + log_params",
                         data=agg, groups="model", vc_formula=vc).fit(method="lbfgs", maxiter=200)
        print("\n=== crossed mixed model (random intercepts: model + scenario) cross-check ===")
        for p in ["tools", "moe", "C(regime)[T.reasoning]", "C(quant_grp)[T.Q8]", "log_params"]:
            if p in mm.params.index:
                print(f"  {p:26} {mm.params[p]:+.3f}  (p={mm.pvalues[p]:.3f})")
        print(f"  var(model)={mm.cov_re.iloc[0,0]:.3f}  var(scenario)~vc  resid={mm.scale:.3f}")
    except Exception as e:
        print("\n(mixed model cross-check skipped:", type(e).__name__, str(e)[:80], ")")

    # standardized effect sizes vs residual model SD
    model_sd = mdf.groupby("model")["judge_score"].mean().std()
    print(f"\nbetween-model SD of quality = {model_sd:.2f} pts (1-5). "
          f"tools partial effect = {m.params['tools']:+.2f} = {m.params['tools']/model_sd:.2f} model-SD.")


if __name__ == "__main__":
    main()
