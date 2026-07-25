"""RDKit-backed tool adapters for the molecular optimization loop.

``tools.py`` defines the ``(molecule) -> ToolResult`` contract with deterministic
reference adapters that read descriptors already present on the molecule record.
This module implements the same contract against real chemistry: descriptors,
QED, Morgan fingerprints, a synthetic-accessibility score, and structural alert
catalogs are computed from the candidate's SMILES.

What actually changes when this backend is selected:

- ``druglikeness`` returns RDKit ``QED.qed`` and Lipinski/Veber flags from
  computed descriptors instead of a trapezoid approximation,
- ``similarity_proxy`` returns a real ECFP4 (Morgan radius 2, 2048 bit) Tanimoto
  instead of a 16-bit hand-authored bit vector,
- ``safety_alerts`` matches the RDKit PAINS and Brenk ``FilterCatalog`` instead
  of reading a list of strings off the record,
- ``synthesizability`` returns the RDKit Contrib SA score instead of an
  atom-count formula.

``admet_risk`` stays a heuristic. It now runs on measured-quality descriptors,
but it is still a rule of thumb and is labelled as such — swapping in ADMET-AI is
the next step at this same seam, and R-003 requires a version-pinned smoke test
before any accuracy claim.

RDKit is an optional dependency. Importing this module without it raises
``ChemBackendUnavailable``; the reference backend stays the default so the core
remains dependency-free and the seeded evaluations stay byte-reproducible.
"""
from __future__ import annotations

import os
import sys
from functools import lru_cache

from h2l.tools import _clamp, _round, tool_result

BACKEND_NAME = "rdkit"
MORGAN_RADIUS = 2
MORGAN_BITS = 2048

# Alert classes associated with mutagenicity. Used only to set the reported
# ``ames`` flag; this is a structural-alert heuristic, not an Ames assay result.
MUTAGENICITY_ALERTS = {
    "nitro_group",
    "aromatic_nitro",
    "nitroso",
    "azo_group",
    "diazo_group",
    "epoxide",
    "aziridine",
    "hydrazine",
    "n-oxide",
    "michael_acceptor",
    "quinone_a(370)",
    "chinone_1",
    "chinone_2",
}


class ChemBackendUnavailable(RuntimeError):
    """Raised when the RDKit backend is requested but RDKit is not installed."""


def _load_rdkit():
    try:
        from rdkit import Chem, DataStructs, RDLogger
        from rdkit.Chem import QED, Descriptors, RDConfig, rdFingerprintGenerator
        from rdkit.Chem.FilterCatalog import FilterCatalog, FilterCatalogParams
    except ImportError as error:  # pragma: no cover - exercised only without rdkit
        raise ChemBackendUnavailable(
            "RDKit is not installed. Install `rdkit` or use the reference backend "
            "(H2L_CHEM_BACKEND=reference)."
        ) from error

    RDLogger.DisableLog("rdApp.*")
    sa_dir = os.path.join(RDConfig.RDContribDir, "SA_Score")
    if sa_dir not in sys.path:
        sys.path.append(sa_dir)
    import sascorer  # noqa: E402  (path is only valid after the append above)

    return {
        "Chem": Chem,
        "DataStructs": DataStructs,
        "QED": QED,
        "Descriptors": Descriptors,
        "sascorer": sascorer,
        "generator": rdFingerprintGenerator.GetMorganGenerator(radius=MORGAN_RADIUS, fpSize=MORGAN_BITS),
        "catalog": _build_catalog(FilterCatalog, FilterCatalogParams),
    }


def _build_catalog(FilterCatalog, FilterCatalogParams):
    params = FilterCatalogParams()
    params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS)
    params.AddCatalog(FilterCatalogParams.FilterCatalogs.BRENK)
    return FilterCatalog(params)


@lru_cache(maxsize=1)
def _rdkit():
    return _load_rdkit()


def available() -> bool:
    """True when the RDKit backend can be used."""
    try:
        _rdkit()
    except ChemBackendUnavailable:
        return False
    return True


@lru_cache(maxsize=1)
def version() -> str:
    import rdkit

    return str(rdkit.__version__)


def _require_smiles(mol: dict) -> str:
    smiles = mol.get("smiles")
    if not smiles:
        raise ValueError(f"molecule {mol.get('candidate_id') or mol.get('id')} has no SMILES for the rdkit backend")
    return smiles


@lru_cache(maxsize=512)
def _parse(smiles: str):
    mol = _rdkit()["Chem"].MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"RDKit could not parse SMILES: {smiles}")
    return mol


@lru_cache(maxsize=512)
def _fingerprint(smiles: str):
    return _rdkit()["generator"].GetFingerprint(_parse(smiles))


def descriptors(smiles: str) -> dict:
    """The descriptor block the loop consumes, computed from the structure."""
    d = _rdkit()["Descriptors"]
    mol = _parse(smiles)
    return {
        "mw": _round(d.MolWt(mol)),
        "logp": _round(d.MolLogP(mol)),
        "hbd": d.NumHDonors(mol),
        "hba": d.NumHAcceptors(mol),
        "tpsa": _round(d.TPSA(mol)),
        "rotatable": d.NumRotatableBonds(mol),
        "aromatic_rings": d.NumAromaticRings(mol),
        "heavy_atoms": mol.GetNumHeavyAtoms(),
    }


def _backed(name, value, evidence_type, confidence, limitation, evidence=None) -> dict:
    result = tool_result(name, value, evidence_type, confidence, limitation, evidence)
    result["backend"] = BACKEND_NAME
    result["backend_version"] = version()
    return result


# ---- adapters ----------------------------------------------------------
def druglikeness(mol: dict) -> dict:
    """RDKit QED plus Lipinski/Veber flags from computed descriptors."""
    smiles = _require_smiles(mol)
    d = descriptors(smiles)
    lipinski = d["mw"] <= 500 and d["logp"] <= 5 and d["hbd"] <= 5 and d["hba"] <= 10
    veber = d["rotatable"] <= 10 and d["tpsa"] <= 140
    qed = _rdkit()["QED"].qed(_parse(smiles))
    return _backed(
        "druglikeness",
        {"qed": _round(qed), "lipinski_pass": lipinski, "veber_pass": veber},
        "model",
        0.85,
        "RDKit QED and Lipinski/Veber flags computed from the structure",
    )


def similarity_proxy(mol: dict, reference_actives: list[dict]) -> dict:
    """Max ECFP4 Tanimoto to the reference set. A proxy — never activity."""
    fp = _fingerprint(_require_smiles(mol))
    similarity = _rdkit()["DataStructs"].TanimotoSimilarity
    best = 0.0
    nearest = None
    for ref in reference_actives:
        score = similarity(fp, _fingerprint(_require_smiles(ref)))
        ref_id = ref.get("id")
        if score > best or (score == best and (nearest is None or str(ref_id) < str(nearest))):
            best = score
            nearest = ref_id
    return _backed(
        "similarity_proxy",
        {"tanimoto": _round(best), "nearest": nearest},
        "proxy",
        0.6,
        f"ECFP4 (Morgan r={MORGAN_RADIUS}, {MORGAN_BITS} bit) Tanimoto; similarity is not measured or predicted activity",
    )


def admet_risk(mol: dict) -> dict:
    """Structural-alert and descriptor heuristic. Replace with ADMET-AI."""
    d = descriptors(_require_smiles(mol))
    alerts = safety_alerts(mol)["value"]["alerts"]
    herg = "high" if (d["logp"] > 4.5 and d["aromatic_rings"] >= 3) else ("warn" if d["logp"] > 3.5 else "low")
    ames = "high" if any(alert in MUTAGENICITY_ALERTS for alert in alerts) else "low"
    dili = "warn" if (d["mw"] > 450 and d["logp"] > 4) else "low"
    cyp3a4 = "warn" if d["logp"] > 4 else "low"
    weight = {"low": 0.0, "warn": 0.5, "high": 1.0}
    risk = weight[herg] * 0.4 + weight[ames] * 0.3 + weight[dili] * 0.2 + weight[cyp3a4] * 0.1
    return _backed(
        "admet_risk",
        {"herg": herg, "ames": ames, "dili": dili, "cyp3a4": cyp3a4, "admet_safety_score": _round(1.0 - risk)},
        "model",
        0.55,
        "heuristic over RDKit descriptors and alert catalogs, not an assay; replace with ADMET-AI after a version-pinned smoke test",
    )


def synthesizability(mol: dict) -> dict:
    """RDKit Contrib SA score (1 easy … 10 hard). Retrosynthesis stays unrun."""
    score = _rdkit()["sascorer"].calculateScore(_parse(_require_smiles(mol)))
    return _backed(
        "synthesizability",
        {"sa_score": _round(min(score, 10.0)), "route_found": None},
        "model",
        0.65,
        "RDKit Contrib SA score; no retrosynthetic route was searched (AiZynthFinder top-5 remains planned)",
    )


def safety_alerts(mol: dict) -> dict:
    """PAINS + Brenk structural alerts matched against the real structure."""
    matches = _rdkit()["catalog"].GetMatches(_parse(_require_smiles(mol)))
    alerts = sorted({entry.GetDescription().strip().lower() for entry in matches})
    return _backed(
        "safety_alerts",
        {"alerts": alerts},
        "model",
        0.75,
        "RDKit FilterCatalog PAINS + Brenk substructure matches",
    )
