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

# reasoning-trained / CoT-emitting families (not plain instruct with thinking_capable)
_REASON_RE = re.compile(r"(?:^|[:/._-])(?:r1|qwq|cogito|deepscaler|marco-o1)|reasoning|thinking|deepseek-r1|-deep\b", re.I)
_META_COLS = ["model", "family", "org", "arch_class", "training_regime", "thinking_capable",
              "tools_capable", "is_moe", "quant", "param_count", "param_size", "size_gb", "bracket"]


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


def _param_size_to_b(s) -> float:
    """Parse a param_size TEXT like '999.89M' / '1.5B' WITH its unit (fallback only)."""
    m = re.search(r"([\d.]+)\s*([mMbB])", str(s))
    if not m:
        return np.nan
    v = float(m.group(1))
    return v / 1000.0 if m.group(2).lower() == "m" else v


def _metadata() -> pd.DataFrame:
    """Rich per-model metadata: model_metadata.csv (94, authoritative) first, then
    models-inventory.csv (158) for the rest."""
    md = pd.read_csv(REPO / "data" / "model_metadata.csv")
    inv = pd.read_csv(REPO / "data" / "models-inventory.csv")
    md = md[[c for c in _META_COLS if c in md.columns]]
    inv = inv[[c for c in _META_COLS if c in inv.columns]]
    combined = pd.concat([md, inv[~inv["model"].isin(md["model"])]], ignore_index=True)
    # params_b: use the clean integer param_count (bug-free); only fall back to the
    # param_size TEXT WITH unit conversion -- never the naked number (999M != 999B).
    combined["params_b"] = pd.to_numeric(combined.get("param_count"), errors="coerce") / 1e9
    combined["params_b"] = combined["params_b"].fillna(combined.get("param_size").map(_param_size_to_b))
    return combined.drop_duplicates("model")


def _join_metadata(df: pd.DataFrame) -> pd.DataFrame:
    df = df.merge(_metadata(), on="model", how="left")
    df["params_b"] = df["params_b"].fillna(df["model"].map(_parse_pb))
    md_reason = df.get("training_regime", pd.Series("", index=df.index)).astype(str).str.contains("reason", case=False, na=False)
    df["is_reasoning"] = md_reason | df["model"].str.contains(_REASON_RE)
    tc = df.get("tools_capable", pd.Series(index=df.index)).astype("string").str.lower()
    df["is_tools"] = tc.map({"true": True, "false": False})  # missing metadata -> NaN (unknown-preserving)
    return df


def _scenario_class_map() -> dict:
    """Authoritative scenario -> class from the scenario set (NOT the name prefix)."""
    p = REPO / "data" / "scenario_sets" / "core-current.json"
    dd = json.loads(p.read_text())
    items = dd if isinstance(dd, list) else dd.get("scenarios", dd.get("items", []))
    return {(it.get("id") or it.get("scenario")): (it.get("class") or it.get("category"))
            for it in items if (it.get("id") or it.get("scenario"))}


def load_full() -> pd.DataFrame:
    res = _load_results()
    jud = _load_judged()
    # 2-judge consensus per (model, scenario, rep)
    cons = jud.groupby(["model", "scenario", "rep"])["score"].mean().rename("judge_score").reset_index()
    df = res.merge(cons, on=["model", "scenario", "rep"], how="left")

    df["scenario_class"] = df["scenario"].map(_scenario_class_map()).fillna(df["scenario"].str.split("-").str[0])
    df["is_safety"] = df["scenario_class"].isin(SAFETY_CLASSES)

    df = _join_metadata(df)

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
    # canonical energy normalizations (analysis_metrics.py): per det-correct + per output token
    _es, _ds, _ts = g["energy_wh"].sum(), g["det_score"].sum(), g["output_tokens"].sum()
    out["wh_per_det_correct"] = _es / _ds.where(_ds > 0)
    out["j_per_output_token"] = _es * 3600.0 / _ts.where(_ts > 0)
    out["mean_watts"] = g["mean_watts"].mean()
    out["trunc_rate"] = g["truncated"].mean()
    out["safety"] = df[df["is_safety"]].groupby("model")["judge_score"].mean()
    out["quality_nonsafety"] = df[~df["is_safety"]].groupby("model")["judge_score"].mean()
    for c in ["family", "org", "training_regime", "tools_capable", "thinking_capable",
              "is_moe", "quant", "params_b", "size_gb", "bracket", "is_reasoning", "is_tools", "arch_class"]:
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
    print(f"is_reasoning models: {df[df.is_reasoning].model.nunique()} | is_tools models: {df[df.is_tools == True].model.nunique()}")
    mt = model_table_full(df)
    out = REPO / "deep-dive" / "out"
    out.mkdir(parents=True, exist_ok=True)
    mt.to_csv(out / "full_model_table.csv", index=False)
    print("\nsaved", out / "full_model_table.csv", f"({len(mt)} models)")
