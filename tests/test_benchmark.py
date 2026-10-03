"""Executable benchmark properties, including fair baselines and outcome boundary."""
from fractions import Fraction
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from benchmark import replay
from fixtures import cases, walk_forward
from testbudget import select


class BenchmarkTests(unittest.TestCase):
    def test_innovation_contrasts_and_adverse_case(self):
        reports = {name: replay(name, req, hist, lambda o=outcomes, l=labels: (o, l)) for name, req, hist, outcomes, labels in cases()}
        def caught(name, policy):
            return len(reports[name]["policies"][policy]["caught_distinct_injected_regressions"])
        self.assertGreater(caught("new-regression-exploration", "testbudget"), caught("new-regression-exploration", "ablation-no-exploration"))
        self.assertLess(caught("exploration-displaces-known-search-regression", "testbudget"), caught("exploration-displaces-known-search-regression", "ablation-no-exploration"))
        self.assertGreater(caught("correlated-redundancy", "testbudget"), caught("correlated-redundancy", "ablation-independent-risk-groups"))
        self.assertGreater(caught("correlated-redundancy", "testbudget"), caught("correlated-redundancy", "raw-failure-rate-constrained"))
        for report in reports.values():
            for policy, values in report["policies"].items():
                if policy == "testbudget" or policy.endswith("-constrained"):
                    self.assertEqual(values["constraint_violations"], [])
                self.assertLessEqual(values["reserved_seconds"], report["budget_seconds"])

    def test_walk_forward_freezes_before_reveal_and_uses_only_prior(self):
        previous_history = 0
        for name, req, hist, outcomes, labels in walk_forward():
            self.assertTrue(all(r["revision"] < req["revision"] for r in hist))
            self.assertGreater(len(hist), previous_history)
            previous_history = len(hist)
            frozen = select(req, hist)
            def reveal():
                self.assertEqual(select(req, hist), frozen)
                return outcomes, labels
            report = replay(name, req, hist, reveal)
            self.assertLess(report["training_max_revision"], report["target_revision"])
            self.assertEqual(report["policies"]["testbudget"]["selected"], frozen["selected"])

