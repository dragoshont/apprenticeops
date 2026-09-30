"""Bounded §10 fixtures; no raw data, labels or model calls."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

import selection_sensitivity as sx
from test_selection_stability import MODELS, SCENARIOS, fixture


def cells():
    d = fixture()
    d["finish_reason"] = "stop"
    d["output_chars"] = 12
    return d


class SelectionSensitivityTests(unittest.TestCase):
    def test_proxy_retains_length_but_excludes_blank_and_dnf(self):
        d = cells().iloc[:5].copy()
        d["finish_reason"] = ["stop", "length", "stop", "DNF:timeout", "DNF:after_done_missing"]
        d["output_chars"] = [4, 8, 0, 20, 30]
        np.testing.assert_array_equal(sx.completion_proxy(d), [1, 1, 0, 0, 0])

    def test_unknown_metadata_rejected(self):
        for col, value in [("finish_reason", None), ("finish_reason", "new-reason"),
                           ("output_chars", np.nan), ("output_chars", np.inf),
                           ("output_chars", -1), ("output_chars", .5)]:
            d = cells()
            d["output_chars"] = d.output_chars.astype(float)
            d.loc[0, col] = value
            with self.subTest(col=col, value=value), self.assertRaises(ValueError):
                sx.completion_proxy(d)

    def test_zero_denominator_is_missing_not_zero(self):
        q = sx.ratio(np.array([12., 0.]), np.array([3, 0]))
        self.assertEqual(q[0], 4)
        self.assertTrue(np.isnan(q[1]))

    def test_energy_zero_success_infinite_and_zero_zero_unavailable(self):
        q = sx.ratio(np.array([12., 8., 0.]), np.array([3, 0, 0]), energy=True)
        self.assertEqual(q[0], 4)
        self.assertEqual(q[1], np.inf)
        self.assertTrue(np.isnan(q[2]))

    def test_cluster_sums_keep_duplicate_draw_multiplicity(self):
        a = np.array([[1, 8, 12], [3, 7, 20]])
        np.testing.assert_array_equal(sx.draw_sums(a, np.array([[0, 0, 2], [1, 1, 1]])),
                                      [[14, 26], [24, 21]])

    def test_conditional_is_ratio_of_totals_not_mean_of_scenario_means(self):
        d = cells()
        a = d.model.eq("a")
        d.loc[a & d.scenario.eq("s0"), "output_chars"] = [2, 0, 0, 0, 0]
        axes, counts = sx.make_axes(d, MODELS, SCENARIOS, np.array([[0, 1], [0, 0]]))
        i = a & (d.output_chars > 0)
        expected = d.loc[i, "consensus"].sum()/i.sum()
        self.assertEqual(axes["proxy-conditional"]["point_q"][0], expected)
        self.assertEqual(axes["proxy-conditional"]["boot_q"][1, 0], d.loc[a, "consensus"].iloc[0])
        self.assertEqual(counts["boot_proxy"][1, 0], 2)

    def test_unconditional_floor_only_known_failures_all_energy_retained(self):
        d = cells()
        d.loc[0, ["finish_reason", "consensus", "claude-opus-4.6", "gpt-5.4"]] = [
            "DNF:timeout", 4, 4, 4]
        d.loc[1, "output_chars"] = 0
        axes, _ = sx.make_axes(d, MODELS, SCENARIOS, np.array([[0, 1]]))
        a = d[d.model.eq("a")]
        q = a.consensus.copy()
        q.iloc[:2] = 1
        self.assertEqual(axes["proxy-unconditional"]["point_q"][0], q.mean())
        e = axes["mean-per-positive"]["point_e"][0]
        self.assertAlmostEqual(e, a.energy_wh.sum()/a.consensus.ge(3).sum())
        self.assertAlmostEqual(axes["proxy-conditional"]["point_e"][0], a.energy_wh.mean())

    def test_equal_infinite_costs_and_strict_dominance(self):
        q = np.array([4., 3., 4., 2.])
        e = np.array([np.inf, np.inf, np.inf, 1.])
        table, summary, _, _ = sx.summarize(q, e, q[None, :], e[None, :], (1, 2))
        np.testing.assert_array_equal(table.point_pareto, [True, False, True, True])
        self.assertEqual(summary["valid_draws"], 1)
        self.assertEqual(summary["point_infinite_cost_models"], 3)

    def test_equal_finite_cost_ties_and_topk_slots(self):
        q, e = np.array([4., 3., 4.]), np.ones(3)
        table, _, _, _ = sx.summarize(q, e, q[None, :], e[None, :], (1, 2))
        np.testing.assert_array_equal(table.point_pareto, [True, False, True])
        np.testing.assert_allclose(table.top_1_probability, [.5, 0, .5])
        self.assertEqual(table.top_2_probability.sum(), 2)

    def test_whole_roster_invalid_draw_retains_all_models_and_draws(self):
        q, e = np.array([4., 3., 2.]), np.ones(3)
        bq = np.array([[4., 3., 2.], [4., np.nan, 2.]])
        be = np.ones_like(bq)
        table, summary, draws, state = sx.summarize(q, e, bq, be, (1, 2))
        self.assertEqual(len(table), 3)
        self.assertEqual(len(draws), 2)
        self.assertEqual(summary["valid_draws"], 1)
        self.assertEqual(draws.quality_unavailable_models.tolist(), [0, 1])
        self.assertTrue(np.isnan(state["ranks"][1]).all())
        np.testing.assert_array_equal(table.quality_unavailable_draws, [0, 1, 0])

    def test_all_unavailable_has_null_not_zero_frequencies(self):
        q, e = np.array([np.nan, 2., 3.]), np.ones(3)
        table, summary, draws, _ = sx.summarize(q, e, q[None, :], e[None, :], (1, 2))
        self.assertEqual(summary["valid_draws"], 0)
        self.assertEqual(summary["point_status"], "not-estimable")
        self.assertTrue(table.pareto_probability.isna().all())
        self.assertTrue(table.top_1_probability.isna().all())
        self.assertTrue(draws.kendall_vs_point.isna().all())

    def test_unavailable_energy_invalidates_draw_not_infinity(self):
        q, e = np.array([4., 3., 2.]), np.array([np.nan, 1., 2.])
        _, summary, draws, _ = sx.summarize(q, e, q[None, :], e[None, :], (1, 2))
        self.assertEqual(summary["valid_draws"], 0)
        self.assertEqual(draws.cost_unavailable_models.iloc[0], 1)

    def test_all_infinite_costs_still_extended_real_front(self):
        q, e = np.array([4., 3., 4.]), np.full(3, np.inf)
        table, summary, _, _ = sx.summarize(q, e, q[None, :], e[None, :], (1, 2))
        self.assertEqual(summary["valid_draws"], 1)
        np.testing.assert_array_equal(table.point_pareto, [True, False, True])

    def test_negative_energy_or_infinite_quality_rejected(self):
        for q, e in [(np.array([4., 3., 2.]), np.array([1., -1., 2.])),
                     (np.array([4., np.inf, 2.]), np.ones(3))]:
            with self.assertRaises(ValueError):
                sx.summarize(q, e, q[None, :], e[None, :], (1, 2))

    def test_paired_comparisons_use_valid_intersection(self):
        q, e = np.array([4., 3., 2.]), np.ones(3)
        a = np.array([[4., 3., 2.], [4., np.nan, 2.]])
        b = np.array([[4., np.nan, 2.], [4., 3., 2.]])
        sa = sx.summarize(q, e, a, np.ones_like(a), (1, 2))[3]
        sb = sx.summarize(q, e, b, np.ones_like(b), (1, 2))[3]
        summary, draws = sx.compare(sa, sb, k=2)
        self.assertEqual(summary["paired_valid_draws"], 0)
        self.assertTrue(draws.kendall_between_arms.isna().all())

    def test_missing_rep_or_unknown_energy_rejected(self):
        for d in [cells().iloc[:-1], cells().assign(energy_wh=np.nan)]:
            with self.assertRaises(ValueError):
                sx.make_axes(d, MODELS, SCENARIOS, np.array([[0, 1]]))

    def test_seeded_reproducibility_and_no_model_dropping(self):
        d = cells()
        d.loc[d.model.eq("a"), "output_chars"] = 0
        first = sx.analyze(d, MODELS, SCENARIOS, n=12, seed=71, top_ks=(1, 2))
        second = sx.analyze(d, MODELS, SCENARIOS, n=12, seed=71, top_ks=(1, 2))
        for key in first:
            pd.testing.assert_frame_equal(first[key], second[key])
        self.assertEqual(len(first["selection"]), 12)  # four arms incl reference
        self.assertEqual(len(first["draw_summary"]), 48)
        row = first["arm_summary"].set_index("arm").loc["proxy-conditional"]
        self.assertEqual(row.valid_draws, 0)

    def test_screen_counts_membership_and_missing_full_run_rows(self):
        selected = [f"m{i}" for i in range(152)]
        excluded = [f"e{i}" for i in range(21)]
        screen = pd.DataFrame({"model": selected+excluded, "in_study": [True]*152+[False]*21})
        disposition = sx.screen_disposition(screen, selected)
        self.assertEqual(disposition["status"], "NOT_IDENTIFIABLE")
        self.assertEqual(disposition["excluded"], 21)
        self.assertEqual(disposition["excluded_full_run_rows"], 0)
        with self.assertRaises(ValueError):
            sx.screen_disposition(screen.iloc[:-1], selected)
        with self.assertRaises(ValueError):
            sx.screen_disposition(screen, selected[:-1]+excluded[:1])

    def test_original_base_file_change_fails_replay_check(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/"out.csv"
            p.write_text("preserved")
            hashes = {"out.csv": sx.ss.sha256(p)}
            sx.verify_outputs(Path(td), hashes)
            p.write_text("changed")
            with self.assertRaises(ValueError):
                sx.verify_outputs(Path(td), hashes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
