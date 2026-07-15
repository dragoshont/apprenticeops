"""Adversarial review of the full-run re-center — attack the foundation with data.

Runs the load-bearing attacks and prints the standing limitations, as the
reproducible backing for FINDINGS 24:
  1. do the full-run judges actually agree? (the quality axis rests on this)
  2. is the energy axis thermal/order-confounded?
  3. is the org "Qwen leads" just quant-variant inflation?
"""

from __future__ import annotations

import glob
import gzip
import json
import re

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

from full_data import JUDGED, RUN, load_full, model_table_full
from full_org_effects import _org


def attack_judges() -> None:
    rows = []
    for line in open(JUDGED):
        r = json.loads(line)
        try:
            rows.append((r["model"], r["scenario"], r["rep"], r.get("judge_model"), float(r["score"])))
        except (TypeError, ValueError):
            continue
    j = pd.DataFrame(rows, columns=["model", "scenario", "rep", "judge", "score"])
    piv = j.pivot_table(index=["model", "scenario", "rep"], columns="judge", values="score", aggfunc="mean").dropna()
    a, b = list(piv.columns)[:2]
    qk = cohen_kappa_score(piv[a].round().astype(int), piv[b].round().astype(int), weights="quadratic")
    print("ATTACK 1 - do the full-run judges agree? (foundation of the quality axis)")
    print(f"  {a} vs {b}: n={len(piv)}  exact={(piv[a]==piv[b]).mean():.1%}  "
          f"within1={(abs(piv[a]-piv[b])<=1).mean():.1%}  r={piv[a].corr(piv[b]):.3f}  quad-kappa={qk:.3f}")
    print(f"  means: {a}={piv[a].mean():.2f}  {b}={piv[b].mean():.2f}  "
          f"-> disclosed systematic bias {abs(piv[a].mean()-piv[b].mean()):.2f} (consensus mean absorbs it)")


def attack_thermal() -> None:
    rows = []
    for f in glob.glob(str(RUN / "*.results.jsonl.gz")):
        for line in gzip.open(f, "rt"):
            r = json.loads(line)
            rows.append((r["model"], r.get("thermal.start_c"), r.get("power.energy_wh")))
    d = pd.DataFrame(rows, columns=["model", "tstart", "energy"]).dropna()
    wc = d.groupby("model").apply(
        lambda g: g.tstart.corr(g.energy) if g.tstart.nunique() > 2 and g.energy.nunique() > 2 else np.nan
    ).dropna()
    print("\nATTACK 2 - is energy thermal/order-confounded?")
    print(f"  thermal.start_c {d.tstart.min():.0f}-{d.tstart.max():.0f}C (median {d.tstart.median():.0f}C, stable = quiesce works)")
    print(f"  mean within-model corr(thermal_start, energy) = {wc.mean():+.3f};  "
          f"|corr|>0.3 in {(wc.abs()>0.3).sum()}/{len(wc)}  -> energy NOT confounded")


def attack_org() -> None:
    mt = model_table_full(load_full())
    mt["maker"] = [_org(m, o) for m, o in zip(mt.model, mt.get("org", pd.Series(index=mt.index)))]

    def bk(m):
        m = str(m).split("/")[-1]
        return re.sub(r"[-:@]?(q\d_?[a-z0-9]*|iq\d.*|fp16|bf16|gguf|instruct|2507|thinking|it|chat).*$",
                      "", m, flags=re.I)

    band = mt[(mt.params_b >= 3) & (mt.params_b < 5)].assign(base=lambda x: x.model.map(bk))
    dedup = band.groupby(["maker", "base"]).quality.mean().reset_index()
    d = dedup.groupby("maker").agg(n_bases=("base", "size"), quality=("quality", "mean")).sort_values(
        "quality", ascending=False)
    print("\nATTACK 3 - is 'Qwen leads' quant-variant inflation? (de-dup to distinct bases, 3-4B band)")
    print(d[d.n_bases >= 2].to_string(float_format=lambda x: f"{x:.2f}"))


def main() -> None:
    attack_judges()
    attack_thermal()
    attack_org()
    print("\nSTANDING LIMITATIONS (kept honest): MoE n=2 and reasoning ~4 lineages are underpowered;")
    print("  p-values across ~8 axes are NOT multiple-comparison-corrected (MoE 0.043 / tools 0.018 are")
    print("  suggestive, not confirmatory); metadata covers 138/152 with name-heuristic fallbacks;")
    print("  single environment / single collection; bundle still provisional (older judges 4.6/5.4).")


if __name__ == "__main__":
    main()
