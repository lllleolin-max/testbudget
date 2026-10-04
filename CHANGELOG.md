# Changelog

## 0.2.0

- Prepare exact cost/signal/noise coefficients and bitmask constraints once;
  incrementally update units in the same ascending binary-mask order. Risk
  groups retain maximum signal semantics and every Pareto point.
- Preserve complete `testbudget.plan.v1` bytes and digests for unchanged inputs
  and state prefixes, including explanations and old-plan verification.
- Add an independent raw-input full-report oracle, exact numeric/history
  boundaries, a 256-point retained frontier regression and a reproducible
  synthetic work/memory benchmark with small-input overhead disclosures.
- Retain existing SDK/CLI execution, simulation and history protocols. CI
  installation selects the built wheel without a hardcoded package version.

## 0.1.0

- Revision/environment-specific prior evidence, bounded exact selection with
  retry reservation, hard coverage/group/exploration constraints, auditable
  frontier and frozen-plan execution/history workflow.
- Original three correctness corrections and synthetic policy losses remain
  documented in `docs/ITERATIONS.md` and `docs/BENCHMARK.md`.
