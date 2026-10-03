# Executable retrospective comparison

Run `python examples/benchmark.py`. `examples/fixtures.py` publishes all deterministic synthetic history and independent hypothetical injected-defect IDs. There is no real CI dataset or product adoption claim. The history includes repeated outcomes at the same revision, highly flaky raw failure rates, observed stable changes, unseen tests and correlated test labels. Models use only revisions 1..9; target is revision 10. `replay` freezes every policy decision before invoking `reveal()` to access target outcomes and labels. Labels are specified independently; proxy transitions do not define ground truth.

All policies use the same test list, visible prior observations, budget and declared per-unit reserve (`duration * runs`). Each reports simulated executed duration separately from reserved duration, distinct injected defects caught/missed, nonregression failing units and all violations of original constraints. An apparent gain from relaxing exploration is never labeled a constraint-respecting gain. No measured real runner duration is claimed.

Baselines:

- Shortest-first: sort by reserved cost then ID; greedily add fitting units. Its constrained version exhaustively selects the feasible tuple closest to this ranking (lexicographic inclusion bits).
- Raw failure fraction: attempts failed / observed attempts, descending, cost/ID ties. Greedy and hard-constraint-respecting variants use the same prior data. Retries may distort this baseline on purpose, reflecting its stated definition.
- Cost-only: unconstrained maximum count / lowest cost is equivalent to shortest-first for independent positive costs; this equivalence is explicitly disclosed. The constrained version minimizes cost among feasible tuples, IDs break ties.
- No-exploration ablation: same evidence/grouping model, exploration minimum set to zero; original constraint violations remain visible.
- Independent-risk-groups ablation: same scoring/requirements, each unit assigned its own risk group; this permits redundant signal addition.

Cases include unseen new regressions, a tight budget where exploration displaces a known regression, no regression with only flaky failures, an unpredicted regression elsewhere, and correlated redundant tests. These are illustrative counterexamples, not an unbiased sample or calibration/accuracy estimate. The tradeoff mechanism can lose. `tests/oracle.py` separately checks small feasible/Pareto/utility optima against 50 deterministic generated cases; this verifies optimization, not predictive validity. Do not infer that a tested proxy is calibrated or that unselected tests pass.
