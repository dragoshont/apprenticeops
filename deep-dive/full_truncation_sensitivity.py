"""Truncation sensitivity — who hit the per-scenario output cap, and do the
findings survive dropping them?

The 152 run (`full-chatok-core20-r5`) used a per-scenario `max_tokens` budget
(400-700). A model row is *truncated* when `finish_reason == "length"`. 92/152
models truncated at least one row (9.6% of all rows), concentrated in the
reasoning + code + tiny/verbose classes.

This module answers the cheap alternative to a de-truncation re-run: *if we drop
the models that suffered the cap, how many survive, and does the headline hold?*
It shows the relative findings (top model, tools effect, scale effect, safety~
quality coupling) are STABLE across the full 152 and the <=10% / <=5% / 0%
subsets, while the absolute mean quality drifts UP as truncated models are
dropped -- a selection bias (the dropped models are smaller, verbose, and
lower-quality), which must be disclosed rather than silently "cleaned".
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

from full_data import REPO, RUN_ID, _load_judged, _load_results, _metadata

# safety = guard|secure classes in core-current (authoritative ids, not name prefix)
SAFETY_SCENARIOS = {
    "guard-08-destructive", "secure-09-plaintext-secret", "secure-10-ingress-no-auth",
    "secure-12-broad-rbac", "secure-14-injection-destructive",
}
OUT = REPO / "deep-dive" / "out" / "full_truncation_sensitivity.csv"


def _pb(model: str) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)\s*b", str(model).lower())
    return float(m.group(1)) if m else np.nan


def model_table() -> pd.DataFrame:
    """Per-model: truncation %, consensus quality (overall / safety / non-safety),
    tools capability, params. Sorted by quality so subset top-1 is deterministic."""
    res = _load_results()
    res["trunc"] = res["finish_reason"].astype(str).str.contains("length")
    trunc = (res.groupby("model")["trunc"].mean() * 100).rename("trunc_pct")

    cell = _load_judged().groupby(["model", "scenario", "rep"])["score"].mean().reset_index()
    cell["safe"] = cell["scenario"].isin(SAFETY_SCENARIOS)
    quality = cell.groupby("model")["score"].mean().rename("quality")
    safety = cell[cell["safe"]].groupby("model")["score"].mean().rename("safety")
    nonsafety = cell[~cell["safe"]].groupby("model")["score"].mean().rename("nonsafety")

    md = _metadata()[["model", "tools_capable", "params_b"]]
    d = pd.concat([trunc, quality, safety, nonsafety], axis=1).reset_index().merge(md, on="model", how="left")
    tc = d["tools_capable"].astype("string").str.lower()
    d["is_tools"] = tc.map({"true": True, "false": False})
    d["params_b"] = d["params_b"].fillna(d["model"].map(_pb))
    return d.sort_values(["quality", "model"], ascending=[False, True], kind="stable").reset_index(drop=True)


def _subset_row(sub: pd.DataFrame, label: str) -> dict:
    s = sub.dropna(subset=["safety", "nonsafety"])
    tools_hi = sub.loc[sub["is_tools"] == True, "quality"].mean()   # noqa: E712 (nullable bool)
    tools_lo = sub.loc[sub["is_tools"] == False, "quality"].mean()  # noqa: E712
    return {
        "subset": label, "n": len(sub),
        "top_model": sub.iloc[0]["model"], "top_q": round(float(sub.iloc[0]["quality"]), 2),
        "mean_q": round(float(sub["quality"].mean()), 3),
        "tools_delta": round(float(tools_hi - tools_lo), 3),
        "params_rho": round(float(spearmanr(sub["params_b"], sub["quality"], nan_policy="omit")[0]), 3),
        "safety_quality_r": round(float(pearsonr(s["safety"], s["nonsafety"])[0]), 3),
    }


def main() -> None:
    d = model_table()
    n = len(d)
    print(f"run: {RUN_ID}")
    print(f"truncation: {(d.trunc_pct > 0).sum()}/{n} models truncated >=1 row; "
          f"{(d.trunc_pct > 20).sum()} >20%, {(d.trunc_pct > 50).sum()} >50%, {(d.trunc_pct >= 100).sum()} at 100%")

    print("\nsurvival if we DROP every model above a truncation threshold:")
    for thr in (0, 2, 5, 10, 20):
        keep = int((d.trunc_pct <= thr).sum())
        print(f"  keep trunc<={thr:>2}%  ->  {keep:3d} survive / {n - keep:3d} dropped")

    report = pd.DataFrame([
        _subset_row(d, "full-152"),
        _subset_row(d[d.trunc_pct <= 10], "le10pct"),
        _subset_row(d[d.trunc_pct <= 5], "le5pct"),
        _subset_row(d[d.trunc_pct <= 0], "zero-trunc"),
    ])
    print("\nrobustness of key findings across subsets "
          "(relative = stable; mean_q drifts up = disclosed selection bias):")
    print(report.to_string(index=False))

    # bias characterisation: what gets dropped at the strict 0% cut?
    dropped, kept = d[d.trunc_pct > 0], d[d.trunc_pct <= 0]
    print(f"\nstrict 0% cut: drop {len(dropped)} / keep {len(kept)}  |  "
          f"mean quality dropped={dropped.quality.mean():.2f} vs kept={kept.quality.mean():.2f}  |  "
          f"median params dropped={dropped.params_b.median():.1f}B vs kept={kept.params_b.median():.1f}B")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    d.to_csv(OUT, index=False)
    print(f"\nwrote {OUT.relative_to(REPO)} ({n} models)")


if __name__ == "__main__":
    main()
