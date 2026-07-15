"""Truncation scan — separate BUDGET VICTIMS from GENUINELY WEAK heavy-truncators.

A model that truncates a lot at the 512-token cap may be (a) a BUDGET VICTIM
(decent when it finishes -> its low overall score is an artifact of the cap) or
(b) GENUINELY WEAK (bad even when it finishes). The non-truncated subset
distinguishes them: a large positive `lift` (q_done - q_all) or a decent `q_done`
despite heavy truncation = budget victim; a 100%-truncated model cannot be judged
at all and must be re-run.

Anything not already queued (reasoning-budget-v1 / timeout-sensitivity-v1) and
classified BUDGET-VICTIM is queued for the higher-budget confirmation run; a few
weak heavy-truncators go along as CONTROLS (predicted to NOT improve with budget,
which nails the mechanism as over-generation, not generic 'more tokens = better').
"""

from __future__ import annotations

import pandas as pd

from full_data import load_full, REPO

TRUNC_HEAVY = 0.30
LIFT_BIG = 0.50
Q_OK = 2.0


def _roster(name: str) -> set[str]:
    return {l.strip() for l in (REPO / "data" / name).read_text().splitlines()
            if l.strip() and not l.startswith("#")}


def scan() -> pd.DataFrame:
    df = load_full()
    g = df.groupby("model")
    done = df[~df["truncated"]].groupby("model")
    T = pd.DataFrame({
        "trunc": g["truncated"].mean(),
        "q_all": g["judge_score"].mean(),
        "q_done": done["judge_score"].mean(),
        "n_done": done.size(),
    })
    T["lift"] = T["q_done"] - T["q_all"]
    already = _roster("models.reasoning-budget-v1.txt") | _roster("models.timeout-sensitivity-v1.txt")
    T["queued"] = T.index.isin(already)

    def verdict(r):
        if r.queued:
            return "already-queued"
        if pd.isna(r.q_done) or r.n_done < 20:
            return "BUDGET-VICTIM (100% truncated, cannot infer -> must re-run)"
        if r.q_done >= Q_OK or r.lift >= LIFT_BIG:
            return "BUDGET-VICTIM (decent when it finishes)"
        return "weak (bad even when finished)"

    T["verdict"] = T.apply(verdict, axis=1)
    return T


def main() -> None:
    T = scan()
    heavy = T[(T.trunc >= TRUNC_HEAVY) | (T.lift >= LIFT_BIG)].sort_values("trunc", ascending=False)
    print(f"=== heavy truncators (>= {TRUNC_HEAVY:.0%}) or high-lift models on the full run ===")
    print(heavy[["trunc", "q_all", "q_done", "n_done", "lift", "queued", "verdict"]].to_string(
        float_format=lambda x: f"{x:.2f}"))

    newq = heavy[(~heavy.queued) & heavy.verdict.str.startswith("BUDGET-VICTIM")]
    ctrl = heavy[(~heavy.queued) & heavy.verdict.str.startswith("weak")]
    print("\nNEW budget victims to queue :", list(newq.index))
    print("weak controls (predict no gain):", list(ctrl.index))


if __name__ == "__main__":
    main()
