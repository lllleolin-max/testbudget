from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from testbudget import InputError, record, select, simulate
from testbudget.cli import main
from testbudget.workflow import load_json, save_json
from test_core import request, row, unit


class WorkflowTests(unittest.TestCase):
    def test_failed_serialization_and_replace_preserve_snapshot_clean_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            save_json(path, {"good": True})
            for invalid in [{"not_json": {1, 2}}, {"nonfinite": float("nan")}]:
                with self.assertRaises((TypeError, ValueError)):
                    save_json(path, invalid)
                self.assertEqual(load_json(path), {"good": True})
                self.assertEqual(list(Path(directory).iterdir()), [path])
            with patch("testbudget.workflow.os.replace", side_effect=OSError("injected replacement failure")):
                with self.assertRaises(OSError):
                    save_json(path, {"new": True})
            self.assertEqual(load_json(path), {"good": True})
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_record_rejects_infeasible_unknown_but_allows_feasible_empty(self):
        for req in [request([unit("x")], budget_seconds=0, mandatory_groups={"optional": 1}), request([unit("x")], exploration_min=1, max_states=1)]:
            p = select(req, [])
            self.assertIn(p["status"], {"UNKNOWN", "INFEASIBLE"})
            e = {"schema": "testbudget.execution.v1", "simulation": False, "plan_digest": p["freeze_digest"], "attempts": []}
            with self.assertRaises(InputError):
                record(p, e, [])
            with self.assertRaises(InputError):
                simulate(p, {})
        p = select(request([unit("x")], budget_seconds=0), [])
        self.assertEqual(p["status"], "FEASIBLE")
        self.assertEqual(record(p, simulate(p, {}), []), [])

    def test_round_trip_idempotence_and_conflict(self):
        hist = [row("x", 1, True)]
        p = select(request([unit("x")], exploration_min=1, stale_after=2), hist)
        e = simulate(p, {"x": [False]})
        new = record(p, e, hist)
        self.assertEqual(len(new), 2)
        self.assertEqual(record(p, e, new), new)
        conflict = deepcopy(e)
        conflict["attempts"][0]["passed"] = True
        with self.assertRaises(InputError):
            record(p, conflict, new)

    def test_stale_history_and_execution_bounds(self):
        p = select(request([unit("x")], exploration_min=1), [])
        e = simulate(p, {"x": [True]})
        with self.assertRaises(InputError):
            record(p, e, [row("x", 1, True)])
        for field, invalid in [("revision", 9), ("attempt", 2), ("test_id", "y"), ("environment", "windows")]:
            broken = deepcopy(e)
            broken["attempts"][0][field] = invalid
            with self.assertRaises(InputError):
                record(p, broken, [])
        broken = deepcopy(e)
        broken["attempts"] = []
        with self.assertRaises(InputError):
            record(p, broken, [])

    def test_atomic_json_and_duplicate_key_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            save_json(path, [row("x", 1, True)])
            self.assertEqual(load_json(path), [row("x", 1, True)])
            path.write_text('{"revision": 1, "revision": 2}', encoding="utf-8")
            with self.assertRaises(InputError):
                load_json(path)
            path.write_text('{"duration_seconds": NaN}', encoding="utf-8")
            with self.assertRaises(InputError):
                load_json(path)

    def test_cli_full_workflow(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            save_json(root / "request.json", request([unit("x")], exploration_min=1))
            save_json(root / "history.json", [])
            save_json(root / "truth.json", {"x": [False]})
            self.assertEqual(main(["select", "--request", str(root / "request.json"), "--history", str(root / "history.json"), "--out", str(root / "plan.json")]), 0)
            self.assertEqual(main(["simulate", "--plan", str(root / "plan.json"), "--outcomes", str(root / "truth.json"), "--out", str(root / "run.json")]), 0)
            self.assertEqual(main(["record", "--plan", str(root / "plan.json"), "--execution", str(root / "run.json"), "--history", str(root / "history.json"), "--out", str(root / "next.json")]), 0)
            self.assertEqual(load_json(root / "next.json")[0]["revision"], 10)
