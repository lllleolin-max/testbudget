"""Fair disclosed retrospective experiment; all policies freeze before outcome reveal."""
from copy import deepcopy
from fractions import Fraction
from itertools import combinations
import json
from pathlib import Path

from fixtures import cases
from testbudget import select, violations
from testbudget.workflow import save_json


def feasible_sets(req, features):
    # Independent enumeration: intentionally does not use selector's frontier.
    tests = sorted(req["tests"], key=lambda t: t["id"])
    for n in range(len(tests) + 1):
        for subset in combinations(tests, n):
            ids = tuple(t["id"] for t in subset)
            cost = sum((Fraction(str(t["duration_seconds"])) * t.get("runs", 1) for t in subset), Fraction())
            if cost > Fraction(str(req["budget_seconds"])):
                continue
            if any(sum(t["group"] == k for t in subset) < v for k, v in req.get("mandatory_groups", {}).items()):
                continue
            if any(sum(k in t.get("tags", []) for t in subset) < v for k, v in req.get("coverage", {}).items()):
                continue
            if sum(features[t["id"]]["exploration_eligible"] for t in subset) < req.get("exploration_min", 0):
                continue
            yield ids, cost


def baseline(req, features, strategy, constrained):
    tests = req["tests"]
    cost = {t["id"]: Fraction(str(t["duration_seconds"])) * t.get("runs", 1) for t in tests}
    if strategy == "raw-failure-rate":
        order = sorted(cost, key=lambda i: (-Fraction(features[i]["raw_failure_rate_exact"]), cost[i], i))
    else:
        order = sorted(cost, key=lambda i: (cost[i], i))
    if constrained:
        candidates = list(feasible_sets(req, features))
        if not candidates:
            return []
        if strategy == "cost-only":
            return list(min(candidates, key=lambda entry: (entry[1], entry[0]))[0])
        # Closest feasible set to a rank-first greedy policy: lexicographic rank bits.
        return list(min(candidates, key=lambda entry: (tuple(-int(i in entry[0]) for i in order), entry[1], entry[0]))[0])
    chosen, total = [], Fraction()
    for ident in order:
        if total + cost[ident] <= Fraction(str(req["budget_seconds"])):
            chosen.append(ident)
            total += cost[ident]
    # Unconstrained cost-only maximizes execution-unit count then minimizes cost;
    # with positive independent costs this equals shortest-first. Disclosed tie.
    return sorted(chosen)


def replay(name, req, history, reveal):
    plan = select(req, history)
    features = plan["features"]
    decisions = {"testbudget": plan["selected"]}
    for policy in ("shortest-first", "raw-failure-rate", "cost-only"):
        for mode in (False, True):
            decisions[policy + ("-constrained" if mode else "-unconstrained")] = baseline(plan["request"], features, policy, mode)
    no_explore = deepcopy(req)
    no_explore["exploration_min"] = 0
    decisions["ablation-no-exploration"] = select(no_explore, history)["selected"]
    additive = deepcopy(req)
    for test in additive["tests"]:
        test["risk_group"] = test["id"]
    decisions["ablation-independent-risk-groups"] = select(additive, history)["selected"]
    # No outcomes or injected-defect labels have been consumed by the policies.
    frozen = deepcopy(decisions)
    outcomes, labels = reveal()
    assert decisions == frozen
    cost = {t["id"]: Fraction(str(t["duration_seconds"])) * t.get("runs", 1) for t in req["tests"]}
    actual_duration = {t["id"]: Fraction(str(t["duration_seconds"])) for t in req["tests"]}
    reports = {}
    for policy, ids in decisions.items():
        caught = sorted({labels[i] for i in ids if i in labels and False in outcomes[i]})
        actual = sum((actual_duration[i] * len(outcomes[i]) for i in ids), Fraction())
        noise = sum(False in outcomes[i] and i not in labels for i in ids)
        reports[policy] = {"selected": ids, "reserved_seconds": float(sum((cost[i] for i in ids), Fraction())), "simulated_executed_seconds": float(actual), "caught_distinct_injected_regressions": caught, "missed_distinct_injected_regressions": sorted(set(labels.values()) - set(caught)), "nonregression_failure_units": noise, "constraint_violations": violations(plan["request"], features, ids)}
    return {"case": name, "target_revision": req["revision"], "training_max_revision": plan["training"]["maximum_revision"], "history_attempts": len(history), "budget_seconds": req["budget_seconds"], "labels_independent_of_proxy": labels, "policies": reports}


def main():
    report = {"synthetic": True, "disclosure": "Deterministic illustrative injected defect labels, not real CI data or calibrated prediction accuracy. Policies have identical visible prior history/catalogue/reserved costs/budget; constrained variants have identical requirements. Both ablations may violate original constraints as separately reported. No executed external incumbent comparison.", "cases": []}
    for name, req, history, outcomes, labels in cases():
        report["cases"].append(replay(name, req, history, lambda o=outcomes, l=labels: (o, l)))
    save_json("out/benchmark.json", report)
    print(json.dumps({"synthetic": True, "cases": [{"name": c["case"], "policy": {p: {"caught": len(v["caught_distinct_injected_regressions"]), "missed": len(v["missed_distinct_injected_regressions"]), "seconds": v["simulated_executed_seconds"], "violations": v["constraint_violations"]} for p, v in c["policies"].items()}} for c in report["cases"]]}, indent=2))


if __name__ == "__main__":
    main()
