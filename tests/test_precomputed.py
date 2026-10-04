from copy import deepcopy
from fractions import Fraction
from math import lcm
import unittest

from testbudget import InputError, select, verify_plan
from testbudget.core import measure, violations
from raw_oracle import cases, reference


class ExactPreparationTests(unittest.TestCase):
    def test_raw_exhaustive_full_reports_and_prefixes(self):
        checked = 0
        for request, history in cases():
            with self.subTest(case=checked, units=len(request["tests"]), max_states=request["max_states"]):
                before = deepcopy((request, history))
                plan = select(request, history)
                self.assertEqual(plan, reference(request, history))
                self.assertEqual((request, history), before)
                verify_plan(plan)
                checked += 1
        self.assertGreaterEqual(checked, 128)

    def test_exact_scaling_at_subnormal_and_decimal_boundaries(self):
        for duration, budget in [(5e-324, 1e-323), (.1, .3), (.1, .29999999999999993), (1e12, 1e12), (.125, .375)]:
            request = {"revision": 10, "budget_seconds": budget, "tests": [
                {"id": "a", "duration_seconds": duration, "runs": 1, "group": "g", "risk_group": "same"},
                {"id": "b", "duration_seconds": duration, "runs": 2 if duration < 1e12 else 1, "group": "g", "risk_group": "same"}],
                "exploration_min": 2}
            self.assertEqual(select(request, []), reference(request, []))

    def test_standalone_measure_and_violations_keep_semantics(self):
        for request, history in list(cases(count=16)):
            plan = select(request, history)
            req, features = plan["request"], plan["features"]
            for point in plan["frontier"]:
                values = measure(req, features, tuple(point["selected"]))
                self.assertEqual(tuple(map(str, values)), (point["reserved_seconds_exact"], point["signal_exact"], point["noise_exact"]))
                self.assertEqual(violations(req, features, point["selected"]), [])
            self.assertEqual(violations(req, features, ["unknown", "unknown"])[0], "unknown or repeated selected identity")

    def test_all_feasible_subsets_can_remain_on_large_frontier(self):
        signals = [Fraction(i + 2, 2 * i + 5) for i in range(8)]
        scale = lcm(*(v.denominator for v in signals))
        tests, history = [], []
        for i, signal in enumerate(signals):
            ident = str(i)
            tests.append({"id": ident, "duration_seconds": int(signal * scale), "group": "g", "risk_group": ident})
            for revision in range(1, i + 3):
                history.append({"test_id": ident, "revision": revision, "attempt": 1,
                                "passed": revision == 1, "duration_seconds": 1})
        req = {"revision": 20, "budget_seconds": sum(t["duration_seconds"] for t in tests), "tests": tests, "max_states": 256}
        plan = select(req, history)
        self.assertEqual(plan, reference(req, history))
        self.assertTrue(plan["complete"])
        self.assertEqual(len(plan["frontier"]), 256)

    def test_missing_and_unattainable_constraint_counts(self):
        for field in ("mandatory_groups", "coverage"):
            for maximum in (1, 4):
                req = {"revision": 3, "budget_seconds": 1, "tests": [
                    {"id": "x", "duration_seconds": .1, "group": "g", "risk_group": "r", "tags": ["api", "api"]}],
                    field: {"missing": 2000}, "max_states": maximum}
                self.assertEqual(select(req, []), reference(req, []))

    def test_full_history_validation_precedes_cached_search(self):
        req = {"revision": 1, "budget_seconds": 0, "tests": [
            {"id": "x", "duration_seconds": 1, "group": "g", "risk_group": "r"}]}
        # Valid future rows never enter training, but still must be validated.
        rows = [{"test_id": "other", "revision": revision, "attempt": 1,
                 "passed": True, "duration_seconds": 1} for revision in range(1, 100001)]
        plan = select(req, rows)
        self.assertEqual(plan["prior_history"], [])
        self.assertTrue(plan["complete"])
        with self.assertRaises(InputError):
            select(req, rows + [rows[0]])
        rows[-1]["duration_seconds"] = -1
        with self.assertRaises(InputError):
            select(req, rows)


if __name__ == "__main__":
    unittest.main()
