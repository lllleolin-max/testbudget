# Model and interoperable JSON input

`select(request: dict, history: list[dict]) -> dict` returns schema `testbudget.plan.v1`. Request fields:

| Field | Meaning |
|---|---|
| revision | Positive integer ordinal; strictly ordered on one caller-managed branch |
| budget_seconds | Finite nonnegative reserved serial seconds |
| tests | Unique IDs; each has `group`, `risk_group`, positive finite `duration_seconds`; optional `environment` defaults to `default`, `runs` 1..10 defaults 1, `tags` defaults [] |
| mandatory_groups / coverage | Label -> positive minimum distinct selected-unit count; defaults {} |
| exploration_min | Minimum selected unseen/stale units; nonnegative, defaults 0 |
| stale_after | Positive revision-age threshold, defaults 5; unseen is always eligible |
| noise_weight | Nonnegative unitless disutility per mixed-revision noise unit, defaults 0.2 |
| max_states | 1..2097152; defaults 262144 |

History attempt: `test_id`, positive integer `revision`, positive integer `attempt`, boolean `passed`, positive finite `duration_seconds`, optional `environment` (default `default`). Identity is (ID, environment, revision, attempt); duplicate or conflicting identities fail. Unknown catalogue history is retained as historical evidence but has no feature effect. Unknown fields fail, rather than being silently misspelled. JSON duplicate keys and nonfinite constants fail. SDK accepts numbers only, excluding booleans.

All costs use exact `Fraction(str(number))`: decimal JSON 0.1+0.2 fits 0.3. The display float is for convenience; `_exact` fields are authoritative. Duration times maximum runs is reserved **once per selected runner unit**. History measured durations currently do not fit duration estimates; the caller must supply conservative estimates. A per-unit reservation above 1e12 seconds fails as outside useful supported range.

Training filters strictly `revision < target`. The plan records the actual prior rows, digest, minimum/maximum revision, attempt count and per-unit support. Future/target rows never affect fitted features, frontier or frozen digest. For existing IDs only the requested environment contributes. Same-revision outcomes collapse to one stable pass, one stable fail, or one mixed revision, regardless of retry count. A mixed revision resets stable-transition adjacency; environment and mixed evidence do not prove any root cause. A single all-fail observation is stable **observed** evidence, not statistical certainty of determinism.

Index: `(post_pass_failed_revisions + pass_to_fail_transitions) / (stable_revisions + transition_opportunities + 2)`. A stable fail adds numerator support only after an observed stable pass in the same stable segment; mixed evidence resets this baseline. First-observed or permanently broken tests without a pass baseline therefore have zero between-revision proxy and separately visible stable-failure support. This does not establish absence of a regression. A transition occurs between adjacent observed stable revision groups; gaps may contain unseen changes. This is a bounded unitless historical index with two units of shrinkage, not a fitted/calibrated probability. `noise_index = mixed_revisions / observed_revisions`. No observations -> zero signal/noise; exploration handles missing support. Raw failure fraction counts attempts and is provided explicitly for baseline comparison, not used as the regression index. Indices are descriptive proxies, not a claim of actual injected-regression ground truth.

Subset signal is the **sum of the maximum per-test signal in each caller-declared risk group**, so multiple tests covering one suspected outcome family cannot add their scores. This conservative model assumes caller-specified overlap, not independence or a proven joint detection probability. Incorrect grouping can undercount complementary tests. Subset noise is the sum of mixed-revision fractions; utility is signal minus `noise_weight * noise`. Units are proxy units, not dollars or expected root-cause count. Costs minimize, signal maximizes and noise minimizes in the three-dimensional Pareto frontier; equal vectors retain the lexicographically smallest ID tuple. Chosen utility ties use lower cost then IDs. No future target outcomes enter any objective.

Reasons include constraints implicated by removing an included unit, budget/constraints implicated by adding a skipped unit, and its marginal signal under group maxima. A unit may be included to satisfy a hard requirement despite zero proxy signal. Unselected outcomes are unknown, even when historical signal is zero.
