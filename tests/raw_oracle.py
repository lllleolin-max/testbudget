"""Tiny raw-input exhaustive reference; imports no TestBudget evaluation code.

Fixtures are valid supported declarations. History/evidence, subset membership,
Pareto filtering and explanations are independently derived from those inputs.
"""
from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
from itertools import combinations
import json
import random


def rational(value):
    return Fraction(str(value))


def normalized(request, history):
    req = deepcopy(request)
    for field, default in (("mandatory_groups", {}), ("coverage", {}), ("exploration_min", 0),
                           ("stale_after", 5), ("noise_weight", .2), ("max_states", 262144)):
        req.setdefault(field, default)
    for field in ("mandatory_groups", "coverage"):
        req[field] = dict(sorted(req[field].items()))
    for test in req["tests"]:
        test.setdefault("environment", "default")
        test.setdefault("runs", 1)
        test["tags"] = sorted(set(test.get("tags", [])))
    req["tests"].sort(key=lambda t: t["id"])
    rows = deepcopy(history)
    for row in rows:
        row.setdefault("environment", "default")
    rows.sort(key=lambda r: (r["test_id"], r["environment"], r["revision"], r["attempt"]))
    return req, [r for r in rows if r["revision"] < req["revision"]]


def raw_evidence(req, prior):
    result = {}
    for test in req["tests"]:
        attempts = [r for r in prior if (r["test_id"], r["environment"]) == (test["id"], test["environment"])]
        revisions = sorted({r["revision"] for r in attempts})
        observations = [[r["passed"] for r in attempts if r["revision"] == rev] for rev in revisions]
        # None breaks the stable segment. True means observed pass, False failure.
        states = [None if len(set(outcomes)) > 1 else outcomes[0] for outcomes in observations]
        segments, current = [], []
        for state in states + [None]:
            if state is None:
                if current:
                    segments.append(current)
                current = []
            else:
                current.append(state)
        stable = sum(len(segment) for segment in segments)
        failed = sum(segment.count(False) for segment in segments)
        transitions = sum(a and not b for segment in segments for a, b in zip(segment, segment[1:]))
        opportunities = sum(len(segment) - 1 for segment in segments)
        post_failed = 0
        for segment in segments:
            if True in segment:
                post_failed += segment[segment.index(True) + 1:].count(False)
        mixed = states.count(None)
        last = max(revisions, default=None)
        raw_failed = sum(not r["passed"] for r in attempts)
        result[test["id"]] = {
            "prior_revisions": len(revisions), "stable_revisions": stable, "mixed_revisions": mixed,
            "stable_failed_revisions": failed, "post_pass_failed_revisions": post_failed,
            "pass_to_fail_transitions": transitions, "transition_opportunities": opportunities,
            "attempts": len(attempts), "raw_failed_attempts": raw_failed, "last_revision": last,
            "exploration_eligible": last is None or req["revision"] - last >= req["stale_after"],
            "signal_exact": str(Fraction(post_failed + transitions, stable + opportunities + 2)),
            "noise_exact": str(Fraction(mixed, len(revisions)) if revisions else Fraction()),
            "raw_failure_rate_exact": str(Fraction(raw_failed, len(attempts)) if attempts else Fraction())}
    return result


def metrics(tests, features):
    cost = sum((rational(t["duration_seconds"]) * t["runs"] for t in tests), Fraction())
    groups = {t["risk_group"] for t in tests}
    signal = sum((max(Fraction(features[t["id"]]["signal_exact"]) for t in tests if t["risk_group"] == group)
                  for group in groups), Fraction())
    noise = sum((Fraction(features[t["id"]]["noise_exact"]) for t in tests), Fraction())
    return cost, signal, noise


def errors(req, features, tests):
    result = []
    if metrics(tests, features)[0] > rational(req["budget_seconds"]):
        result.append("budget")
    result.extend(f"mandatory_group:{g}" for g, minimum in req["mandatory_groups"].items()
                  if sum(t["group"] == g for t in tests) < minimum)
    result.extend(f"coverage:{tag}" for tag, minimum in req["coverage"].items()
                  if sum(tag in t["tags"] for t in tests) < minimum)
    if sum(features[t["id"]]["exploration_eligible"] for t in tests) < req["exploration_min"]:
        result.append("exploration")
    return result


def output_point(ids, values):
    cost, signal, noise = values
    return {"selected": list(ids), "reserved_seconds": float(cost), "reserved_seconds_exact": str(cost),
            "signal_units": float(signal), "signal_exact": str(signal),
            "noise_units": float(noise), "noise_exact": str(noise)}


def reference(request, history):
    req, prior = normalized(request, history)
    features = raw_evidence(req, prior)
    tests = req["tests"]
    visited = min(1 << len(tests), req["max_states"])
    complete = visited == 1 << len(tests)
    feasible = []
    # Cardinality ordering differs from the solver. Mask filtering enforces the
    # exact published ascending-binary prefix without relying on its search loop.
    for size in range(len(tests) + 1):
        for indices in combinations(range(len(tests)), size):
            if sum(1 << i for i in indices) >= visited:
                continue
            chosen = [tests[i] for i in indices]
            if not errors(req, features, chosen):
                feasible.append((tuple(t["id"] for t in chosen), metrics(chosen, features)))
    frontier = []
    for ids, vector in feasible:
        if not any((v[0] <= vector[0] and v[1] >= vector[1] and v[2] <= vector[2] and v != vector)
                   or (v == vector and other < ids) for other, v in feasible):
            frontier.append((ids, vector))
    frontier.sort(key=lambda e: (e[1][0], -e[1][1], e[1][2], e[0]))
    status = "FEASIBLE" if feasible else "INFEASIBLE" if complete else "UNKNOWN"
    limits = [] if complete else ["max_states exhausted; frontier is a checked candidate frontier, not globally Pareto"]
    if status == "INFEASIBLE":
        limits.append("all subsets exhausted without satisfying budget/coverage/group/exploration constraints")
    plan = {"schema": "testbudget.plan.v1", "request": req, "prior_history": prior, "features": features,
            "training": {"strictly_before_revision": req["revision"], "minimum_revision": min((r["revision"] for r in prior), default=None),
                         "maximum_revision": max((r["revision"] for r in prior), default=None), "attempts": len(prior)},
            "status": status, "complete": complete, "visited_states": visited, "selected": [],
            "frontier": [output_point(ids, v) for ids, v in frontier], "reasons": {}, "limits": limits,
            "assumptions": ["ordinal revisions; environment-specific evidence",
                            "declared serial duration times maximum runs; actual runtimes may exceed estimates",
                            "signal/noise indices are not calibrated probabilities or root-cause diagnoses",
                            "risk_group maximum is a caller-declared conservative redundancy model",
                            "skipped tests have unknown outcomes"]}
    chosen_ids = ()
    if feasible:
        chosen_ids, values = min(feasible, key=lambda e: (-(e[1][1] - rational(req["noise_weight"]) * e[1][2]), e[1][0], e[0]))
        plan.update(selected=list(chosen_ids), selected_point=output_point(chosen_ids, values),
                    utility_exact=str(values[1] - rational(req["noise_weight"]) * values[2]))
    chosen = [t for t in tests if t["id"] in chosen_ids]
    for test in tests:
        ident, f = test["id"], features[test["id"]]
        entry = {"included": ident in chosen_ids, "signal_exact": f["signal_exact"], "noise_exact": f["noise_exact"],
                 "exploration_eligible": f["exploration_eligible"],
                 "reserve_seconds_exact": str(rational(test["duration_seconds"]) * test["runs"]),
                 "risk_group": test["risk_group"], "mandatory_group_min": req["mandatory_groups"].get(test["group"], 0),
                 "coverage": {tag: req["coverage"][tag] for tag in test["tags"] if tag in req["coverage"]}}
        if status != "FEASIBLE":
            entry["decision"] = status
        elif ident in chosen_ids:
            entry["decision"] = "selected by constrained utility; removing it has the following violations"
            entry["removal_violations"] = errors(req, features, [t for t in chosen if t["id"] != ident])
        else:
            entry["decision"] = "not in the chosen constrained optimum" if complete else "not in the bounded candidate choice"
            added = sorted(chosen + [test], key=lambda t: t["id"])
            entry["addition_violations"] = errors(req, features, added)
            entry["marginal_signal_exact"] = str(metrics(added, features)[1] - metrics(chosen, features)[1])
        plan["reasons"][ident] = entry
    plan["freeze_digest"] = sha256(json.dumps(plan, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
    return plan


def cases(seed=92147, count=128):
    rng = random.Random(seed)
    for index in range(count):
        n = index % 8
        tests, history = [], []
        for i in range(n):
            ident = ["a", "aa", "b", "x", "z", "Δ", "租户"][i]
            tests.append({"id": ident, "duration_seconds": rng.choice([.1, .2, .3, .125, 1, 2]),
                          "runs": rng.randint(1, 3), "group": f"g{i % 2}", "risk_group": f"r{i % 3}",
                          "tags": ["api", "api"] if i % 2 else ["db"], "environment": rng.choice(["default", "linux"])})
            for revision in range(1, rng.randint(1, 6)):
                for attempt in range(1, rng.randint(1, 3)):
                    history.append({"test_id": ident, "revision": revision, "attempt": attempt,
                                    "environment": tests[-1]["environment"], "passed": rng.choice([True, False]), "duration_seconds": .1})
            history.append({"test_id": ident, "revision": 10, "attempt": 1, "passed": False, "duration_seconds": 1})
        request = {"revision": 10, "budget_seconds": rng.choice([0, .1, .3, 1, 3, 10]), "tests": tests,
                   "mandatory_groups": {"g0": rng.randint(1, 2)} if index % 3 == 0 else {},
                   "coverage": {"api": 1, "missing": 1} if index % 11 == 0 else {"api": 1} if index % 5 == 0 else {},
                   "exploration_min": rng.randint(0, 2), "stale_after": rng.randint(1, 10),
                   "noise_weight": rng.choice([0, -0.0, .1, .2, 1, 2])}
        rng.shuffle(tests)
        rng.shuffle(history)
        full = 1 << n
        for cap in sorted({1, 2, max(1, full - 1), full, rng.randint(1, full)}):
            yield {**request, "max_states": cap}, deepcopy(history)
