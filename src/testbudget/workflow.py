"""Explicit simulation and atomic history ingestion; no arbitrary runner execution."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from .core import InputError, digest, keys, normalize, number, verify_plan


def simulate(plan: dict, disclosed_outcomes: dict) -> dict:
    """Read target outcomes only after validating the frozen plan. Synthetic/demo only."""
    verify_plan(plan)
    if plan["status"] != "FEASIBLE":
        raise InputError("cannot execute an infeasible/unknown plan")
    if not isinstance(disclosed_outcomes, dict):
        raise InputError("outcomes must map test IDs to pass/fail booleans")
    rows = []
    for test in plan["request"]["tests"]:
        if test["id"] not in plan["selected"]:
            continue
        outcomes = disclosed_outcomes.get(test["id"])
        if not isinstance(outcomes, list) or not 1 <= len(outcomes) <= test["runs"] or any(not isinstance(p, bool) for p in outcomes):
            raise InputError(f"provide 1..{test['runs']} boolean outcomes for selected {test['id']}")
        rows.extend({"test_id": test["id"], "environment": test["environment"], "revision": plan["request"]["revision"], "attempt": i + 1, "passed": passed, "duration_seconds": test["duration_seconds"]} for i, passed in enumerate(outcomes))
    return {"schema": "testbudget.execution.v1", "simulation": True, "plan_digest": plan["freeze_digest"], "attempts": rows, "disclosure": "Synthetic outcomes and declared durations; no actual test runner or elapsed time measurement."}


def validated_execution(plan: dict, execution: dict) -> list[dict]:
    verify_plan(plan)
    if plan["status"] != "FEASIBLE":
        raise InputError("cannot record execution of an infeasible/unknown plan")
    keys(execution, {"schema", "simulation", "plan_digest", "attempts", "disclosure"}, {"schema", "simulation", "plan_digest", "attempts"}, "execution")
    if execution["schema"] != "testbudget.execution.v1" or execution["plan_digest"] != plan["freeze_digest"] or not isinstance(execution["simulation"], bool):
        raise InputError("execution does not match plan")
    _, rows = normalize(plan["request"], execution["attempts"])
    specs = {t["id"]: t for t in plan["request"]["tests"]}
    for row in rows:
        test = specs.get(row["test_id"])
        if row["test_id"] not in plan["selected"] or row["revision"] != plan["request"]["revision"] or row["environment"] != test["environment"] or row["attempt"] > test["runs"]:
            raise InputError("attempt outside frozen selection/revision/environment/run reservation")
    if set(r["test_id"] for r in rows) != set(plan["selected"]):
        raise InputError("every selected test needs at least one attempt; partial runs must not be recorded as complete")
    return rows


def record(plan: dict, execution: dict, history: list[dict]) -> list[dict]:
    """Append verified attempts without changing prior history. Idempotent replay accepted."""
    additions = validated_execution(plan, execution)
    _, current = normalize(plan["request"], history)
    # A stale plan cannot erase/change the prior evidence on which it relied.
    prior = [r for r in current if r["revision"] < plan["request"]["revision"]]
    if prior != plan["prior_history"]:
        raise InputError("history changed since plan freeze; reselect")
    index = {(r["test_id"], r["environment"], r["revision"], r["attempt"]): r for r in current}
    for row in additions:
        key = (row["test_id"], row["environment"], row["revision"], row["attempt"])
        if key in index and index[key] != row:
            raise InputError("conflicting recorded attempt")
        index[key] = row
    _, result = normalize(plan["request"], list(index.values()))
    return result


def load_json(path: str | Path):
    def object_pairs(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise InputError(f"duplicate JSON key: {k}")
            result[k] = v
        return result
    def constant(value):
        raise InputError(f"nonfinite JSON constant: {value}")
    path = Path(path)
    if path.stat().st_size > 32 * 1024 * 1024:
        raise InputError("input exceeds 32 MiB")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=object_pairs, parse_constant=constant)


def save_json(path: str | Path, data) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        try:
            json.dump(data, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            temp.unlink(missing_ok=True)
            raise
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)
