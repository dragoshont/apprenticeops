"""Matched-pair reasoning analysis on the full run + its adversarial defense.

Holds the base model fixed and flips ONLY the mode (instruct vs thinking/
reasoning) across same-lineage pairs, so the contrast has no cross-model confound
(unlike the frozen "reasoning-trained is worse" claim, which compared deepseek-r1
to unrelated models).

ADVERSARIAL RESULT (do not drop this caveat): the raw ~-0.4 "thinking hurts"
penalty is LARGELY a token-budget artifact. Both modes share a 512-token cap;
thinking variants blow past it 74-100% of the time. On the answers where thinking
actually FINISHES, 3 of 5 match or beat their instruct sibling. So the honest
claim is about FIT, not reasoning quality: thinking mode is a poor fit for a tight
token/latency budget on bounded ops tasks -- it exhausts the budget before
answering, not because its reasoning is worse. Confirm with the budget-sensitivity
re-run (data/models.reasoning-budget-v1.txt) at higher max_tokens.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from full_data import REPO, load_full

# same-lineage pairs (instruct/base , thinking/reasoning variant , label + lineage note)
PAIRS = [
    ("qwen3:4b-instruct-2507-q8_0",   "qwen3:4b-thinking-2507-q8_0",   "Qwen3-4B 2507 (Q8)"),
    ("qwen3:4b-instruct-2507-q4_K_M", "qwen3:4b-thinking-2507-q4_K_M", "Qwen3-4B 2507 (Q4)"),
    ("phi4-mini",                     "phi4-mini-reasoning",           "Phi-4-mini (Microsoft)"),
    ("qwen2.5:3b-instruct-q4_K_M",    "smallthinker:3b-preview-q4_K_M", "Qwen2.5-3B-Instruct base (Q4)"),
    ("exaone3.5:7.8b",                "exaone-deep:7.8b",              "EXAONE 7.8B (LG, near-match)"),
]


def main() -> None:
    df = load_full()
    g = df.groupby("model")
    mstat = pd.DataFrame({
        "quality": g["judge_score"].mean(),
        "trunc": g["truncated"].mean(),
        "energy": g["energy_wh"].mean(),
        "out_tok": g["output_tokens"].mean(),
    })
    mstat["safety"] = df[df["is_safety"]].groupby("model")["judge_score"].mean()

    cell = df.groupby(["model", "scenario"])["judge_score"].mean().rename("q").reset_index()
    cell["sclass"] = cell["scenario"].str.split("-").str[0]

    print("=== matched instruct vs thinking/reasoning pairs (same lineage) ===")
    summ, deltas = [], []
    for ins, think, label in PAIRS:
        if ins not in mstat.index or think not in mstat.index:
            print(f"  [skip] missing in run: {ins} / {think}")
            continue
        j = cell[cell.model == ins].merge(cell[cell.model == think], on="scenario", suffixes=("_i", "_t"))
        deltas.append(pd.DataFrame({"scenario": j.scenario, "sclass": j.sclass_i,
                                    "dq": j.q_t - j.q_i, "pair": label}))
        i, t = mstat.loc[ins], mstat.loc[think]
        summ.append({"pair": label, "instruct_q": i.quality, "think_q": t.quality,
                     "d_quality": t.quality - i.quality, "d_safety": t.safety - i.safety,
                     "ins_trunc": i.trunc, "think_trunc": t.trunc,
                     "tok_x": t.out_tok / i.out_tok, "energy_x": t.energy / i.energy})
    S = pd.DataFrame(summ)
    print(S.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    alld = pd.concat(deltas, ignore_index=True)
    _, p_t = stats.ttest_1samp(alld.dq, 0.0)
    _, p_w = stats.wilcoxon(alld.dq)
    print(f"\n=== pooled paired test (thinking - instruct), scenario grain ===")
    print(f"  mean delta = {alld.dq.mean():+.2f} quality  (n={len(alld)} matched cells across {S.shape[0]} pairs)")
    print(f"  95% CI = [{alld.dq.mean()-1.96*alld.dq.sem():+.2f}, {alld.dq.mean()+1.96*alld.dq.sem():+.2f}]"
          f"  | paired t p={p_t:.1e} | Wilcoxon p={p_w:.1e}")
    print(f"  pairs worse: {(S.d_quality < 0).sum()}/{len(S)}  |  matched cells worse: {(alld.dq < 0).mean():.0%}")
    print("  (caveat: cells sharing a scenario across pairs are not fully independent)")

    print("\n=== where thinking hurts most (by task class) ===")
    byc = alld.groupby("sclass").dq.agg(["mean", "count"]).sort_values("mean")
    print(byc.to_string(float_format=lambda x: f"{x:.2f}"))

    print("\n=== mechanism: thinking over-generates, then runs out of budget ===")
    print(f"  truncation:     instruct {S.ins_trunc.mean():.0%}  ->  thinking {S.think_trunc.mean():.0%}")
    print(f"  output tokens:  thinking = {S.tok_x.mean():.1f}x instruct")
    print(f"  energy:         thinking = {S.energy_x.mean():.1f}x instruct")

    # ---- adversarial defense: is the penalty just the shared 512-token cap? ----
    print("\n=== ADVERSARIAL: is the penalty just the 512-token cap? ===")
    print("  both modes share max_tokens=512; compare thinking on answers it did NOT truncate:")
    print(f"  {'pair':30} {'ins_q':>6} {'thk_all':>7} {'thk_DONE':>8} {'d_DONE':>7}")
    d_done = []
    for ins, think, label in PAIRS:
        if ins not in mstat.index or think not in mstat.index:
            continue
        iq = mstat.loc[ins, "quality"]
        t = df[df.model == think]
        done = t[~t["truncated"]]
        tq_done = done["judge_score"].mean() if len(done) else np.nan
        d_done.append(tq_done - iq)
        print(f"  {label:30} {iq:6.2f} {mstat.loc[think,'quality']:7.2f} {tq_done:8.2f} {tq_done-iq:+7.2f}")
    finite = [x for x in d_done if np.isfinite(x)]
    print(f"\n  VERDICT: on non-truncated answers mean delta = {np.mean(finite):+.2f} "
          f"({sum(x >= 0 for x in finite)}/{len(finite)} pairs >= instruct).")
    print("  => the raw penalty is mostly BUDGET EXHAUSTION, not degraded reasoning. The")
    print("     operational claim stands (avoid thinking under a tight budget); the mechanism")
    print("     is fit-to-budget. Confirm by re-running at higher max_tokens (budget-sensitivity).")

    out = REPO / "deep-dive" / "out"
    out.mkdir(parents=True, exist_ok=True)
    S.to_csv(out / "reasoning_pairs.csv", index=False)
    print(f"\nsaved {out/'reasoning_pairs.csv'}")


if __name__ == "__main__":
    main()
