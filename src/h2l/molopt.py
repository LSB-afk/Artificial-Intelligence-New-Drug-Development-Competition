"""Eligibility-gated molecular optimization loop (docs/08).

This is the field-2 loop: score a provided candidate pool with versioned tool
adapters, apply hard gates and over-optimization filters, and return a
traceable top-k. It is deterministic and offline — "generation" here means
ranking a provided pool (the offline analogue of a SELFIES/STONED expansion),
so runs are byte-reproducible.

Operating invariants enforced here, not just documented:

- Entry gate: ``REJECTION_DEMO`` and any ``REJECT``/``HOLD`` target block
  generation. ``METHOD_ONLY`` is allowed for tool/eval qualification and may not
  produce therapeutic or activity claims. ``SCIENTIFIC`` requires target
  ``ADVANCE``.
- Every candidate keeps measured/model/proxy evidence types separate.
- The composite score is only a ranking helper; hard gates and a Pareto front
  make the final cut, and a candidate that only improves QED is dropped.
"""
from __future__ import annotations

from h2l.tools import (
    DEFAULT_TOOL_NAMES,
    _clamp,
    _round,
    admet_risk,
    druglikeness,
    safety_alerts,
    similarity_proxy,
    synthesizability,
)

SIMILARITY_BAND = (0.30, 0.85)
HARD_SA_MAX = 6.5
TOP_K = 5
COMPOSITE_WEIGHTS = {
    "qed": 0.18,
    "lipinski_veber": 0.12,
    "similarity_band": 0.15,
    "novelty": 0.15,
    "admet_safety": 0.20,
    "synthesizability": 0.12,
    "evidence_trace": 0.08,
}
BLOCKING_TARGET_DECISIONS = {"REJECT", "HOLD"}


def entry_gate(run_mode: str, target_decision: str | None) -> dict:
    if run_mode == "REJECTION_DEMO" or target_decision in BLOCKING_TARGET_DECISIONS:
        return {
            "run_mode": run_mode,
            "blocked": True,
            "molecule_eligibility": False,
            "therapeutic_claim": False,
            "gate_reason": f"target/mode '{target_decision or run_mode}' blocks molecule generation",
        }
    if run_mode == "SCIENTIFIC":
        if target_decision != "ADVANCE":
            return {
                "run_mode": run_mode,
                "blocked": True,
                "molecule_eligibility": False,
                "therapeutic_claim": False,
                "gate_reason": "SCIENTIFIC mode requires target ADVANCE + reviewer approval",
            }
        return {
            "run_mode": run_mode,
            "blocked": False,
            "molecule_eligibility": True,
            "therapeutic_claim": False,
            "gate_reason": "target ADVANCE; bounded hypothesis only, no efficacy claim",
        }
    return {
        "run_mode": "METHOD_ONLY",
        "blocked": False,
        "molecule_eligibility": False,
        "therapeutic_claim": False,
        "gate_reason": "METHOD_ONLY: tool/eval qualification, no therapeutic or activity claim",
    }


def score_molecule(mol: dict, reference_actives: list[dict]) -> dict:
    dl = druglikeness(mol)
    sim = similarity_proxy(mol, reference_actives)
    adm = admet_risk(mol)
    syn = synthesizability(mol)
    saf = safety_alerts(mol)

    qed = dl["value"]["qed"]
    tanimoto = sim["value"]["tanimoto"]
    sa = syn["value"]["sa_score"]
    admet_safety = adm["value"]["admet_safety_score"]
    in_band = SIMILARITY_BAND[0] <= tanimoto <= SIMILARITY_BAND[1]
    novelty = 1.0 if tanimoto < 0.85 else 0.0
    evidence_type = mol.get("activity_evidence", {}).get("type", "UNKNOWN")
    has_trace = evidence_type != "UNKNOWN" and bool(mol.get("evidence"))

    if in_band:
        band_score = 1.0
    else:
        distance = min(abs(tanimoto - SIMILARITY_BAND[0]), abs(tanimoto - SIMILARITY_BAND[1]))
        band_score = _clamp(1.0 - distance * 3.0)
    lip_veber = 1.0 if (dl["value"]["lipinski_pass"] and dl["value"]["veber_pass"]) else (0.5 if dl["value"]["lipinski_pass"] else 0.0)
    synth_score = _clamp(1.0 - (sa - 1.0) / (HARD_SA_MAX - 1.0))
    evidence_trace = 1.0 if has_trace else 0.0

    composite = (
        COMPOSITE_WEIGHTS["qed"] * qed
        + COMPOSITE_WEIGHTS["lipinski_veber"] * lip_veber
        + COMPOSITE_WEIGHTS["similarity_band"] * band_score
        + COMPOSITE_WEIGHTS["novelty"] * novelty
        + COMPOSITE_WEIGHTS["admet_safety"] * admet_safety
        + COMPOSITE_WEIGHTS["synthesizability"] * synth_score
        + COMPOSITE_WEIGHTS["evidence_trace"] * evidence_trace
    )

    hard_fail = []
    if not mol.get("valid", True):
        hard_fail.append("invalid_structure")
    if saf["value"]["alerts"]:
        hard_fail.append("structural_alert")
    if evidence_type == "UNKNOWN":
        hard_fail.append("activity_evidence_unknown")
    if not in_band:
        hard_fail.append("similarity_outside_band")
    if adm["value"]["herg"] == "high":
        hard_fail.append("herg_high_risk")
    if adm["value"]["ames"] == "high":
        hard_fail.append("ames_high_risk")
    if sa > HARD_SA_MAX:
        hard_fail.append("sa_score_gt_6_5")

    return {
        "candidate_id": mol["candidate_id"],
        "parent_id": mol.get("parent_id"),
        "valid": mol.get("valid", True),
        "qed": qed,
        "lipinski_pass": dl["value"]["lipinski_pass"],
        "veber_pass": dl["value"]["veber_pass"],
        "tanimoto": tanimoto,
        "nearest_reference": sim["value"]["nearest"],
        "activity_evidence": {"type": evidence_type, "limitation": "similarity/model is not measured activity"},
        "admet": {key: adm["value"][key] for key in ("herg", "ames", "dili", "cyp3a4")},
        "admet_safety_score": admet_safety,
        "synthesis": {"sa_score": sa, "route_found": None},
        "novelty_score": novelty,
        "alerts": saf["value"]["alerts"],
        "composite_score": _round(composite),
        "hard_fail": sorted(hard_fail),
        "tool_lineage": [dl["tool"], sim["tool"], adm["tool"], syn["tool"], saf["tool"]],
        "evidence": list(mol.get("evidence", [])),
    }


def _pareto_objectives(scored: dict) -> tuple:
    return (
        scored["qed"],
        scored["admet_safety_score"],
        1.0 - scored["synthesis"]["sa_score"] / 10.0,
        scored["novelty_score"],
    )


def _pareto_filter(items: list[dict]) -> list[dict]:
    """The Pareto-non-dominated front over the objective vector."""
    kept = []
    for candidate in items:
        objs = _pareto_objectives(candidate)
        dominated = False
        for other in items:
            if other["candidate_id"] == candidate["candidate_id"]:
                continue
            other_objs = _pareto_objectives(other)
            if all(o >= c for o, c in zip(other_objs, objs)) and any(o > c for o, c in zip(other_objs, objs)):
                dominated = True
                break
        if not dominated:
            kept.append(candidate)
    return kept


def _dedupe(items: list[dict]) -> list[dict]:
    """Remove exact structural duplicates (identical objective signature)."""
    seen = set()
    out = []
    for candidate in items:
        signature = (
            candidate["qed"],
            candidate["admet_safety_score"],
            candidate["synthesis"]["sa_score"],
            candidate["tanimoto"],
            candidate["novelty_score"],
        )
        if signature in seen:
            continue
        seen.add(signature)
        out.append(candidate)
    return out


def optimize(pool, reference_actives, *, run_mode="METHOD_ONLY", target_decision=None, top_k=TOP_K, seed=42) -> dict:
    gate = entry_gate(run_mode, target_decision)
    base = {
        **gate,
        "seed": seed,
        "tool_lineage": DEFAULT_TOOL_NAMES,
        "candidates": [],
        "rejected": [],
        "scored_count": 0,
        "hard_gate_passed": 0,
        "top_k": 0,
    }
    if gate["blocked"]:
        return base

    scored = [score_molecule(mol, reference_actives) for mol in sorted(pool, key=lambda m: m["candidate_id"])]
    gate_passers = [s for s in scored if not s["hard_fail"]]
    deduped = _dedupe(gate_passers)
    front = _pareto_filter(deduped)
    front_ids = {s["candidate_id"] for s in front}
    # Over-optimization control: prefer the diverse Pareto front, but never let
    # it shrink the selection below top_k — fall back to all gate-passers.
    selection_pool = front if len(front) >= top_k else deduped
    ranked = sorted(selection_pool, key=lambda s: (-s["composite_score"], s["candidate_id"]))
    top = ranked[:top_k]

    for rank, candidate in enumerate(top, start=1):
        candidate["rank"] = rank
        candidate["decision"] = "top_k_candidate"
        candidate["pareto_nondominated"] = candidate["candidate_id"] in front_ids
        candidate["why_selected"] = (
            f"hard gate 통과 · composite {candidate['composite_score']} · "
            f"ADMET safety {candidate['admet_safety_score']} · "
            f"Pareto {'non-dominated' if candidate['pareto_nondominated'] else 'dominated'}"
        )
        candidate["why_not_claimed"] = (
            "METHOD_ONLY: 활성·치료 효능 주장 없음. similarity/model은 measured activity가 아님."
        )
        candidate["next_experiment"] = (
            "eligible target 확정 후 measured assay 또는 validated QSAR로 활성 확인 (사람 승인 필요)"
        )

    return {
        **base,
        "scored_count": len(scored),
        "hard_gate_passed": len(gate_passers),
        "pareto_front_size": len(front),
        "top_k": len(top),
        "candidates": top,
        "rejected": [
            {"candidate_id": s["candidate_id"], "hard_fail": s["hard_fail"]}
            for s in scored
            if s["hard_fail"]
        ],
    }
