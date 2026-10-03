"""Standalone self-review probes. Run against an installed wheel at each commit."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import tempfile

from testbudget import InputError, record, select
from testbudget.workflow import save_json


def request(budget=1, **extra):
    return {"revision": 3, "budget_seconds": budget, "tests": [{"id": "x", "group": "smoke", "risk_group": "x", "duration_seconds": 1}], **extra}


def cycle1():
    history = [{"test_id": "x", "revision": 1, "attempt": 1, "passed": False, "duration_seconds": 1}]
    plan = select(request(), history)
    print(json.dumps({"initial_failure_signal": plan["features"]["x"]["signal_exact"]}))
    assert Fraction(plan["features"]["x"]["signal_exact"]) == 0, "first observed failure without any prior pass is not between-revision regression evidence"


def cycle2():
    plan = select(request(0, mandatory_groups={"smoke": 1}), [])
    execution = {"schema": "testbudget.execution.v1", "simulation": False, "plan_digest": plan["freeze_digest"], "attempts": []}
    rejected = False
    try:
        result = record(plan, execution, [])
        print(json.dumps({"recorded_infeasible": result}))
    except InputError as error:
        rejected = True
        print(json.dumps({"rejected": str(error)}))
    assert rejected, "record must reject an infeasible plan even with an empty execution"


def cycle3():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "snapshot.json"
        save_json(path, {"valid": True})
        try:
            save_json(path, {"not_json": {1, 2}})
        except (TypeError, OSError) as error:
            print(json.dumps({"serialization_error": type(error).__name__}))
        files = sorted(p.name for p in Path(directory).iterdir())
        print(json.dumps({"remaining_files": files}))
        assert files == ["snapshot.json"], "failed serialization must leave no temporary artifact"
        assert json.loads(path.read_text()) == {"valid": True}, "failed write must preserve old snapshot"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("cycle", choices=["1", "2", "3"])
    args = parser.parse_args()
    {"1": cycle1, "2": cycle2, "3": cycle3}[args.cycle]()
