"""PHASE 4 — correctness repairs found by the Phase-3 tri-family gate.

Every block here fixes a DEFECT IN OUR OWN PRIOR ANALYSIS that was verified against the
data. No experiment is re-run; this is re-derivation from committed evidence.

A. ACTION-SAFETY CHECK SET WAS INCOMPLETE (fixes finding 28).
   `safety_construct_validity.py` treated only {must_exclude, must_not_endorse} as action
   safety. The corpus also contains `must_exclude_action` with 6,840 occurrences -- MORE
   than the other two combined (3,040 + 1,520). Finding 28's numbers therefore omitted the
   largest action-safety check type and must be recomputed.

B. CHECKPOINT IDENTITY WAS UNSOUND (fixes finding 29).
   Finding 29 grouped by (family, parameter_count). That over-merges: parameter_count
   1,543,714,304 is shared by qwen2-math:1.5b, qwen2.5-coder:1.5b, qwen2:1.5b and
   qwen2.5:1.5b -- different models. This recomputes identity three defensible ways and
   reports the RANGE rather than a single false number:
     * tags                     (upper bound on independence)
     * ollama digest            (distinct on-disk artifacts, quantization-specific)
     * name-stem x param_count  (best estimate of distinct weights)

C. <=5B PRIMARY POPULATION. STATISTICS §1 makes <=5B the primary population; the headline
   numbers were reported on all 152. Re-derived on <=5B.

D. SCENARIO-CLUSTERED BOOTSTRAP CIs for the two surviving empirical claims (energy
   inversion, reliability gap) -- neither had an interval.

E. THRESHOLD SENSITIVITY. Both claims depend on an unvalidated "usable" cutoff
   (consensus >= 3). Recomputed at 2.5 / 3 / 3.5 / 4 and per individual judge.

Run: ./deep-dive/.venv/bin/python deep-dive/phase4_repairs.py
"""
from __future__ import annotations

import gzip
import json
import pathlib
import re

import numpy as np
import pandas as pd
from scipy import stats

import full_data

HERE = pathlib.Path(__file__).resolve().parent
ACTION_SAFETY = {"must_exclude", "must_not_endorse", "must_exclude_action"}  # FIXED (was missing the largest)
RECALL = {"any_include", "must_include", "all_include"}
QUANT_RE = re.compile(r"[-:](q\d[_a-z0-9]*|bf16|fp16|f16|iq\d[_a-z0-9]*|q\d)$", re.I)


def _stem(model: str) -> str:
    """Strip quantization/repackaging decoration to approximate the underlying weights."""
    m = model.split("/")[-1]                      # drop hf.co/org/
    m = re.sub(r"-gguf.*$", "", m, flags=re.I)
    m = QUANT_RE.sub("", m)
    m = re.sub(r"[-:](instruct|it|chat)([-:]\d+)?$", "", m, flags=re.I)
    return m.lower()


def _rows():
    with gzip.open(full_data.LOCKED / "canonical" / "results.jsonl.gz", "rt") as fh:
        for line in fh:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _cluster_boot(df, stat_fn, n=4000, seed=20260725):
    """Bootstrap resampling SCENARIOS (the cluster), not rows."""
    rng = np.random.default_rng(seed)
    scen = df["scenario"].unique()
    by = {s: g for s, g in df.groupby("scenario")}
    out = []
    for _ in range(n):
        pick = rng.choice(scen, size=len(scen), replace=True)
        out.append(stat_fn(pd.concat([by[s] for s in pick], ignore_index=True)))
    out = np.array([o for o in out if np.isfinite(o)])
    return np.percentile(out, [2.5, 97.5])


def main() -> None:
    full = full_data.load_full()
    smap = full.groupby("scenario")["is_safety"].first()

    # ---------------- A. corrected action-safety ----------------
    print("=" * 78)
    print("A. FINDING 28 RECOMPUTED with the complete action-safety check set")
    print("=" * 78)
    rec = []
    for r in _rows():
        det = r.get("det_detail") or []
        a = [c for c in det if c.get("type") in ACTION_SAFETY]
        c_ = [c for c in det if c.get("type") in RECALL]
        rec.append({"model": r["model"], "scenario": r["scenario"],
                    "action_safety": (np.mean([bool(x["pass"]) for x in a]) if a else np.nan),
                    "content_recall": (np.mean([bool(x["pass"]) for x in c_]) if c_ else np.nan),
                    "n_act": len(a), "chars": r.get("gen_ai.usage.output_chars") or 0})
    dd = pd.DataFrame(rec)
    dd["is_safety"] = dd["scenario"].map(smap).fillna(False)
    saf = dd[dd["is_safety"]]
    print(f"safety-scenario cells with >=1 action-safety check: "
          f"{saf.n_act.gt(0).sum():,}/{len(saf):,} (was far fewer before the fix)")
    comp = saf.groupby("scenario").agg(action_checks=("n_act", "first")).reset_index()
    print(comp.to_string(index=False))

    mt = (saf.groupby("model").agg(action_safety=("action_safety", "mean"),
                                   content_recall=("content_recall", "mean")).reset_index())
    q = full.groupby("model")["judge_score"].mean().rename("quality")
    tok = full.groupby("model")["output_tokens"].median().rename("tok")
    cmp_ = (1 - full.groupby("model")["dnf_bool"].mean()).rename("complete")
    pb = full.groupby("model")["params_b"].first().rename("params_b")
    mt = mt.merge(q, on="model").merge(tok, on="model").merge(cmp_, on="model").merge(pb, on="model")
    mt = mt.dropna(subset=["action_safety", "content_recall"])
    print(f"\nr(action_safety, content_recall) = "
          f"{stats.pearsonr(mt.action_safety, mt.content_recall)[0]:+.3f}   (was +0.220)")
    print(f"r(action_safety, quality)        = "
          f"{stats.pearsonr(mt.action_safety, mt.quality)[0]:+.3f}   (was +0.411)")
    print(f"r(content_recall, quality)       = "
          f"{stats.pearsonr(mt.content_recall, mt.quality)[0]:+.3f}   (was +0.783)")

    # vacuous-pass, corrected set
    saf2 = saf.dropna(subset=["action_safety"])
    empty = saf2[pd.to_numeric(saf2.chars, errors="coerce").fillna(0) == 0]
    resp = saf2[pd.to_numeric(saf2.chars, errors="coerce").fillna(0) > 0]
    print(f"\nvacuous pass: P(action-safety=1 | EMPTY output) = {empty.action_safety.mean():.3f} "
          f"(n={len(empty)});  P(pass | responsive) = {resp.action_safety.mean():.3f}")

    # ---------------- B. identity ----------------
    print("\n" + "=" * 78)
    print("B. FINDING 29 RECOMPUTED — how many INDEPENDENT models are there really?")
    print("=" * 78)
    ident = {}
    for r in _rows():
        m = r["model"]
        if m not in ident:
            ident[m] = (r.get("ollama.digest"), r.get("ollama.parameter_count"))
    idf = pd.DataFrame([{"model": k, "digest": v[0], "param_count": v[1]} for k, v in ident.items()])
    idf["stem"] = idf.model.map(_stem)
    idf["weights"] = idf.groupby(["stem", "param_count"], dropna=False).ngroup()
    print(f"tags                                   : {len(idf)}")
    print(f"distinct ollama digests (artifacts)    : {idf.digest.nunique()}")
    print(f"distinct (name-stem x param_count)     : {idf.weights.nunique()}   <- best estimate of distinct weights")
    print(f"distinct param_count alone             : {idf.param_count.nunique()}   (OVER-merges: different models share counts)")
    print(f"\n=> honest statement: 152 tags correspond to ~{idf.weights.nunique()} distinct model "
          f"weight-sets (~{len(idf)/idf.weights.nunique():.1f} tags each).")
    print("   The earlier '90 checkpoints / 73 lineages' used (family x param_count), which merged")
    print("   genuinely different models (e.g. qwen2-math / qwen2.5-coder / qwen2 all at 1,543,714,304).")
    grp = idf.groupby("weights").filter(lambda g: len(g) >= 4).groupby("weights")
    print("\nlargest true weight-groups:")
    for _, g in list(grp)[:3]:
        print(f"  n={len(g)}: {', '.join(x[:38] for x in g.model.head(5))}")

    # headline correlation at the weights level
    w = idf[["model", "weights"]].merge(mt[["model", "quality", "params_b"]], on="model").dropna()
    wl = w.groupby("weights").agg(quality=("quality", "mean"), params_b=("params_b", "mean"))
    print(f"\nSpearman(params, quality): tags n={len(w)} rho="
          f"{stats.spearmanr(w.params_b, w.quality).correlation:+.3f} | "
          f"weights n={len(wl)} rho={stats.spearmanr(wl.params_b, wl.quality).correlation:+.3f}")

    # ---------------- C/D/E. <=5B, CIs, thresholds ----------------
    print("\n" + "=" * 78)
    print("C-E. <=5B PRIMARY POPULATION, CLUSTERED CIs, THRESHOLD SENSITIVITY")
    print("=" * 78)
    d = full.copy()
    le5_models = set(mt[mt.params_b <= 5].model)
    d5 = d[d.model.isin(le5_models)]
    print(f"<=5B population: {len(le5_models)} tags, {len(d5):,} cells "
          f"(all-152: {d.model.nunique()} tags, {len(d):,} cells)")

    print("\n--- reliability gap (pass^5) by threshold, <=5B primary ---")
    print(f"{'thresh':>7} {'mean-good%':>11} {'all-5-good%':>12} {'gap pp':>8} {'95% CI on gap':>20}")
    for th in (2.5, 3.0, 3.5, 4.0):
        def stat(df, th=th):
            c = df.groupby(["model", "scenario"])["judge_score"].agg(["mean", "min"])
            return 100 * ((c["mean"] >= th).mean() - (c["min"] >= th).mean())
        c = d5.groupby(["model", "scenario"])["judge_score"].agg(["mean", "min"])
        mg, ag = 100 * (c["mean"] >= th).mean(), 100 * (c["min"] >= th).mean()
        lo, hi = _cluster_boot(d5, stat)
        print(f"{th:7.1f} {mg:11.1f} {ag:12.1f} {mg-ag:8.1f} {f'[{lo:.1f}, {hi:.1f}]':>20}")

    print("\n--- energy inversion by threshold, <=5B primary ---")
    print(f"{'thresh':>7} {'rho(Wh/attempt, Wh/correct)':>30} {'95% CI':>20}")
    for th in (2.5, 3.0, 3.5, 4.0):
        def stat_e(df, th=th):
            g = df.assign(good=df.judge_score >= th).groupby("model").agg(
                tot=("energy_wh", "sum"), n=("judge_score", "size"), good=("good", "sum"))
            g = g[g.good > 0]
            if len(g) < 5:
                return np.nan
            return stats.spearmanr(g.tot / g.n, g.tot / g.good).correlation
        pt = stat_e(d5)
        lo, hi = _cluster_boot(d5, stat_e)
        print(f"{th:7.1f} {pt:30.3f} {f'[{lo:.3f}, {hi:.3f}]':>20}")

    print("\n--- per-judge sensitivity (is the gap an artifact of one judge?) ---")
    jud = full_data._load_judged()
    for jm, g in jud.groupby("judge_model"):
        cc = (g[g.model.isin(le5_models)]
              .groupby(["model", "scenario"])["score"].agg(["mean", "min"]))
        print(f"  {jm:20} mean-good {100*(cc['mean']>=3).mean():5.1f}%   "
              f"all-5-good {100*(cc['min']>=3).mean():5.1f}%   "
              f"gap {100*((cc['mean']>=3).mean()-(cc['min']>=3).mean()):4.1f} pp")

    out = HERE / "out"
    mt.to_csv(out / "phase4_action_safety.csv", index=False)
    idf.to_csv(out / "phase4_identity.csv", index=False)
    print(f"\nsaved phase4_action_safety.csv, phase4_identity.csv")


if __name__ == "__main__":
    main()
