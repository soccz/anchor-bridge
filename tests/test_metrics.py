import math
import unittest

from analysis.metrics import conditional_lq, location_quotient, standardized_share, evaluate
from analysis.synthetic import records, worked_example


class MetricsTest(unittest.TestCase):
    def test_adjustment_changes_eligibility(self):
        example = worked_example()
        self.assertAlmostEqual(example["lq"], .88)
        self.assertAlmostEqual(example["clq"], 1.32)

    def test_scaling_does_not_change_quotient(self):
        self.assertAlmostEqual(location_quotient(220, 1000, 2500, 10000),
                               location_quotient(2200, 10000, 25000, 100000))

    def test_both_denominators_must_remove_anchor(self):
        actual = conditional_lq(220, 1000, 400, 2500, 10000, 1000)
        local_only = location_quotient(220, 600, 2500, 10000)
        self.assertNotAlmostEqual(actual, local_only)

    def test_zero_and_invalid_denominators(self):
        self.assertIsNone(location_quotient(0, 0, 1, 10))
        self.assertIsNone(location_quotient(2, 10, 0, 10))
        with self.assertRaises(ValueError):
            location_quotient(11, 10, 1, 10)
        with self.assertRaises(ValueError):
            location_quotient(math.nan, 10, 1, 10)
        with self.assertRaises(ValueError):
            conditional_lq(1, 10, 12, 1, 10, 0)

    def test_age_weights_and_missing_groups(self):
        self.assertAlmostEqual(standardized_share([.2, .6], [.75, .25]), .3)
        with self.assertRaises(ValueError):
            standardized_share([.2], [.75, .25])
        with self.assertRaises(ValueError):
            standardized_share([.2, .6], [.75, .5])

    def test_all_rejection_and_hold_reasons(self):
        actual = {r["id"]: r for r in records()}
        self.assertEqual(actual["gaon-meal"]["status"], "검토 후보")
        self.assertEqual(actual["gaon-snack"]["reason"], "역행 가정")
        self.assertEqual(actual["gaon-course"]["reason"], "공급 확인")
        self.assertEqual(actual["nuri-korean"]["reason"], "소비기반 부족")
        self.assertEqual(actual["daon-bakery"]["reason"], "연령 실험")
        self.assertIsNone(actual["daon-bakery"]["coverage"])
        self.assertEqual(actual["haeon-bakery"]["reason"], "관측 부족")
        self.assertEqual(actual["saebom-meal"]["reason"], "거리 조건 미달")
        no_store = dict(actual["gaon-meal"], stores=0)
        self.assertEqual(evaluate(no_store)[1], "점포 없음")


if __name__ == "__main__":
    unittest.main()
