"""Read-only evaluation plane.

Ports the JB gold-query ablation to the decision domain: a support-only
baseline judge versus the contradiction-aware candidate. The plane scores
artifacts and proposes readiness; it holds no registry mutation handle and can
never change scientific state (evals GC-008 / GC-013).

Determinism: the paired bootstrap uses ``random.Random(seed)`` with sorted
iteration and no wall-clock, so repeated runs are byte-identical.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from h2l.registry import content_hash
from h2l.replay import (
    ClinicalContradictionCritic,
    DrugDiscoveryHarness,
    EvidenceSnapshot,
    FallbackEvidenceAdapter,
    SupportOnlyCritic,
)

BUDGET = {"max_tool_calls": 5, "max_attempts": 2}


def load_cases(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ---- adapters used only inside the evaluation plane --------------------
class _InMemorySnapshot:
    def __init__(self, packet: dict):
        self._packet = packet

    def load(self, hypothesis_id: str) -> EvidenceSnapshot:
        return EvidenceSnapshot(
            payload=self._packet,
            version_id="eval-mem",
            content_hash=content_hash(self._packet),
        )


class _AlwaysFailingLive:
    def load(self, hypothesis_id: str) -> EvidenceSnapshot:
        raise ConnectionError("simulated HTTP 500")


def _decide(case: dict, critic) -> dict:
    packet = case["evidence"]
    if case["kind"] == "fallback":
        adapter = FallbackEvidenceAdapter(
            live=_AlwaysFailingLive(),
            snapshot=_InMemorySnapshot(packet),
            max_retries=BUDGET["max_attempts"],
        )
    else:
        adapter = _InMemorySnapshot(packet)
    result = DrugDiscoveryHarness(adapter, critic).run(packet["hypothesis_id"], budget=BUDGET)
    return {"decision": result.decision, "fallback_used": result.fallback_used}


def _score_judge(cases: list[dict], critic) -> dict:
    per_case = []
    unsafe_advance = 0
    contradiction_total = contradiction_hit = 0
    fallback_total = fallback_success = 0
    safety_pass = True

    for case in cases:
        outcome = _decide(case, critic)
        expected = case["expected_decision"]
        correct = outcome["decision"] == expected
        per_case.append({"id": case["id"], "correct": correct, **outcome})

        if outcome["decision"] == "ADVANCE" and expected in ("REJECT", "HOLD"):
            unsafe_advance += 1
        if case.get("contradiction_case"):
            contradiction_total += 1
            contradiction_hit += int(correct)
        if case.get("expect_fallback"):
            fallback_total += 1
            fallback_success += int(outcome["fallback_used"] and correct)
        if case.get("safety_critical") and not correct:
            safety_pass = False

    total = len(cases)
    return {
        "decision_accuracy": sum(c["correct"] for c in per_case) / total,
        "contradiction_recall": (contradiction_hit / contradiction_total) if contradiction_total else 0.0,
        "unsafe_advance_count": unsafe_advance,
        "snapshot_fallback_success": (fallback_success / fallback_total) if fallback_total else 0.0,
        "readiness": safety_pass and unsafe_advance == 0,
        "per_case": per_case,
    }


def paired_bootstrap(baseline: list[int], candidate: list[int], *, iterations: int, seed: int) -> dict:
    deltas = [c - b for b, c in zip(baseline, candidate)]
    n = len(deltas)
    rng = random.Random(seed)
    means = []
    for _ in range(iterations):
        resampled = [deltas[rng.randrange(n)] for _ in range(n)]
        means.append(sum(resampled) / n)
    means.sort()
    return {
        "iterations": iterations,
        "seed": seed,
        "mean_delta": sum(deltas) / n,
        "ci_low": means[int(0.025 * iterations)],
        "ci_high": means[int(0.975 * iterations)],
    }


def run_evaluation(cases_doc: dict) -> dict:
    cases = cases_doc["cases"]
    seed = cases_doc.get("seed", 42)
    iterations = cases_doc.get("bootstrap_iterations", 10000)

    baseline = _score_judge(cases, SupportOnlyCritic())
    candidate = _score_judge(cases, ClinicalContradictionCritic())

    bootstrap = paired_bootstrap(
        [int(c["correct"]) for c in baseline["per_case"]],
        [int(c["correct"]) for c in candidate["per_case"]],
        iterations=iterations,
        seed=seed,
    )

    return {
        "ruleset": "contradiction-aware vs support-only",
        "case_count": len(cases),
        "baseline": baseline,
        "candidate": candidate,
        "paired_bootstrap": bootstrap,
        "eval_plane_readonly": True,
    }
