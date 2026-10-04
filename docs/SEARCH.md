# Exact subset work and limits

Version 0.2 prepares each unit's exact reserved cost, signal and noise once after
normalization and prior-only evidence construction. Each axis has a positive
common denominator; the search compares integer numerators on that scale.
Budget comparison floors the scaled rational budget, preserving fractional and
zero-budget boundaries. Output values are reduced Fractions again. There is no
float approximation in feasibility, dominance or utility selection.

Masks still advance in ascending binary order. A carry toggles the changed units,
updating additive cost/noise and maxima only for affected risk groups. Each risk
group stores descending signal tiers and their unit masks; signal remains the
group maximum, including after removing its previous maximum. Group, tag and
exploration requirements count selected bits. The preparation stores at most one
coefficient per unit/axis, bounded group tiers and declared requirement masks;
it does not store a table for all subsets.

The `testbudget.plan.v1` schema, complete/partial semantics, lexical ties, all
Pareto points and every explanation are preserved. Existing plans can be
reverified: unchanged declared inputs and the same `max_states` prefix produce
identical full reports and freeze digests. Standalone `core.measure` and
`violations` keep their existing behavior. Explanation generation still uses
these functions; it adds bounded work outside the subset loop.

For N units, S visited subsets, R requirements and F retained frontier points,
the search still has O(S * (N + R + F)) worst-case work. Carries toggle fewer than
two units per mask on average, but a changed risk group can inspect up to N
tiers. Exact integer operation cost depends on numerator/denominator bit length.
Pareto comparisons and retained output can be exponential. Storage remains
O(H + N + declared tags/requirements + N*F), counting the selected IDs retained
for every frontier point; preparing this cache does not bound F. Verification
reruns selection. Use `max_states` and external process limits for strict time
or memory budgets. The 20-unit cap and state cap have not increased.

## Reproduce synthetic measurements

Use the same script with separately installed old/new wheels and fresh output
folders, rather than changing package imports. These commands run the current
installed package:

```console
python benchmarks/selection_work.py --units 16 18 20 --max-states 65536 --output out/search-65536
python benchmarks/selection_work.py --case independent --units 10 --max-states 1024 --output out/search-independent
python benchmarks/selection_work.py --case frontier --units 8 --max-states 256 --output out/search-frontier
python benchmarks/selection_work.py --case empty-history --units 0 1 2 --max-states 4 --output out/search-small
```

The standard fixture has declared duplicate risk groups, fractional retry
reservations, mandatory group/tag coverage and exploration. At 65,536 states,
16 units complete the search; 18 and 20 units inspect only their first 65,536
binary masks. These runs do not prove complete search performance for 20 units.
The independent case removes risk-group redundancy. The eight-unit frontier
case deliberately retains all 256 subsets as Pareto points. The smallest cases
expose preparation overhead instead of hiding it behind a large search.

Each run saves the input and entire plan, separate profiling counts, three
untraced wall times (median), whole-plan tracemalloc peak with the result still
retained, cache-only preparation cost and process-lifetime RSS highwater.
Normalized-catalogue visits count elements yielded from that catalogue, not
every integer/mask operation. Fraction string constructions count parsing;
total Fraction constructions separately count `__new__` and the coprime factory
when present on the interpreter. The optional factory hook is reported rather
than assumed on every Python version. RSS includes interpreter imports, earlier
runs and profiling, and is not a per-plan allocation measure. For independent
process RSS measurements, run one `--units` value per fresh process.

The measurements are synthetic local work evidence, not calibrated CI accuracy,
customer adoption, revenue or production latency guarantees. See the 0.2 update
record for actual values and byte comparisons, and the existing benchmark for
policy losses and outcome limitations.
