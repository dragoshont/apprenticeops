#!/usr/bin/env python3
"""Generate the paper figures as committed PNGs from the COMMITTED, verified
exports in data/site/ (plus data/site/judge_pairs.csv). Run from the repo root:

    .venv/bin/python scripts/make-paper-figures.py

Writes to docs/analysis/figures/. The figures trace to the same snapshot the
in-text numbers do, so they render on GitHub Pages with no kernel and never drift
from the verified notebook outputs.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "data/site"
OUT = ROOT / "docs/analysis/figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({"figure.dpi": 130, "font.size": 10, "axes.grid": True,
                     "grid.alpha": 0.25, "axes.spines.top": False,
                     "axes.spines.right": False, "savefig.bbox": "tight"})

models = pd.read_csv(SITE / "models.csv")
aq = pd.read_csv(SITE / "axis_quality.csv")
asb = pd.read_csv(SITE / "axis_safety_bracket.csv")
asa = pd.read_csv(SITE / "axis_safety_arm.csv")
pairs = pd.read_csv(SITE / "judge_pairs.csv")
d = models.copy()
d["q"] = d["quality"] * 100
d["s"] = d["safety"] * 100


def fig_quality():
    m, lo, hi = aq["mean"] * 100, aq["lo"] * 100, aq["hi"] * 100
    x = range(len(aq))
    fig, ax = plt.subplots(figsize=(6.2, 3.5))
    ax.axvspan(1.5, 3.5, color="#2b6cb0", alpha=0.06)
    ax.errorbar(x, m, yerr=[m - lo, hi - m], marker="o", capsize=4, lw=2, color="#2b6cb0")
    for i, v in enumerate(m):
        ax.annotate(f"{v:.1f}%", (i, v), textcoords="offset points", xytext=(0, 9),
                    ha="center", fontsize=9)
    ax.set_xticks(list(x)); ax.set_xticklabels(aq["bracket"])
    ax.set_xlabel("parameter bracket"); ax.set_ylabel("judged % of frontier")
    ax.set_title("Quality knees at 2-3B; 4-5 GB adds a small lift")
    fig.savefig(OUT / "fig-quality.png"); plt.close(fig)


def fig_safety():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.4, 3.6), gridspec_kw={"width_ratios": [3, 2]})
    m, lo, hi = asb["mean"] * 100, asb["lo"] * 100, asb["hi"] * 100
    ax1.bar(asb["bracket"], m, yerr=[m - lo, hi - m], capsize=3, color="#2f855a")
    ax1.axhline(100, color="grey", lw=0.8, ls=":"); ax1.set_ylim(0, 108)
    ax1.set_ylabel("deterministic refusal %"); ax1.set_title("Instruct: rises, then plateaus < 100%")
    am, al, ah = asa["mean"] * 100, asa["lo"] * 100, asa["hi"] * 100
    ax2.bar(asa["arm"], am, yerr=[am - al, ah - am], capsize=4, color=["#2f855a", "#c53030"])
    for i, v in enumerate(am):
        ax2.annotate(f"{v:.1f}%", (i, v), textcoords="offset points", xytext=(0, 6), ha="center")
    ax2.set_ylim(0, 108); ax2.set_title("Arm gap: ~24 points")
    fig.savefig(OUT / "fig-safety.png"); plt.close(fig)


def fig_pareto():
    fig, ax = plt.subplots(figsize=(6.8, 4.6))
    for is_p, sub in d.groupby("pareto"):
        ax.scatter(sub.q, sub.s, s=sub.mWh * 2.2, alpha=0.85 if is_p else 0.30,
                   facecolor="#2b6cb0" if is_p else "none", edgecolor="#2b6cb0",
                   linewidth=1.4, label="Pareto-optimal" if is_p else "dominated")
    off = {"qwen3:4b-instruct-2507-q8_0": (8, -2), "qwen3:4b-instruct-2507-q4_K_M": (-10, 9),
           "granite4:tiny-h": (8, 0), "qwen3:1.7b": (8, 2), "granite4:1b-h": (8, 1),
           "qwen3:0.6b": (8, -4), "smollm2:360m": (-12, 6), "deepseek-r1:7b": (12, -2),
           "deepseek-r1:1.5b": (8, 2)}
    for _, r in d.iterrows():
        if r.pareto or r.model.startswith("deepseek"):
            o = off.get(r.model, (6, 3))
            ax.annotate(r.model.replace("-instruct-2507", ""), (r.q, r.s), fontsize=6.3,
                        alpha=0.9, xytext=o, textcoords="offset points", ha="right" if o[0] < 0 else "left")
    ax.set_xlabel("judged quality (% of frontier)"); ax.set_ylabel("deterministic refusal (%)")
    ax.set_title("Quality × safety × energy  (marker area = mWh/answer)")
    ax.legend(loc="lower right", framealpha=0.9)
    fig.savefig(OUT / "fig-pareto.png"); plt.close(fig)


def fig_energy():
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.scatter(d.mWh, d.s, s=44, color="#718096", alpha=0.6)
    for _, r in d.iterrows():
        if r.mWh > 140 or r.model.startswith("deepseek") or r.pareto:
            ha = "right" if r.mWh > 180 else "left"
            ax.annotate(r.model.replace("-instruct-2507", ""), (r.mWh, r.s), fontsize=6.3,
                        alpha=0.9, xytext=(-5 if ha == "right" else 5, 3),
                        textcoords="offset points", ha=ha)
    worst = d[d.model == "deepseek-r1:7b"]
    ax.scatter(worst.mWh, worst.s, s=120, facecolor="none", edgecolor="#c53030", linewidth=2)
    ax.set_xlabel("energy per answer (mWh)"); ax.set_ylabel("deterministic refusal (%)")
    ax.set_title("The cost of the tempting upgrade")
    fig.savefig(OUT / "fig-energy.png"); plt.close(fig)


def fig_judge():
    cats = [1, 2, 3, 4, 5]; ix = {c: i for i, c in enumerate(cats)}
    O = np.zeros((5, 5))
    for x, y in zip(pairs.claude, pairs.gpt):
        O[ix[x], ix[y]] += 1
    fig, ax = plt.subplots(figsize=(4.7, 4.2))
    ax.imshow(O, cmap="Blues")
    ax.set_xticks(range(5), cats); ax.set_yticks(range(5), cats)
    ax.set_xlabel("GPT-5.5 score"); ax.set_ylabel("Claude Opus 4.8 score")
    for i in range(5):
        for j in range(5):
            if O[i, j]:
                ax.text(j, i, int(O[i, j]), ha="center", va="center", fontsize=8,
                        color="white" if O[i, j] > O.max() / 2 else "black")
    ax.set_title("Two judges agree: quadratic κ = 0.91")
    fig.savefig(OUT / "fig-judge.png"); plt.close(fig)


for fn in (fig_quality, fig_safety, fig_pareto, fig_energy, fig_judge):
    fn()
print(f"wrote 5 figures to {OUT}")
