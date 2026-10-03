from copy import deepcopy
from fractions import Fraction
import random
import unittest

from testbudget import InputError, select, verify_plan, violations
from oracle import enumerate_feasible, expected_frontier


def unit(ident, duration=1, group="optional", risk=None, tags=None, **extra):
    return {"id": ident, "duration_seconds": duration, "group": group, "risk_group": risk or ident, "tags": tags or [], **extra}


def row(ident, revision, passed, attempt=1, environment="default"):
    return {"test_id": ident, "environment": environment, "revision": revision, "attempt": attempt, "passed": passed, "duration_seconds": 1}


def request(tests, **extra):
    return {"revision": 10, "budget_seconds": 3, "tests": tests, **extra}


class EvidenceTests(unittest.TestCase):
    def test_same_revision_flakiness_not_regression(self):
        hist = [row("flaky", rev, passed, i + 1) for rev in range(1, 6) for i, passed in enumerate([True, False, False])]
        plan = select(request([unit("flaky")]), hist)
        f = plan["features"]["flaky"]
        self.assertEqual(f["signal_exact"], "0")
        self.assertEqual(f["noise_exact"], "1")
        self.assertEqual(plan["selected"], [])

    def test_retries_do_not_inflate_revision_signal(self):
        hist = [row("x", 1, True), row("x", 2, False)]
        repeated = hist + [row("x", 2, False, i) for i in range(2, 101)]
        a, b = select(request([unit("x")]), hist), select(request([unit("x")]), repeated)
        self.assertEqual(a["features"]["x"]["signal_exact"], b["features"]["x"]["signal_exact"])
        self.assertNotEqual(a["features"]["x"]["raw_failure_rate_exact"], b["features"]["x"]["raw_failure_rate_exact"])

    def test_future_and_target_outcomes_never_used(self):
        req = request([unit("x")])
        prior = [row("x", 1, True)]
        a = select(req, prior)
        b = select(req, prior + [row("x", 10, False), row("x", 11, False)])
        self.assertEqual(a, b)
        self.assertLess(a["training"]["maximum_revision"], req["revision"])

    def test_environment_partition(self):
        req = request([unit("x", environment="linux")])
        hist = [row("x", 1, True, environment="linux"), row("x", 2, False, environment="windows")]
        self.assertEqual(select(req, hist)["features"]["x"]["signal_exact"], "0")

    def test_missing_history_and_staleness(self):
        req = request([unit("new"), unit("old"), unit("recent")], exploration_min=2, stale_after=5)
        plan = select(req, [row("old", 5, True), row("recent", 6, True)])
        self.assertEqual(plan["selected"], ["new", "old"])

    def test_mixed_revision_breaks_transition(self):
        f = select(request([unit("x")]), [row("x", 1, True), row("x", 2, True), row("x", 2, False, 2), row("x", 3, False)])["features"]["x"]
        self.assertEqual(f["pass_to_fail_transitions"], 0)


class SolverTests(unittest.TestCase):
    def test_constraints_and_infeasibility(self):
        req = request([unit("a", 2, group="smoke", tags=["api"]), unit("b", 2)], mandatory_groups={"smoke": 1}, coverage={"api": 1}, exploration_min=2)
        self.assertEqual(select(req, [])["status"], "INFEASIBLE")
        req["budget_seconds"] = 4
        plan = select(req, [])
        self.assertEqual(plan["selected"], ["a", "b"])
        self.assertEqual(violations(plan["request"], plan["features"], plan["selected"]), [])

    def test_tiny_budget_empty_selection_and_required_failure(self):
        req = request([unit("x", 1)], budget_seconds=0.01)
        self.assertEqual(select(req, [])["selected"], [])
        req["exploration_min"] = 1
        self.assertEqual(select(req, [])["status"], "INFEASIBLE")

    def test_exact_decimal_budget(self):
        req = request([unit("a", .1), unit("b", .2)], budget_seconds=.3, exploration_min=2)
        p = select(req, [])
        self.assertEqual(p["status"], "FEASIBLE")
        self.assertEqual(p["selected_point"]["reserved_seconds_exact"], "3/10")

    def test_unknown_vs_checked_partial_vs_infeasible(self):
        req = request([unit("a"), unit("b")], exploration_min=1, max_states=1)
        p = select(req, [])
        self.assertEqual(p["status"], "UNKNOWN")
        req["max_states"] = 2
        p = select(req, [])
        self.assertEqual(p["status"], "FEASIBLE")
        self.assertFalse(p["complete"])
        self.assertEqual(violations(p["request"], p["features"], p["selected"]), [])
        req["max_states"] = 4
        self.assertTrue(select(req, [])["complete"])
        self.assertEqual(select(request([unit(str(i)) for i in range(21)]), [])["status"], "UNKNOWN")

    def test_risk_group_non_double_count_changes_decision(self):
        tests = [unit("a", 2, risk="shared"), unit("b", 2, risk="shared"), unit("c", 2)]
        hist = [row("a", 1, True), row("a", 2, False), row("b", 1, True), row("b", 2, False), row("c", 1, True), row("c", 2, False)]
        p = select(request(tests, budget_seconds=4), hist)
        self.assertEqual(p["selected"], ["a", "c"])
        self.assertEqual(p["reasons"]["b"]["marginal_signal_exact"], "0")

    def test_random_independent_exhaustive_oracle(self):
        rng = random.Random(4721)
        for _ in range(50):
            n = rng.randrange(1, 8)
            tests = [unit(str(i), rng.choice([.1, .2, 1, 2]), group=f"g{i % 2}", risk=f"r{i % 3}", tags=["api"] if i % 2 else []) for i in range(n)]
            hist = [row(str(i), rev, rng.choice([True, False])) for i in range(n) for rev in range(1, rng.randrange(2, 6))]
            req = request(tests, budget_seconds=rng.choice([0, .3, 1, 3, 6]), mandatory_groups={"g0": 1}, coverage={"api": 1} if n > 1 else {}, exploration_min=rng.randrange(2), stale_after=7)
            p = select(req, hist)
            feasible = enumerate_feasible(req, p["features"])
            oracle = expected_frontier(feasible)
            observed = [(tuple(v["selected"]), (Fraction(v["reserved_seconds_exact"]), Fraction(v["signal_exact"]), Fraction(v["noise_exact"]))) for v in p["frontier"]]
            self.assertEqual(observed, oracle)
            if feasible:
                expected = min(feasible, key=lambda e: (-(e[1][1] - Fraction("0.2") * e[1][2]), e[1][0], e[0]))[0]
                self.assertEqual(tuple(p["selected"]), expected)
            else:
                self.assertEqual(p["status"], "INFEASIBLE")

    def test_permutation_stability_and_digest(self):
        tests = [unit("a"), unit("b", 2)]
        hist = [row("a", 2, False), row("a", 1, True)]
        a = select(request(tests), hist)
        b = select(request(list(reversed(tests))), list(reversed(hist)))
        self.assertEqual(a, b)
        verify_plan(a)
        b["selected"] = []
        with self.assertRaises(InputError):
            verify_plan(b)


class ValidationTests(unittest.TestCase):
    def test_numeric_types_durations_and_runs(self):
        for invalid in [0, -1, float("nan"), float("inf"), float("-inf"), True, "1", None]:
            with self.subTest(value=invalid), self.assertRaises(InputError):
                select(request([unit("x", invalid)]), [])
        for invalid in [0, -1, 1.1, True, 11]:
            with self.subTest(value=invalid), self.assertRaises(InputError):
                select(request([unit("x", runs=invalid)]), [])
        for invalid in [-1, float("inf"), True]:
            with self.assertRaises(InputError):
                select(request([], budget_seconds=invalid), [])

    def test_duplicates_conflicts_and_unknown_fields(self):
        with self.assertRaises(InputError):
            select(request([unit("x"), unit("x", 2)]), [])
        for duplicate in [row("x", 1, True), row("x", 1, False)]:
            with self.assertRaises(InputError):
                select(request([unit("x")]), [row("x", 1, True), duplicate])
        with self.assertRaises(InputError):
            select(request([unit("x")], typo=1), [])


if __name__ == "__main__":
    unittest.main()
