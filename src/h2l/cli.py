"""Command-line entry point for the H2L-Forge decision harness.

    python -m h2l.cli run  --evidence <packet.json>   # seed, approve, decide
    python -m h2l.cli eval --cases <cases.json> [--out <report.json>]

Output is deterministic JSON on stdout so runs can be diffed and replayed.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from h2l.eval_runner import load_cases, run_evaluation
from h2l.molopt import optimize
from h2l.molopt_eval import load_pool, run_molopt_eval
from h2l.registry import SnapshotRegistry
from h2l.replay import ClinicalContradictionCritic, DrugDiscoveryHarness, SnapshotEvidenceAdapter

BUDGET = {"max_tool_calls": 5, "max_attempts": 2}


def _dumps(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def cmd_run(args: argparse.Namespace) -> int:
    packet = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        registry = SnapshotRegistry(Path(tmp) / "registry.json")
        version = registry.detect(packet["hypothesis_id"], packet, observed_at=packet["observed_at"])
        registry.approve(version["version_id"], actor="cli_reviewer", approved_at=packet["observed_at"])
        harness = DrugDiscoveryHarness(SnapshotEvidenceAdapter(registry), ClinicalContradictionCritic())
        result = harness.run(packet["hypothesis_id"], budget=BUDGET)
    print(_dumps(result.to_dict()))
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    report = run_evaluation(load_cases(Path(args.cases)))
    rendered = _dumps(report)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


def cmd_molopt(args: argparse.Namespace) -> int:
    doc = json.loads(Path(args.pool).read_text(encoding="utf-8"))
    result = optimize(
        doc["pool"],
        doc["reference_actives"],
        run_mode=args.run_mode,
        target_decision=args.target_decision,
        top_k=doc.get("top_k", 5),
        seed=doc.get("seed", 42),
    )
    print(_dumps(result))
    return 0


def cmd_molopt_eval(args: argparse.Namespace) -> int:
    report = run_molopt_eval(load_pool(Path(args.pool)))
    rendered = _dumps(report)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="h2l", description="Evidence-critical drug-discovery decision harness.")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="run one decision over an approved evidence packet")
    run_p.add_argument("--evidence", required=True, help="path to a normalized evidence packet JSON")
    run_p.set_defaults(func=cmd_run)

    eval_p = sub.add_parser("eval", help="run the read-only baseline vs candidate evaluation")
    eval_p.add_argument("--cases", required=True, help="path to the decision cases JSON")
    eval_p.add_argument("--out", help="optional path to write the report JSON")
    eval_p.set_defaults(func=cmd_eval)

    molopt_p = sub.add_parser("molopt", help="run the eligibility-gated molecular optimization loop")
    molopt_p.add_argument("--pool", required=True, help="path to a candidate pool JSON")
    molopt_p.add_argument("--run-mode", default="METHOD_ONLY", choices=["METHOD_ONLY", "SCIENTIFIC", "REJECTION_DEMO"])
    molopt_p.add_argument("--target-decision", default=None, help="ADVANCE/HOLD/REJECT of the eligible target")
    molopt_p.set_defaults(func=cmd_molopt)

    molopt_eval_p = sub.add_parser("molopt-eval", help="proxy-only vs multi-objective molecular ranking ablation")
    molopt_eval_p.add_argument("--pool", required=True, help="path to a labeled candidate pool JSON")
    molopt_eval_p.add_argument("--out", help="optional path to write the report JSON")
    molopt_eval_p.set_defaults(func=cmd_molopt_eval)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
