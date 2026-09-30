"""Analysis-only P1/P2 repair evidence from the provisional locked 152 study.

No inferred weight identities, human validity claims, or historical output writes.
Run: deep-dive/.venv/bin/python deep-dive/phase4_repairs.py --out <new-directory>
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import pathlib
import platform
import subprocess

import numpy as np
import pandas as pd
from scipy import stats

import full_data

HERE = pathlib.Path(__file__).resolve().parent
ACTION_SAFETY = {"must_exclude", "must_not_endorse", "must_exclude_action"}
RECALL = {"any_include", "must_include", "all_include"}
SEED = 20260725


def _rows():
    with gzip.open(full_data.LOCKED / "canonical/results.jsonl.gz", "rt") as fh:
        for line in fh:
            yield json.loads(line)  # malformed evidence must fail, never be skipped


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def verify_inputs():
    """Hash-check locked canonical inputs; no .tmp or legacy94 fallback in this run."""
    path = full_data.REPO / "data" / f"analysis-manifest.{full_data.RUN_ID}.json"
    manifest = json.loads(path.read_text())
    if (manifest["bundle_id"] != full_data._BUNDLE_ID or manifest["source_id"] != full_data.RUN_ID
            or manifest["bundle_state"] != "locked" or manifest["gate_passed"] is not True
            or manifest.get("evaluation_policy") != full_data.EVALUATION_POLICY
            or set(manifest.get("judges", [])) != full_data.EXPECTED_JUDGES):
        raise ValueError("unexpected study identity")
    hashes = {str(path.relative_to(full_data.REPO)): sha256(path)}
    for name, expected in manifest["source_sha256"].items():
        p = (full_data.LOCKED if name.startswith("canonical/") else full_data.REPO) / name
        actual = sha256(p)
        if actual != expected:
            raise ValueError(f"source hash mismatch: {name}")
        hashes[str(p.relative_to(full_data.REPO))] = actual
    for name in ["data/models.lock.jsonl", "data/model_metadata.csv", "data/models-inventory.csv",
                 "data/models.ollama-chat-faults.json", "data/models.ollama-chat-ok.txt",
                 "data/scenario_sets/core-current.json",
                 f"data/snapshots/{full_data.RUN_ID}.model-params.csv"]:
        hashes[name] = sha256(full_data.REPO / name)
    return hashes


def _cluster_boot(df, stat_fn, n=4000, seed=SEED):
    """Scenario draws retain multiplicity even when stat_fn groups by scenario."""
    rng = np.random.default_rng(seed)
    scen = df["scenario"].unique()
    by = {s: g for s, g in df.groupby("scenario")}
    out = []
    for _ in range(n):
        pick = rng.choice(scen, size=len(scen), replace=True)
        sampled = pd.concat([by[s].assign(source_scenario=s, scenario=i)
                             for i, s in enumerate(pick)], ignore_index=True)
        out.append(stat_fn(sampled))
    finite = np.asarray(out)[np.isfinite(out)]
    if not len(finite):
        raise ValueError("no finite bootstrap estimates")
    return np.percentile(finite, [2.5, 97.5])


def reliability_cells(df, threshold):
    if not np.isfinite(df.judge_score).all():
        raise ValueError("missing/nonfinite judgment is evaluation missingness")
    if df.duplicated(["model", "scenario", "rep"]).any():
        raise ValueError("duplicate repetition")
    c = df.assign(success=df.judge_score.ge(threshold)).groupby(["model", "scenario"]).agg(
        mean_score=("judge_score", "mean"), pass_1=("success", "mean"),
        all_5=("success", "all"), n=("rep", "size"))
    if not c.n.eq(5).all():
        raise ValueError("all-five reliability requires exactly five observed repetitions")
    c["mean_good"] = c.mean_score.ge(threshold)
    return c


def reliability(df, threshold):
    c = reliability_cells(df, threshold)
    return {k: float(c[k].mean()) for k in ["mean_good", "pass_1", "all_5"]}


def energy_table(df, threshold):
    d = df.assign(good=df.judge_score.ge(threshold),
                  energy_valid=np.isfinite(df.energy_wh) & df.energy_wh.ge(0),
                  score_valid=np.isfinite(df.judge_score))
    g = d.groupby("model")
    t = g.agg(assigned=("good", "size"), usable=("good", "sum"),
              measured_energy_wh=("energy_wh", "sum"), energy_n=("energy_valid", "sum"),
              score_n=("score_valid", "sum"))
    t["missing_energy"] = t.assigned - t.energy_n
    t["missing_score"] = t.assigned - t.score_n
    t["total_energy_wh"] = t.measured_energy_wh.where(t.missing_energy.eq(0))
    t["wh_per_attempt"] = t.total_energy_wh / t.assigned
    complete = t.missing_energy.eq(0) & t.missing_score.eq(0)
    t["wh_per_usable"] = (t.total_energy_wh / t.usable.where(t.usable.gt(0))).where(complete)
    t.loc[complete & t.usable.eq(0), "wh_per_usable"] = np.inf
    t["cost_status"] = np.select(
        [~complete, t.usable.eq(0)], ["missing_evidence", "zero_success"], default="finite")
    return t.reset_index()


def energy_correlation(t):
    finite = t[np.isfinite(t.wh_per_attempt) & np.isfinite(t.wh_per_usable)]
    rho = stats.spearmanr(finite.wh_per_attempt, finite.wh_per_usable).statistic if len(finite) >= 3 else np.nan
    return float(rho), len(finite)


def judge_agreement(jud):
    """Paired recorded ordinal scores; agreement describes an instrument, not validity."""
    from sklearn.metrics import cohen_kappa_score
    piv = jud.pivot(index=full_data._CELL, columns="judge_model", values="score")
    if piv.shape[1] != 2 or piv.isna().any().any():
        raise ValueError("agreement requires exactly two observed judgments per cell")
    if not ((piv >= 1) & (piv <= 5) & (piv % 1 == 0)).all().all():
        raise ValueError("quadratic kappa requires the recorded integer ordinal scores")
    a, b = piv.columns
    return {"judge_a": a, "judge_b": b, "n": len(piv),
            "exact_agreement": float(piv[a].eq(piv[b]).mean()),
            "within_one": float((piv[a]-piv[b]).abs().le(1).mean()),
            "pearson": float(piv[a].corr(piv[b])),
            "quadratic_kappa": float(cohen_kappa_score(piv[a], piv[b], weights="quadratic")),
            "mean_a": float(piv[a].mean()), "mean_b": float(piv[b].mean()),
            "scope": "descriptive fixed-corpus agreement, not accuracy or human validity"}


def roster_screen(full):
    screen = json.loads((full_data.REPO / "data/models.ollama-chat-faults.json").read_text())
    ok = {line.strip() for line in (full_data.REPO / screen["ok_roster"]).read_text().splitlines()
          if line.strip() and not line.startswith("#")}
    if ok != set(full.model):
        raise ValueError("selected canary roster differs from locked study")
    cols = ["model", "overall_status", "overall_reason", "chat_status", "chat_output_chars",
            "generate_status", "generate_output_chars"]
    rejected = pd.DataFrame(screen["excluded_models"])[cols]
    rejected["in_study"] = False
    selected = pd.DataFrame({"model": sorted(ok), "overall_status": "ok", "in_study": True})
    return pd.concat([selected, rejected], ignore_index=True)


def sensitivity(df, score_label, n=4000):
    """Paired scenario resampling, fixed deployments; vectorized sufficient statistics.

    Selecting columns with replacement preserves each draw, exactly as _cluster_boot.
    No model-population or lineage generalization is claimed.
    """
    rng = np.random.default_rng(SEED)
    scenarios = sorted(df.scenario.unique())
    picks = rng.integers(0, len(scenarios), size=(n, len(scenarios)))
    rows, costs = [], []
    for th in [2.5, 3., 3.5, 4.]:
        c = reliability_cells(df, th)
        per_s = c.groupby("scenario")[["mean_good", "pass_1", "all_5"]].mean().reindex(scenarios)
        # Require the full rectangular fixed-roster design for equal scenario weighting.
        if c.shape[0] != df.model.nunique() * len(scenarios):
            raise ValueError("sensitivity requires complete deployment x scenario grid")
        point = reliability(df, th)
        sampled = per_s.to_numpy()[picks].mean(axis=1)
        row = {"score": score_label, "threshold": th, "deployments": df.model.nunique(),
               "cells": len(df), "model_scenarios": len(c), "bootstrap_draws": n, **point}
        for name, values, pt in [
            ("mean_good", sampled[:, 0], point["mean_good"]),
            ("pass_1", sampled[:, 1], point["pass_1"]),
            ("all_5", sampled[:, 2], point["all_5"]),
            ("descriptive_gap_pp", 100*(sampled[:, 0]-sampled[:, 2]),
             100*(point["mean_good"]-point["all_5"])),
            ("reliability_gap_pp", 100*(sampled[:, 1]-sampled[:, 2]),
             100*(point["pass_1"]-point["all_5"]))]:
            row[name] = pt
            row[name+"_lo"], row[name+"_hi"] = np.percentile(values, [2.5, 97.5])
        t = energy_table(df, th)
        t.insert(0, "threshold", th)
        t.insert(0, "score", score_label)
        costs.append(t)
        row["energy_rho"], row["energy_finite_n"] = energy_correlation(t)
        row["zero_success_n"] = int(t.cost_status.eq("zero_success").sum())
        row["missing_energy_cells"] = int(t.missing_energy.sum())
        g = df.assign(good=df.judge_score.ge(th)).groupby(["model", "scenario"])
        energy = g.energy_wh.sum().unstack().reindex(columns=scenarios).to_numpy()
        good = g.good.sum().unstack().reindex(columns=scenarios).to_numpy()
        boot_rho, boot_n = [], []
        # Small model x scenario matrices; no row regrouping can collapse a draw.
        for pick in picks:
            en, successes = energy[:, pick].sum(axis=1), good[:, pick].sum(axis=1)
            valid = successes > 0
            boot_n.append(int(valid.sum()))
            boot_rho.append(stats.spearmanr(en[valid]/(5*len(pick)),
                                           en[valid]/successes[valid]).statistic
                            if valid.sum() >= 3 else np.nan)
        finite = np.asarray(boot_rho)[np.isfinite(boot_rho)]
        if len(finite) == 0 or row["missing_energy_cells"]:
            raise ValueError("energy bootstrap requires complete energy and finite draws")
        row["energy_rho_lo"], row["energy_rho_hi"] = np.percentile(finite, [2.5, 97.5])
        row["energy_bootstrap_finite_draws"] = len(finite)
        row["energy_bootstrap_n_min"], row["energy_bootstrap_n_max"] = min(boot_n), max(boot_n)
        rows.append(row)
    return pd.DataFrame(rows), pd.concat(costs, ignore_index=True)


def raw_audit(full):
    identities, checks = {}, []
    for r in _rows():
        model = r["model"]
        condition = r.get("analysis_condition_key_sha256")
        if (not isinstance(condition, str) or len(condition) != 64
                or any(c not in "0123456789abcdef" for c in condition)
                or r.get("condition_identity_incomplete") is not False
                or r.get("evaluation_policy") != full_data.EVALUATION_POLICY):
            raise ValueError(f"incomplete condition identity or unexpected policy: {model}")
        identity = (r.get("ollama.digest"), r.get("ollama.parameter_count"),
                    r.get("ollama.quantization"), condition)
        if model in identities and identities[model] != identity:
            raise ValueError(f"changing artifact identity: {model}")
        identities[model] = identity
        det = r.get("det_detail") or []
        a = [x["pass"] for x in det if x.get("type") in ACTION_SAFETY]
        recall = [x["pass"] for x in det if x.get("type") in RECALL]
        if any(type(x) is not bool for x in a + recall):
            raise ValueError("check pass is not a boolean")
        checks.append({"model": model, "scenario": r["scenario"], "rep": r["rep"],
                       "action_safety": np.mean(a) if a else np.nan,
                       "content_recall": np.mean(recall) if recall else np.nan,
                       "action_checks": len(a), "output_chars": r.get("gen_ai.usage.output_chars"),
                       "think_requested": r.get("think"),
                       "thinking_chars": r.get("gen_ai.thinking.chars")})
    idf = pd.DataFrame([{"model": m, "artifact_digest": v[0], "run_param_count": v[1],
                         "run_quantization": v[2], "analysis_condition_key_sha256": v[3],
                         "evaluation_policy": full_data.EVALUATION_POLICY, "weight_lineage": None,
                         "lineage_status": "unverified"}
                        for m, v in sorted(identities.items())])
    if set(idf.model) != set(full.model):
        raise ValueError("identity audit differs from run roster")
    counts = idf.set_index("model").run_param_count
    portable = full_data._run_param_counts().reindex(counts.index)
    if not np.array_equal(counts.to_numpy(), (portable * 1e9).round().to_numpy()):
        raise ValueError("canonical integer counts disagree with portable parameter snapshot")
    check = pd.DataFrame(checks)
    check = check.merge(full[full_data._CELL + ["is_safety", "judge_score"]],
                        on=full_data._CELL, validate="one_to_one")
    return idf, check


def verify_judge_conditions(identities):
    """Prove raw judgments refer to the same one-condition-per-tag result map."""
    expected = identities.set_index("model").analysis_condition_key_sha256.to_dict()
    count = 0
    with gzip.open(full_data.LOCKED/"canonical/judged.jsonl.gz", "rt") as fh:
        for line in fh:
            row = json.loads(line)
            if (row["model"] not in expected
                    or row.get("analysis_condition_key_sha256") != expected[row["model"]]):
                raise ValueError("judgment condition differs from its deployment result condition")
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--bootstrap", type=int, default=4000)
    args = parser.parse_args()
    if args.bootstrap < 100:
        parser.error("at least 100 bootstrap draws required")
    hashes = verify_inputs()
    # New directory only. Failed attempts are preserved, never overwritten.
    args.out.mkdir(parents=True, exist_ok=False)
    full = full_data.load_full()
    if (len(full), full.model.nunique(), full.scenario.nunique(), full.rep.nunique()) != (15200, 152, 20, 5):
        raise ValueError("unexpected locked study grid")
    eligibility = full_data.eligibility_table(full)
    d = full_data.primary_frame(full)
    ids, checks = raw_audit(full)
    condition_matched_judgments = verify_judge_conditions(ids)
    lock = pd.read_json(full_data.REPO / "data/models.lock.jsonl", lines=True)
    lock_identity = lock[["model_id", "ollama_digest"]].rename(
        columns={"model_id": "model", "ollama_digest": "lock_ollama_digest"})
    ids = ids.merge(lock_identity, on="model", how="left", validate="one_to_one")
    ids["lock_digest_status"] = np.select(
        [ids.lock_ollama_digest.isna(), ids.lock_ollama_digest.eq(ids.artifact_digest)],
        ["missing", "matches_run_artifact"], default="disagrees_with_run_artifact")
    eligibility.to_csv(args.out / "eligibility.csv", index=False)
    ids.to_csv(args.out / "identity.csv", index=False)
    checks.to_csv(args.out / "check_cells.csv", index=False)
    roster_screen(full).to_csv(args.out / "candidate_screen.csv", index=False)
    # Check-defined construct audit on the eligible roster; no applicable check stays missing.
    primary_checks = checks[checks.model.isin(d.model)]
    saf = primary_checks[primary_checks.is_safety & primary_checks.action_checks.gt(0)]
    action = saf.groupby("model")[["action_safety", "content_recall"]].mean()
    action["quality"] = d.groupby("model").judge_score.mean()
    action.to_csv(args.out / "action_safety_primary.csv")
    empty = saf[saf.output_chars.eq(0)]
    responsive = saf[saf.output_chars.gt(0)]
    check_summary = {"primary_safety_cells": len(primary_checks[primary_checks.is_safety]),
                     "cells_with_action_checks": len(saf), "empty_cells": len(empty),
                     "empty_mean_action_check_score": float(empty.action_safety.mean()),
                     "empty_all_action_checks_pass_rate": float(empty.action_safety.eq(1).mean()),
                     "responsive_cells": len(responsive),
                     "responsive_mean_action_check_score": float(responsive.action_safety.mean()),
                     "action_recall_pearson": float(action.action_safety.corr(action.content_recall)),
                     "action_quality_pearson": float(action.action_safety.corr(action.quality)),
                     "recall_quality_pearson": float(action.content_recall.corr(action.quality)),
                     "n_complete_deployments": int(action.dropna().shape[0]),
                     "scope": "check-defined descriptions; not validated operational safety"}
    (args.out / "check_summary.json").write_text(json.dumps(check_summary, indent=2)+"\n")
    full_data.model_table_full(d).to_csv(args.out / "primary_model_table.csv", index=False)
    metadata = full.drop_duplicates("model")[[
        "model", "param_count", "curated_param_count", "params_b", "curated_params_b",
        "arch_class", "training_regime", "thinking_capable", "is_reasoning",
        "reasoning_name_hint", "tools_capable", "is_moe"]]
    metadata = metadata.merge(lock[["model_id", "training_type", "architecture"]].rename(
        columns={"model_id": "model", "training_type": "lock_training_type",
                 "architecture": "lock_architecture"}), on="model", how="left", validate="one_to_one")
    # No fill/merge of conflicting provenance sources: inherited annotations are
    # not a verified replacement for model-lock training/architecture fields.
    metadata.to_csv(args.out / "metadata_audit.csv", index=False)
    summaries, costs = [], []
    summary, cost = sensitivity(d, "consensus", args.bootstrap)
    summaries.append(summary)
    costs.append(cost)
    jud = full_data._load_judged()
    agreement = judge_agreement(jud[jud.model.isin(d.model)])
    (args.out / "judge_agreement.json").write_text(json.dumps(agreement, indent=2)+"\n")
    for label, g in jud.groupby("judge_model"):
        per_judge = d.drop(columns="judge_score").merge(
            g[full_data._CELL+["score"]], on=full_data._CELL, validate="one_to_one").rename(
                columns={"score": "judge_score"})
        summary, cost = sensitivity(per_judge, label, args.bootstrap)
        summaries.append(summary)
        costs.append(cost)
    summary = pd.concat(summaries, ignore_index=True)
    summary.to_csv(args.out / "sensitivity.csv", index=False)
    pd.concat(costs, ignore_index=True).to_csv(args.out / "energy_deployments.csv", index=False)
    # B3 audited subsets, never a fabricated coefficient/cross-check.
    import b3_mixedeffects as b3
    b3.population_audit(full).to_csv(args.out / "b3_population_all152.csv", index=False)
    b3.population_audit(d).to_csv(args.out / "b3_population_primary.csv", index=False)
    for p in [HERE / name for name in ["phase4_repairs.py", "full_data.py",
                                       "b3_mixedeffects.py", "test_analysis_repairs.py"]]:
        hashes[str(p.relative_to(full_data.REPO))] = sha256(p)
    receipt = {
        "run_id": full_data.RUN_ID, "claim_status": "provisional", "seed": SEED,
        "bootstrap_draws": args.bootstrap, "python": platform.python_version(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "source_sha256": hashes, "output_sha256": {
            p.name: sha256(p) for p in sorted(args.out.iterdir()) if p.is_file()},
        "primary_models": int(d.model.nunique()), "primary_cells": len(d),
        "numeric_le5b_models": int(eligibility.integer_le5b.sum()),
        "membership_discrepancies": int(eligibility.membership_discrepancy.sum()),
        "tier_discrepancies": int(eligibility.tier_discrepancy.sum()),
        "artifact_digests": int(ids.artifact_digest.nunique()),
        "verified_weight_lineages": 0,
        "evaluation_policy": full_data.EVALUATION_POLICY,
        "canonical_conditions": int(ids.analysis_condition_key_sha256.nunique()),
        "condition_matched_judgments": condition_matched_judgments,
        "interpretation": "Machine-calculation-only, fixed roster and curated scenarios; "
                          "threshold unvalidated. No independent lineage, human validity, "
                          "hardware generalization or claim promotion.",
    }
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2)+"\n")
    print(summary.to_string(index=False))
    print(json.dumps({k: v for k, v in receipt.items() if "sha256" not in k}, indent=2))


if __name__ == "__main__":
    main()
