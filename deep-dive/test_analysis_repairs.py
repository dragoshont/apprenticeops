"""Focused deterministic regressions; run with deep-dive/.venv/bin/python."""
import contextlib
import io
import json
import pathlib
import tempfile
import types
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

import full_data
import phase4_repairs as repairs
import b3_mixedeffects as b3


def cells():
    return pd.DataFrame([
        ("m", s, r, score, 1.0)
        for s, scores in [("a", [1, 1, 1, 1, 1]), ("b", [2, 3, 3, 3, 4])]
        for r, score in enumerate(scores, 1)
    ], columns=["model", "scenario", "rep", "judge_score", "energy_wh"])


def load_scenario_fixture(scenario, class_map):
    res = pd.DataFrame([{
        "model": "a", "scenario": scenario, "rep": 0, "det_score": 1.,
        "energy_wh": 1., "mean_watts": 1., "decode_tokens_per_s": 1.,
        "wall_s": 1., "output_tokens": 1, "finish_reason": "stop",
        "no_turbo": 1, "power_source": "rapl:package-0"}])
    jud = pd.DataFrame([{"model": "a", "scenario": scenario, "rep": 0,
                         "judge_model": name, "score": 3.}
                        for name in ["claude-opus-4.6", "gpt-5.4"]])
    with patch.object(full_data, "_load_results", return_value=res), patch.object(
            full_data, "_load_judged", return_value=jud), patch.object(
            full_data, "_scenario_class_map", return_value=class_map), patch.object(
            full_data, "_join_metadata", side_effect=lambda d: d.assign(params_b=1., size_gb=1.)):
        return full_data.load_full()


class Repairs(unittest.TestCase):
    def test_two_wrong_named_judges_do_not_satisfy_policy(self):
        res = pd.DataFrame([("a", "s", 0)], columns=full_data._CELL)
        jud = pd.DataFrame([("a", "s", 0, name, 3.) for name in ["other-a", "other-b"]],
                           columns=full_data._CELL+["judge_model", "score"])
        cons = jud.groupby(full_data._CELL).score.mean().rename("judge_score").reset_index()
        with self.assertRaisesRegex(AssertionError, "policy"):
            full_data._assert_join_integrity(res, jud, cons)

    def test_raw_judges_require_named_backend_and_policy(self):
        row = {"model": "a", "scenario": "s", "rep": 0, "score": 3.,
               "judge_model": "claude-opus-4.6", "judge_backend": "copilot",
               "evaluation_policy": "deterministic-checks-v1|judges:copilot:claude-opus-4.6+copilot:gpt-5.4"}
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td)/"judged.jsonl"
            for field, bad in [("judge_backend", "other"), ("evaluation_policy", None)]:
                path.write_text(json.dumps({**row, field: bad})+"\n")
                with patch.object(full_data, "_source", return_value=([], path)), self.assertRaisesRegex(
                        ValueError, "policy"):
                    full_data._load_judged()

    def test_raw_condition_identity_cannot_be_collapsed(self):
        row = {"model": "a", "scenario": "s", "rep": 0, "det_detail": [],
               "ollama.digest": "digest", "ollama.parameter_count": 1_000_000_000,
               "ollama.quantization": "Q4_0", "analysis_condition_key_sha256": "a"*64,
               "condition_identity_incomplete": False,
               "evaluation_policy": "deterministic-checks-v1|judges:copilot:claude-opus-4.6+copilot:gpt-5.4"}
        df = pd.DataFrame({"model": ["a", "a"], "scenario": ["s", "s"], "rep": [0, 1],
                           "is_safety": [False, False], "judge_score": [3., 3.]})
        for second in [{**row, "analysis_condition_key_sha256": "b"*64},
                       {**row, "evaluation_policy": "unknown"},
                       {**row, "analysis_condition_key_sha256": None}]:
            second["rep"] = 1
            with patch.object(repairs, "_rows", return_value=iter([row, second])), patch.object(
                    full_data, "_run_param_counts", return_value=pd.Series({"a": 1.})), self.assertRaises(ValueError):
                repairs.raw_audit(df)

    def test_judgment_condition_must_match_result_condition(self):
        identities = pd.DataFrame({"model": ["a"], "analysis_condition_key_sha256": ["a"*64]})
        for model, key in [("a", "b"*64), ("other", "a"*64)]:
            stream = io.StringIO(json.dumps({"model": model, "analysis_condition_key_sha256": key})+"\n")
            with patch.object(repairs.gzip, "open", return_value=stream), self.assertRaisesRegex(
                    ValueError, "condition"):
                repairs.verify_judge_conditions(identities)
        stream = io.StringIO(json.dumps({"model": "a", "analysis_condition_key_sha256": "a"*64})+"\n")
        with patch.object(repairs.gzip, "open", return_value=stream):
            self.assertEqual(repairs.verify_judge_conditions(identities), 1)

    def test_unknown_or_invalid_scenario_class_fails_closed(self):
        scenario = "guard-looks-valid-but-is-unmapped"
        for mapping in [{}, {scenario: None}, {scenario: ""}, {scenario: 42}]:
            with self.subTest(mapping=mapping), self.assertRaisesRegex(ValueError, "authoritative"):
                load_scenario_fixture(scenario, mapping)

    def test_authoritative_scenario_class_outranks_prefix(self):
        d = load_scenario_fixture("guard-misleading-prefix", {"guard-misleading-prefix": "test"})
        self.assertEqual(d.scenario_class.iloc[0], "test")
        self.assertFalse(d.is_safety.iloc[0])

    def test_category_field_cannot_replace_authoritative_class(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            p = root / "data/scenario_sets/core-current.json"
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps([{"id": "guard-unknown", "category": "guard"}]))
            with patch.object(full_data, "REPO", root):
                self.assertIsNone(full_data._scenario_class_map()["guard-unknown"])

    def test_a2_unvalidated_safety_axis_is_explicit(self):
        import a2_efficiency
        # Use the existing full-run adapter shape, without reading any study data.
        mt = pd.DataFrame({
            "model": ["a", "b", "c"], "quality": [2., 3., 4.], "safety": [2.5, 3., 3.5],
            "size_gb": [1., 2., 4.], "params_b": [1., 2., 4.], "wall_s": [1., 2., 3.],
            "energy_wh_controlled": [1., 2., 3.],
            "quality_per_gb": [2., 1.5, 1.], "quality_per_sec": [2., 1.5, 4/3],
            "quality_per_wh_controlled": [2., 1.5, 4/3]})
        with tempfile.TemporaryDirectory() as td, patch.object(
                a2_efficiency, "load_runs", return_value=pd.DataFrame()), patch.object(
                a2_efficiency, "model_table", return_value=mt), patch.object(
                a2_efficiency, "FIG", pathlib.Path(td)), contextlib.redirect_stdout(io.StringIO()) as out:
            a2_efficiency.main()
        text = out.getvalue()
        self.assertIn("unvalidated safety-scenario judge score", text)
        self.assertIn("safety_scenario_judge_score_unvalidated", text)
        self.assertNotIn("safety up", text)
        a2_efficiency.plt.close("all")

    def test_bootstrap_keeps_duplicate_cluster_draws(self):
        df = cells()
        fake = types.SimpleNamespace(choice=lambda *a, **kw: np.array(["a", "a", "b"]))
        def regroup(d):
            return d.groupby(["model", "scenario"]).judge_score.mean().mean()
        with patch.object(repairs.np.random, "default_rng", return_value=fake):
            np.testing.assert_allclose(repairs._cluster_boot(df, regroup, n=2),
                                       [5 / 3, 5 / 3])

    def test_mean_threshold_is_not_pass_one(self):
        r = repairs.reliability(cells(), 3)
        self.assertEqual(r["mean_good"], .5)
        self.assertEqual(r["pass_1"], .4)
        self.assertEqual(r["all_5"], 0)

    def test_reliability_missing_or_duplicate_repeats_fail(self):
        for bad in (cells().iloc[:-1], pd.concat([cells(), cells().iloc[[0]]])):
            with self.assertRaises(ValueError):
                repairs.reliability(bad, 3)
        bad = cells()
        bad.loc[0, "judge_score"] = np.nan
        with self.assertRaises(ValueError):
            repairs.reliability(bad, 3)

    def test_energy_includes_failed_attempts_and_zero_success(self):
        d = pd.DataFrame({"model": ["a", "a", "b", "b"], "judge_score": [4, 1, 1, 1],
                          "energy_wh": [2., 8., 4., 6.]})
        t = repairs.energy_table(d, 3).set_index("model")
        self.assertEqual(t.loc["a", "wh_per_usable"], 10)
        self.assertTrue(np.isinf(t.loc["b", "wh_per_usable"]))
        self.assertEqual(t.loc["b", "cost_status"], "zero_success")
        self.assertEqual(len(t), 2)

    def test_missing_energy_or_judgment_does_not_become_zero(self):
        d = pd.DataFrame({"model": ["a", "a"], "judge_score": [4, 1],
                          "energy_wh": [2., np.nan]})
        t = repairs.energy_table(d, 3).iloc[0]
        self.assertTrue(np.isnan(t.wh_per_usable))
        self.assertEqual(t.missing_energy, 1)
        d["energy_wh"] = [2., 8.]
        d.loc[0, "judge_score"] = np.nan
        self.assertTrue(np.isnan(repairs.energy_table(d, 3).iloc[0].wh_per_usable))

    def test_integer_parameters_override_curated_and_names_never_fill(self):
        md = pd.DataFrame({"model": ["m:4b", "unknown:5b"], "params_b": [9., .5],
                           "training_regime": [None, None]})
        with patch.object(full_data, "_metadata", return_value=md), patch.object(
                full_data, "_run_param_counts", return_value=pd.Series({"m:4b": 4.})):
            d = full_data._join_metadata(pd.DataFrame({"model": md.model}))
        self.assertEqual(d.params_b.iloc[0], 4)
        self.assertEqual(d.param_count.iloc[0], 4_000_000_000)
        self.assertTrue(pd.isna(d.params_b.iloc[1]))
        self.assertTrue(pd.isna(d.param_count.iloc[1]))
        self.assertTrue(d.is_reasoning.isna().all())

    def test_roster_not_safety_complete_cases(self):
        d = pd.DataFrame({"model": ["a", "b", "c", "d", "e"],
                          "params_b": [5., 1., 5.000000001, 2., np.nan],
                          "is_safety": [False] * 5, "judge_score": [np.nan] * 5})
        lock = pd.DataFrame({"model_id": ["a", "b", "c", "d", "e"],
                             "included": [True, True, True, False, True],
                             "tier": ["T5", "T1", "T5", "T2", "T1"],
                             "params_b": [5, 1, 5, 2, 1]})
        t = full_data.eligibility_table(d, lock).set_index("model")
        self.assertEqual(set(t[t.eligible].index), {"a", "b"})
        self.assertTrue(t.loc["c", "membership_discrepancy"])
        self.assertTrue(t.loc["d", "membership_discrepancy"])

    def test_unknown_boolean_and_quantization_preserved(self):
        d = pd.DataFrame({"model": ["a", "b", "c"], "scenario": ["s"] * 3,
                          "judge_score": [3.] * 3, "params_b": [1.] * 3,
                          "tools_capable": [True, None, False], "is_moe": [False] * 3,
                          "thinking_capable": [None] * 3,
                          "training_regime": ["instruct"] * 3,
                          "quant": ["Q4_K_M", "Q8_0", None]})
        prepared = b3.prepare(d)
        self.assertTrue(pd.isna(prepared.tools.iloc[1]))
        self.assertTrue(pd.isna(prepared.quant_grp.iloc[2]))
        fitted = b3.complete_cases(prepared)
        self.assertEqual(list(fitted.model), ["a"])

    def test_b3_unverified_lineage_excludes_inference(self):
        d = pd.DataFrame({"model": ["a"], "scenario": ["s"], "judge_score": [3.],
                          "params_b": [1.], "tools_capable": [True], "is_moe": [False],
                          "thinking_capable": [False], "training_regime": ["instruct"],
                          "quant": ["Q4_K_M"]})
        with patch.object(b3, "load_runs", return_value=d), contextlib.redirect_stdout(io.StringIO()) as out:
            b3.main()
        self.assertIn("NOT IDENTIFIABLE", out.getvalue())
        self.assertIn("1 deployments", out.getvalue())

    def test_batch_failure_raises_and_restores_output_hooks(self):
        import full_ab
        orig = pd.DataFrame.to_csv
        fake = types.SimpleNamespace(main=lambda: (_ for _ in ()).throw(RuntimeError("fixture failure")))
        with tempfile.TemporaryDirectory() as td, patch.object(full_ab, "OUT", pathlib.Path(td)), patch.object(
                full_data, "load_full", return_value=pd.DataFrame({"model": ["a"]})):
            with self.assertRaises(RuntimeError):
                full_ab.run_one("broken", fake, False)
            self.assertIn("fixture failure", (pathlib.Path(td) / "broken.txt").read_text())
        self.assertIs(pd.DataFrame.to_csv, orig)

    def test_friedman_treatments_are_models(self):
        import a1_ranking
        from scipy import stats
        matrix = pd.DataFrame([[1, 2, 3, 4], [4, 3, 4, 5], [2, 4, 5, 3]])
        actual = a1_ranking.friedman_models(matrix)
        expected = stats.friedmanchisquare(*matrix.to_numpy())
        self.assertEqual(actual, expected)

    def test_pareto_requires_strict_dominance_not_equal_cost(self):
        import a2_efficiency
        q = np.array([4., 3., 4., 2.])
        cost = np.array([1., 1., 1., .5])
        np.testing.assert_array_equal(a2_efficiency.pareto_mask(q, cost),
                                      [True, False, True, True])

    def test_vectorized_sensitivity_matches_cluster_draw_multiplicity(self):
        df = pd.concat([cells().assign(model=m, energy_wh=float(i+1))
                        for i, m in enumerate(["a", "b", "c"])], ignore_index=True)
        # Avoid constant cost ranks, while keeping all three models observed.
        df.loc[(df.model == "b") & (df.scenario == "a"), "judge_score"] = 5.
        df.loc[(df.model == "c") & (df.rep == 1), "judge_score"] = 5.
        fake = types.SimpleNamespace(integers=lambda *a, **k: np.array([[0, 0], [0, 1], [1, 1]]))
        with patch.object(repairs.np.random, "default_rng", return_value=fake):
            summary, _ = repairs.sensitivity(df, "fixture", n=3)
        point = summary[summary.threshold.eq(3)].iloc[0]
        c = repairs.reliability_cells(df, 3)
        s = c.groupby("scenario")[["pass_1", "all_5"]].mean()
        gap = 100*(s.pass_1-s.all_5).to_numpy()
        expected = np.percentile([gap[0], gap.mean(), gap[1]], [2.5, 97.5])
        np.testing.assert_allclose([point.reliability_gap_pp_lo, point.reliability_gap_pp_hi], expected)

    def test_digest_does_not_verify_weight_lineage(self):
        row = {"model": "a", "scenario": "s", "rep": 0,
               "ollama.digest": "digest", "ollama.parameter_count": 1_000_000_000,
               "ollama.quantization": "Q4_0", "det_detail": [],
               "analysis_condition_key_sha256": "a"*64, "condition_identity_incomplete": False,
               "evaluation_policy": "deterministic-checks-v1|judges:copilot:claude-opus-4.6+copilot:gpt-5.4"}
        df = pd.DataFrame({"model": ["a"], "scenario": ["s"], "rep": [0],
                           "is_safety": [False], "judge_score": [3.]})
        with patch.object(repairs, "_rows", return_value=iter([row])), patch.object(
                full_data, "_run_param_counts", return_value=pd.Series({"a": 1.})):
            identities, _ = repairs.raw_audit(df)
        self.assertTrue(identities.weight_lineage.isna().all())
        self.assertEqual(identities.lineage_status.iloc[0], "unverified")

    def test_run_integer_snapshot_rejects_fractional_or_duplicate_counts(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            dest = root / "data/snapshots"
            dest.mkdir(parents=True)
            path = dest / f"{full_data.RUN_ID}.model-params.csv"
            with patch.object(full_data, "REPO", root):
                for frame in [pd.DataFrame({"model": ["a"], "param_count": [2.5]}),
                              pd.DataFrame({"model": ["a", "a"], "param_count": [10, 10]})]:
                    frame.to_csv(path, index=False)
                    with self.assertRaises(ValueError):
                        full_data._run_param_counts()

    def test_judge_agreement_is_exact_and_missing_pair_fails(self):
        j = pd.DataFrame([("a", "s", rep, judge, score)
                          for rep, score in enumerate([1, 2, 5])
                          for judge in ["a", "b"]],
                         columns=full_data._CELL + ["judge_model", "score"])
        r = repairs.judge_agreement(j)
        self.assertEqual(r["n"], 3)
        self.assertEqual(r["quadratic_kappa"], 1)
        with self.assertRaises(ValueError):
            repairs.judge_agreement(j.iloc[:-1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
