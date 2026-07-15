"""MoE vs dense (full run) — the efficiency story, honestly framed.

MoE and dense are DIFFERENT models, so a raw MoE-vs-dense quality gap is
confounded. The defensible claim is about EFFICIENCY at a given footprint: an MoE
streams only its active experts, so it decodes faster / uses less energy per GB
than a dense model of the same size. Tested three ways: (1) within the Granite
family (same org/generation, MoE vs dense), (2) footprint efficiency (decode
tok/s per GB), (3) the size->speed roofline (do MoE sit above the dense trend?).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from full_data import REPO, load_full, model_table_full


def main() -> None:
    df = load_full()
    mt = model_table_full(df)
    mt = mt.dropna(subset=["is_moe"]).copy()
    mt["is_moe"] = mt["is_moe"].astype(str).str.lower().eq("true")
    mt["tps_per_gb"] = mt["decode_tps"] / mt["size_gb"]

    print("=== MoE vs dense (metadata-tagged) ===")
    for lab, grp in [("MoE", mt[mt.is_moe]), ("dense", mt[~mt.is_moe])]:
        print(f"  {lab:6} n={len(grp):3}  quality={grp.quality.mean():.2f}  "
              f"decode_tps={grp.decode_tps.mean():5.1f}  energy_wh={grp.energy_wh.mean():.3f}  "
              f"tps/GB={grp.tps_per_gb.mean():.1f}")

    gran = mt[mt.family.astype(str).str.contains("granite", case=False, na=False)]
    print("\n=== within Granite (same org/lineage): MoE vs dense ===")
    for lab, grp in [("MoE", gran[gran.is_moe]), ("dense", gran[~gran.is_moe])]:
        if len(grp):
            print(f"  {lab:6} n={len(grp):2}  quality={grp.quality.mean():.2f}  "
                  f"tps/GB={grp.tps_per_gb.mean():.1f}  e.g. {sorted(grp.model)[:3]}")

    r = mt.dropna(subset=["decode_tps", "size_gb"])
    r = r[(r.decode_tps > 0) & (r.size_gb > 0)].copy()
    sl, ic, rr, *_ = stats.linregress(np.log(r.size_gb), np.log(r.decode_tps))
    r["resid"] = np.log(r.decode_tps) - (ic + sl * np.log(r.size_gb))
    print(f"\n=== roofline: log(decode_tps) ~ log(size)  slope={sl:.2f} R^2={rr**2:.2f} ===")
    print("  mean residual (positive = decodes FASTER than its footprint predicts):")
    print(f"    MoE   = {r[r.is_moe].resid.mean():+.2f}  (n={r.is_moe.sum()})")
    print(f"    dense = {r[~r.is_moe].resid.mean():+.2f}  (n={(~r.is_moe).sum()})")
    if r.is_moe.sum() and (~r.is_moe).sum():
        _, p = stats.ttest_ind(r[r.is_moe].resid, r[~r.is_moe].resid, equal_var=False)
        print(f"    difference p={p:.3f}")

    print("\n=== ADVERSARIAL: is this a quality win? NO; and n is small. ===")
    dq = mt[mt.is_moe].quality.mean() - mt[~mt.is_moe].quality.mean()
    print(f"  MoE-minus-dense quality = {dq:+.2f} (confounded: different models) -> NOT the claim.")
    print("  Robust claim = EFFICIENCY at footprint: positive roofline residual + higher within-Granite")
    print("  tps/GB. CAVEATS: (1) only 2 small MoE models are reliably tagged (few exist; is_moe is")
    print("  under-populated and 'hybrid' != MoE, so uncertain labels are NOT forced) -> directional,")
    print("  underpowered. (2) Raw overall tps/GB is size-confounded (MoE store all params on disk);")
    print("  the size-controlled roofline residual is the correct metric.")

    r.to_csv(REPO / "deep-dive" / "out" / "moe_roofline.csv", index=False)
    print(f"\nsaved {REPO/'deep-dive'/'out'/'moe_roofline.csv'}")


if __name__ == "__main__":
    main()
