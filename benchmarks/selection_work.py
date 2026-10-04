"""Synthetic whole-plan work measurement against an ordinary installed package.

Run the identical script with old/new isolated interpreters and separate output
folders. Instrumentation is separate from timing and does not change reports.
"""
import argparse
from copy import deepcopy
from fractions import Fraction
import gc
import hashlib
import json
from pathlib import Path
import statistics
import time
import tracemalloc
from unittest.mock import patch
import testbudget.core as core


def fixture(n, max_states, case="standard"):
    tests = [{"id": f"u{i:02}", "duration_seconds": (i % 5 + 1) / 10, "runs": i % 3 + 1,
              "group": f"g{i % 3}", "risk_group": f"r{i % 4}", "tags": ["api"] if i % 2 else ["db"]}
             for i in range(n)]
    request = {"revision": 10, "budget_seconds": 3, "tests": tests, "mandatory_groups": {"g0": 1},
               "coverage": {"api": 1}, "exploration_min": 1, "max_states": max_states}
    history = []
    for i, test in enumerate(tests):
        for revision in range(1, i % 5 + 3):
            history.append({"test_id": test["id"], "revision": revision, "attempt": 1,
                            "passed": revision == 1, "duration_seconds": test["duration_seconds"]})
    if case == "empty-history":
        history = []
        request.update(mandatory_groups={}, coverage={}, exploration_min=0)
    elif case == "independent":
        for test in tests:
            test["risk_group"] = test["id"]
    elif case == "frontier":
        from math import lcm
        signals = [Fraction(i + 2, 2 * i + 5) for i in range(n)]
        scale = lcm(*(v.denominator for v in signals))
        history = []
        for i, test in enumerate(tests):
            test.update(duration_seconds=int(signals[i] * scale), runs=1, risk_group=test["id"])
            for revision in range(1, i + 3):
                history.append({"test_id": test["id"], "revision": revision, "attempt": 1,
                                "passed": revision == 1, "duration_seconds": 1})
        request.update(revision=n + 10, budget_seconds=sum(t["duration_seconds"] for t in tests),
                       mandatory_groups={}, coverage={}, exploration_min=0)
    return request, history


def rss_highwater():
    import os
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
        get_handle = ctypes.windll.kernel32.GetCurrentProcess
        get_handle.restype = wintypes.HANDLE
        get_info = ctypes.windll.psapi.GetProcessMemoryInfo
        get_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        value = Counters()
        value.cb = ctypes.sizeof(value)
        assert get_info(get_handle(), ctypes.byref(value), value.cb)
        return value.PeakWorkingSetSize
    import resource
    import sys
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if sys.platform == "darwin" else value * 1024


def measure(n, max_states, output, case="standard"):
    req, history = fixture(n, max_states, case)
    original_input = deepcopy((req, history))
    counts = {"number_calls": 0, "fraction_string_constructions": 0, "fraction_new_constructions": 0,
              "fraction_coprime_factory_constructions": 0, "normalized_catalogue_element_visits": 0,
              "measure_calls": 0, "prepared_unit_toggle_calls": 0}
    original_normalize, original_number, original_measure = core.normalize, core.number, core.measure
    original_new = Fraction.__new__
    factory_method = getattr(Fraction, "_from_coprime_ints", None)
    original_factory = factory_method.__func__ if factory_method is not None else None
    class CountedList(list):
        def __iter__(self):
            for item in super().__iter__():
                counts["normalized_catalogue_element_visits"] += 1
                yield item
    def normalized(*args, **kwargs):
        request, rows = original_normalize(*args, **kwargs)
        request["tests"] = CountedList(request["tests"])
        return request, rows
    def number(*args, **kwargs):
        counts["number_calls"] += 1
        return original_number(*args, **kwargs)
    def measured(*args, **kwargs):
        counts["measure_calls"] += 1
        return original_measure(*args, **kwargs)
    def new(cls, *args, **kwargs):
        counts["fraction_new_constructions"] += 1
        if args and isinstance(args[0], str):
            counts["fraction_string_constructions"] += 1
        return original_new(cls, *args, **kwargs)
    def factory(cls, numerator, denominator):
        counts["fraction_coprime_factory_constructions"] += 1
        return original_factory(cls, numerator, denominator)
    from contextlib import ExitStack
    with ExitStack() as stack:
        stack.enter_context(patch.object(core, "normalize", normalized))
        stack.enter_context(patch.object(core, "number", number))
        stack.enter_context(patch.object(core, "measure", measured))
        stack.enter_context(patch.object(Fraction, "__new__", staticmethod(new)))
        if original_factory is not None:
            stack.enter_context(patch.object(Fraction, "_from_coprime_ints", classmethod(factory)))
        prepared = getattr(core, "_SubsetSearch", None)
        if prepared is not None:
            old_toggle = prepared.toggle
            def toggle(self, *args, **kwargs):
                counts["prepared_unit_toggle_calls"] += 1
                return old_toggle(self, *args, **kwargs)
            stack.enter_context(patch.object(prepared, "toggle", toggle))
        profiled = core.select(req, history)
    canonical_profiled = core.canonical(profiled)
    counts["fraction_objects_constructed_total"] = counts["fraction_new_constructions"] + counts["fraction_coprime_factory_constructions"]
    del profiled
    gc.collect()
    times = []
    for _ in range(3):
        start = time.perf_counter()
        plan = core.select(req, history)
        times.append(time.perf_counter() - start)
        assert core.canonical(plan) == canonical_profiled
    del plan
    gc.collect()
    tracemalloc.start()
    plan = core.select(req, history)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert (req, history) == original_input
    assert core.canonical(plan) == canonical_profiled
    preparation = None
    prepared = getattr(core, "_SubsetSearch", None)
    if prepared is not None:
        normalized_request, rows = core.normalize(req, history)
        features = core.evidence(normalized_request, [r for r in rows if r["revision"] < normalized_request["revision"]])
        preparation_times = []
        for _ in range(3):
            start = time.perf_counter()
            cache = prepared(normalized_request, features)
            preparation_times.append(time.perf_counter() - start)
            del cache
        gc.collect()
        tracemalloc.start()
        cache = prepared(normalized_request, features)
        retained_cache, peak_cache = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        preparation = {"seconds_median": statistics.median(preparation_times),
                       "retained_bytes": retained_cache, "peak_bytes": peak_cache,
                       "axis_denominator_bits": [s.bit_length() for s in cache.scales],
                       "scope": "search cache only; normalized inputs and evidence already exist"}
        del cache
    output.mkdir()
    (output / "plan.json").write_text(core.canonical(plan), encoding="utf-8")
    (output / "input.json").write_text(core.canonical({"request": req, "history": history}), encoding="utf-8")
    return {"case": case, "units": n, "max_states": max_states, "preparation": preparation,
            "fraction_factory_hook_available": original_factory is not None, "status": plan["status"], "complete": plan["complete"],
            "visited_states": plan["visited_states"], "frontier_points": len(plan["frontier"]),
            "selected": plan["selected"], "freeze_digest": plan["freeze_digest"],
            "full_plan_sha256": hashlib.sha256(canonical_profiled.encode()).hexdigest(),
            "actual_counts": counts, "wall_seconds_median": statistics.median(times),
            "tracemalloc_retained_result_bytes": current, "tracemalloc_peak_bytes": peak,
            "process_lifetime_rss_highwater_bytes": rss_highwater(), "input_unchanged": True,
            "scope": "whole plan; profiling separate from timing; RSS highwater includes process lifetime"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-states", type=int, default=4096)
    parser.add_argument("--units", type=int, nargs="+", default=[16, 18, 20])
    parser.add_argument("--assert-precomputed", action="store_true")
    parser.add_argument("--case", choices=["standard", "empty-history", "independent", "frontier"], default="standard")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    results = [measure(n, args.max_states, args.output / f"units-{n}", args.case) for n in args.units]
    (args.output / "result.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    if args.assert_precomputed:
        assert all(r["actual_counts"]["fraction_string_constructions"] < 1000 for r in results), "subset loop still repeats rational string parsing"
