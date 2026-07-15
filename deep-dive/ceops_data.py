"""Unified CEOps / ApprenticeOps analysis dataset.

Joins the canonical snapshots (results + judged) with model metadata into one
run-level DataFrame at (model x scenario x rep) grain, plus a model-level
aggregate. Faithful to the repo's canonical semantics:

* safety scenarios = scenario ``class`` in {guard, secure} (analysis_metrics.SAFETY_CLASSES);
* energy is only cross-model-comparable within the controlled single-regime scope
  (``energy_analysis_scope == 'controlled_three_axis'``); we honour
  ``energy_cross_batch_comparison_allowed == false``.

Standard-library + pandas only. Reuses the published snapshots; never mutates them.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[1]
DATA = REPO / "data"
SAFETY_CLASSES = {"guard", "secure"}

_NUMERIC = [
    "det_score", "judge_score", "decode_tokens_per_s", "prefill_tokens_per_s",
    "wall_s", "membw_peak_mb_s", "energy_wh", "parameter_count", "artifact_size_bytes",
    "size_gb", "param_count", "expert_count", "expert_used_count", "native_ctx",
]


def _scenario_classes() -> dict[str, str]:
    classes: dict[str, str] = {}
    for name in ("scenarios.json", "scenarios.candidates.json"):
        p = DATA / name
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        items = d if isinstance(d, list) else d.get("scenarios", d.get("items", []))
        for it in items:
            sid = it.get("id") or it.get("scenario")
            cls = it.get("class") or it.get("category")
            if sid and cls:
                classes.setdefault(str(sid), str(cls))
    for p in (DATA / "scenario_sets").glob("*.json"):
        d = json.loads(p.read_text())
        items = d if isinstance(d, list) else d.get("scenarios", d.get("items", []))
        for it in items:
            sid = it.get("id") or it.get("scenario")
            cls = it.get("class") or it.get("category")
            if sid and cls:
                classes.setdefault(str(sid), str(cls))
    return classes


def load_runs() -> pd.DataFrame:
    res = pd.read_csv(DATA / "snapshots" / "results_snapshot.csv")
    jud = pd.read_csv(DATA / "snapshots" / "judged_snapshot.csv")
    meta = pd.read_csv(DATA / "model_metadata.csv")

    keys = [
        "model", "runtime_adapter", "parameter_tier", "legacy_footprint_bracket",
        "collection_batch", "cpu_frequency_regime", "scenario", "rep",
    ]
    keys = [k for k in keys if k in res.columns and k in jud.columns]
    jcols = keys + [c for c in ("judge_score",) if c in jud.columns]
    df = res.merge(jud[jcols], on=keys, how="left", validate="one_to_one")

    meta_cols = ["model"] + [c for c in meta.columns if c != "model" and c not in df.columns]
    df = df.merge(meta[meta_cols], on="model", how="left")

    sc = _scenario_classes()
    df["scenario_class"] = df["scenario"].map(sc)
    unmapped = df["scenario_class"].isna()
    df.loc[unmapped, "scenario_class"] = df.loc[unmapped, "scenario"].str.split("-").str[0]
    df["is_safety"] = df["scenario_class"].isin(SAFETY_CLASSES)

    for c in _NUMERIC:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df["dnf_bool"] = df["dnf"].astype(str).str.lower().isin(["true", "1", "yes"])
    df["completed"] = ~df["dnf_bool"]
    df["truncated"] = df["finish_reason"].astype(str).eq("length")
    # size in GB from artifact bytes when metadata size_gb missing
    if "size_gb" in df.columns:
        df["size_gb"] = df["size_gb"].fillna(df["artifact_size_bytes"] / 1e9)
    else:
        df["size_gb"] = df["artifact_size_bytes"] / 1e9
    df["params_b"] = df.get("param_count", df.get("parameter_count")) / 1e9
    # energy comparability (controlled single regime)
    df["energy_comparable"] = df.get("energy_analysis_scope", "").eq("controlled_three_axis")
    return df


def model_table(df: pd.DataFrame) -> pd.DataFrame:
    """Model-level aggregates. Quality/safety use the 2-judge consensus judge_score;
    energy means use only the controlled-comparable subset."""
    g = df.groupby("model", dropna=False)
    tax_cols = [c for c in ["family", "org", "arch_class", "training_regime", "quant",
                            "bracket", "legacy_footprint_bracket", "is_moe", "thinking_capable",
                            "tools_capable", "license", "params_b", "size_gb", "native_ctx"]
                if c in df.columns]
    out = pd.DataFrame(index=g.size().index)
    out["n_runs"] = g.size()
    out["quality"] = g["judge_score"].mean()
    out["det_score"] = g["det_score"].mean()
    out["quality_sd"] = g["judge_score"].std()
    out["dnf_rate"] = g["dnf_bool"].mean()
    out["trunc_rate"] = g["truncated"].mean()
    out["decode_tps"] = g["decode_tokens_per_s"].mean()
    out["prefill_tps"] = g["prefill_tokens_per_s"].mean()
    out["wall_s"] = g["wall_s"].mean()
    out["membw_peak_mb_s"] = g["membw_peak_mb_s"].mean()
    # safety = judge_score on safety scenarios
    saf = df[df["is_safety"]].groupby("model")["judge_score"].mean()
    out["safety"] = saf
    nonsaf = df[~df["is_safety"]].groupby("model")["judge_score"].mean()
    out["quality_nonsafety"] = nonsaf
    # energy: controlled-comparable only
    ec = df[df["energy_comparable"]].groupby("model")["energy_wh"].mean()
    out["energy_wh_controlled"] = ec
    out["energy_wh_all"] = g["energy_wh"].mean()  # descriptive only
    for c in tax_cols:
        out[c] = g[c].first()
    out = out.reset_index()
    # efficiency ratios (quality per resource)
    out["quality_per_gb"] = out["quality"] / out["size_gb"]
    out["quality_per_bparam"] = out["quality"] / out["params_b"]
    out["quality_per_sec"] = out["quality"] / out["wall_s"]
    out["quality_per_wh_controlled"] = out["quality"] / out["energy_wh_controlled"]
    return out


if __name__ == "__main__":
    df = load_runs()
    print("=== run-level frame ===")
    print("rows:", len(df), "| models:", df["model"].nunique(),
          "| scenarios:", df["scenario"].nunique(), "| reps:", sorted(df["rep"].unique()))
    print("judge_score matched:", df["judge_score"].notna().sum(), "/", len(df))
    print("det_score  range: %.3f .. %.3f (mean %.3f)" % (df.det_score.min(), df.det_score.max(), df.det_score.mean()))
    print("judge_score range: %.3f .. %.3f (mean %.3f)" % (df.judge_score.min(), df.judge_score.max(), df.judge_score.mean()))
    print("scenario classes:", dict(df.groupby("scenario_class")["scenario"].nunique()))
    print("safety scenarios:", sorted(df[df.is_safety]["scenario"].unique()))
    print("energy_comparable rows:", int(df.energy_comparable.sum()),
          "| models with controlled energy:", df[df.energy_comparable]["model"].nunique())
    print("collection_batch x regime:", dict(df.groupby(["collection_batch", "cpu_frequency_regime"]).size()))

    mt = model_table(df)
    out = REPO / "deep-dive" / "out"
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "runs.parquet")
    mt.to_csv(out / "model_table.csv", index=False)
    print("\n=== model table (top 8 by quality) ===")
    cols = ["model", "quality", "safety", "det_score", "energy_wh_controlled", "decode_tps", "size_gb", "params_b", "family"]
    print(mt.sort_values("quality", ascending=False)[cols].head(8).to_string(index=False))
    print("\nsaved:", out / "runs.parquet", "and", out / "model_table.csv")
