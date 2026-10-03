"""Published deterministic synthetic data; labels do not derive from scoring proxies."""
from copy import deepcopy


def attempt(ident, revision, passed, index=1):
    return {"test_id": ident, "revision": revision, "attempt": index, "passed": passed, "duration_seconds": 1}


def fixture():
    tests = [
        {"id": "smoke", "duration_seconds": .5, "group": "smoke", "risk_group": "smoke", "tags": ["startup"]},
        {"id": "known", "duration_seconds": 3, "group": "integration", "risk_group": "checkout", "tags": ["integration"]},
        {"id": "overlap", "duration_seconds": 2, "group": "integration", "risk_group": "checkout", "tags": ["integration"]},
        {"id": "fresh", "duration_seconds": 3, "group": "integration", "risk_group": "new-parser", "tags": ["integration"]},
        {"id": "noise", "duration_seconds": 1, "runs": 2, "group": "optional", "risk_group": "infra", "tags": []},
        {"id": "fast", "duration_seconds": .5, "group": "optional", "risk_group": "utility", "tags": []},
        {"id": "search", "duration_seconds": 2, "group": "integration", "risk_group": "search", "tags": ["integration"]},
    ]
    history = []
    known = [True, False, False, True, False, False, False, True, False]
    overlap = [True, False, False, True, False, True, False, True, False]
    search = [True, True, False, True, True, True, False, False, True]
    for revision in range(1, 10):
        for ident, states in [("known", known), ("overlap", overlap), ("search", search)]:
            history.append(attempt(ident, revision, states[revision - 1]))
        for ident in ("smoke", "fast"):
            history.append(attempt(ident, revision, True))
        # Ten attempts at each revision; 90% raw failures but every revision mixed.
        history.extend(attempt("noise", revision, index == 1, index) for index in range(1, 11))
    request = {"revision": 10, "budget_seconds": 7.5, "tests": tests, "mandatory_groups": {"smoke": 1}, "coverage": {"integration": 1}, "exploration_min": 1, "stale_after": 20, "noise_weight": .2}
    return request, history


def cases():
    request, history = fixture()
    definitions = [
        ("new-regression-exploration", 7.5, {"fresh": "parser-regression", "known": "checkout-regression"}),
        ("exploration-adverse-tight-budget", 4.5, {"known": "checkout-regression"}),
        ("exploration-displaces-known-search-regression", 4.5, {"search": "search-regression"}),
        ("no-regression-flaky-noise", 7.5, {}),
        ("unpredicted-fast-regression", 4.5, {"fast": "utility-regression"}),
    ]
    result = []
    for name, budget, labels in definitions:
        req = deepcopy(request)
        req["budget_seconds"] = budget
        # Independent target labels: explicit hypothetical injected defect IDs.
        outcomes = {t["id"]: ([False, True] if t["id"] == "noise" else [t["id"] not in labels]) for t in req["tests"]}
        result.append((name, req, deepcopy(history), outcomes, labels))
    req = deepcopy(request)
    req["tests"] = [t for t in req["tests"] if t["id"] != "fresh"]
    req.update(budget_seconds=5.5, exploration_min=0, coverage={})
    labels = {"known": "checkout-regression", "overlap": "checkout-regression", "search": "search-regression"}
    outcomes = {t["id"]: ([False, True] if t["id"] == "noise" else [t["id"] not in labels]) for t in req["tests"]}
    result.append(("correlated-redundancy", req, deepcopy(history), outcomes, labels))
    return result


def walk_forward():
    """Five full-suite logged revisions with independent hypothetical injections.

    One new runner unit is introduced at each revision. The caller receives its
    catalogue now; its target outcomes can be revealed only after all decisions.
    Earlier full-suite logs are common counterfactual input to every policy.
    """
    request, history = fixture()
    request["tests"] = [t for t in request["tests"] if t["id"] != "fresh"]
    injections = [
        {"new-10": "new-10-defect"},
        {"known": "checkout-11", "overlap": "checkout-11"},
        {"search": "search-12"},
        {"new-13": "new-13-defect", "fast": "unexpected-utility-13"},
        {},
    ]
    budgets = [7.5, 4.5, 5.5, 7.5, 4.5]
    for offset, labels in enumerate(injections):
        revision = 10 + offset
        request["revision"] = revision
        request["budget_seconds"] = budgets[offset]
        request["tests"].append({"id": f"new-{revision}", "duration_seconds": [3, 2, 1, 3, 2][offset], "group": "integration", "risk_group": f"new-family-{revision}", "tags": ["integration"]})
        outcomes = {t["id"]: ([False, True] if t["id"] == "noise" else [t["id"] not in labels]) for t in request["tests"]}
        yield f"walk-forward-{revision}", deepcopy(request), deepcopy(history), outcomes, labels
        # Advance only after the consumer froze and evaluated the current round.
        for t in request["tests"]:
            history.extend({"test_id": t["id"], "revision": revision, "attempt": i + 1, "passed": passed, "duration_seconds": t["duration_seconds"]} for i, passed in enumerate(outcomes[t["id"]]))
