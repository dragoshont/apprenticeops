"""Bounded completion-proxy/energy selection sensitivity on frozen r4 evidence.

No usability validation, new measurements, served-exclusion imputation or claims.
The existing 15-arm implementation and all r4 artifacts remain unchanged.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import platform
import subprocess
import sys

import numpy as np
import pandas as pd
from scipy import stats

import selection_stability as ss

BASE = ss.HERE / "out/selection-stability-152-20260909-r4"
BASE_SHA = "4b929c382f69c7e8d07a75d4e4be2b49540b43cc6d90b08e90708ac372d70fd2"
FINISH_REASONS = {"stop", "length", "DNF:timeout", "DNF:after_done_missing"}
ARMS = ("mean-per-attempt", "proxy-conditional", "proxy-unconditional", "mean-per-positive")


def completion_proxy(df):
    """Nonblank terminal output, including flagged length; NOT usable completion."""
    if not df.finish_reason.isin(FINISH_REASONS).all():
        raise ValueError("missing/unknown frozen completion category")
    chars = df.output_chars.to_numpy(dtype=float)
    if not (np.isfinite(chars) & (chars >= 0) & (chars == np.floor(chars))).all():
        raise ValueError("output_chars must be known nonnegative integers")
    return (df.finish_reason.isin(["stop", "length"]) & df.output_chars.gt(0)).to_numpy()


def ratio(numerator, denominator, *, energy=False):
    """Zero denominator is missing, except positive Wh / zero positives is +inf."""
    num, den = np.broadcast_arrays(np.asarray(numerator, float), np.asarray(denominator, float))
    if not (np.isfinite(num).all() and np.isfinite(den).all()) or (num < 0).any() or (den < 0).any():
        raise ValueError("unknown or negative aggregate")
    value = np.full(num.shape, np.nan)
    np.divide(num, den, out=value, where=den > 0)
    if energy:
        value[(den == 0) & (num > 0)] = np.inf
    return value


def draw_sums(totals, picks):
    if (picks.ndim != 2 or picks.shape[1] != totals.shape[1] or not len(picks)
            or not np.issubdtype(picks.dtype, np.integer)
            or (picks < 0).any() or (picks >= totals.shape[1]).any()):
        raise ValueError("invalid full-size scenario-cluster draws")
    return totals[:, picks].sum(axis=2).T


def make_axes(df, models, scenarios, picks):
    df = ss.validate_grid(df, models, scenarios)
    shape = (len(models), len(scenarios), ss.REPS)
    proxy = completion_proxy(df).reshape(shape)
    score = df.consensus.to_numpy().reshape(shape)
    energy = df.energy_wh.to_numpy().reshape(shape)
    n = len(scenarios)*ss.REPS

    def totals(values):
        by_scenario = values.sum(axis=2)
        return by_scenario.sum(axis=1), draw_sums(by_scenario, picks)

    cp, cb = totals(proxy)
    sp, sb = totals(score)
    pp, pb = totals(score*proxy)
    up, ub = totals(np.where(proxy, score, 1.))
    ep, eb = totals(energy)
    np_, nb = totals(score >= 3)
    axes = {}
    for arm, qp, qb, epoint, eboot in [
        ("mean-per-attempt", sp/n, sb/n, ep/n, eb/n),
        ("proxy-conditional", ratio(pp, cp), ratio(pb, cb), ep/n, eb/n),
        ("proxy-unconditional", up/n, ub/n, ep/n, eb/n),
        ("mean-per-positive", sp/n, sb/n, ratio(ep, np_, energy=True),
         ratio(eb, nb, energy=True))]:
        axes[arm] = {"point_q": qp, "point_e": epoint, "boot_q": qb, "boot_e": eboot}
    counts = {
        "point_proxy": cp, "boot_proxy": cb, "point_positive": np_, "boot_positive": nb,
        "point_energy": ep, "assigned": n,
        "point_length": (df.finish_reason.eq("length").to_numpy().reshape(shape) & proxy).sum(axis=(1, 2)),
        "point_blank": df.output_chars.eq(0).to_numpy().reshape(shape).sum(axis=(1, 2)),
        "point_dnf": df.finish_reason.str.startswith("DNF:").to_numpy().reshape(shape).sum(axis=(1, 2)),
    }
    return axes, counts


def central(values):
    values = np.asarray(values)
    values = values[np.isfinite(values)]
    return {"n": len(values), "mean": float(values.mean()) if len(values) else None,
            "q025": float(np.percentile(values, 2.5)) if len(values) else None,
            "q975": float(np.percentile(values, 97.5)) if len(values) else None}


def summarize(point_q, point_e, boot_q, boot_e, top_ks=ss.TOP_KS):
    """Whole-roster summaries: never rank an available-case subset of tags.

    NaN is unavailable. +inf is a known extended-real cost, NOT a finite choice.
    A high-quality +inf point need not be dominated by lower-quality finite cost.
    """
    if (boot_q.ndim != 2 or boot_q.shape != boot_e.shape or not len(boot_q)
            or boot_q.shape[1] != len(point_q) or len(point_q) != len(point_e)):
        raise ValueError("unaligned selection axes")
    if (np.isinf(point_q).any() or np.isinf(boot_q).any()
            or (point_e < 0).any() or (boot_e < 0).any()):
        raise ValueError("infinite quality or negative cost")
    valid = (np.isfinite(boot_q) & ~np.isnan(boot_e)).all(axis=1)
    point_valid = bool((np.isfinite(point_q) & ~np.isnan(point_e)).all())
    ranks, fronts = np.full(boot_q.shape, np.nan), np.full(boot_q.shape, np.nan)
    credits = {k: np.full(boot_q.shape, np.nan) for k in top_ks}
    point_rank = np.full(len(point_q), np.nan)
    point_front = np.full(len(point_q), np.nan)
    point_credit = {k: np.full(len(point_q), np.nan) for k in top_ks}
    if valid.any():
        ranks[valid], calculated = ss.rank_and_topk(boot_q[valid], top_ks)
        for k in top_ks:
            credits[k][valid] = calculated[k]
            if not np.allclose(calculated[k].sum(axis=1), k, rtol=0, atol=1e-12):
                raise ValueError("top-k credits do not preserve k slots")
        fronts[valid] = np.stack([ss.pareto_mask(q, e) for q, e in zip(boot_q[valid], boot_e[valid])])
    if point_valid:
        point_rank, point_credit = ss.rank_and_topk(point_q, top_ks)
        point_front = ss.pareto_mask(point_q, point_e)

    def mean_or_missing(array):
        return array[valid].mean(axis=0) if valid.any() else np.full(len(point_q), np.nan)

    table = pd.DataFrame({
        "point_quality": point_q, "point_cost_wh": point_e,
        "point_quality_status": np.where(np.isfinite(point_q), "estimable", "not-estimable"),
        "point_cost_status": np.where(np.isnan(point_e), "not-estimable-zero-over-zero",
                                     np.where(np.isinf(point_e), "unbounded-zero-success", "finite")),
        "point_rank": point_rank, "point_pareto": pd.array(point_front, dtype="boolean"),
        "point_selection_status": "estimable" if point_valid else "not-estimable",
        "valid_draws": int(valid.sum()),
        "quality_unavailable_draws": (~np.isfinite(boot_q)).sum(axis=0),
        "cost_unavailable_draws": np.isnan(boot_e).sum(axis=0),
        "infinite_cost_draws": np.isposinf(boot_e).sum(axis=0),
        "rank_mean": mean_or_missing(ranks),
        "rank_q025": np.percentile(ranks[valid], 2.5, axis=0) if valid.any() else np.nan,
        "rank_q975": np.percentile(ranks[valid], 97.5, axis=0) if valid.any() else np.nan,
        "pareto_probability": mean_or_missing(fronts),
    })
    for k in top_ks:
        table[f"point_top_{k}_credit"] = point_credit[k]
        table[f"top_{k}_probability"] = mean_or_missing(credits[k])
    tau, jaccard, size = (np.full(len(valid), np.nan) for _ in range(3))
    size[valid] = fronts[valid].sum(axis=1)
    if point_valid:
        for i in np.flatnonzero(valid):
            tau[i] = stats.kendalltau(point_q, boot_q[i]).statistic
            f = fronts[i].astype(bool)
            jaccard[i] = (f & point_front).sum()/(f | point_front).sum()
    draws = pd.DataFrame({
        "draw": np.arange(len(valid)), "estimable": valid,
        "quality_unavailable_models": (~np.isfinite(boot_q)).sum(axis=1),
        "cost_unavailable_models": np.isnan(boot_e).sum(axis=1),
        "finite_cost_models": np.isfinite(boot_e).sum(axis=1),
        "infinite_cost_models": np.isposinf(boot_e).sum(axis=1),
        "kendall_vs_point": tau, "pareto_size": size, "pareto_jaccard_vs_point": jaccard,
    })
    summary = {
        "point_status": "estimable" if point_valid else "not-estimable",
        "point_pareto_size": int(point_front.sum()) if point_valid else None,
        "point_finite_cost_models": int(np.isfinite(point_e).sum()),
        "point_infinite_cost_models": int(np.isposinf(point_e).sum()),
        "draws": len(valid), "valid_draws": int(valid.sum()), "unavailable_draws": int((~valid).sum()),
    }
    for key, values in [("kendall", tau), ("pareto_size", size), ("pareto_jaccard", jaccard)]:
        summary.update({key+"_"+stat: value for stat, value in central(values).items()})
    state = {"valid": valid, "q": boot_q, "ranks": ranks, "fronts": fronts, "credits": credits,
             "point_valid": point_valid, "point_q": point_q, "point_front": point_front}
    return table, summary, draws, state


def compare(a, b, k=5):
    """Paired scenario comparisons only on the intersection of valid draws."""
    valid = a["valid"] & b["valid"]
    tau, jaccard, overlap = (np.full(len(valid), np.nan) for _ in range(3))
    for i in np.flatnonzero(valid):
        tau[i] = stats.kendalltau(a["q"][i], b["q"][i]).statistic
        fa, fb = a["fronts"][i].astype(bool), b["fronts"][i].astype(bool)
        jaccard[i] = (fa & fb).sum()/(fa | fb).sum()
        overlap[i] = np.minimum(a["credits"][k][i], b["credits"][k][i]).sum()/k
    summary = {"paired_valid_draws": int(valid.sum()), "draws": len(valid)}
    for key, values in [("kendall", tau), ("pareto_jaccard", jaccard), ("topk_overlap", overlap)]:
        summary.update({key+"_"+stat: value for stat, value in central(values).items()})
    point_valid = a["point_valid"] and b["point_valid"]
    summary["point_kendall"] = stats.kendalltau(a["point_q"], b["point_q"]).statistic if point_valid else None
    if point_valid:
        fa, fb = a["point_front"], b["point_front"]
        summary["point_pareto_jaccard"] = (fa & fb).sum()/(fa | fb).sum()
    else:
        summary["point_pareto_jaccard"] = None
    return summary, pd.DataFrame({"draw": np.arange(len(valid)), "paired_estimable": valid,
                                 "kendall_between_arms": tau, "pareto_jaccard_between_arms": jaccard,
                                 "topk_credit_overlap": overlap})


def analyze(df, models, scenarios, n=ss.DRAWS, seed=ss.SEED, top_ks=ss.TOP_KS):
    picks = ss.scenario_draws(len(scenarios), n, seed)
    axes, counts = make_axes(df, models, scenarios, picks)
    denominator = pd.DataFrame({
        "model": models, "assigned_attempts": counts["assigned"],
        "proxy_attempts": counts["point_proxy"], "proxy_rate": counts["point_proxy"]/counts["assigned"],
        "length_attempts_retained": counts["point_length"], "blank_attempts": counts["point_blank"],
        "dnf_attempts": counts["point_dnf"], "raw_score_ge3_attempts": counts["point_positive"],
        "total_assigned_wh": counts["point_energy"],
        "proxy_draw_min": counts["boot_proxy"].min(axis=0),
        "proxy_draw_max": counts["boot_proxy"].max(axis=0),
        "proxy_zero_denominator_draws": (counts["boot_proxy"] == 0).sum(axis=0),
        "positive_draw_min": counts["boot_positive"].min(axis=0),
        "positive_draw_max": counts["boot_positive"].max(axis=0),
        "positive_zero_denominator_draws": (counts["boot_positive"] == 0).sum(axis=0),
    })
    selections, summaries, draws, states = [], [], [], {}
    for arm, axis in axes.items():
        table, summary, draw, state = summarize(**axis, top_ks=top_ks)
        table.insert(0, "model", models)
        table = table.merge(denominator, on="model", validate="one_to_one", sort=False)
        for frame in [table, draw]:
            frame.insert(0, "arm", arm)
        draw["proxy_zero_denominator_models"] = (counts["boot_proxy"] == 0).sum(axis=1)
        selections.append(table)
        summaries.append({"arm": arm, "deployments": len(models), **summary})
        draws.append(draw)
        states[arm] = state
    comparisons, comparison_draws = [], []
    for a, b in [("proxy-conditional", "proxy-unconditional"),
                 ("proxy-conditional", "mean-per-attempt"),
                 ("proxy-unconditional", "mean-per-attempt"),
                 ("mean-per-positive", "mean-per-attempt")]:
        summary, draw = compare(states[a], states[b], k=5 if 5 in top_ks else top_ks[-1])
        name = a+" vs "+b
        comparisons.append({"comparison": name, **summary})
        draw.insert(0, "comparison", name)
        comparison_draws.append(draw)
    return {"selection": pd.concat(selections, ignore_index=True),
            "arm_summary": pd.DataFrame(summaries), "draw_summary": pd.concat(draws, ignore_index=True),
            "denominators": denominator, "comparisons": pd.DataFrame(comparisons),
            "comparison_draws": pd.concat(comparison_draws, ignore_index=True)}


def screen_disposition(screen, selected_models):
    if (screen.model.duplicated().any() or screen.model.isna().any() or len(screen) != 173
            or not screen.in_study.isin([True, False]).all()):
        raise ValueError("invalid frozen candidate boundary")
    chosen = set(screen.loc[screen.in_study.eq(True), "model"])
    excluded = set(screen.loc[screen.in_study.eq(False), "model"])
    if (len(chosen) != 152 or len(excluded) != 21 or chosen & excluded
            or chosen != set(selected_models)):
        raise ValueError("candidate boundary does not match full-run roster")
    return {"dimension": "served-failure-policy selection sensitivity", "status": "NOT_IDENTIFIABLE",
            "screened": 173, "selected_full_run": 152, "excluded": 21, "excluded_full_run_rows": 0,
            "excluded_models": sorted(excluded),
            "reason": "Screen outcomes are not comparable 20-scenario/five-repeat quality/energy rows. "
                      "The 21 excluded tags cannot be ranked or assigned failed-attempt energy. "
                      "No imputation or additional measurement is performed."}


def verify_outputs(directory, hashes):
    for name, digest in hashes.items():
        ss.verify_hash(directory/name, digest)


def load_inputs():
    ss.verify_hash(BASE/"receipt.json", BASE_SHA)
    baseline = json.loads((BASE/"receipt.json").read_text())
    for path, digest in baseline["code_sha256"].items():
        ss.verify_hash(ss.REPO/path, digest)
    verify_outputs(BASE, baseline["output_sha256"])
    df, population, models, scenarios, inputs = ss.load_inputs()
    checks = pd.read_csv(ss.FROZEN/"check_cells.csv", usecols=ss.full_data._CELL+["output_chars"])
    checks = checks[checks.model.isin(models)]
    if len(checks) != len(df):
        raise ValueError("metadata population differs from frozen primary cells")
    df = df.merge(checks, on=ss.full_data._CELL, how="left", validate="one_to_one")
    completion_proxy(df)  # missing key/metadata never treated as noncompletion
    core = json.loads((ss.FROZEN/"receipt.json").read_text())
    screen_path = ss.FROZEN/"candidate_screen.csv"
    ss.verify_hash(screen_path, core["output_sha256"]["candidate_screen.csv"])
    inputs[str(screen_path.relative_to(ss.REPO))] = core["output_sha256"]["candidate_screen.csv"]
    inputs[str((BASE/"receipt.json").relative_to(ss.REPO))] = BASE_SHA
    inputs.update(baseline["code_sha256"])
    selected_models = pd.read_csv(ss.full_data._SNAP_RESULTS, usecols=["model"]).model.unique()
    disposition = screen_disposition(pd.read_csv(screen_path), selected_models)
    return df, population, models, scenarios, inputs, baseline, disposition


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()
    df, population, models, scenarios, inputs, baseline, disposition = load_inputs()
    args.out.mkdir(parents=True, exist_ok=False)
    # New base receipt has exactly the same source and outputs as r4, not rewritten anchors.
    subprocess.run([sys.executable, str(ss.HERE/"selection_stability.py"), "--out", str(args.out/"base")],
                   check=True, capture_output=True, text=True)
    verify_outputs(args.out/"base", baseline["output_sha256"])
    ss.verify_hash(args.out/"base/receipt.json", BASE_SHA)
    outputs = analyze(df, models, scenarios)
    for name, frame in outputs.items():
        frame.to_csv(args.out/(name+".csv"), index=False)
    population.to_csv(args.out/"population.csv", index=False)
    df[ss.full_data._CELL+["finish_reason", "output_chars"]].to_csv(args.out/"completion_metadata.csv", index=False)
    (args.out/"served_failure_disposition.json").write_text(json.dumps(disposition, indent=2)+"\n")
    code = [pathlib.Path(__file__).resolve(), ss.HERE/"test_selection_sensitivity.py"]
    receipt = {
        "status": "computation-completed-review-pending", "claim_status": "provisional",
        "study": ss.full_data.RUN_ID, "seed": ss.SEED, "draws": ss.DRAWS,
        "models": models, "scenarios": scenarios, "repetitions": list(range(ss.REPS)),
        "top_ks": list(ss.TOP_KS), "original_arms": 15, "additional_consensus_arms": 3,
        "reference_arm": "mean-per-attempt", "original_base_replay": "six CSVs and receipt byte-identical",
        "base_receipt_sha256": BASE_SHA, "input_sha256": inputs,
        "code_sha256": {str(p.relative_to(ss.REPO)): ss.sha256(p) for p in code},
        "output_sha256": {str(p.relative_to(args.out)): ss.sha256(p)
                          for p in sorted(args.out.rglob("*")) if p.is_file()},
        "python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
        "completion_proxy": "output_chars>0 AND finish_reason in {stop,length}; length retained/flagged. "
                            "NOT human-validated usable completion.",
        "quality": "Conditional=sum(proxy*raw consensus)/sum(proxy). Unconditional="
                   "sum(proxy*raw consensus+(1-proxy)*1)/assigned attempts. Failure floor1 is an "
                   "exploratory versioned sensitivity, not retrospectively preregistered.",
        "energy": "RAPL package-0 only. All assigned Wh / assigned attempts OR / count(raw consensus>=3). "
                  "All failed energy included. Positive Wh/zero positives=+inf; 0/0 unavailable.",
        "missingness": "Unknown input rejected. Derived zero-denominator quality is missing. "
                       "Any unavailable model axis invalidates the entire fixed-roster arm/draw. "
                       "Frequencies use reported whole-roster-valid draws; zero valid draws=>null. "
                       "Paired comparisons use valid-draw intersections.",
        "infinity": "Extended-real Pareto costs; +inf is not missing, nor a finite-cost deployment choice. "
                    "An infinite-cost higher-quality point need not be dominated by lower finite-cost quality.",
        "served_failure_policy": disposition,
        "limits": "Fixed-tag scenario-composition sensitivity only. No human usability/safety validation, "
                  "weight-population inference, new measurements, new preregistration or claim promotion.",
    }
    (args.out/"receipt.json").write_text(json.dumps(receipt, indent=2, allow_nan=False)+"\n")
    print(outputs["arm_summary"].to_string(index=False))
    print(outputs["comparisons"].to_string(index=False))
    print(f"Saved bounded extension to {args.out}; original15 arms replayed exactly.")


if __name__ == "__main__":
    main()
