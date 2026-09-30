"""New-file-only selection-stability tests; use the existing deep-dive interpreter."""
import pathlib
import tempfile
import unittest

import numpy as np
import pandas as pd

import selection_stability as ss


MODELS = ["a", "b", "c"]
SCENARIOS = ["s0", "s1"]


def fixture():
    rows = []
    for i, model in enumerate(MODELS):
        for s, scenario in enumerate(SCENARIOS):
            for rep in range(5):
                a = i + 1 + s
                b = i + 1 + rep % 2
                rows.append({"model": model, "scenario": scenario, "rep": rep,
                             "energy_wh": .5 + i + .1*s + .01*rep,
                             "consensus": (a+b)/2,
                             "claude-opus-4.6": a, "gpt-5.4": b})
    return pd.DataFrame(rows)


class SelectionStabilityTests(unittest.TestCase):
    def test_midrank_and_fractional_boundary_ties(self):
        ranks, credit = ss.rank_and_topk(np.array([4., 3., 3., 1.]), (1, 2))
        np.testing.assert_array_equal(ranks, [1, 2.5, 2.5, 4])
        np.testing.assert_allclose(credit[2], [1, .5, .5, 0])
        self.assertEqual(credit[2].sum(), 2)

    def test_all_ties_have_no_tag_order_advantage(self):
        ranks, credit = ss.rank_and_topk(np.ones((3, 4)), (1, 2))
        np.testing.assert_array_equal(ranks, np.full((3, 4), 2.5))
        np.testing.assert_array_equal(credit[1], np.full((3, 4), .25))
        np.testing.assert_array_equal(credit[2], np.full((3, 4), .5))

    def test_strict_pareto_equal_cost_and_duplicate_points(self):
        np.testing.assert_array_equal(
            ss.pareto_mask(np.array([4., 3., 4., 2.]), np.array([1., 1., 1., .5])),
            [True, False, True, True])

    def test_duplicate_scenario_draws_have_full_weight(self):
        totals = np.array([[5., 15., 25.]])  # five repetitions per scenario
        picks = np.array([[0, 0, 2], [1, 1, 1]])
        np.testing.assert_allclose(ss.bootstrap_means(totals, picks), [[7/3], [3.]])

    def test_draws_are_shared_seeded_and_not_deduplicated(self):
        first = ss.scenario_draws(3, n=40, seed=17)
        np.testing.assert_array_equal(first, ss.scenario_draws(3, n=40, seed=17))
        self.assertTrue(any(len(set(row)) < 3 for row in first))

    def test_valid_grid_is_canonically_sorted(self):
        expected = ss.validate_grid(fixture(), MODELS, SCENARIOS)
        shuffled = ss.validate_grid(fixture().sample(frac=1, random_state=8), MODELS, SCENARIOS)
        pd.testing.assert_frame_equal(expected, shuffled)

    def test_declared_model_order_cannot_mislabel_metrics(self):
        declared = ["c", "a", "b"]
        d = ss.validate_grid(fixture(), declared, SCENARIOS)
        self.assertEqual(list(d.model.drop_duplicates()), declared)
        result, _, _, _ = ss.analyze(d, declared, SCENARIOS, n=4, top_ks=(1, 2))
        point = result[result.arm.eq("consensus/mean")].set_index("model").point_quality
        expected = fixture().groupby("model").consensus.mean()
        np.testing.assert_allclose(point.loc[MODELS], expected.loc[MODELS])

    def test_missing_repetition_fails(self):
        with self.assertRaises(ValueError):
            ss.validate_grid(fixture().iloc[:-1], MODELS, SCENARIOS)

    def test_duplicate_repetition_fails(self):
        d = fixture()
        with self.assertRaises(ValueError):
            ss.validate_grid(pd.concat([d, d.iloc[[0]]]), MODELS, SCENARIOS)

    def test_wrong_roster_scenario_or_rep_fails(self):
        for col, val in [("model", "unexpected"), ("scenario", "unexpected"), ("rep", 8)]:
            d = fixture()
            d.loc[0, col] = val
            with self.assertRaises(ValueError):
                ss.validate_grid(d, MODELS, SCENARIOS)

    def test_unknown_nonfinite_or_negative_energy_is_not_imputed(self):
        for col, val in [("energy_wh", np.nan), ("energy_wh", np.inf),
                         ("energy_wh", -1.), ("consensus", np.nan),
                         ("gpt-5.4", np.nan), ("claude-opus-4.6", 0.)]:
            d = fixture()
            d.loc[0, col] = val
            with self.assertRaises(ValueError):
                ss.validate_grid(d, MODELS, SCENARIOS)

    def test_consensus_must_match_complete_judge_pair(self):
        d = fixture()
        d.loc[0, "consensus"] = 5.
        with self.assertRaises(ValueError):
            ss.validate_grid(d, MODELS, SCENARIOS)

    def test_zero_success_is_retained_on_energy_per_attempt_front(self):
        q, e = np.array([0., 1., 2.]), np.array([1., 2., 3.])
        table, summary, draws = ss.selection_statistics(q, e, q[None, :], e[None, :], (1, 2))
        self.assertEqual(len(table), 3)
        np.testing.assert_array_equal(table.pareto_probability, [1., 1., 1.])
        self.assertEqual(summary["point_pareto_size"], 3)

    def test_degenerate_rank_agreement_stays_undefined(self):
        q, e = np.ones(3), np.arange(1., 4.)
        table, summary, draws = ss.selection_statistics(q, e, q[None, :], e[None, :], (1, 2))
        self.assertEqual(summary["kendall_valid_draws"], 0)
        self.assertIsNone(summary["kendall_mean"])
        np.testing.assert_allclose(table.top_1_probability, [1/3]*3)

    def test_integer_tier_boundaries_and_unknowns(self):
        for value, expected in [(1, "T1"), (1_000_000_000, "T1"),
                                (1_000_000_001, "T2"), (4_000_000_000, "T4"),
                                (4_000_000_001, "T5"), (5_000_000_000, "T5")]:
            self.assertEqual(ss.integer_tier(value), expected)
        for value in [np.nan, None, 0, -1, 2.5, True, 5_000_000_001]:
            with self.assertRaises(ValueError):
                ss.integer_tier(value)

    def test_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p = pathlib.Path(td) / "input.csv"
            p.write_text("fixed evidence")
            ss.verify_hash(p, ss.sha256(p))
            with self.assertRaises(ValueError):
                ss.verify_hash(p, "0"*64)

    def test_reproducibility_and_k_slots_across_all_arms(self):
        d = ss.validate_grid(fixture(), MODELS, SCENARIOS)
        first = ss.analyze(d, MODELS, SCENARIOS, n=24, seed=11, top_ks=(1, 2))
        second = ss.analyze(d, MODELS, SCENARIOS, n=24, seed=11, top_ks=(1, 2))
        for a, b in zip(first, second):
            pd.testing.assert_frame_equal(a, b)
        selection, summaries, draws, picks = first
        self.assertEqual(selection.arm.nunique(), 15)
        for _, g in selection.groupby("arm"):
            self.assertEqual(len(g), 3)
            self.assertAlmostEqual(g.top_1_probability.sum(), 1)
            self.assertAlmostEqual(g.top_2_probability.sum(), 2)

    def test_integer_and_lock_tier_descriptions_remain_separate(self):
        population = pd.DataFrame({"model": MODELS, "run_param_count": [10**9, 10**9+1, 5*10**9],
                                   "integer_tier": ["T1", "T2", "T5"],
                                   "lock_tier": ["T1", "T1", "T4"]})
        selection, _, _, _ = ss.analyze(fixture(), MODELS, SCENARIOS, n=4, top_ks=(1, 2))
        tiers = ss.tier_descriptions(selection, population, top_ks=(1, 2))
        primary = tiers[tiers.arm.eq("consensus/mean")]
        integer = primary[primary.tier_system.eq("integer_tier")].set_index("tier")
        lock = primary[primary.tier_system.eq("lock_tier")].set_index("tier")
        self.assertEqual(integer.deployments.to_dict(), {"T1": 1, "T2": 1, "T5": 1})
        self.assertEqual(lock.deployments.to_dict(), {"T1": 2, "T4": 1})
        self.assertAlmostEqual(integer.expected_top_2_slots.sum(), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
