"""Independent small-instance exhaustive oracle: no solver evaluation functions."""
from fractions import Fraction
from itertools import combinations


def enumerate_feasible(request, features):
    tests = sorted(request["tests"], key=lambda t: t["id"])
    result = []
    for size in range(len(tests) + 1):
        for chosen in combinations(tests, size):
            cost = sum((Fraction(str(t["duration_seconds"])) * t.get("runs", 1) for t in chosen), Fraction())
            if cost > Fraction(str(request["budget_seconds"])):
                continue
            if any(sum(t["group"] == group for t in chosen) < minimum for group, minimum in request.get("mandatory_groups", {}).items()):
                continue
            if any(sum(tag in t.get("tags", []) for t in chosen) < minimum for tag, minimum in request.get("coverage", {}).items()):
                continue
            if sum(features[t["id"]]["exploration_eligible"] for t in chosen) < request.get("exploration_min", 0):
                continue
            groups = {}
            for t in chosen:
                groups[t["risk_group"]] = max(groups.get(t["risk_group"], Fraction()), Fraction(features[t["id"]]["signal_exact"]))
            signal = sum(groups.values(), Fraction())
            noise = sum((Fraction(features[t["id"]]["noise_exact"]) for t in chosen), Fraction())
            result.append((tuple(t["id"] for t in chosen), (cost, signal, noise)))
    return result


def expected_frontier(feasible):
    result = []
    for ids, vector in feasible:
        inferior = False
        for other, v in feasible:
            dominates = v[0] <= vector[0] and v[1] >= vector[1] and v[2] <= vector[2] and v != vector
            if dominates or (v == vector and other < ids):
                inferior = True
                break
        if not inferior:
            result.append((ids, vector))
    return sorted(result, key=lambda row: (row[1][0], -row[1][1], row[1][2], row[0]))
