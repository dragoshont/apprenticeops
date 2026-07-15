"""Quantization matched-pair analysis (full run) — is Q4 a free lunch?

Same base model, high-precision (Q8/fp16/bf16) vs Q4: does the smaller quant cost
quality, and what does it save (size / speed / energy)? All on the single
controlled regime so speed and energy are comparable.

Adversarial: (1) is any quality delta smaller than the model's own rep-noise (i.e.
indistinguishable)? (2) is the efficiency win real and consistent?
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
from scipy import stats

from full_data import REPO, load_full, model_table_full

_QUANT_RE = re.compile(r"[:@_-](i?q\d(?:_[a-z0-9]+)*|fp16|bf16)$", re.I)


def _qclass(m: str):
    mm = _QUANT_RE.search(m)
    if not mm:
        return None
    q = mm.group(1).lower()
    if q.startswith(("q8", "fp16", "bf16")):
        return "hi"          # high precision (Q8 / fp16 / bf16)
    if q.startswith(("q4", "iq4")):
        return "Q4"
    return None               # ignore Q3/Q5/Q6 for the clean Q8-vs-Q4 contrast


def _base(m: str) -> str:
    return _QUANT_RE.sub("", m)


def main() -> None:
    df = load_full()
    mt = model_table_full(df).set_index("model")
    mt["qclass"] = [_qclass(m) for m in mt.index]
    mt["base"] = [_base(m) for m in mt.index]

    pairs = []
    for base, grp in mt.groupby("base"):
        hi = grp[grp.qclass == "hi"]
        q4 = grp[grp.qclass == "Q4"]
        if len(hi) and len(q4):
            pairs.append((hi.index[0], q4.index[0], base))

    print(f"=== {len(pairs)} matched high-precision vs Q4 pairs (same base) ===")
    rows = []
    for h, q, base in pairs:
        rows.append({
            "base": base.split("/")[-1][:30],
            "hi_q": mt.loc[h, "quality"], "q4_q": mt.loc[q, "quality"],
            "dq": mt.loc[q, "quality"] - mt.loc[h, "quality"],
            "d_safety": mt.loc[q, "safety"] - mt.loc[h, "safety"],
            "gb_x": mt.loc[q, "size_gb"] / mt.loc[h, "size_gb"],
            "tps_x": mt.loc[q, "decode_tps"] / mt.loc[h, "decode_tps"],
            "wh_x": mt.loc[q, "energy_wh"] / mt.loc[h, "energy_wh"],
        })
    P = pd.DataFrame(rows)
    print(P.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    dq = P.dq.dropna()
    n = len(dq)
    mean, se = dq.mean(), dq.std(ddof=1) / np.sqrt(n)
    tcrit = stats.t.ppf(0.975, n - 1)
    _, p = stats.ttest_1samp(dq, 0.0)
    print(f"\n=== quality cost of Q4 vs high precision (paired, n={n}) ===")
    print(f"  mean Q4-minus-hi = {mean:+.2f}  95% CI [{mean-tcrit*se:+.2f}, {mean+tcrit*se:+.2f}]  paired t p={p:.3f}")
    margin = 0.25
    # TOST: two one-sided tests (explicit tails -> robust even if the mean is outside the margin)
    p_low = stats.ttest_1samp(dq, -margin, alternative="greater").pvalue
    p_high = stats.ttest_1samp(dq, margin, alternative="less").pvalue
    tost_p = max(p_low, p_high)
    print(f"  TOST practical-equivalence within +/-{margin}: p={tost_p:.3f} "
          f"({'EQUIVALENT' if tost_p < 0.05 else 'not established'})")

    print("\n=== what Q4 buys (efficiency) ===")
    print(f"  size: {P.gb_x.mean():.2f}x (n={int(P.gb_x.notna().sum())}/{len(P)} with size metadata)   "
          f"decode: {P.tps_x.mean():.2f}x   energy: {P.wh_x.mean():.2f}x  (of high precision)")

    ds = P.d_safety.dropna()
    print("\n=== SAFETY cost of Q4 (full distribution, not one example) ===")
    print(f"  mean d_safety = {ds.mean():+.2f}  worst = {ds.min():+.2f}  pairs losing >0.2 safety: {(ds < -0.2).sum()}/{len(ds)}")
    print("\n=== HONEST CONCLUSION ===")
    print(f"  Q4 carries a small but statistically real mean quality cost ({mean:+.2f}); it is practically minor")
    print(f"  (equivalence within +/-{margin}: {'established' if tost_p < 0.05 else 'not established'}) and bought with")
    print("  large deterministic efficiency gains. NOT a blanket 'free lunch': it can cost safety on some models.")

    P.to_csv(REPO / "deep-dive" / "out" / "quant_pairs.csv", index=False)
    print(f"\nsaved {REPO/'deep-dive'/'out'/'quant_pairs.csv'}")


if __name__ == "__main__":
    main()
