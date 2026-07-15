"""C1 — Capstone: the sweet-spot curve + a model-selection guide.

Turns the battery into two actionable artifacts:
* quality vs parameters over the full 152-model spectrum, showing the ~4B plateau;
* best-in-class picks per operating constraint (quality / efficiency / speed /
  size / safety), grounded in the Pareto frontiers.
"""

from __future__ import annotations

import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ceops_data import REPO, load_runs, model_table

FIG = REPO / "deep-dive" / "figures"
CHATOK = REPO / ".tmp" / "completed-run-intake" / "full-chatok-core20-r5-ollama-20260705-150053" / \
    "judged.full-chatok-core20-r5-ollama-20260705-150053.jsonl"


def main() -> None:
    # spectrum (152) quality vs params
    rows = []
    with open(CHATOK) as f:
        for line in f:
            r = json.loads(line)
            if isinstance(r.get("score"), (int, float)):
                rows.append((r["model"], r["score"]))
    c = pd.DataFrame(rows, columns=["model", "score"]).groupby("model")["score"].mean()
    inv = pd.read_csv(REPO / "data" / "models-inventory.csv").set_index("model")
    inv["pb"] = pd.to_numeric(inv["param_size"].astype(str).str.extract(r"([\d.]+)")[0], errors="coerce")
    reg = inv["training_regime"].astype(str)
    tab = pd.DataFrame({"q": c}).join(inv[["pb"]]).join(reg.rename("regime")).dropna(subset=["q", "pb"])
    tab = tab[tab.pb <= 9]

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    is_reason = tab.regime.str.contains("reason", case=False, na=False)
    ax.scatter(tab.pb[~is_reason], tab.q[~is_reason], s=30, c="#2b6cb0", label="instruct/other", alpha=.8)
    ax.scatter(tab.pb[is_reason], tab.q[is_reason], s=34, c="#c53030", marker="^", label="reasoning", alpha=.9)
    # running max (frontier) by param
    ts = tab.sort_values("pb")
    fr_x, fr_y, best = [], [], -1
    for x, y in zip(ts.pb, ts.q):
        if y > best:
            best = y; fr_x.append(x); fr_y.append(y)
    ax.plot(fr_x, fr_y, "k--", lw=1, alpha=.6, label="best-so-far frontier")
    champ = tab.q.idxmax()
    ax.annotate(f"{champ}\n(best, {tab.loc[champ,'pb']:.0f}B)", (tab.loc[champ, "pb"], tab.loc[champ, "q"]),
                fontsize=8, xytext=(tab.loc[champ, "pb"]-2.7, tab.loc[champ, "q"]+0.15),
                arrowprops=dict(arrowstyle="->", lw=.8))
    ax.axvspan(3.5, 4.5, color="gold", alpha=.15)
    ax.text(4.0, 1.1, "~4B\nsweet spot", ha="center", fontsize=8, color="#946c00")
    ax.set(xlabel="parameters (B)", ylabel="quality (judge 1-5)",
           title="Bigger isn't better: quality plateaus at ~4B (152-model spectrum)")
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout(); FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "c1_sweet_spot.png", dpi=140)
    print(f"saved {FIG/'c1_sweet_spot.png'}")

    # ---- model-selection guide ----
    df = load_runs()
    mt = model_table(df)
    mt = mt[~mt.model.eq("phi:2.7b")]  # exclude the broken outlier
    def pick(sub, by, asc=False):
        return sub.sort_values(by, ascending=asc).iloc[0]

    print("\n=== MODEL-SELECTION GUIDE (per operating constraint) ===")
    guide = []
    guide.append(("Best quality (no constraint)", pick(mt, "quality")))
    guide.append(("Best quality/energy (efficiency pick)", pick(mt.dropna(subset=["energy_wh_controlled"]).assign(
        e=lambda d: d.quality - 3 * d.energy_wh_controlled), "e")))
    guide.append(("Fastest with quality>=2.8 (low latency)", pick(mt[mt.quality >= 2.8], "decode_tps")))
    guide.append(("Best under 1.5 GB (tight memory)", pick(mt[mt.size_gb <= 1.5], "quality")))
    guide.append(("Tiny <=0.7 GB (edge)", pick(mt[mt.size_gb <= 0.7], "quality")))
    guide.append(("Safest (destructive/secure tasks)", pick(mt.dropna(subset=["safety"]), "safety")))
    for label, row in guide:
        print(f"  {label:40} -> {row['model']:34} q={row['quality']:.2f} safety={row.get('safety',float('nan')):.2f} "
              f"{row['size_gb']:.1f}GB {row['decode_tps']:.0f}tps")

    print("\nRULES OF THUMB (from the battery):")
    print("  * ~4B instruct is the sweet spot; 7-8B does not earn its cost on ops tasks (B6).")
    print("  * prefer tool-trained models (+0.29 quality, +0.39 safety, sig) (A3/B3).")
    print("  * avoid reasoning-trained models here (-0.88 quality, 2.4x energy, timeouts) (A3/B3/A6).")
    print("  * Q4_K_M over Q8 (nearly free: -0.11 quality, less energy) (A3).")
    print("  * MoE/hybrid (granite4) for energy/speed at a given footprint (~2.4x roofline) (B4).")


if __name__ == "__main__":
    main()
