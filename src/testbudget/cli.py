from __future__ import annotations

import argparse
import json
import sys

from .core import InputError, select
from .workflow import load_json, record, save_json, simulate, verify_plan


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Freeze revision-aware constrained CI plans; no pass guarantee.")
    commands = parser.add_subparsers(dest="command", required=True)
    selection = commands.add_parser("select")
    selection.add_argument("--request", required=True)
    selection.add_argument("--history", required=True)
    selection.add_argument("--out", required=True)
    simulation = commands.add_parser("simulate", help="only disclosed synthetic/demo outcomes; runs no commands")
    simulation.add_argument("--plan", required=True)
    simulation.add_argument("--outcomes", required=True)
    simulation.add_argument("--out", required=True)
    recording = commands.add_parser("record")
    recording.add_argument("--plan", required=True)
    recording.add_argument("--execution", required=True)
    recording.add_argument("--history", required=True)
    recording.add_argument("--out", required=True)
    try:
        if args := parser.parse_args(argv):
            if args.command == "select":
                result = select(load_json(args.request), load_json(args.history))
                save_json(args.out, result)
                print(json.dumps({"status": result["status"], "selected": result["selected"], "complete": result["complete"], "frontier_points": len(result["frontier"]), "freeze_digest": result["freeze_digest"]}))
                return {"FEASIBLE": 0, "INFEASIBLE": 3, "UNKNOWN": 4}[result["status"]]
            plan = load_json(args.plan)
            verify_plan(plan)  # Outcomes are opened only after decision verification.
            if args.command == "simulate":
                result = simulate(plan, load_json(args.outcomes))
                save_json(args.out, result)
                print(json.dumps({"simulation": True, "attempts": len(result["attempts"])}))
            else:
                result = record(plan, load_json(args.execution), load_json(args.history))
                save_json(args.out, result)
                print(json.dumps({"history_attempts": len(result)}))
            return 0
    except (InputError, OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2
    return 2
