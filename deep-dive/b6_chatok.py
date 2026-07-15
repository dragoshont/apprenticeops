"""B6 — The broader 152-model spectrum (full-chatok-core20-r5).

An earlier, wider run: 152 models (up to 8B), dual judge (gpt-5.4 + claude-opus-4.6),
chatok format, baseline strategy. Two questions the canonical 95-model snapshot
can't answer:
1. Does the "4B sweet spot" hold when 7-8B models are in the pool?
2. Robustness: does the model ranking survive a judge-version AND prompt-format
   change (chatok/old-judges vs snapshot/new-judges) on the 90 shared models?
"""

from __future__ import annotations

import json
import numpy as np
import pandas as pd
from scipy import stats

from ceops_data import REPO, load_runs

CHATOK = REPO / ".tmp" / "completed-run-intake" / "full-chatok-core20-r5-ollama-20260705-150053" / \
    "judged.full-chatok-core20-r5-ollama-20260705-150053.jsonl"


def main() -> None:
    rows = []
    with open(CHATOK) as f:
        for line in f:
            r = json.loads(line)
            s = r.get("score")
            if isinstance(s, (int, float)):
                rows.append((r["model"], r["scenario"], s))
    c = pd.DataFrame(rows, columns=["model", "scenario", "score"])
    cq = c.groupby("model")["score"].mean().rename("chatok_quality")
    print(f"=== chatok run: {c['model'].nunique()} models, {c['scenario'].nunique()} scenarios ===")

    inv = pd.read_csv(REPO / "data" / "models-inventory.csv")
    # params_b from the bug-free integer param_count; unit-aware param_size fallback (M->/1000)
    _ps = inv["param_size"].astype(str).str.extract(r"([\d.]+)\s*([mMbB])")
    _ps_b = pd.to_numeric(_ps[0], errors="coerce") * _ps[1].str.lower().map({"m": 1e-3, "b": 1.0})
    inv["params_b"] = (pd.to_numeric(inv.get("param_count"), errors="coerce") / 1e9).fillna(_ps_b)
    inv = inv.set_index("model")
    tab = pd.DataFrame(cq).join(inv[["family", "size_gb", "params_b", "bracket", "is_moe"]])
    tab["size_gb"] = pd.to_numeric(tab["size_gb"], errors="coerce")

    print("\n=== top 12 of the 152-model spectrum ===")
    print(tab.sort_values("chatok_quality", ascending=False).head(12)[["chatok_quality", "params_b", "size_gb", "family"]].to_string(float_format=lambda x: f"{x:.2f}"))

    # does the 4B sweet spot hold vs 7-8B?
    big = tab[tab["params_b"] >= 6.5]
    mid = tab[(tab["params_b"] >= 3) & (tab["params_b"] < 6.5)]
    small = tab[tab["params_b"] < 3]
    print("\n=== quality by size tier (does bigger win?) ===")
    for name, grp in [("<3B", small), ("3-6.5B", mid), (">=6.5B (7-8B)", big)]:
        g = grp.dropna(subset=["chatok_quality"])
        print(f"  {name:16} n={len(g):3}  mean quality={g.chatok_quality.mean():.2f}  best={g.chatok_quality.max():.2f} ({g.chatok_quality.idxmax()})")
    # is the very best model big or ~4B?
    bestrow = tab.sort_values("chatok_quality", ascending=False).iloc[0]
    print(f"  overall best: {tab.chatok_quality.idxmax()} ({bestrow.params_b:.1f}B)")
    # correlation of quality with params across the full 152
    t = tab.dropna(subset=["chatok_quality", "params_b"])
    print(f"  Spearman(params, quality) over 152 = {stats.spearmanr(t.params_b, t.chatok_quality).correlation:.3f}")

    # robustness: cross-run rank correlation on shared models
    df = load_runs()
    snap_q = df.groupby("model")["judge_score"].mean().rename("snap_quality")
    merged = pd.concat([cq, snap_q], axis=1).dropna()
    rho = stats.spearmanr(merged.chatok_quality, merged.snap_quality).correlation
    tau = stats.kendalltau(merged.chatok_quality, merged.snap_quality).correlation
    print(f"\n=== cross-run robustness on {len(merged)} shared models ===")
    print(f"chatok(gpt-5.4/claude-4.6, chatok fmt) vs snapshot(gpt-5.5/claude-4.8, current fmt)")
    print(f"Spearman={rho:.3f}  Kendall={tau:.3f}  -> ranking is {'robust to judge-version + format' if rho>0.9 else 'format/judge-sensitive'}")
    # biggest movers between runs
    merged["cz"] = merged.chatok_quality.rank()
    merged["sz"] = merged.snap_quality.rank()
    merged["move"] = merged.sz - merged.cz
    print("models that rose most in the newer run:")
    print(merged.sort_values("move", ascending=False).head(4)[["chatok_quality", "snap_quality"]].to_string(float_format=lambda x: f"{x:.2f}"))
    print("models that fell most:")
    print(merged.sort_values("move").head(4)[["chatok_quality", "snap_quality"]].to_string(float_format=lambda x: f"{x:.2f}"))

    tab.reset_index().to_csv(REPO / "deep-dive" / "out" / "b6_chatok_spectrum.csv", index=False)
    print("\nsaved out/b6_chatok_spectrum.csv")


if __name__ == "__main__":
    main()
