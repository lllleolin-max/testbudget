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

Five further walk-forward rounds use target revisions 10..14 and append disclosed full-suite logs **after** freezing/evaluating each round. One new runnable unit enters the catalogue at each round. At target 14 the fitted history includes only revisions <=13. This is a common-history retrospective comparison: each policy receives the same full-suite logs, rather than policy-specific partial feedback. It isolates decisions fairly, but does not measure adaptive feedback dynamics of independently deployed policies. Every round checks that the prior cutoff remains strict. All 11 cases are executed, including the original adverse checkout case where removing exploration also misses checkout; it is retained rather than claiming an advantage it did not show.

## Observed synthetic results (2026-10-03)

Windows/Python 3.14.3 normal installed wheel. Table cells count distinct independently labeled hypothetical injected defects caught; they are not predictive accuracy estimates. Columns marked constrained use identical hard requirements. Ablations are explicitly evaluated for original-policy violations in the JSON report.

| Case | TestBudget | Shortest constrained | Raw failure constrained | Cost constrained | No exploration | Independent groups |
|---|---:|---:|---:|---:|---:|---:|
| new-regression-exploration | 1 | 1 | 1 | 1 | 0 | 1 |
| exploration-adverse-tight-budget | 0 | 0 | 0 | 0 | 0 | 0 |
| exploration-displaces-known-search-regression | 0 | 0 | 0 | 0 | 1 | 0 |
| no-regression-flaky-noise | 0 | 0 | 0 | 0 | 0 | 0 |
| unpredicted-fast-regression | 0 | 1 | 1 | 0 | 0 | 0 |
| correlated-redundancy | 2 | 1 | 1 | 0 | 2 | 1 |
| walk-forward-10 | 1 | 1 | 1 | 1 | 0 | 1 |
| walk-forward-11 | 1 | 0 | 0 | 0 | 1 | 1 |
| walk-forward-12 | 1 | 0 | 0 | 0 | 1 | 1 |
| walk-forward-13 | 1 | 2 | 1 | 1 | 0 | 1 |
| walk-forward-14 | 0 | 0 | 0 | 0 | 0 | 0 |

For the redundancy case, TestBudget reserves/executes 4.5 simulated seconds and catches 2 injected defects; raw-failure constrained and the independent-group ablation reserve/execute 5.5 seconds and catch 1. For the tight known-search adverse case, TestBudget reserves/executes 3.5 seconds and catches 0; disabling exploration reserves/executes 4.5 and catches 1 **while violating exploration**. In walk-forward-13, shortest constrained catches 2 where TestBudget catches 1. These losses bound the claim. Full selected IDs, exact training cutoff, missing defect IDs, noise and violations are executable in `out/benchmark.json`; no summary average is used to hide violations or losses.
