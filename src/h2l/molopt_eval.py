"""Read-only ablation for the molecular optimization loop.

Mirrors ``eval_runner`` for field 2: a proxy-only baseline scorer versus the
multi-objective tool-adapter candidate scorer, measured against a fixed labeled
pool. This is the concrete "raise the inference rate without weight-training the
LLM" claim — the accuracy gain comes from the tools and the multi-objective
gate, and it is byte-reproducible under a fixed seed.

The plane holds no mutation handle, makes no therapeutic claim, and runs
``METHOD_ONLY``. ``label_desirability`` is ground truth used only for scoring;
neither scorer sees it.
"""
from __future__ import annotations

import json
from pathlib import Path

from h2l.eval_runner import paired_bootstrap
from h2l.molopt import score_molecule
from h2l.tools import _round, similarity_proxy


def load_pool(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _top_k_ids(scores: dict, top_k: int) -> list[str]:
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return [candidate_id for candidate_id, _ in ranked[:top_k]]


def _candidate_scores(pool: list[dict], reference_actives: list[dict]) -> dict:
    # Multi-objective composite; hard-gate failures are scored 0 (excluded).
    scores = {}
    for mol in sorted(pool, key=lambda m: m["candidate_id"]):
        scored = score_molecule(mol, reference_actives)
        scores[mol["candidate_id"]] = 0.0 if scored["hard_fail"] else scored["composite_score"]
    return scores


def _baseline_scores(pool: list[dict], reference_actives: list[dict]) -> dict:
    # Proxy-only: rank purely by similarity to known actives.
    return {
        mol["candidate_id"]: similarity_proxy(mol, reference_actives)["value"]["tanimoto"]
        for mol in sorted(pool, key=lambda m: m["candidate_id"])
    }


def _metrics(top: list[str], correct: list[int], truth: dict, good_ids: list[str]) -> dict:
    hits = sum(1 for candidate_id in top if truth[candidate_id])
    return {
        "selection_accuracy": _round(sum(correct) / len(correct)) if correct else 0.0,
        "top_k_precision": _round(hits / len(top)) if top else 0.0,
        "top_k_recall": _round(hits / len(good_ids)) if good_ids else 0.0,
        "top_k": sorted(top),
    }


def run_molopt_eval(doc: dict) -> dict:
    pool = doc["pool"]
    reference_actives = doc["reference_actives"]
    seed = doc.get("seed", 42)
    top_k = doc.get("top_k", 5)
    iterations = doc.get("bootstrap_iterations", 10000)
    threshold = doc.get("good_threshold", 0.7)

    ids = sorted(mol["candidate_id"] for mol in pool)
    truth = {mol["candidate_id"]: (mol["label_desirability"] >= threshold) for mol in pool}
    good_ids = sorted(candidate_id for candidate_id, good in truth.items() if good)

    baseline_scores = _baseline_scores(pool, reference_actives)
    candidate_scores = _candidate_scores(pool, reference_actives)
    baseline_top = _top_k_ids(baseline_scores, top_k)
    candidate_top = _top_k_ids(candidate_scores, top_k)

    # Per-molecule correctness: does the scorer's include/exclude match truth?
    baseline_correct = [int((candidate_id in baseline_top) == truth[candidate_id]) for candidate_id in ids]
    candidate_correct = [int((candidate_id in candidate_top) == truth[candidate_id]) for candidate_id in ids]

    bootstrap = paired_bootstrap(baseline_correct, candidate_correct, iterations=iterations, seed=seed)

    return {
        "task": "molecular ranking: proxy-only baseline vs multi-objective tool-adapter candidate",
        "run_mode": "METHOD_ONLY",
        "therapeutic_claim": False,
        "molecule_count": len(pool),
        "good_count": len(good_ids),
        "top_k": top_k,
        "seed": seed,
        "baseline": _metrics(baseline_top, baseline_correct, truth, good_ids),
        "candidate": _metrics(candidate_top, candidate_correct, truth, good_ids),
        "paired_bootstrap": bootstrap,
        "eval_plane_readonly": True,
    }
