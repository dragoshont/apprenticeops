"""Fixed-roster selection sensitivity; new files only, no claim promotion.

Read the frozen core eligibility/identity and its hash-bound 152-study snapshots.
Resample scenarios jointly across deployments and score definitions. Never drop
failed attempts, impute unknown inputs, or infer independent weight lineages.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import platform
import subprocess

import numpy as np
import pandas as pd
import scipy
from scipy import stats

import full_data
from a2_efficiency import pareto_mask

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
FROZEN = HERE / "out/analysis-repair-152-20260909-r4"
RECEIPT_SHA = "22fac59e27ec3df40406d00c5b31cd39ae55596140c0d16f817abc1af185371a"
AB_RECEIPT_SHA = "269e6a5c334850bcc866222dc184defbb34f46daaaaf6a47dcf6b76dd62df108"
JUDGES = ("claude-opus-4.6", "gpt-5.4")
SOURCES = ("consensus",) + JUDGES
REPS = 5
DRAWS = 4000
SEED = 20260725
TOP_KS = (1, 5, 10)


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def verify_hash(path, expected):
    if sha256(path) != expected:
        raise ValueError(f"frozen input hash mismatch: {path}")


def integer_tier(value):
    try:
        count = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("missing/noninteger parameter count") from exc
    if isinstance(value, (bool, np.bool_)) or count != value or not 0 < count <= 5_000_000_000:
        raise ValueError("primary parameter count must be an integer in (0, 5B]")
    return f"T{(count-1)//1_000_000_000+1}"


def validate_grid(df, models, scenarios):
    """Require the exact assigned grid and all numeric observations; no complete cases."""
    keys = full_data._CELL
    if df[keys].isna().any().any() or df.duplicated(keys).any():
        raise ValueError("missing or duplicate deployment/scenario/repetition key")
    expected = pd.MultiIndex.from_product([models, scenarios, range(REPS)], names=keys)
    actual = pd.MultiIndex.from_frame(df[keys])
    if len(actual) != len(expected) or len(expected.difference(actual)) or len(actual.difference(expected)):
        raise ValueError("not the complete frozen roster x scenarios x five repetitions")
    numeric = df[["energy_wh", *SOURCES]].to_numpy(dtype=float)
    if not np.isfinite(numeric).all() or df.energy_wh.lt(0).any():
        raise ValueError("unknown/nonfinite metric input or negative measured energy")
    for judge in JUDGES:
        score = df[judge]
        if not (score.between(1, 5) & score.mod(1).eq(0)).all():
            raise ValueError("judge observations must be recorded integer scores 1..5")
    if not np.array_equal(df.consensus.to_numpy(), df[list(JUDGES)].mean(axis=1).to_numpy()):
        raise ValueError("consensus differs from complete paired judgments")
    return df.set_index(keys).reindex(expected).reset_index()


def load_inputs():
    """Portable frozen-snapshot path, with an anchored predecessor receipt."""
    verify_hash(FROZEN / "receipt.json", RECEIPT_SHA)
    verify_hash(FROZEN / "ab/receipt.json", AB_RECEIPT_SHA)
    prior = json.loads((FROZEN / "receipt.json").read_text())
    ab = json.loads((FROZEN / "ab/receipt.json").read_text())
    if prior["run_id"] != full_data.RUN_ID or prior["primary_models"] != 137:
        raise ValueError("wrong frozen study or primary population")
    inputs = {str((FROZEN/"receipt.json").relative_to(REPO)): RECEIPT_SHA,
              str((FROZEN/"ab/receipt.json").relative_to(REPO)): AB_RECEIPT_SHA}
    # Guard the existing helpers being reused, not unrelated reviewed modules.
    for path, digest in [
        (HERE/"full_data.py", prior["source_sha256"]["deep-dive/full_data.py"]),
        (HERE/"a2_efficiency.py", ab["source_sha256"]["deep-dive/a2_efficiency.py"]),
        (full_data._SNAP_RESULTS, prior["source_sha256"][str(full_data._SNAP_RESULTS.relative_to(REPO))]),
        (full_data._SNAP_JUDGED, prior["source_sha256"][str(full_data._SNAP_JUDGED.relative_to(REPO))]),
        *[(FROZEN/name, prior["output_sha256"][name]) for name in
          ["eligibility.csv", "identity.csv", "check_cells.csv", "primary_model_table.csv"]]]:
        verify_hash(path, digest)
        inputs[str(path.relative_to(REPO))] = digest
    eligibility = pd.read_csv(FROZEN/"eligibility.csv")
    if eligibility.model.duplicated().any() or len(eligibility) != 152:
        raise ValueError("invalid frozen eligibility roster")
    population = eligibility[eligibility.eligible.eq(True)].copy()
    if len(population) != 137 or not population.included.eq(True).all():
        raise ValueError("wrong included primary roster")
    population["integer_tier"] = population.run_param_count.map(integer_tier)
    if not population.lock_tier.isin(["T1", "T2", "T3", "T4", "T5"]).all():
        raise ValueError("unknown frozen lock tier")
    population["tier_disagrees"] = population.integer_tier.ne(population.lock_tier)
    ids = pd.read_csv(FROZEN/"identity.csv")
    population = population.merge(ids[["model", "artifact_digest", "lineage_status"]],
                                  on="model", how="left", validate="one_to_one")
    models = sorted(population.model)
    res = pd.read_csv(full_data._SNAP_RESULTS)
    jud = pd.read_csv(full_data._SNAP_JUDGED)
    if set(jud.judge_model) != set(JUDGES) or set(res.model) != set(eligibility.model):
        raise ValueError("frozen roster or judge identities differ from snapshots")
    cons = jud.groupby(full_data._CELL).score.mean().rename("judge_score").reset_index()
    full_data._assert_join_integrity(res, jud, cons)
    paired = jud.pivot(index=full_data._CELL, columns="judge_model", values="score").reset_index()
    df = res.merge(paired, on=full_data._CELL, validate="one_to_one")
    df = df[df.model.isin(models)].copy()
    if not (df.no_turbo.eq(1) & df.power_source.eq("rapl:package-0")).all():
        raise ValueError("energy is not entirely from the recorded controlled RAPL scope")
    df["consensus"] = df[list(JUDGES)].mean(axis=1)
    scenarios = sorted(df.scenario.unique())
    if len(scenarios) != 20:
        raise ValueError("expected 20 frozen scenarios")
    df = validate_grid(df, models, scenarios)
    checks = pd.read_csv(FROZEN/"check_cells.csv", usecols=full_data._CELL+["judge_score"])
    joined = df.merge(checks, on=full_data._CELL, validate="one_to_one")
    if not np.array_equal(joined.consensus.to_numpy(), joined.judge_score.to_numpy()):
        raise ValueError("snapshot consensus disagrees with frozen core evidence")
    prior_means = pd.read_csv(FROZEN/"primary_model_table.csv").set_index("model").loc[models]
    means = df.groupby("model")[["consensus", "energy_wh"]].mean().loc[models]
    if not np.allclose(means.to_numpy(), prior_means[["quality", "energy_wh"]].to_numpy(),
                       rtol=0, atol=1e-12):
        raise ValueError("primary point means differ from frozen core outputs")
    return df, population.sort_values("model").reset_index(drop=True), models, scenarios, inputs


def scenario_draws(n_scenarios, n=DRAWS, seed=SEED):
    if n_scenarios < 1 or n < 1:
        raise ValueError("positive scenario and draw counts required")
    return np.random.default_rng(seed).integers(0, n_scenarios, size=(n, n_scenarios))


def bootstrap_means(scenario_totals, picks):
    """Each repeated column is a separate draw, retaining its five attempts."""
    if picks.ndim != 2 or picks.shape[1] != scenario_totals.shape[1]:
        raise ValueError("draws must retain the original number of scenario clusters")
    return scenario_totals[:, picks].sum(axis=2).T / (REPS*picks.shape[1])


def rank_and_topk(quality, top_ks=TOP_KS):
    if not np.isfinite(quality).all():
        raise ValueError("ranking cannot impute unknown quality")
    lo = stats.rankdata(-quality, method="min", axis=-1)
    hi = stats.rankdata(-quality, method="max", axis=-1)
    ranks = (lo+hi)/2
    credit = {}
    for k in top_ks:
        if not 1 <= k <= quality.shape[-1]:
            raise ValueError("top-k must be within the fixed roster")
        # The boundary tie receives remaining k slots / tied deployments.
        credit[k] = np.clip((k-(lo-1))/(hi-lo+1), 0, 1)
    return ranks, credit


def selection_statistics(point_q, point_e, boot_q, boot_e, top_ks=TOP_KS):
    if (boot_q.shape != boot_e.shape or boot_q.shape[1] != len(point_q)
            or len(point_q) != len(point_e) or len(boot_q) == 0):
        raise ValueError("unaligned quality and energy resamples")
    if not all(np.isfinite(a).all() for a in [point_q, point_e, boot_q, boot_e]):
        raise ValueError("unknown selection axes")
    if (point_e < 0).any() or (boot_e < 0).any():
        raise ValueError("negative measured energy")
    ranks, credit = rank_and_topk(boot_q, top_ks)
    point_ranks, point_credit = rank_and_topk(point_q, top_ks)
    point_front = pareto_mask(point_q, point_e)
    front = np.stack([pareto_mask(q, e) for q, e in zip(boot_q, boot_e)])
    table = pd.DataFrame({
        "point_quality": point_q, "point_wh_per_attempt": point_e, "point_rank": point_ranks,
        "rank_mean": ranks.mean(axis=0), "rank_median": np.median(ranks, axis=0),
        "rank_q025": np.percentile(ranks, 2.5, axis=0),
        "rank_q975": np.percentile(ranks, 97.5, axis=0),
        "point_pareto": point_front, "pareto_probability": front.mean(axis=0)})
    for k in top_ks:
        if not np.allclose(credit[k].sum(axis=-1), k, rtol=0, atol=1e-12):
            raise ValueError("tie handling did not preserve exactly k selection slots")
        table[f"point_top_{k}_credit"] = point_credit[k]
        table[f"top_{k}_probability"] = credit[k].mean(axis=0)
    tau = np.array([stats.kendalltau(point_q, q).statistic for q in boot_q])
    size = front.sum(axis=1)
    jaccard = (front & point_front).sum(axis=1)/(front | point_front).sum(axis=1)
    draw_table = pd.DataFrame({"draw": np.arange(len(front)), "kendall_vs_point": tau,
                               "pareto_size": size, "pareto_jaccard_vs_point": jaccard})
    finite_tau = tau[np.isfinite(tau)]
    summary = {"point_pareto_size": int(point_front.sum()), "draws": len(front),
               "kendall_valid_draws": len(finite_tau)}
    for name, values in [("kendall", finite_tau), ("pareto_size", size),
                          ("pareto_jaccard", jaccard)]:
        summary[name+"_mean"] = float(values.mean()) if len(values) else None
        summary[name+"_q025"] = float(np.percentile(values, 2.5)) if len(values) else None
        summary[name+"_q975"] = float(np.percentile(values, 97.5)) if len(values) else None
    return table, summary, draw_table


def analyze(df, models, scenarios, n=DRAWS, seed=SEED, top_ks=TOP_KS):
    df = validate_grid(df, models, scenarios)
    picks = scenario_draws(len(scenarios), n, seed)
    shape = (len(models), len(scenarios), REPS)
    energy = df.energy_wh.to_numpy().reshape(shape).sum(axis=2)
    point_e = energy.sum(axis=1)/(len(scenarios)*REPS)
    boot_e = bootstrap_means(energy, picks)
    selections, summaries, draws = [], [], []
    for source in SOURCES:
        scores = df[source].to_numpy().reshape(shape)
        for threshold in [None, 2.5, 3., 3.5, 4.]:
            # Integer/half-integer score totals before dividing avoid false rank
            # ties/non-ties caused by summing rounded scenario means.
            values = scores if threshold is None else (scores >= threshold).astype(int)
            totals = values.sum(axis=2)
            point_q = totals.sum(axis=1)/(len(scenarios)*REPS)
            boot_q = bootstrap_means(totals, picks)
            arm = source + ("/mean" if threshold is None else f"/pass1-ge-{threshold:g}")
            table, summary, draw = selection_statistics(point_q, point_e, boot_q, boot_e, top_ks)
            table.insert(0, "model", models)
            for frame in [table, draw]:
                frame.insert(0, "arm", arm)
            table["score_source"] = source
            table["metric"] = "mean_score" if threshold is None else "pass_1"
            table["threshold"] = threshold
            table["assigned_attempts"] = len(scenarios)*REPS
            table["zero_success"] = (point_q == 0) if threshold is not None else False
            selections.append(table)
            summaries.append({"arm": arm, "score_source": source,
                              "threshold": threshold, "metric": table.metric.iloc[0],
                              "deployments": len(models), "scenarios": len(scenarios), **summary})
            draws.append(draw)
    pick_table = pd.DataFrame(picks, columns=[f"scenario_{i:02}" for i in range(len(scenarios))])
    pick_table.insert(0, "draw", np.arange(n))
    return (pd.concat(selections, ignore_index=True), pd.DataFrame(summaries),
            pd.concat(draws, ignore_index=True), pick_table)


def tier_descriptions(selection, population, top_ks=TOP_KS):
    joined = selection.merge(population[["model", "run_param_count", "integer_tier", "lock_tier"]],
                             on="model", validate="many_to_one")
    rows = []
    for system in ["integer_tier", "lock_tier"]:
        for (arm, tier), g in joined.groupby(["arm", system]):
            row = {"arm": arm, "tier_system": system, "tier": tier, "deployments": len(g),
                   "min_parameters": int(g.run_param_count.min()),
                   "max_parameters": int(g.run_param_count.max()),
                   "mean_quality_axis": float(g.point_quality.mean()),
                   "mean_wh_per_attempt": float(g.point_wh_per_attempt.mean()),
                   "mean_pareto_probability": float(g.pareto_probability.mean())}
            for k in top_ks:
                row[f"expected_top_{k}_slots"] = float(g[f"top_{k}_probability"].sum())
            rows.append(row)
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args()
    df, population, models, scenarios, inputs = load_inputs()
    args.out.mkdir(parents=True, exist_ok=False)
    selection, summary, draws, picks = analyze(df, models, scenarios)
    selection = selection.merge(population[["model", "run_param_count", "integer_tier",
                                            "lock_tier", "tier_disagrees"]],
                                on="model", validate="many_to_one")
    selection.to_csv(args.out/"selection.csv", index=False)
    summary.to_csv(args.out/"arm_summary.csv", index=False)
    draws.to_csv(args.out/"draw_summary.csv", index=False)
    picks.to_csv(args.out/"scenario_draws.csv", index=False)
    population.to_csv(args.out/"population.csv", index=False)
    tier_descriptions(selection.drop(columns=["run_param_count", "integer_tier", "lock_tier"]),
                      population).to_csv(args.out/"tier_descriptives.csv", index=False)
    code = [pathlib.Path(__file__), HERE/"test_selection_stability.py"]
    receipt = {
        "status": "computation-completed-review-pending", "claim_status": "provisional",
        "study": full_data.RUN_ID, "seed": SEED, "draws": DRAWS, "top_ks": list(TOP_KS),
        "models": models, "scenarios": scenarios, "repetitions": list(range(REPS)),
        "input_sha256": inputs,
        "code_sha256": {str(p.relative_to(REPO)): sha256(p) for p in code},
        "output_sha256": {p.name: sha256(p) for p in sorted(args.out.iterdir()) if p.is_file()},
        "python": platform.python_version(),
        "packages": {"numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__},
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "axes": "Maximize mean recorded judge score or threshold-defined per-attempt success; "
                "minimize mean measured RAPL package-0 Wh over ALL assigned attempts.",
        "ties": "Average ranks; top-k boundary credit = remaining slots / tied tags. "
                "Pareto requires at least one strictly better axis; equal points all survive.",
        "scope": "Fixed 137 deployment tags, curated 20 scenarios, five repetitions, "
                 "common scenario draws for all 15 arms. No model/weight population generalization.",
        "limits": "Resampling frequencies/ranges, not posterior superiority or confidence in "
                  "operational validity. No action-safety axis, new preregistration, "
                  "human labels, inference runs, metadata imputation or claim promotion.",
    }
    (args.out/"receipt.json").write_text(json.dumps(receipt, indent=2, allow_nan=False)+"\n")
    print(summary.to_string(index=False))
    print(f"Saved {len(selection)} deployment-arm rows; {len(draws)} arm-draw summaries; "
          f"{DRAWS} shared scenario draws to {args.out}")


if __name__ == "__main__":
    main()
