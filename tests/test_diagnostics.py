import unittest

from analysis.diagnostics import correlation, leave_one_out, eligibility_change, require_available_before
from analysis.synthetic import studies


class DiagnosticsTest(unittest.TestCase):
    def test_constant_series_has_no_defined_correlation(self):
        self.assertIsNone(correlation([1, 1, 1], [2, 3, 4]))

    def test_one_observation_can_reverse_relationship(self):
        x, y = [1, 2, 3, 10], [3, 2, 1, 10]
        self.assertGreater(correlation(x, y), 0)
        self.assertAlmostEqual(leave_one_out(x, y)[-1], -1)

    def test_common_weights_reduce_but_do_not_erase_gap(self):
        life = studies()["life"]
        self.assertAlmostEqual(life["before_a"] - life["before_b"], .34)
        self.assertAlmostEqual(life["after_a"] - life["after_b"], .18)

    def test_population_change_is_not_called_age_effect(self):
        self.assertIn("관측대상 변경", eligibility_change(.8, 1.05, 1.2))
        self.assertIn("동일 관측대상", eligibility_change(.8, .9, 1.2))

    def test_old_features_do_not_make_future_training_labels_valid(self):
        with self.assertRaisesRegex(ValueError, "학습 정답"):
            require_available_before("2030-04-30", {"특징": "2030-04-30", "학습 정답": "2030-06-30"})
        self.assertTrue(require_available_before("2030-04-30", {"특징": "2030-03-31", "학습 정답": "2030-04-15"}))
