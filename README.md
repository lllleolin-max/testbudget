# TestBudget

Transparent, revision-aware selection of CI execution units under a declared serial runtime budget. CI owners can reserve retries, require smoke groups and tag coverage, insist on unseen/stale exploration, and inspect an exact rational cost/signal/noise frontier. A frozen plan carries its prior evidence and explanations into result recording.

**Scope:** offline pilot tool, at most 20 runner units for bounded exhaustive search. A runner unit can be a suite/class managed by your adapter. This is not a calibrated regression predictor; skipped outcomes remain unknown. Synthetic examples demonstrate decisions, not real-world accuracy or adoption.

## Install and run / 安装与运行

Python 3.11 or newer; commands below work in PowerShell and POSIX shells from this repository. No runtime dependencies.

```console
python -m pip install .
python -m unittest discover -s tests -v
python examples/demo.py
python examples/benchmark.py
```

Demo writes `out/request.json`, `out/history.json`, a frozen plan, disclosed target outcomes, simulated execution and new history. It prints selected IDs, reserved seconds and history sizes. Benchmark writes the full per-policy report to `out/benchmark.json`; it includes an adverse exploration case. All fixtures are explicitly synthetic and published in `examples/fixtures.py`.

```console
testbudget select --request out/request.json --history out/history.json --out out/cli-plan.json
testbudget simulate --plan out/cli-plan.json --outcomes out/outcomes.json --out out/cli-run.json
testbudget record --plan out/cli-plan.json --execution out/cli-run.json --history out/history.json --out out/cli-next.json
```

`simulate` executes no shell commands: it consumes disclosed boolean outcomes and declared durations **after** verifying a frozen decision. Your CI adapter can instead emit `testbudget.execution.v1` with actual observed attempt durations and `simulation: false`. `record` validates identity/environment/revision/run bounds, retains existing history, accepts identical replays, and rejects conflicts. CLI exit codes: 0 checked feasible/success; 2 invalid input or I/O; 3 proven infeasible; 4 search unknown. A feasible incomplete search is explicitly `complete: false`; its frontier/choice has no global optimality claim.

中文：这是用于 CI 预算试点的离线 SDK/CLI。以版本序号和环境分组，重试不会被当成独立回归样本；强制组、覆盖和探索均为硬约束。预算是每个单元“声明秒数 × 最大运行次数”的串行预留成本，实际运行可能超时。`INFEASIBLE` 仅在穷举完成时输出；搜索受限输出 `UNKNOWN` 或已检查的可行候选。未运行测试没有通过保证。上面的完整流程先冻结选择，再读取合成结果，最后生成新历史；生产接入需自行维护单写入者和真实测试执行器。

## SDK

```python
from testbudget import select, simulate, record
request = {
    "revision": 3, "budget_seconds": 2,
    "tests": [{"id": "smoke", "group": "smoke", "risk_group": "startup",
               "duration_seconds": 1, "runs": 2, "tags": ["startup"]}],
    "mandatory_groups": {"smoke": 1}, "coverage": {"startup": 1},
    "exploration_min": 1, "stale_after": 5,
}
plan = select(request, [])
assert plan["status"] == "FEASIBLE"
execution = simulate(plan, {"smoke": [True]})  # explicitly synthetic
history = record(plan, execution, [])
```

See [model and schema](docs/MODEL.md), [architecture and boundaries](docs/ARCHITECTURE.md), [benchmark interpretation](docs/BENCHMARK.md), [commercial pilot](docs/PILOT.md), [iteration evidence](docs/ITERATIONS.md), [security](SECURITY.md), and [contributing](CONTRIBUTING.md).

## Prior art and honest distinction

Verified 2026-10-03: [Launchable's official selection documentation](https://help.launchableinc.com/features/predictive-test-selection/how-launchable-selects-tests/) describes historical test execution, test characteristics, changed-file correlations, change characteristics and environments, followed by duration or confidence subset targets. TestBudget credits predictive test selection, test prioritization and constrained subset optimization as established methods. We have not executed Launchable or established that it lacks a feature.

This project's falsifiable local distinction is the interaction of environment/revision evidence, retry reservations, caller-declared redundant risk groups, hard exploration/coverage and an auditable bounded frontier. The executable comparison is against clearly defined simple policies and mechanism ablations. It is not a superiority, scientific novelty, customer or revenue claim.
