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
RUN_ID = "full-chatok-core20-r5-ollama-20260705-150053"
# Prefer the durable, content-addressed LOCKED bundle (survives .tmp cleanup and is
# hash-bound by bundle-manifest.json); fall back to the ephemeral .tmp intake only if
# the promoted bundle is absent (AGENTS.md: read the locked bundle, not .tmp/).
_BUNDLE_ID = "dd262a5c94593cb4b35bbb3554cc7ed1d608fab8b16160a3215329637c614baa"
LOCKED = REPO / "data" / "completed-runs" / f"{RUN_ID}-{_BUNDLE_ID}"
_TMP = REPO / ".tmp" / "completed-run-intake" / RUN_ID
# Portable tracked fallback for a fresh clone without the heavy (gitignored) bundle:
# compact CSVs that ARE the serialized _load_results()/_load_judged() output.
# Regenerated from the locked bundle by deep-dive/full_snapshot.py.
_SNAP_RESULTS = REPO / "data" / "snapshots" / f"{RUN_ID}.results.csv"
_SNAP_JUDGED = REPO / "data" / "snapshots" / f"{RUN_ID}.judged.csv"
SAFETY_CLASSES = {"guard", "secure"}
EXPECTED_JUDGES = frozenset({"claude-opus-4.6", "gpt-5.4"})
EVALUATION_POLICY = "deterministic-checks-v1|judges:copilot:claude-opus-4.6+copilot:gpt-5.4"
# Canonical per-observation cell key. The whole analysis is keyed on it, so the
# results<->judged join MUST be 1-to-1 on exactly these columns (see _assert_join_integrity).
_CELL = ["model", "scenario", "rep"]

# reasoning-trained / CoT-emitting families (not plain instruct with thinking_capable)
_REASON_RE = re.compile(r"(?:^|[:/._-])(?:r1|qwq|cogito|deepscaler|marco-o1)|reasoning|thinking|deepseek-r1|-deep\b", re.I)
_META_COLS = ["model", "family", "org", "arch_class", "training_regime", "thinking_capable",
              "tools_capable", "is_moe", "quant", "param_count", "param_size", "size_gb", "bracket"]


def _source() -> tuple[list[pathlib.Path], pathlib.Path]:
    """Resolve (results_files, judged_file). The locked bundle uses a single canonical
    ``results.jsonl.gz`` + ``judged.jsonl.gz``; the .tmp intake uses per-model
    ``*.results.jsonl.gz`` + one plaintext ``judged.<run>.jsonl``. Both carry identical
    field semantics, so the analysis is source-agnostic."""
    canon = LOCKED / "canonical"
    if (canon / "results.jsonl.gz").exists():
        return [canon / "results.jsonl.gz"], canon / "judged.jsonl.gz"
    return ([pathlib.Path(f) for f in glob.glob(str(_TMP / "*.results.jsonl.gz"))],
            _TMP / f"judged.{RUN_ID}.jsonl")


def _open_text(path: pathlib.Path):
    return gzip.open(path, "rt") if str(path).endswith(".gz") else open(path)


def _load_results() -> pd.DataFrame:
    results_files, _ = _source()
    if not results_files or not results_files[0].exists():
        return pd.read_csv(_SNAP_RESULTS)  # portable tracked fallback (pre-mapped)
    rows = []
    for f in results_files:
        with _open_text(f) as fh:
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
    _, judged_file = _source()
    if not judged_file.exists():
        return pd.read_csv(_SNAP_JUDGED)  # portable tracked fallback (pre-mapped)
    rows = []
    with _open_text(judged_file) as fh:
        for line in fh:
            r = json.loads(line)
            if (r.get("judge_backend") != "copilot" or r.get("judge_model") not in EXPECTED_JUDGES
                    or r.get("evaluation_policy") != EVALUATION_POLICY):
                raise ValueError("judgment does not match the fixed named judge policy")
            try:
                s = float(r.get("score"))
            except (TypeError, ValueError):
                continue
            rows.append({"model": r["model"], "scenario": r["scenario"],
                         "rep": int(r["rep"]), "judge_model": r.get("judge_model"), "score": s})
    return pd.DataFrame(rows)


def _parse_pb(m: str) -> float:
    """Last-resort: parse a size out of the MODEL NAME, unit-aware ('4b' -> 4.0, '270m' -> 0.27).

    Previously this matched only `b`, so every M-suffixed name (gemma3:270m,
    granite4:350m, LFM2-350M/700M) silently became NaN and dropped out of every
    size-based analysis -- which biased size correlations by deleting the small end.
    """
    mm = re.search(r"(\d+(?:\.\d+)?)\s*([mb])\b", str(m), re.I)
    if not mm:
        return np.nan
    v = float(mm.group(1))
    return v / 1000.0 if mm.group(2).lower() == "m" else v


def _run_param_counts() -> pd.Series:
    """Per-model parameter_count AS REPORTED BY THE RUN ITSELF (`ollama.parameter_count`).

    This is the authoritative source -- it is what the engine actually loaded -- and it
    covers all 152 models, unlike the curated CSVs (which left 11 models, mostly the
    sub-1B end plus phi3:mini, without any parameter metadata). Extracted from the locked
    bundle into a compact tracked snapshot so offline reproduction keeps working.
    """
    path = REPO / "data" / "snapshots" / f"{RUN_ID}.model-params.csv"
    if not path.exists():
        return pd.Series(dtype=float)
    mp = pd.read_csv(path)
    if mp["model"].duplicated().any():
        raise ValueError("duplicate model in run parameter snapshot")
    count = pd.to_numeric(mp["param_count"], errors="raise")
    if ((count.notna()) & ((count <= 0) | (count % 1 != 0))).any():
        raise ValueError("run parameter counts must be positive integers or missing")
    return (count / 1e9).set_axis(mp["model"])


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
    # Retain curated integers for auditing, never use text/name estimates for eligibility.
    combined["params_b"] = pd.to_numeric(combined.get("param_count"), errors="coerce") / 1e9
    return combined.drop_duplicates("model")


def _join_metadata(df: pd.DataFrame) -> pd.DataFrame:
    df = df.merge(_metadata(), on="model", how="left")
    # Actual run integers outrank curated metadata. Absence is unknown, not a tag estimate.
    df["curated_params_b"] = df["params_b"]
    df["params_b"] = df["model"].map(_run_param_counts())
    df["curated_param_count"] = df.get("param_count", np.nan)
    df["param_count"] = (df.params_b * 1e9).round().astype("Int64")
    # Training, capability and actual runtime thinking mode are different axes.
    # A name is a search hint, not verified training metadata.
    regime = df.get("training_regime", pd.Series(index=df.index, dtype="string"))
    df["is_reasoning"] = regime.map({"reasoning": True, "instruct": False, "code/math": False})
    df["reasoning_name_hint"] = df["model"].str.contains(_REASON_RE)
    tc = df.get("tools_capable", pd.Series(index=df.index)).astype("string").str.lower()
    df["is_tools"] = tc.map({"true": True, "false": False})  # missing metadata -> NaN (unknown-preserving)
    return df


def eligibility_table(df: pd.DataFrame, lock: pd.DataFrame | None = None) -> pd.DataFrame:
    """Frozen run roster intersected with model-lock inclusion and integer <=5B.

    No outcome/check/metadata complete-case filter defines membership. Discrepancies
    are columns in the audit, never mutations of the lock or silently repaired tiers.
    """
    if lock is None:
        lock = pd.read_json(REPO / "data/models.lock.jsonl", lines=True)
    if lock.model_id.duplicated().any():
        raise ValueError("duplicate model in model lock")
    if df.groupby("model").params_b.nunique(dropna=False).gt(1).any():
        raise ValueError("parameter count changes within a deployment")
    roster = df[["model", "params_b"]].drop_duplicates("model")
    keep = lock[["model_id", "included", "tier", "params_b"]].rename(
        columns={"model_id": "model", "params_b": "lock_params_b", "tier": "lock_tier"})
    t = roster.merge(keep, on="model", how="left", validate="one_to_one")
    t["run_param_count"] = (t.params_b * 1e9).round().astype("Int64")
    t["integer_le5b"] = t.run_param_count.between(1, 5_000_000_000).fillna(False)
    t["run_tier"] = t.params_b.map(
        lambda p: f"T{max(1, int(np.ceil(p)))}" if pd.notna(p) and 0 < p <= 5 else None)
    locked = t.included.eq(True) & t.lock_tier.isin(["T1", "T2", "T3", "T4", "T5"])
    t["eligible"] = locked & t.integer_le5b
    t["membership_discrepancy"] = locked.ne(t.integer_le5b)
    t["tier_discrepancy"] = t.run_tier.fillna("outside_or_unknown").ne(
        t.lock_tier.fillna("outside_or_unknown"))
    t["lock_minus_run_params_b"] = t.lock_params_b - t.params_b
    t["exclusion"] = np.select(
        [t.eligible, t.params_b.isna(), ~t.integer_le5b, ~t.included.eq(True)],
        ["", "unknown_run_integer", "above_5b", "not_lock_included"],
        default="invalid_or_missing_lock_tier")
    return t.sort_values("model").reset_index(drop=True)


def primary_frame(df: pd.DataFrame) -> pd.DataFrame:
    audit = eligibility_table(df)
    return df[df.model.isin(audit.loc[audit.eligible, "model"])].copy()


def _scenario_class_map() -> dict:
    """Authoritative scenario -> class from the scenario set (NOT the name prefix)."""
    p = REPO / "data" / "scenario_sets" / "core-current.json"
    dd = json.loads(p.read_text())
    items = dd if isinstance(dd, list) else dd.get("scenarios", dd.get("items", []))
    return {(it.get("id") or it.get("scenario")): it.get("class")
            for it in items if (it.get("id") or it.get("scenario"))}


def _assert_join_integrity(res: pd.DataFrame, jud: pd.DataFrame, cons: pd.DataFrame) -> None:
    """Fail loudly *before* the results<->judged merge if the two frames cannot be joined
    1-to-1 on the cell key. This is the CEOps analogue of the MSc reflection's
    clean-running-but-wrong ``left_join()``: a left merge on non-unique or partially
    overlapping keys returns a plausible frame silently, after which every per-model mean
    is computed on a fan-out or a hole. The 152-run invariants are exact -- enforce them so
    a repointed/partial/re-judged source cannot degrade a claim without stopping the run.
    """
    # This reduced key is compatibility for this hash-bound single-condition
    # study only, not a replacement for canonical condition identity at promotion.
    assert set(jud["judge_model"]) == EXPECTED_JUDGES, (
        "join-integrity: observed judge identities differ from the fixed named policy "
        f"{EVALUATION_POLICY}")
    # 1. results cell keys are unique -> the left merge cannot fan out.
    dup_res = int(res.duplicated(_CELL).sum())
    assert dup_res == 0, (
        f"join-integrity: {dup_res} duplicate {tuple(_CELL)} rows in results; a 1-to-1 "
        "merge would fan out and inflate every per-model mean.")

    # 2. every cell is judged by EXACTLY two distinct judges, each exactly once, so the
    #    consensus is a genuine 2-judge mean (not a lone judge, nor a double-count).
    per_cell = jud.groupby(_CELL)["judge_model"].agg(n_judges="nunique", n_rows="size")
    bad_judges = per_cell[per_cell["n_judges"] != 2]
    assert bad_judges.empty, (
        f"join-integrity: {len(bad_judges)} cells not scored by exactly 2 distinct judges "
        f"(e.g. {bad_judges.head(3).index.tolist()}); the '2-judge consensus' is void and the "
        "mean denominator is wrong.")
    dbl = per_cell[per_cell["n_rows"] != 2]
    assert dbl.empty, (
        f"join-integrity: {len(dbl)} cells have != 2 judgement rows (a judge scored a cell more "
        f"than once, or one is missing) (e.g. {dbl.head(3).index.tolist()}).")

    # 3. consensus keys are unique (structural after groupby, but assert the contract).
    dup_cons = int(cons.duplicated(_CELL).sum())
    assert dup_cons == 0, f"join-integrity: {dup_cons} duplicate consensus keys."

    # 4. the key sets match EXACTLY -> no results cell silently becomes NaN judge_score, and
    #    no judged cell is silently dropped by the left join.
    rk = set(res[_CELL].itertuples(index=False, name=None))
    ck = set(cons[_CELL].itertuples(index=False, name=None))
    res_only, cons_only = rk - ck, ck - rk
    assert not res_only, (
        f"join-integrity: {len(res_only)} results cells have no judgement "
        f"(e.g. {sorted(res_only)[:3]}) -> silent NaN judge_score after the left join.")
    assert not cons_only, (
        f"join-integrity: {len(cons_only)} judged cells have no results row "
        f"(e.g. {sorted(cons_only)[:3]}) -> silently dropped by the left join.")


def load_full() -> pd.DataFrame:
    res = _load_results()
    jud = _load_judged()
    # 2-judge consensus per (model, scenario, rep)
    cons = jud.groupby(_CELL)["score"].mean().rename("judge_score").reset_index()
    _assert_join_integrity(res, jud, cons)  # left_join can run clean but be wrong -- guard it
    df = res.merge(cons, on=_CELL, how="left", validate="one_to_one")

    df["scenario_class"] = df["scenario"].map(_scenario_class_map())
    valid_class = df["scenario_class"].map(lambda value: isinstance(value, str) and bool(value.strip()))
    if not valid_class.all():
        missing = sorted(df.loc[~valid_class, "scenario"].unique())
        raise ValueError(f"Missing or invalid authoritative scenario class: {missing}")
    df["is_safety"] = df["scenario_class"].isin(SAFETY_CLASSES)

    df = _join_metadata(df)

    for c in ["det_score", "energy_wh", "mean_watts", "decode_tokens_per_s", "wall_s",
              "output_tokens", "judge_score", "params_b", "size_gb"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["truncated"] = df["finish_reason"].astype(str).str.contains("length", case=False)
    df["dnf_bool"] = df["finish_reason"].astype(str).str.contains("timeout|dnf", case=False, regex=True)
    # single controlled regime across ALL rows -> energy is comparable for every model
    df["energy_comparable"] = df["no_turbo"].astype(str).eq("1") & df["power_source"].astype(str).eq("rapl:package-0")
    # Canonical row order so every downstream analysis is byte-reproducible regardless of
    # source layout (locked bundle's single canonical file vs the .tmp per-model glob).
    return df.sort_values(["model", "scenario", "rep"], kind="stable").reset_index(drop=True)


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
    print(f"known reasoning-trained models: {df[df.is_reasoning.eq(True)].model.nunique()} | "
          f"is_tools models: {df[df.is_tools.eq(True)].model.nunique()}")
    mt = model_table_full(df)
    out = REPO / "deep-dive" / "out"
    out.mkdir(parents=True, exist_ok=True)
    mt.to_csv(out / "full_model_table.csv", index=False)
    print("\nsaved", out / "full_model_table.csv", f"({len(mt)} models)")
