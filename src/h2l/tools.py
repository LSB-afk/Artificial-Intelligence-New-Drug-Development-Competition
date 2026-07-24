"""Versioned tool adapters for the molecular optimization loop.

Each adapter turns molecular descriptors into a bounded ``ToolResult`` that
keeps the evidence type explicit — ``measured``, ``model``, or ``proxy`` — per
the project rule that measured activity, model prediction, and similarity proxy
must never be conflated.

These reference adapters are deterministic and offline: they read descriptors
that are already present on the molecule record instead of computing them with
RDKit. A trained model or hosted API (ADMET-AI, a validated QSAR model,
SA/RAscore, AiZynthFinder) plugs in later by implementing the same
``(molecule) -> ToolResult`` contract; the optimization loop and the evaluation
plane do not change. This is the seam where "learned" accuracy enters without
touching orchestration or fine-tuning the LLM.
"""
from __future__ import annotations

EVIDENCE_TYPES = {"measured", "model", "proxy", "unknown"}

# Names of the reference tool lineage, in stable order (used for traceability).
DEFAULT_TOOL_NAMES = [
    "druglikeness",
    "similarity_proxy",
    "admet_risk",
    "synthesizability",
    "safety_alerts",
]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _round(value: float) -> float:
    # Fixed precision keeps emitted JSON byte-reproducible across runs.
    return round(float(value), 6)


def tool_result(name, value, evidence_type, confidence, limitation, evidence=None):
    if evidence_type not in EVIDENCE_TYPES:
        raise ValueError(f"unknown evidence_type: {evidence_type}")
    return {
        "tool": name,
        "value": value,
        "evidence_type": evidence_type,
        "confidence": _round(confidence),
        "limitation": limitation,
        "evidence": list(evidence or []),
    }


def _trapezoid(x: float, a: float, b: float, c: float, d: float) -> float:
    """Desirability 0 outside [a, d], ramping to 1 across [b, c]."""
    if x <= a or x >= d:
        return 0.0
    if x < b:
        return (x - a) / (b - a)
    if x <= c:
        return 1.0
    return (d - x) / (d - c)


def druglikeness(mol: dict) -> dict:
    """Lipinski/Veber pass flags plus a QED-like desirability from descriptors."""
    d = mol["descriptors"]
    lipinski = d["mw"] <= 500 and d["logp"] <= 5 and d["hbd"] <= 5 and d["hba"] <= 10
    veber = d["rotatable"] <= 10 and d["tpsa"] <= 140
    parts = [
        _trapezoid(d["mw"], 180, 280, 420, 520),
        _trapezoid(d["logp"], -0.5, 1.0, 3.5, 5.2),
        _trapezoid(d["tpsa"], 20, 45, 110, 150),
        _trapezoid(d["hbd"], -1, 0, 3, 5.5),
        _trapezoid(d["hba"], 0, 2, 8, 11),
        _trapezoid(d["rotatable"], -1, 1, 8, 11),
    ]
    qed = sum(parts) / len(parts)
    return tool_result(
        "druglikeness",
        {"qed": _round(qed), "lipinski_pass": lipinski, "veber_pass": veber},
        "model",
        0.7,
        "rule-based reference (Lipinski/Veber + QED-like); replace with RDKit QED",
    )


def _tanimoto(fp1, fp2) -> float:
    s1 = {i for i, bit in enumerate(fp1) if bit}
    s2 = {i for i, bit in enumerate(fp2) if bit}
    union = len(s1 | s2)
    return (len(s1 & s2) / union) if union else 0.0


def similarity_proxy(mol: dict, reference_actives: list[dict]) -> dict:
    """Max Tanimoto to a reference active set. A proxy — never activity."""
    best = 0.0
    nearest = None
    for ref in reference_actives:
        score = _tanimoto(mol["fingerprint"], ref["fingerprint"])
        if score > best or (score == best and (nearest is None or ref["id"] < nearest)):
            best = score
            nearest = ref["id"]
    return tool_result(
        "similarity_proxy",
        {"tanimoto": _round(best), "nearest": nearest},
        "proxy",
        0.5,
        "similarity is not measured or predicted activity",
    )


def admet_risk(mol: dict) -> dict:
    """Reference ADMET risk flags + a safety score. Replace with ADMET-AI."""
    d = mol["descriptors"]
    alerts = mol.get("alerts", [])
    herg = "high" if (d["logp"] > 4.5 and d["aromatic_rings"] >= 3) else ("warn" if d["logp"] > 3.5 else "low")
    ames = "high" if "mutagenic" in alerts else "low"
    dili = "warn" if (d["mw"] > 450 and d["logp"] > 4) else "low"
    cyp3a4 = "warn" if d["logp"] > 4 else "low"
    weight = {"low": 0.0, "warn": 0.5, "high": 1.0}
    risk = weight[herg] * 0.4 + weight[ames] * 0.3 + weight[dili] * 0.2 + weight[cyp3a4] * 0.1
    return tool_result(
        "admet_risk",
        {"herg": herg, "ames": ames, "dili": dili, "cyp3a4": cyp3a4, "admet_safety_score": _round(1.0 - risk)},
        "model",
        0.55,
        "reference heuristic; replace with ADMET-AI after version-pinned smoke validation",
    )


def synthesizability(mol: dict) -> dict:
    """Reference SA-like score (lower is easier). Replace with SA/RAscore."""
    d = mol["descriptors"]
    sa = 1.0 + 0.09 * d["heavy_atoms"] + 0.25 * d["aromatic_rings"] + 0.12 * d["rotatable"]
    return tool_result(
        "synthesizability",
        {"sa_score": _round(min(sa, 10.0)), "route_found": None},
        "model",
        0.5,
        "reference SA proxy; replace with SA/RAscore, optional AiZynthFinder top-5",
    )


def safety_alerts(mol: dict) -> dict:
    """Structural alert flags from provided annotations. Replace with RDKit."""
    alerts = [a for a in mol.get("alerts", []) if a in {"pains", "reactive", "toxicophore", "mutagenic"}]
    return tool_result(
        "safety_alerts",
        {"alerts": sorted(alerts)},
        "model",
        0.6,
        "structural alert flags from provided annotations; replace with RDKit filter catalogs",
    )
