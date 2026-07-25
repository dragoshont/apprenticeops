"""PHASE 2 — hardening analyses prescribed by the 2026-07-25 adversarial review.

Each block answers a specific attack that a reviewer will make, using data we already
have (no re-runs). Read-only.

A. EFFECTIVE n — "157 models" is a count of TAGS. Many tags are the same checkpoint at
   different quantizations (identical parameter_count within a family). This computes the
   honest denominator: tags -> distinct checkpoints -> lineages, and restates the headline
   correlations with the lineage as the unit.

B. COMPLETION NOMOGRAM — the "cliff" is arithmetic: a cell completes iff
   tokens / decode_rate < wall. This tests how much of observed completion is explained by
   that identity alone (deterministic predictor), and whether `is_reasoning` retains any
   signal once measured verbosity and decode rate are in the model. If the arithmetic
   explains it, the honest artifact is a NOMOGRAM (given median output length and your
   machine's decode rate, here is your completion rate) -- useful selection guidance --
   not a discovery.

C. MULTIPLICITY — Benjamini-Hochberg over the headline test family, which has never been
   corrected. Reports which findings survive FDR control.

D. ENERGY PER CORRECT ANSWER — the selection-relevant cost metric (energy per *usable*
   answer, not per attempt), plus the Pareto front on (quality, energy-per-correct).

E. RELIABILITY — ops cares about the worst case, not the mean: per-model all-5-good rate
   and score variance, and whether a consistent mid model beats an erratic better one.

Run: ./deep-dive/.venv/bin/python deep-dive/phase2_hardening.py
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
from scipy import stats

import full_data

HERE = pathlib.Path(__file__).resolve().parent
WALL_S = 180.0        # run.py DEFAULT_TIMEOUT_S for the 152 protocol
GOOD = 3.0            # judge score >= 3 counts as a usable ops answer


def _bh(pvals, alpha=0.05):
    """Benjamini-Hochberg; returns (rejected, adjusted p) preserving input order."""
    p = np.asarray(pvals, dtype=float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order]
    adj = ranked * n / (np.arange(n) + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    adj = np.clip(adj, 0, 1)
    out = np.empty(n)
    out[order] = adj
    return out <= alpha, out


def main() -> None:
    d = full_data.load_full()
    mt = (d.groupby("model")
            .agg(quality=("judge_score", "mean"),
                 det=("det_score", "mean"),
                 params_b=("params_b", "first"),
                 family=("family", "first"),
                 org=("org", "first"),
                 quant=("quant", "first"),
                 is_reasoning=("is_reasoning", "first"),
                 is_tools=("is_tools", "first"),
                 energy_wh=("energy_wh", "mean"),
                 decode_tps=("decode_tokens_per_s", "median"),
                 med_tokens=("output_tokens", "median"),
                 wall_s=("wall_s", "median"),
                 complete=("dnf_bool", lambda s: 1 - s.mean()))
            .reset_index())

    # ---------------- A. EFFECTIVE n ----------------
    print("=" * 78)
    print("A. EFFECTIVE n — the honest denominator")
    print("=" * 78)
    mt["param_exact"] = pd.to_numeric(mt["params_b"], errors="coerce").round(6)
    # a distinct CHECKPOINT = same family + identical parameter count
    ckpt = mt.groupby(["family", "param_exact"], dropna=False).ngroup()
    mt["checkpoint"] = ckpt
    # a LINEAGE = same family + same rounded size class (quant + minor variants collapse)
    mt["lineage"] = mt.groupby(["family", pd.cut(mt.param_exact,
                                                 [0, .5, 1, 2, 3, 4, 5, 6, 8, 100])],
                               observed=False).ngroup()
    n_tags = len(mt)
    n_ckpt = mt.checkpoint.nunique()
    n_lin = mt.lineage.nunique()
    print(f"tags (what we call 'models'): {n_tags}")
    print(f"distinct CHECKPOINTS (family + identical param_count): {n_ckpt}")
    print(f"distinct LINEAGES (family + size class): {n_lin}")
    print(f"=> inflation factor {n_tags / n_lin:.1f}x; every model-level p-value should use "
          f"n≈{n_lin}, not {n_tags}.")
    big = (mt.groupby("checkpoint").size().sort_values(ascending=False).head(5))
    print("\nlargest checkpoint groups (tags measuring the same weights):")
    for c, k in big.items():
        names = mt[mt.checkpoint == c].model.tolist()
        print(f"  n={k}: {', '.join(x[:34] for x in names[:5])}")

    print("\n--- headline correlations, TAG-level vs LINEAGE-level ---")
    ok = mt.dropna(subset=["params_b"])
    r_tag = stats.spearmanr(ok.params_b, ok.quality)
    lin = ok.groupby("lineage").agg(params_b=("params_b", "mean"), quality=("quality", "mean"))
    r_lin = stats.spearmanr(lin.params_b, lin.quality)
    print(f"  Spearman(params, quality)  tag-level  n={len(ok):3}  rho={r_tag.correlation:+.3f} "
          f"p={r_tag.pvalue:.2e}")
    print(f"  Spearman(params, quality)  LINEAGE    n={len(lin):3}  rho={r_lin.correlation:+.3f} "
          f"p={r_lin.pvalue:.2e}")

    # ---------------- B. COMPLETION NOMOGRAM ----------------
    print("\n" + "=" * 78)
    print("B. IS THE COMPLETION CLIFF JUST ARITHMETIC? (nomogram test)")
    print("=" * 78)
    cell = d.copy()
    cell["tok"] = pd.to_numeric(cell["output_tokens"], errors="coerce")
    cell["tps"] = pd.to_numeric(cell["decode_tokens_per_s"], errors="coerce")
    cell["completed"] = ~cell["dnf_bool"].astype(bool)
    # NB: DNF cells have no observed tokens/rate, so a cell-level dropna would delete exactly
    # the failures and make any "agreement" trivially 100%. Instead predict each model's
    # completion rate from its verbosity/rate measured ON COMPLETED cells, and score that
    # prediction against ALL assigned cells (ITT denominator).
    obs = cell[cell["completed"]].dropna(subset=["tok", "tps"])
    prof = (obs.groupby("model").agg(med_tok=("tok", "median"), med_tps=("tps", "median")))
    lm = (cell.groupby("model")
              .agg(complete=("completed", "mean"), is_reasoning=("is_reasoning", "first"))
              .join(prof, how="inner").dropna())
    lm["predicted_s"] = lm.med_tok / lm.med_tps
    lm["pred_complete"] = (lm.predicted_s < WALL_S).astype(float)
    print(f"models with a usable verbosity/rate profile: {len(lm)}")
    acc = ((lm.pred_complete > 0.5) == (lm.complete > 0.5)).mean()
    print(f"binary agreement (predicted-fits-wall vs mostly-completes): {acc:.1%}")
    r = stats.spearmanr(lm.predicted_s, lm.complete)
    print(f"model-level Spearman(predicted seconds, ACTUAL completion rate) = "
          f"{r.correlation:+.3f} (n={len(lm)}, p={r.pvalue:.1e})")
    print("(strong negative => completion is largely the timeout identity: longer predicted")
    print(" time -> lower completion. That makes it a NOMOGRAM, i.e. selection guidance.)")
    # does the reasoning badge add anything beyond measured verbosity + rate?
    X = np.column_stack([np.ones(len(lm)), np.log(lm.med_tok), np.log(lm.med_tps)])
    y = lm.complete.values
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    rb = lm.is_reasoning.astype(bool).values
    if rb.sum() >= 3 and (~rb).sum() >= 3:
        t = stats.ttest_ind(resid[rb], resid[~rb], equal_var=False)
        print(f"residual completion after log(tokens)+log(rate): reasoning {resid[rb].mean():+.3f} "
              f"vs non {resid[~rb].mean():+.3f}  (Welch p={t.pvalue:.3f})")
        print("=> if p is large, the 'reasoning' badge carries NO information beyond measured "
              "verbosity: the mechanism is length, and the badge is a bad proxy.")

    # ---------------- C. MULTIPLICITY ----------------
    print("\n" + "=" * 78)
    print("C. MULTIPLICITY — Benjamini-Hochberg over the headline family")
    print("=" * 78)
    tests = []
    okq = ok.dropna(subset=["quality"])
    tests.append(("params~quality (lineage)", stats.spearmanr(lin.params_b, lin.quality).pvalue))
    tl = okq.dropna(subset=["is_tools"])
    if tl.is_tools.nunique() > 1:
        a = tl[tl.is_tools == True].quality; b = tl[tl.is_tools == False].quality  # noqa: E712
        tests.append(("tool-training quality", stats.ttest_ind(a, b, equal_var=False).pvalue))
    rr = okq.dropna(subset=["is_reasoning"])
    if rr.is_reasoning.nunique() > 1:
        a = rr[rr.is_reasoning == True].quality; b = rr[rr.is_reasoning == False].quality  # noqa: E712
        tests.append(("reasoning quality", stats.ttest_ind(a, b, equal_var=False).pvalue))
    tests.append(("params~energy", stats.spearmanr(ok.params_b, ok.energy_wh, nan_policy="omit").pvalue))
    tests.append(("quality~energy", stats.spearmanr(ok.quality, ok.energy_wh, nan_policy="omit").pvalue))
    tests.append(("params~completion", stats.spearmanr(ok.params_b, ok.complete).pvalue))
    tests.append(("verbosity~completion", stats.spearmanr(lm.med_tok, lm.complete).pvalue))
    tests.append(("det~quality", stats.spearmanr(ok.det, ok.quality).pvalue))
    names = [t[0] for t in tests if np.isfinite(t[1])]
    pv = [t[1] for t in tests if np.isfinite(t[1])]
    dropped = [t[0] for t in tests if not np.isfinite(t[1])]
    if dropped:
        print(f"(excluded, p undefined: {', '.join(dropped)})")
    rej, adj = _bh(pv)
    print(f"{'test':32} {'raw p':>10} {'BH p':>10}  survives FDR 5%")
    for nme, p, a, rj in zip(names, pv, adj, rej):
        print(f"{nme:32} {p:10.2e} {a:10.2e}  {'YES' if rj else 'no'}")

    # ---------------- D. ENERGY PER CORRECT ANSWER ----------------
    print("\n" + "=" * 78)
    print("D. ENERGY PER *CORRECT* ANSWER (the selection-relevant cost)")
    print("=" * 78)
    e = d.copy()
    e["good"] = e["judge_score"] >= GOOD
    ee = (e.groupby("model")
            .agg(total_wh=("energy_wh", "sum"), n=("judge_score", "size"),
                 good=("good", "sum"), quality=("judge_score", "mean"),
                 params_b=("params_b", "first")).reset_index())
    ee["wh_per_attempt"] = ee.total_wh / ee.n
    ee["wh_per_good"] = ee.total_wh / ee.good.replace(0, np.nan)
    usable = ee.dropna(subset=["wh_per_good"])
    print(f"models that produced >=1 usable (score>={GOOD:.0f}) answer: {len(usable)}/{len(ee)}")
    print("\ncheapest 8 by energy PER CORRECT ANSWER:")
    print(usable.nsmallest(8, "wh_per_good")[
        ["model", "quality", "wh_per_attempt", "wh_per_good", "params_b"]]
        .round(4).to_string(index=False))
    rho_a = stats.spearmanr(usable.wh_per_attempt, usable.wh_per_good)
    print(f"\nSpearman(wh_per_attempt, wh_per_good) = {rho_a.correlation:+.3f} "
          "-> if well below 1, ranking on cost-per-attempt MISRANKS true cost")

    # Pareto front on (quality high, wh_per_good low)
    pf = []
    for _, r0 in usable.iterrows():
        dominated = ((usable.quality >= r0.quality) & (usable.wh_per_good <= r0.wh_per_good) &
                     ((usable.quality > r0.quality) | (usable.wh_per_good < r0.wh_per_good))).any()
        if not dominated:
            pf.append(r0)
    pf = pd.DataFrame(pf).sort_values("quality", ascending=False)
    print(f"\nPareto front (quality vs energy-per-correct): {len(pf)} models")
    print(pf[["model", "quality", "wh_per_good", "params_b"]].round(4).to_string(index=False))

    # ---------------- E. RELIABILITY ----------------
    print("\n" + "=" * 78)
    print("E. RELIABILITY — ops cares about the worst case, not the mean")
    print("=" * 78)
    cellq = (d.groupby(["model", "scenario"])
               .agg(mean_q=("judge_score", "mean"),
                    min_q=("judge_score", "min"),
                    all_good=("judge_score", lambda s: bool((s >= GOOD).all())),
                    sd=("judge_score", "std")).reset_index())
    rel = (cellq.groupby("model")
                .agg(mean_q=("mean_q", "mean"), all5_rate=("all_good", "mean"),
                     within_sd=("sd", "mean")).reset_index()
                .merge(mt[["model", "params_b"]], on="model"))
    rel["rank_mean"] = rel.mean_q.rank(ascending=False)
    rel["rank_all5"] = rel.all5_rate.rank(ascending=False)
    rel["rank_shift"] = rel.rank_mean - rel.rank_all5
    print("models that RISE most when ranked on all-5-good instead of the mean:")
    print(rel.nlargest(6, "rank_shift")[
        ["model", "mean_q", "all5_rate", "within_sd", "rank_mean", "rank_all5"]]
        .round(3).to_string(index=False))
    print("\nmodels that FALL most (mean flatters them; they are erratic):")
    print(rel.nsmallest(6, "rank_shift")[
        ["model", "mean_q", "all5_rate", "within_sd", "rank_mean", "rank_all5"]]
        .round(3).to_string(index=False))
    rr2 = stats.spearmanr(rel.mean_q, rel.all5_rate)
    print(f"\nSpearman(mean quality, all-5-good rate) = {rr2.correlation:+.3f}")
    v = rel.dropna(subset=["within_sd", "params_b"])
    print(f"Spearman(params, within-scenario SD)    = "
          f"{stats.spearmanr(v.params_b, v.within_sd).correlation:+.3f} "
          "(negative => bigger models are more consistent)")

    out = HERE / "out"
    out.mkdir(parents=True, exist_ok=True)
    mt.to_csv(out / "phase2_model_table.csv", index=False)
    ee.to_csv(out / "phase2_energy_per_correct.csv", index=False)
    rel.to_csv(out / "phase2_reliability.csv", index=False)
    print(f"\nsaved phase2_model_table.csv, phase2_energy_per_correct.csv, phase2_reliability.csv")


if __name__ == "__main__":
    main()
