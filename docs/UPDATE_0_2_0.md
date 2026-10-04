# 0.2 implementation review and measured limits

Original public baseline: `0e27a8f5029a62a97418b51ae554419455ca8fa6`, version
0.1.0. Parallel README changes were preserved by a normal fast-forward to
`3e04a27c4eef7aa352bc829825dc5e2077d6a6f0`. All measurements below used ordinary
wheels built from explicit canonical LF Git archives, fresh virtual environments
and isolated imports on Windows / CPython 3.14.3. Raw Git blobs, archive, wheel
and installed bytes matched for all five runtime modules. No editable install
or product-source import injection was used.

## Review 1: repeated subset work

The original installed wheel passed 28 tests. A standalone measured probe
visited the same 4,096-state prefix for 16, 18 and 20 units. It constructed
84,694 / 84,771 / 84,852 Fractions from strings and scanned 161,120 / 181,368 /
201,640 normalized catalogue elements. Its explicit precomputation work
assertion failed; it did not find incorrect old selections.

Correction `024c9ca00f60554501c2bfc03ed6f51f28f43236` (0.2.0.dev1) introduced
bounded exact coefficients, ascending-mask incremental cost/noise and affected
risk-group maxima, plus an independent raw full-report oracle. The same unchanged
probe passed after normal installation: 558 / 641 / 728 string constructions,
736 / 936 / 1,160 catalogue visits and 8,178 unit toggles. All three entire plan
files and freeze digests matched the baseline byte for byte. The 31-test suite
passed. This is one substantive performance correction.

## Review 2: completeness, oracle and adverse resource cases

Review candidate `0a17cf90b48137b96813a8eaa32b8e20f1dd9836` (0.2.0.dev2)
added the portable measurement script, cache/resource documentation, all-frontier
and unattainable-constraint regressions, and version-independent CI wheel
installation. Runtime modules were unchanged from review 1. Normal installation
passed 33 tests. No new product correctness defect was found in this review.

The raw oracle imports no product evaluation functions. It derives evidence from
raw revision/environment attempts, enumerates subsets by cardinality and filters
the exact binary-mask prefix, then independently derives all nondominated points,
lexical ties, selected utility and explanations. Both the old and new installed
packages passed 128 distinct raw scenarios / 512 distinct prefix inputs: 144
complete, 368 partial; 173 FEASIBLE, 89 INFEASIBLE and 250 UNKNOWN. All complete
report bytes matched; their aggregate SHA-256 is
`90de0cdcb7e11087bc1f03e5b44ef44581014e9fc7b0a56826d4c754decec702`.

The same standard fixture at 65,536 states produced identical input/plan bytes.
Each retained 15 Pareto points. The 16-unit case completed; 18 and 20 remained
partial. Counters include explanations and output conversion, not just the loop:

| Units | Fraction string constructions old → new | All Fraction constructions old → new | Catalogue element visits old → new | Whole-plan median seconds old → new | tracemalloc peak bytes old → new |
|---|---|---|---|---|---|
| 16 | 1,635,202 → 558 | 4,800,828 → 1,682 | 2,251,712 → 736 | 3.6463 → 0.08046 | 126,812 → 126,392 |
| 18 | 1,635,279 → 641 | 4,801,067 → 1,931 | 2,533,284 → 936 | 3.6958 → 0.08410 | 138,489 → 138,565 |
| 20 | 1,635,360 → 728 | 4,801,310 → 2,184 | 2,814,880 → 1,160 | 3.5921 → 0.08128 | 152,827 → 153,367 |

There were 131,054 unit toggles per new 65,536-state run. All Fraction counts
include both `__new__` and CPython 3.14's coprime factory. Parsing reduction is
not a claim that every Fraction allocation is constant: retained points,
explanations, input size and evidence affect the total. Timing uses three
untraced runs separately from instrumentation and tracemalloc.

Resource counterexamples retained:

- Eight unique risk groups with exactly proportional integer costs/signals
  retain all 256 feasible subsets as Pareto points. Complete reports matched;
  median 0.05141 → 0.007586 seconds, peak 464,479 → 425,039 bytes. A larger
  frontier can still dominate work and memory; it is never truncated.
- Ten independent risk groups retained 17 points: 0.04769 → 0.003561 seconds,
  peak 94,069 → 94,241 bytes. There is no redundancy assumption in this case.
- With empty history, zero/one/two-unit cases retained one point. One unit took
  0.000121 → 0.000205 seconds and peak 12,875 → 14,635 bytes; preparation can
  be a loss at tiny scales, and microsecond timing is noisy. Two units took
  0.000206 → 0.000194 seconds. Empty catalogue took 0.0000563 → 0.0000611.
- Cache-only preparation for the eight-unit frontier used median 0.0000521
  seconds, 5,084 retained / 8,843 peak bytes, after normalized inputs and
  evidence already existed. The process-lifetime RSS highwaters were measured
  separately and saved by the probe; they include imports and preceding runs,
  so they are not per-plan allocation deltas or constant-memory guarantees.

## Review 3: installed delivery and retained protocols

Final release review adds a 100,000-valid-future-row boundary test, rejection of
100,001 rows and invalid future rows, and final documentation/version metadata.
It does not change the runtime algorithm or count a third invented defect.
Final source/fresh-wheel association and the 34-test result are recorded in the
handoff against the exact frozen SHA, because a commit cannot contain its own
SHA without changing it.

Actual installed workflows run SDK and the console executable located through
`sysconfig`, including native encoding, PYTHONUTF8=0/1 and strict cp1252/cp936
stdout. Nineteen CLI calls check selection/simulation/recording equality, machine
JSON, original exit states and strict invalid input. Input and source bytes
remain unchanged. The demo preserves selected fresh/overlap/search/smoke,
7.5 seconds and history 135 → 139. All 11 original synthetic contrasts, all
three original correction probes, and old frozen-plan consumption pass.

One initial integration harness supplied outcomes only for the signaled unit
while hard exploration also selected `other`. Both installed versions correctly
rejected the missing outcome. The original helper and failed outputs were
retained, and a corrected helper supplied both outcomes in new output folders.
This was a harness mistake, not a product defect or a correction cycle.

The original three real 0.1 correction cycles remain in `ITERATIONS.md` and were
not renamed or reused as new findings. These three review stages comprise one
algorithmic improvement, verification/delivery work and no additional claimed
correctness bug. Local results do not certify every environment; remote CI is
run by the repository publication process. No external runner, customer data,
revenue, calibrated prediction quality or production performance was measured.
