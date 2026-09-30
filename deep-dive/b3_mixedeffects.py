"""B3 population audit; training/architecture inferential claims are excluded.

The earlier fit reported the input roster as its fitted cluster count. It also
treated unknown flags as false and fitted scenario effects nested within model,
not shared crossed effects. Tag-level clusters are not verified weight lineages.
We report the observed complete-case design, not spurious partial-effect CIs.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ceops_data import load_runs


def known_bool(s: pd.Series) -> pd.Series:
    return s.astype("string").str.lower().map(
        {"true": 1., "false": 0., "1": 1., "0": 0.})


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    for col, source in [("tools", "tools_capable"), ("moe", "is_moe"),
                        ("think", "thinking_capable")]:
        d[col] = known_bool(d[source])
    d["regime"] = d.training_regime.astype("string").replace({"code/math": "code_math"})
    d["regime"] = d.regime.where(d.regime.isin(["instruct", "code_math", "reasoning"]))
    q = d["quant"].astype("string").str.upper()
    d["quant_grp"] = q.map({"Q4_K_M": "Q4", "Q4_K_S": "Q4", "Q4_0": "Q4",
                            "Q8_0": "Q8", "F16": "hi", "FP16": "hi", "BF16": "hi"})
    d["log_params"] = np.log(d.params_b.where(d.params_b > 0))
    return d


def complete_cases(d: pd.DataFrame) -> pd.DataFrame:
    # Thinking capability was not in the previous formula; do not invent an arm.
    return d.dropna(subset=["model", "scenario", "judge_score", "log_params",
                           "tools", "moe", "regime", "quant_grp"]).copy()


def population_audit(df: pd.DataFrame) -> pd.DataFrame:
    prepared = prepare(df)
    fitted = complete_cases(prepared)
    t = prepared.groupby("model").agg(
        assigned_rows=("scenario", "size"), observed_scores=("judge_score", "count"),
        known_tools=("tools", "count"), known_moe=("moe", "count"),
        known_regime=("regime", "count"), known_quant=("quant_grp", "count"))
    t["complete_case_rows"] = fitted.groupby("model").size().reindex(t.index, fill_value=0)
    return t.reset_index()


def main() -> None:
    df = load_runs()
    prepared = prepare(df)
    cc = complete_cases(prepared)
    print(f"Input: {len(df)} rows, {df.model.nunique()} deployments, "
          f"{df.scenario.nunique()} scenarios.")
    print(f"Observed complete-case design: {len(cc)} rows, {cc.model.nunique()} deployments, "
          f"{cc.scenario.nunique()} scenarios; excluded {len(df)-len(cc)} rows.")
    print("Fitted rows: 0; no inferential model retained.")
    for c in ["tools", "moe", "regime", "quant_grp", "log_params"]:
        print(f"  {c}: unknown rows={prepared[c].isna().sum()}, "
              f"complete-case deployment levels="
              f"{cc.drop_duplicates('model')[c].value_counts().to_dict()}")
    print("NOT IDENTIFIABLE: verified independent weight lineages and sufficiently "
          "replicated architecture/training arms are unavailable. Unknown metadata "
          "is excluded, not false. Old model-clustered coefficient intervals and "
          "the mis-specified mixed-model cross-check are withdrawn. No causal effects.")
    print("No cov_re access or nested-as-crossed fit is attempted. A future crossed "
          "model requires identified lineage and scenario effects shared across deployments.")


if __name__ == "__main__":
    main()
