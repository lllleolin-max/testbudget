"""Executable SDK input -> frozen plan -> disclosed simulation -> history workflow."""
from pathlib import Path
import json

from fixtures import fixture
from testbudget import record, select, simulate
from testbudget.workflow import save_json


def main():
    req, history = fixture()
    save_json("out/request.json", req)
    save_json("out/history.json", history)
    plan = select(req, history)  # Target outcomes do not exist in this scope yet.
    save_json("out/plan.json", plan)
    outcomes = {t["id"]: ([False, True] if t["id"] == "noise" else [t["id"] not in {"fresh", "known"}]) for t in req["tests"]}
    save_json("out/outcomes.json", outcomes)
    execution = simulate(plan, outcomes)
    save_json("out/execution.json", execution)
    updated = record(plan, execution, history)
    save_json("out/next-history.json", updated)
    print(json.dumps({"synthetic": True, "selected": plan["selected"], "reserve_seconds": plan["selected_point"]["reserved_seconds"], "frontier_points": len(plan["frontier"]), "history_before": len(history), "history_after": len(updated)}, indent=2))


if __name__ == "__main__":
    main()
