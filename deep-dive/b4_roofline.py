"""B4 — Roofline / memory-bandwidth analysis of CPU decode.

On a CPU with tiny batch, autoregressive decode streams the weights once per token,
so it is memory-bandwidth-bound: decode_tokens/s ~ bandwidth / bytes_per_token.
For a dense model bytes_per_token ~ model size; for MoE only the active experts
stream, so MoE beats the dense roofline. This quantifies both.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from ceops_data import REPO, load_runs, model_table


def main() -> None:
    df = load_runs()
    mt = model_table(df).dropna(subset=["decode_tps", "size_gb"]).copy()
    mt = mt[mt["decode_tps"] > 0]

    # roofline: log(tps) ~ log(size); memory-bound predicts slope ~ -1
    lr = stats.linregress(np.log(mt["size_gb"]), np.log(mt["decode_tps"]))
    print("=== roofline: decode_tps vs size (log-log) ===")
    print(f"slope={lr.slope:.2f} (memory-bound predicts -1.0), R^2={lr.rvalue**2:.2f}")
    print(f"  -> {'strongly memory-bandwidth-bound' if -1.3 < lr.slope < -0.7 else 'partially memory-bound'}; "
          "bigger models decode proportionally slower because more bytes stream per token.")

    # effective streamed bandwidth if it streamed full weights each token
    mt["eff_bw_gb_s"] = mt["size_gb"] * mt["decode_tps"]
    peak = (mt["membw_peak_mb_s"] / 1000).replace(0, np.nan)
    mt["dense_mbu"] = mt["eff_bw_gb_s"] / peak  # >1 is impossible for a true dense stream -> MoE/quant sparsity
    print(f"\nmedian effective bandwidth (size x tps) = {mt['eff_bw_gb_s'].median():.1f} GB/s")
    print(f"measured peak bandwidth (median) = {peak.median():.1f} GB/s")

    # residual from the roofline: who beats it (fewer bytes/token than size => MoE / efficient kernels)
    mt["log_tps_resid"] = np.log(mt["decode_tps"]) - (lr.intercept + lr.slope * np.log(mt["size_gb"]))
    print("\n=== models that BEAT the size-roofline (decode faster than size predicts) ===")
    beat = mt.sort_values("log_tps_resid", ascending=False)[["model", "size_gb", "decode_tps", "log_tps_resid", "is_moe", "quant"]].head(8)
    print(beat.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print("=== models BELOW the roofline (slower than size predicts -> overhead/compute-bound) ===")
    below = mt.sort_values("log_tps_resid")[["model", "size_gb", "decode_tps", "log_tps_resid", "is_moe", "quant"]].head(6)
    print(below.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    # MoE vs dense on the roofline residual
    moe = mt["is_moe"].astype(str).str.lower().isin(["true", "1"])
    print(f"\nMoE/hybrid roofline residual mean = {mt.loc[moe,'log_tps_resid'].mean():+.2f} "
          f"vs dense {mt.loc[~moe,'log_tps_resid'].mean():+.2f}  "
          f"(positive = decodes faster than a dense model of the same footprint)")

    # quantization vs speed: does lower-bit quant decode faster (fewer bytes/token)?
    mt["qbits"] = mt["quant"].astype(str).str.upper().map(lambda q: 4 if q.startswith("Q4") else 8 if q.startswith("Q8") else 16 if q in ("F16", "FP16", "BF16") else np.nan)
    qs = mt.dropna(subset=["qbits"]).groupby("qbits").agg(n=("model", "size"), tps=("decode_tps", "mean"), size=("size_gb", "mean"))
    print("\n=== decode speed by quant bit-width ===")
    print(qs.to_string(float_format=lambda x: f"{x:.2f}"))

    mt[["model", "size_gb", "decode_tps", "eff_bw_gb_s", "log_tps_resid", "is_moe"]].to_csv(
        REPO / "deep-dive" / "out" / "b4_roofline.csv", index=False)
    print("\nsaved out/b4_roofline.csv")


if __name__ == "__main__":
    main()
