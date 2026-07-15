"""Matched-pair reasoning analysis (full run) + adversarial defense — CORRECTED.

Holds the base model fixed and flips only the mode (instruct vs thinking). Fixes
applied after the dual-family judge gate (Claude Opus 4.8 + GPT-5.6 Sol):

 * the non-truncated "recovers when it finishes" test is now MATCHED — instruct is
   compared to thinking on the SAME (scenario, rep) cells where the thinking variant
   did not truncate, removing the earlier survivorship bias;
 * significance is tested at the LINEAGE level (distinct base lineages), not the
   pseudoreplicated ~100 scenario-cells — qwen3:4b at Q8 and Q4 are ONE lineage, so
   the honest n is ~4, and the result is reported as directional, not p~=1e-6;
 * budgets are per-scenario (400-700 tokens), not a single 512 cap.

Honest conclusion: at the small per-scenario budget the thinking variant
underperforms, but on matched non-truncated cells the gap largely closes -> the
penalty is mostly fit-to-budget (truncation), not degraded reasoning. Underpowered
(~4 lineages); the queued budget-sensitivity run is the confirmation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from full_data import REPO, load_full

# (instruct, thinking/reasoning, lineage, label) — same-lineage pairs; two are near-matches (*)
PAIRS = [
    ("qwen3:4b-instruct-2507-q8_0",   "qwen3:4b-thinking-2507-q8_0",   "qwen3-4b",  "Qwen3-4B 2507 Q8"),
    ("qwen3:4b-instruct-2507-q4_K_M", "qwen3:4b-thinking-2507-q4_K_M", "qwen3-4b",  "Qwen3-4B 2507 Q4"),
    ("phi4-mini",                     "phi4-mini-reasoning",           "phi4-mini", "Phi-4-mini"),
    ("qwen2.5:3b-instruct-q4_K_M",    "smallthinker:3b-preview-q4_K_M", "qwen2.5-3b", "Qwen2.5-3B->SmallThinker*"),
    ("exaone3.5:7.8b",                "exaone-deep:7.8b",              "exaone",    "EXAONE-3.5->Deep*"),
]


def main() -> None:
    df = load_full()
    d = df[["model", "scenario", "rep", "judge_score", "truncated"]].copy()

    rows, pair_all, pair_done = [], [], []
    for ins, think, lineage, label in PAIRS:
        di = d[d.model == ins].set_index(["scenario", "rep"])
        dt = d[d.model == think].set_index(["scenario", "rep"])
        j = di.join(dt, lsuffix="_i", rsuffix="_t", how="inner").dropna(subset=["judge_score_i", "judge_score_t"])
        if not len(j):
            continue
        d_all = (j.judge_score_t - j.judge_score_i).mean()                 # matched, all cells
        done = j[~j.truncated_t]                                            # cells where thinking finished
        d_done = (done.judge_score_t - done.judge_score_i).mean() if len(done) else np.nan  # MATCHED non-truncated
        rows.append({"pair": label, "lineage": lineage, "instruct_q": j.judge_score_i.mean(),
                     "think_q": j.judge_score_t.mean(), "d_all": d_all,
                     "think_trunc": j.truncated_t.mean(), "n_done": len(done), "d_done": d_done})
        pair_all.append((lineage, d_all))
        if np.isfinite(d_done):
            pair_done.append((lineage, d_done))

    P = pd.DataFrame(rows)
    print("=== matched instruct vs thinking pairs (same-(scenario,rep)-cell deltas) ===")
    print(P.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    lin_all = pd.DataFrame(pair_all, columns=["lineage", "d"]).groupby("lineage").d.mean()
    lin_done = pd.DataFrame(pair_done, columns=["lineage", "d"]).groupby("lineage").d.mean()
    print(f"\n=== significance at the LINEAGE level (honest n; qwen3 Q8/Q4 collapse to one) ===")
    _, p_all = stats.ttest_1samp(lin_all, 0.0) if len(lin_all) > 1 else (np.nan, np.nan)
    print(f"  full per-scenario budget:  mean delta = {lin_all.mean():+.2f} over {len(lin_all)} lineages, "
          f"t p={p_all:.2f}  ({(lin_all<0).sum()}/{len(lin_all)} lineages worse)")
    if len(lin_done) > 1:
        _, p_done = stats.ttest_1samp(lin_done, 0.0)
        print(f"  MATCHED non-truncated:     mean delta = {lin_done.mean():+.2f} over {len(lin_done)} lineages, "
              f"t p={p_done:.2f}  ({(lin_done<0).sum()}/{len(lin_done)} lineages worse)")

    print("\nMECHANISM: per-scenario budgets are 400-700 tokens (NOT a single 512 cap);")
    print(f"  the thinking variant truncates {P.think_trunc.mean():.0%} of cells (exhausts the budget mid-reasoning).")
    print("HONEST CLAIM (directional, ~4 lineages): thinking underperforms at the small per-scenario")
    print("  budget, but on MATCHED non-truncated cells the gap largely closes -> mostly fit-to-budget,")
    print("  not degraded reasoning. Confirm with the queued budget-sensitivity run (higher max_tokens).")

    P.to_csv(REPO / "deep-dive" / "out" / "reasoning_pairs.csv", index=False)
    print(f"\nsaved {REPO/'deep-dive'/'out'/'reasoning_pairs.csv'}")


if __name__ == "__main__":
    main()
