"""Full-run analysis dataset — `full-chatok-core20-r5-ollama-20260705-150053`.

The 152-model, single controlled-regime run (env.cpu_no_turbo=1, RAPL package-0
on 100% of 15,200 rows) that carries quality (2-judge consensus), safety,
determinism, AND comparable energy on every row. Built to the same shape as
`ceops_data` so the analysis suite can center on it instead of the two-batch
var/wave2 snapshot. Reuses the committed intake bundle; never mutates it.
"""

from __future__ import annotations

import glob
import gzip
import json
import pathlib
import re

import numpy as np
import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[1]
RUN = REPO / ".tmp" / "completed-run-intake" / "full-chatok-core20-r5-ollama-20260705-150053"
JUDGED = RUN / "judged.full-chatok-core20-r5-ollama-20260705-150053.jsonl"
SAFETY_CLASSES = {"guard", "secure"}


def _load_results() -> pd.DataFrame:
    rows = []
    for f in glob.glob(str(RUN / "*.results.jsonl.gz")):
        with gzip.open(f, "rt") as fh:
            for line in fh:
                r = json.loads(line)
                fin = r.get("gen_ai.response.finish_reasons") or []
                rows.append({
                    "model": r["model"], "scenario": r["scenario"], "rep": int(r["rep"]),
                    "det_score": r.get("det_score"),
                    "energy_wh": r.get("power.energy_wh"),
                    "mean_watts": r.get("power.mean_watts"),
                    "decode_tokens_per_s": r.get("decode_tok_s"),
                    "wall_s": r.get("wall_s"),
                    "output_tokens": r.get("gen_ai.usage.output_tokens"),
                    "finish_reason": (fin[0] if isinstance(fin, list) and fin else str(fin)),
                    "no_turbo": r.get("env.cpu_no_turbo"),
                    "power_source": r.get("power.source"),
                })
    return pd.DataFrame(rows)


def _load_judged() -> pd.DataFrame:
    rows = []
    with open(JUDGED) as fh:
        for line in fh:
            r = json.loads(line)
            try:
                s = float(r.get("score"))
            except (TypeError, ValueError):
                continue
            rows.append({"model": r["model"], "scenario": r["scenario"],
                         "rep": int(r["rep"]), "judge_model": r.get("judge_model"), "score": s})
    return pd.DataFrame(rows)


def _parse_pb(m: str) -> float:
    mm = re.search(r"(\d+(?:\.\d+)?)\s*b\b", str(m), re.I)
    return float(mm.group(1)) if mm else np.nan


def load_full() -> pd.DataFrame:
    res = _load_results()
    jud = _load_judged()
    # 2-judge consensus per (model, scenario, rep)
    cons = jud.groupby(["model", "scenario", "rep"])["score"].mean().rename("judge_score").reset_index()
    df = res.merge(cons, on=["model", "scenario", "rep"], how="left")

    df["scenario_class"] = df["scenario"].str.split("-").str[0]
    df["is_safety"] = df["scenario_class"].isin(SAFETY_CLASSES)

    inv = pd.read_csv(REPO / "data" / "models-inventory.csv")
    inv["params_b"] = pd.to_numeric(inv["param_size"].astype(str).str.extract(r"([\d.]+)")[0], errors="coerce")
    mcols = [c for c in ["model", "family", "org", "training_regime", "tools_capable",
                         "thinking_capable", "is_moe", "quant", "params_b", "size_gb",
                         "bracket", "license"] if c in inv.columns]
    df = df.merge(inv[mcols], on="model", how="left")
    df["params_b"] = df["params_b"].fillna(df["model"].map(_parse_pb))

    for c in ["det_score", "energy_wh", "mean_watts", "decode_tokens_per_s", "wall_s",
              "output_tokens", "judge_score", "params_b", "size_gb"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["truncated"] = df["finish_reason"].astype(str).str.contains("length", case=False)
    df["dnf_bool"] = df["finish_reason"].astype(str).str.contains("timeout|dnf", case=False, regex=True)
    # single controlled regime across ALL rows -> energy is comparable for every model
    df["energy_comparable"] = df["no_turbo"].astype(str).eq("1") & df["power_source"].astype(str).eq("rapl:package-0")
    return df


def model_table_full(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("model", dropna=False)
    out = pd.DataFrame(index=g.size().index)
    out["n_runs"] = g.size()
    out["quality"] = g["judge_score"].mean()
    out["quality_sd"] = g["judge_score"].std()
    out["det_score"] = g["det_score"].mean()
    out["decode_tps"] = g["decode_tokens_per_s"].mean()
    out["wall_s"] = g["wall_s"].mean()
    out["energy_wh"] = g["energy_wh"].mean()          # comparable across ALL 152 (single regime)
    out["mean_watts"] = g["mean_watts"].mean()
    out["trunc_rate"] = g["truncated"].mean()
    out["safety"] = df[df["is_safety"]].groupby("model")["judge_score"].mean()
    out["quality_nonsafety"] = df[~df["is_safety"]].groupby("model")["judge_score"].mean()
    for c in ["family", "org", "training_regime", "tools_capable", "thinking_capable",
              "is_moe", "quant", "params_b", "size_gb", "bracket"]:
        if c in df.columns:
            out[c] = g[c].first()
    out = out.reset_index()
    out["quality_per_wh"] = out["quality"] / out["energy_wh"]
    out["quality_per_gb"] = out["quality"] / out["size_gb"]
    out["quality_per_bparam"] = out["quality"] / out["params_b"]
    return out


if __name__ == "__main__":
    df = load_full()
    print("=== full run frame ===")
    print(f"rows={len(df)} | models={df.model.nunique()} | scenarios={df.scenario.nunique()} | reps={sorted(df.rep.unique())}")
    print(f"judge_score {df.judge_score.min():.2f}..{df.judge_score.max():.2f} (mean {df.judge_score.mean():.2f}) matched {df.judge_score.notna().mean()*100:.1f}%")
    print(f"det_score mean {df.det_score.mean():.3f} | energy_wh mean {df.energy_wh.mean():.4f} | energy_comparable {df.energy_comparable.mean()*100:.0f}%")
    print("safety scenarios:", sorted(df[df.is_safety].scenario.unique()))
    mt = model_table_full(df)
    out = REPO / "deep-dive" / "out"
    out.mkdir(parents=True, exist_ok=True)
    mt.to_csv(out / "full_model_table.csv", index=False)
    print("\nsaved", out / "full_model_table.csv", f"({len(mt)} models)")
