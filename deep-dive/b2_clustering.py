"""B2 — Model archetypes and metric correlation structure.

Standardises the model-level metric space, reports the correlation structure and
PCA, then clusters models into archetypes (k chosen by silhouette). Produces a
correlation heatmap and a PC1-PC2 archetype map.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from ceops_data import REPO, load_runs, model_table

FIG = REPO / "deep-dive" / "figures"
FEATURES = ["quality", "safety", "det_score", "decode_tps", "wall_s",
            "membw_peak_mb_s", "quality_sd", "trunc_rate", "dnf_rate", "size_gb", "params_b"]


def main() -> None:
    df = load_runs()
    mt = model_table(df).set_index("model")
    X = mt[FEATURES].copy()
    X = X.fillna(X.median())
    Z = StandardScaler().fit_transform(X)

    # correlation structure
    corr = pd.DataFrame(Z, columns=FEATURES).corr()
    print("=== metric correlation structure (Pearson, standardized) ===")
    print(corr.round(2).to_string())
    print("\nnotable:")
    print(f"  quality~safety     {corr.loc['quality','safety']:+.2f} (collinear -> not an independent tradeoff)")
    print(f"  quality~size_gb    {corr.loc['quality','size_gb']:+.2f}")
    print(f"  quality~decode_tps {corr.loc['quality','decode_tps']:+.2f} (bigger/better = slower)")
    print(f"  size~decode_tps    {corr.loc['size_gb','decode_tps']:+.2f} (bigger = slower decode)")
    print(f"  quality~quality_sd {corr.loc['quality','quality_sd']:+.2f} (are better models more stochastic?)")

    # PCA
    pca = PCA(n_components=4).fit(Z)
    pcs = pca.transform(Z)
    print(f"\n=== PCA: explained variance {np.round(pca.explained_variance_ratio_[:4],2)} ===")
    load = pd.DataFrame(pca.components_[:3].T, index=FEATURES, columns=["PC1", "PC2", "PC3"])
    print(load.round(2).to_string())

    # choose k by silhouette
    best = None
    for k in range(3, 7):
        km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(Z)
        s = silhouette_score(Z, km.labels_)
        if best is None or s > best[1]:
            best = (k, s, km)
    k, sil, km = best
    mt["cluster"] = km.labels_
    print(f"\n=== archetypes: k={k} (silhouette={sil:.2f}) ===")
    prof = mt.groupby("cluster")[FEATURES].mean()
    profz = (prof - X.mean()) / X.std()
    for c in range(k):
        sub = mt[mt.cluster == c].sort_values("quality", ascending=False)
        top = profz.loc[c].sort_values()
        hi = ", ".join(f"{i}+" for i in top.index[-2:])
        lo = ", ".join(f"{i}-" for i in top.index[:2])
        print(f"\ncluster {c} (n={len(sub)}): quality={prof.loc[c,'quality']:.2f} size={prof.loc[c,'size_gb']:.2f}GB "
              f"decode={prof.loc[c,'decode_tps']:.1f}tps  [{hi}; {lo}]")
        print("  members:", ", ".join(sub.index[:6]))

    # figures
    fig, ax = plt.subplots(1, 2, figsize=(13, 5.5))
    im = ax[0].imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax[0].set_xticks(range(len(FEATURES))); ax[0].set_xticklabels(FEATURES, rotation=90, fontsize=7)
    ax[0].set_yticks(range(len(FEATURES))); ax[0].set_yticklabels(FEATURES, fontsize=7)
    ax[0].set_title("metric correlation structure"); fig.colorbar(im, ax=ax[0], fraction=0.046)
    sc = ax[1].scatter(pcs[:, 0], pcs[:, 1], c=km.labels_, cmap="tab10", s=30)
    for i, mname in enumerate(mt.index):
        if mt.iloc[i]["quality"] > 2.9 or mt.iloc[i]["quality"] < 1.2 or mt.iloc[i]["decode_tps"] > 25:
            ax[1].annotate(mname.split("/")[-1][:14], (pcs[i, 0], pcs[i, 1]), fontsize=6)
    ax[1].set(xlabel=f"PC1 ({pca.explained_variance_ratio_[0]:.0%})",
              ylabel=f"PC2 ({pca.explained_variance_ratio_[1]:.0%})", title=f"model archetypes (k={k})")
    fig.tight_layout(); FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "b2_archetypes.png", dpi=130)
    mt.reset_index()[["model", "cluster"] + FEATURES].to_csv(REPO / "deep-dive" / "out" / "b2_clusters.csv", index=False)
    print(f"\nsaved figure {FIG/'b2_archetypes.png'} and out/b2_clusters.csv")


if __name__ == "__main__":
    main()
