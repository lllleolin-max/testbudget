# Implementation and self-review evidence

Initial working build: `a605c4c9d3bbd9bb8295057c5438359edc35deba`. Normal wheel build/install, 19 tests, SDK demo and five-case benchmark passed on Windows/Python 3.14.3. Demo selected fresh/overlap/search/smoke, 7.5 reserved seconds, history 135 -> 139. This document does not substitute for independent scoring.

## Cycle 1 — initial broken tests were counted as regression evidence

Before: `a605c4c9d3bbd9bb8295057c5438359edc35deba`. Review of the distinction between pre-existing stable failure and between-revision regression found the numerator included first-observed failures. Running installed initial wheel with `python tests/review_probes.py 1` printed `initial_failure_signal: 1/3` and exited 1 at the assertion requiring zero without a pass baseline. This was an actual observed failure after the initial build.

Correction: evidence now requires a same-environment stable pass baseline, resets it at mixed revisions, and exposes post-pass failed revision support separately. Permanently failing/no-baseline histories receive zero regression proxy without implying they are safe. Added assertions for first failure, permanent failure, mixed reset and persistent post-transition support. Benchmark also gained an explicit known-search tight-budget case because the initial checkout adverse case did not demonstrate benefit from removing exploration: both variants missed checkout. The separate search case exposes the observed opportunity cost without changing the original outcomes.

Verification: normal wheel rebuild/reinstall; `python tests/review_probes.py 1` prints signal 0 and exits 0; `python -m unittest discover -s tests -v` passes 21 tests; demo and six-case benchmark execute. After commit: see the commit titled `Require prior stable pass for between-revision regression proxy` (recorded explicitly in the next review entry to avoid a self-referential SHA).

Cycle 1 after: `8819993dfcb122eedd714e3f71c97e8cef5b46b5`.

## Cycle 2 — ingestion accepted an infeasible empty execution

Before: `8819993dfcb122eedd714e3f71c97e8cef5b46b5`. SDK ingestion review found `simulate` required FEASIBLE, but direct real-run `record` only compared selected IDs with observation IDs. For an INFEASIBLE empty selection, both sets were empty. `python tests/review_probes.py 2` printed `recorded_infeasible: []` and exited 1. This allowed an invalid workflow to look like successful result ingestion.

Correction: `validated_execution` now rejects INFEASIBLE and UNKNOWN plans before ingesting any rows. Valid feasible empty selections still work. Regression tests cover all three state cases and ensure simulator and recorder agree.

Verification: normal wheel rebuild/reinstall; `python tests/review_probes.py 2` prints the explicit infeasible/unknown rejection and exits 0; full suite passes 22 tests. SDK demo and CLI select/simulate/record remain runnable. After commit is recorded in the following entry.

Cycle 2 after: `a0cce43472c66df5c13c002c1e74d68af39a35d0`.

## Cycle 3 — failed serialization leaked a temporary file on Windows

Before: `a0cce43472c66df5c13c002c1e74d68af39a35d0`. The atomic writer's exception path attempted deletion while its NamedTemporaryFile was still open. `python tests/review_probes.py 3` on Windows printed `serialization_error: PermissionError`, `remaining_files: [snapshot.json, tmpo1mrn56d]`, and exited 1. The previous snapshot survived, but cleanup masked the true serialization error and leaked an artifact.

Correction: one outer try/finally now encloses serialization, fsync and replacement, closes the stream before deletion, and cleans failure paths after the handle is closed. Regression tests independently exercise nonserializable sets, nonfinite JSON and injected replacement failure, requiring the old contents and no residual temp files.

Verification: normal wheel rebuild/reinstall; `python tests/review_probes.py 3` prints `serialization_error: TypeError` and only `snapshot.json`, exit 0. Full suite passes 23 tests. All three probes, demo and benchmark execute on the updated normal wheel. After commit is recorded in the final evidence entry. Remaining boundary: externally killed processes may leave a temp file; no multiwriter lock or OS sandbox is claimed.
