"""A3 — Scaling, quantization, and architecture effects.

* Quantization: within-model Q4 vs Q8 vs F16 paired deltas (quality/energy/speed).
* Group contrasts with bootstrap 95% CI + Mann-Whitney: MoE vs dense, thinking vs
  not, tools vs not, training regime, and per-family quality.
"""

from __future__ import annotations

import re
import numpy as np
import pandas as pd
from scipy import stats

from ceops_data import REPO, load_runs, model_table

RNG = np.random.default_rng(7)
QUANT_RE = re.compile(r"[:\-_](q4_k_m|q4_0|q4_k_s|q5_k_m|q8_0|q6_k|fp16|f16|bf16|it-qat|qat)\b", re.I)


def base_key(model: str) -> str:
    return QUANT_RE.sub("", model.lower()).replace("-instruct", "").strip("-:_ ")


def boot_diff(a: np.ndarray, b: np.ndarray, n=10000):
    a, b = a[~np.isnan(a)], b[~np.isnan(b)]
    if len(a) < 2 or len(b) < 2:
        return np.nan, np.nan, np.nan, np.nan
    da = RNG.choice(a, (n, len(a))).mean(1)
    db = RNG.choice(b, (n, len(b))).mean(1)
    d = da - db
    p = stats.mannwhitneyu(a, b, alternative="two-sided").pvalue
    return a.mean() - b.mean(), np.percentile(d, 2.5), np.percentile(d, 97.5), p


def contrast(mt, col, mask_a, mask_b, name_a, name_b, metric="quality"):
    a = mt.loc[mask_a, metric].values
    b = mt.loc[mask_b, metric].values
    d, lo, hi, p = boot_diff(a, b)
    star = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
    print(f"  {metric:16} {name_a}({mask_a.sum()})={np.nanmean(a):.2f}  {name_b}({mask_b.sum()})={np.nanmean(b):.2f}  "
          f"Δ={d:+.2f} [{lo:+.2f},{hi:+.2f}] p={p:.3f} {star}")


def main() -> None:
    df = load_runs()
    mt = model_table(df)
    mt["base"] = mt["model"].map(base_key)

    # ---- quantization: within-base paired deltas ----
    print("=== quantization effect (within-model families with >1 quant) ===")
    deltas = []
    for base, grp in mt.groupby("base"):
        qs = grp.dropna(subset=["quality"])
        if qs["quant"].nunique() < 2:
            continue
        # compare Q8_0 vs Q4_K_M within the same base when both exist
        q8 = qs[qs["quant"].astype(str).str.upper().eq("Q8_0")]
        q4 = qs[qs["quant"].astype(str).str.upper().str.startswith("Q4")]
        if len(q8) and len(q4):
            dq = q8["quality"].mean() - q4["quality"].mean()
            de = (q8["energy_wh_controlled"].mean() - q4["energy_wh_controlled"].mean())
            ds = (q8["decode_tps"].mean() - q4["decode_tps"].mean())
            deltas.append((base, dq, de, ds))
    D = pd.DataFrame(deltas, columns=["base", "dq_q8_minus_q4", "denergy", "dspeed"])
    print(f"paired bases with Q8 and Q4: {len(D)}")
    print(f"  mean quality Δ (Q8 - Q4): {D.dq_q8_minus_q4.mean():+.3f}  (median {D.dq_q8_minus_q4.median():+.3f})")
    print(f"  Wilcoxon p (quality Q8 vs Q4): {stats.wilcoxon(D.dq_q8_minus_q4).pvalue:.3f}" if len(D) > 5 else "  (too few for Wilcoxon)")
    print(f"  mean energy Δ (Q8 - Q4): {D.denergy.mean():+.3f} Wh   mean speed Δ: {D.dspeed.mean():+.1f} tok/s")
    print(D.sort_values("dq_q8_minus_q4", ascending=False).head(6).to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # ---- architecture / capability contrasts ----
    moe = mt["is_moe"].astype(str).str.lower().isin(["true", "1"])
    think = mt["thinking_capable"].astype(str).str.lower().isin(["true", "1"])
    tools = mt["tools_capable"].astype(str).str.lower().isin(["true", "1"])

    print("\n=== MoE/hybrid vs dense ===")
    for m in ["quality", "energy_wh_controlled", "decode_tps", "safety"]:
        contrast(mt, m, moe, ~moe, "MoE", "dense", m)

    print("\n=== thinking-capable vs not ===")
    for m in ["quality", "safety", "energy_wh_controlled", "decode_tps"]:
        contrast(mt, m, think, ~think, "think", "no-think", m)

    print("\n=== tools-capable vs not ===")
    for m in ["quality", "safety"]:
        contrast(mt, m, tools, ~tools, "tools", "no-tools", m)

    print("\n=== training regime (quality, safety) ===")
    for reg in ["instruct", "code/math", "reasoning"]:
        sub = mt[mt["training_regime"].astype(str).eq(reg)]
        if len(sub):
            print(f"  {reg:10} n={len(sub):2}  quality={sub.quality.mean():.2f}  safety={sub.safety.mean():.2f}  energy={sub.energy_wh_controlled.mean():.3f}")

    # ---- per-family quality ----
    print("\n=== per-family (n>=3) mean quality / safety / size ===")
    fam = mt.groupby("family").agg(n=("model", "size"), quality=("quality", "mean"),
                                   safety=("safety", "mean"), size_gb=("size_gb", "mean"),
                                   params_b=("params_b", "mean")).query("n>=3").sort_values("quality", ascending=False)
    print(fam.to_string(float_format=lambda x: f"{x:.2f}"))

    # ---- per-org ----
    print("\n=== per-org (n>=3) mean quality ===")
    org = mt.groupby("org").agg(n=("model", "size"), quality=("quality", "mean"),
                                safety=("safety", "mean")).query("n>=3").sort_values("quality", ascending=False)
    print(org.to_string(float_format=lambda x: f"{x:.2f}"))


if __name__ == "__main__":
    main()
