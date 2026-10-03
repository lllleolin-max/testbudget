"""Revision-aware evidence and bounded exact constrained selection."""
from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from hashlib import sha256
import json
import math
from typing import Any


class InputError(ValueError):
    """Invalid declared data; different from infeasibility or search exhaustion."""


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return sha256(canonical(value).encode("utf-8")).hexdigest()


def number(value: Any, name: str, *, zero: bool = False) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f"{name} must be a finite number")
    try:
        valid = math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid or value < 0 or (not zero and value == 0):
        raise InputError(f"{name} must be finite and {'nonnegative' if zero else 'positive'}")
    return Fraction(str(value))


def integer(value: Any, name: str, minimum: int = 0, maximum: int = 10**9) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise InputError(f"{name} must be an integer in [{minimum}, {maximum}]")
    return value


def label(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 200 or any(ord(c) < 32 for c in value):
        raise InputError(f"{name} must be a nonempty string of <=200 characters without controls")
    return value


def keys(value: Any, allowed: set[str], required: set[str], name: str) -> dict:
    if not isinstance(value, dict) or set(value) - allowed or required - set(value):
        raise InputError(f"invalid fields in {name}; allowed={sorted(allowed)}, required={sorted(required)}")
    return value


def normalize(request: dict, history: list[dict]) -> tuple[dict, list[dict]]:
    keys(request, {"revision", "budget_seconds", "tests", "mandatory_groups", "coverage", "exploration_min", "stale_after", "noise_weight", "max_states"}, {"revision", "budget_seconds", "tests"}, "request")
    revision = integer(request["revision"], "revision", 1)
    number(request["budget_seconds"], "budget_seconds", zero=True)
    if not isinstance(request["tests"], list) or len(request["tests"]) > 2000:
        raise InputError("tests must be a list of at most 2000 execution units")
    tests, seen = [], set()
    for test in request["tests"]:
        keys(test, {"id", "environment", "group", "risk_group", "tags", "duration_seconds", "runs"}, {"id", "duration_seconds", "group", "risk_group"}, "test")
        ident = label(test["id"], "test.id")
        if ident in seen:
            raise InputError(f"duplicate test identity: {ident}")
        seen.add(ident)
        tags = test.get("tags", [])
        if not isinstance(tags, list) or len(tags) > 100:
            raise InputError("tags must be a list of <=100 labels")
        tags = sorted({label(t, "tag") for t in tags})
        duration = number(test["duration_seconds"], "duration_seconds")
        runs = integer(test.get("runs", 1), "runs", 1, 10)
        if duration * runs > 10**12:
            raise InputError("per-unit reserved duration exceeds supported 1e12 seconds")
        tests.append({"id": ident, "environment": label(test.get("environment", "default"), "environment"), "group": label(test["group"], "group"), "risk_group": label(test["risk_group"], "risk_group"), "tags": tags, "duration_seconds": test["duration_seconds"], "runs": runs})
    requirements = {}
    for field in ("mandatory_groups", "coverage"):
        value = request.get(field, {})
        if not isinstance(value, dict) or len(value) > 100:
            raise InputError(f"{field} must be an object with <=100 keys")
        requirements[field] = {label(k, field): integer(v, field, 1, 2000) for k, v in sorted(value.items())}
    req = {"revision": revision, "budget_seconds": request["budget_seconds"], "tests": sorted(tests, key=lambda t: t["id"]), **requirements, "exploration_min": integer(request.get("exploration_min", 0), "exploration_min", 0, 2000), "stale_after": integer(request.get("stale_after", 5), "stale_after", 1), "noise_weight": request.get("noise_weight", 0.2), "max_states": integer(request.get("max_states", 262144), "max_states", 1, 2097152)}
    number(req["noise_weight"], "noise_weight", zero=True)
    if not isinstance(history, list) or len(history) > 100000:
        raise InputError("history must be a list of <=100000 attempts")
    normalized, identities = [], set()
    for row in history:
        keys(row, {"test_id", "environment", "revision", "attempt", "passed", "duration_seconds"}, {"test_id", "revision", "attempt", "passed", "duration_seconds"}, "history attempt")
        item = {"test_id": label(row["test_id"], "test_id"), "environment": label(row.get("environment", "default"), "environment"), "revision": integer(row["revision"], "history.revision", 1), "attempt": integer(row["attempt"], "attempt", 1, 100000), "passed": row["passed"], "duration_seconds": row["duration_seconds"]}
        if not isinstance(item["passed"], bool):
            raise InputError("passed must be a boolean")
        number(item["duration_seconds"], "history.duration_seconds")
        identity = (item["test_id"], item["environment"], item["revision"], item["attempt"])
        if identity in identities:
            raise InputError(f"duplicate/conflicting history identity: {identity}")
        identities.add(identity)
        normalized.append(item)
    normalized.sort(key=lambda r: (r["test_id"], r["environment"], r["revision"], r["attempt"]))
    return req, normalized


def evidence(request: dict, prior: list[dict]) -> dict[str, dict]:
    by_test = defaultdict(lambda: defaultdict(list))
    for row in prior:
        by_test[(row["test_id"], row["environment"])][row["revision"]].append(row["passed"])
    result = {}
    for test in request["tests"]:
        rows = by_test[(test["id"], test["environment"])]
        mixed = stable = failed = transitions = opportunities = post_pass_failed = 0
        previous = None
        pass_baseline = False
        attempts = raw_failed = 0
        for _, outcomes in sorted(rows.items()):
            attempts += len(outcomes)
            raw_failed += outcomes.count(False)
            if any(outcomes) and not all(outcomes):
                mixed += 1
                previous = None  # Mixed evidence cannot establish a stable transition.
                pass_baseline = False
                continue
            state = not all(outcomes)
            stable += 1
            failed += int(state)
            if state and pass_baseline:
                post_pass_failed += 1
            if not state:
                pass_baseline = True
            if previous is not None:
                opportunities += 1
                transitions += int(not previous and state)
            previous = state
        # Stable failures alone include pre-existing broken tests. Only a prior
        # observed pass in the same uninterrupted stable segment supports this
        # between-revision proxy; repeated post-transition failures add support.
        signal = Fraction(post_pass_failed + transitions, stable + opportunities + 2)
        noise = Fraction(mixed, len(rows)) if rows else Fraction(0)
        last = max(rows) if rows else None
        result[test["id"]] = {"prior_revisions": len(rows), "stable_revisions": stable, "mixed_revisions": mixed, "stable_failed_revisions": failed, "post_pass_failed_revisions": post_pass_failed, "pass_to_fail_transitions": transitions, "transition_opportunities": opportunities, "attempts": attempts, "raw_failed_attempts": raw_failed, "last_revision": last, "exploration_eligible": last is None or request["revision"] - last >= request["stale_after"], "signal_exact": str(signal), "noise_exact": str(noise), "raw_failure_rate_exact": str(Fraction(raw_failed, attempts) if attempts else Fraction(0))}
    return result


def violations(request: dict, features: dict, selected: list[str] | tuple[str, ...]) -> list[str]:
    chosen = [t for t in request["tests"] if t["id"] in selected]
    errors = []
    if len(chosen) != len(selected) or len(set(selected)) != len(selected):
        errors.append("unknown or repeated selected identity")
    if sum((number(t["duration_seconds"], "duration") * t["runs"] for t in chosen), Fraction(0)) > number(request["budget_seconds"], "budget", zero=True):
        errors.append("budget")
    for group, minimum in request["mandatory_groups"].items():
        if sum(t["group"] == group for t in chosen) < minimum:
            errors.append(f"mandatory_group:{group}")
    for tag, minimum in request["coverage"].items():
        if sum(tag in t["tags"] for t in chosen) < minimum:
            errors.append(f"coverage:{tag}")
    if sum(features[t["id"]]["exploration_eligible"] for t in chosen) < request["exploration_min"]:
        errors.append("exploration")
    return errors


def measure(request: dict, features: dict, ids: tuple[str, ...]) -> tuple[Fraction, Fraction, Fraction]:
    groups = {}
    cost = noise = Fraction(0)
    for test in request["tests"]:
        if test["id"] not in ids:
            continue
        feature = features[test["id"]]
        cost += number(test["duration_seconds"], "duration") * test["runs"]
        noise += Fraction(feature["noise_exact"])
        group = test["risk_group"]
        groups[group] = max(groups.get(group, Fraction(0)), Fraction(feature["signal_exact"]))
    return cost, sum(groups.values(), Fraction(0)), noise


def point(ids: tuple[str, ...], values: tuple[Fraction, Fraction, Fraction]) -> dict:
    cost, signal, noise = values
    return {"selected": list(ids), "reserved_seconds": float(cost), "reserved_seconds_exact": str(cost), "signal_units": float(signal), "signal_exact": str(signal), "noise_units": float(noise), "noise_exact": str(noise)}


def dominates(a: tuple, b: tuple) -> bool:
    return a[0] <= b[0] and a[1] >= b[1] and a[2] <= b[2] and a != b


def select(request: dict, history: list[dict]) -> dict:
    """Freeze a prior-only decision. FEASIBLE is checked; exact requires complete search."""
    request, rows = normalize(request, history)
    prior = [r for r in rows if r["revision"] < request["revision"]]
    features = evidence(request, prior)
    plan = {"schema": "testbudget.plan.v1", "request": request, "prior_history": prior, "features": features, "training": {"strictly_before_revision": request["revision"], "minimum_revision": min((r["revision"] for r in prior), default=None), "maximum_revision": max((r["revision"] for r in prior), default=None), "attempts": len(prior)}, "status": "UNKNOWN", "complete": False, "visited_states": 0, "selected": [], "frontier": [], "reasons": {}, "limits": [], "assumptions": ["ordinal revisions; environment-specific evidence", "declared serial duration times maximum runs; actual runtimes may exceed estimates", "signal/noise indices are not calibrated probabilities or root-cause diagnoses", "risk_group maximum is a caller-declared conservative redundancy model", "skipped tests have unknown outcomes"]}
    tests = request["tests"]
    # A narrow exact scope is intentional; never call missing search a proof.
    if len(tests) > 20:
        plan["limits"].append("catalogue exceeds exact limit of 20 execution units; group runner units upstream")
    else:
        budget = number(request["budget_seconds"], "budget", zero=True)
        frontier = []
        for mask in range(1 << len(tests)):
            if plan["visited_states"] >= request["max_states"]:
                plan["limits"].append("max_states exhausted; frontier is a checked candidate frontier, not globally Pareto")
                break
            plan["visited_states"] += 1
            ids = tuple(t["id"] for i, t in enumerate(tests) if mask & (1 << i))
            values = measure(request, features, ids)
            if values[0] > budget or violations(request, features, ids):
                continue
            if any(dominates(v, values) or (v == values and old <= ids) for old, v in frontier):
                continue
            frontier = [(old, v) for old, v in frontier if not dominates(values, v) and not (v == values and ids < old)]
            frontier.append((ids, values))
        else:
            plan["complete"] = True
        frontier.sort(key=lambda entry: (entry[1][0], -entry[1][1], entry[1][2], entry[0]))
        plan["frontier"] = [point(ids, values) for ids, values in frontier]
        if frontier:
            weight = number(request["noise_weight"], "noise_weight", zero=True)
            ids, values = min(frontier, key=lambda e: (-(e[1][1] - weight * e[1][2]), e[1][0], e[0]))
            plan.update(status="FEASIBLE", selected=list(ids), selected_point=point(ids, values), utility_exact=str(values[1] - weight * values[2]))
        elif plan["complete"]:
            plan["status"] = "INFEASIBLE"
            plan["limits"].append("all subsets exhausted without satisfying budget/coverage/group/exploration constraints")
    chosen = set(plan["selected"])
    for test in tests:
        ident = test["id"]
        f = features[ident]
        entry = {"included": ident in chosen, "signal_exact": f["signal_exact"], "noise_exact": f["noise_exact"], "exploration_eligible": f["exploration_eligible"], "reserve_seconds_exact": str(number(test["duration_seconds"], "duration") * test["runs"]), "risk_group": test["risk_group"], "mandatory_group_min": request["mandatory_groups"].get(test["group"], 0), "coverage": {tag: request["coverage"][tag] for tag in test["tags"] if tag in request["coverage"]}}
        if plan["status"] != "FEASIBLE":
            entry["decision"] = plan["status"]
        elif ident in chosen:
            entry["decision"] = "selected by constrained utility; removing it has the following violations"
            entry["removal_violations"] = violations(request, features, sorted(chosen - {ident}))
        else:
            entry["decision"] = "not in the chosen constrained optimum" if plan["complete"] else "not in the bounded candidate choice"
            entry["addition_violations"] = violations(request, features, sorted(chosen | {ident}))
            old = measure(request, features, tuple(sorted(chosen)))
            new = measure(request, features, tuple(sorted(chosen | {ident})))
            entry["marginal_signal_exact"] = str(new[1] - old[1])
        plan["reasons"][ident] = entry
    plan["freeze_digest"] = digest(plan)
    return plan


def verify_plan(plan: dict) -> None:
    """Verify integrity and recompute selection; this is not origin authentication."""
    if not isinstance(plan, dict) or "freeze_digest" not in plan:
        raise InputError("missing frozen plan digest")
    content = {k: v for k, v in plan.items() if k != "freeze_digest"}
    if digest(content) != plan["freeze_digest"]:
        raise InputError("frozen plan changed")
    regenerated = select(plan["request"], plan["prior_history"])
    if regenerated != plan:
        raise InputError("plan differs from deterministic prior-only selection")
