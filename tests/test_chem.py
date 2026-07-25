"""RDKit chemistry backend: real structures behind the same tool contract.

These tests pin what the backend swap is supposed to buy. The reference
adapters read authored descriptors; this backend derives every number from the
structure, so the properties that matter are that it (a) computes rather than
reads, (b) matches published values for known descriptors, (c) finds structural
liabilities the reference backend cannot see, and (d) never becomes required —
the dependency-free path stays the default.
"""
import json
from pathlib import Path

import pytest

from h2l.molopt import optimize, score_molecule
from h2l.molopt_eval import run_molopt_eval
from h2l.tools import REFERENCE_ADAPTERS, resolve_backend

chem = pytest.importorskip("h2l.chem", reason="RDKit is an optional dependency")
pytest.importorskip("rdkit", reason="RDKit is an optional dependency")

POOL_PATH = Path(__file__).parent / "fixtures" / "molopt" / "pool_rdkit.json"

# Aspirin, a molecule whose descriptors are unambiguous and widely published.
ASPIRIN = {"candidate_id": "ASPIRIN", "smiles": "CC(=O)Oc1ccccc1C(=O)O"}
CORE = "C[C@@H]1CCN(C[C@@H]1N(C)c1ncnc2[nH]ccc12)"


@pytest.fixture(scope="module")
def pool_doc() -> dict:
    return json.loads(POOL_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def refs(pool_doc) -> list[dict]:
    return pool_doc["reference_actives"]


@pytest.fixture(scope="module")
def rdkit_tools():
    return resolve_backend("rdkit")


# ---- backend selection -------------------------------------------------
def test_reference_backend_is_the_default(monkeypatch):
    monkeypatch.delenv("H2L_CHEM_BACKEND", raising=False)
    assert resolve_backend() is REFERENCE_ADAPTERS
    assert resolve_backend().name == "reference"


def test_env_selects_the_rdkit_backend(monkeypatch):
    monkeypatch.setenv("H2L_CHEM_BACKEND", "rdkit")
    assert resolve_backend().name == "rdkit"


def test_unknown_backend_is_rejected():
    with pytest.raises(ValueError, match="unknown chemistry backend"):
        resolve_backend("chemdraw")


def test_results_carry_backend_provenance(rdkit_tools):
    result = rdkit_tools.druglikeness(ASPIRIN)
    assert result["backend"] == "rdkit"
    assert result["backend_version"] == chem.version()
    assert REFERENCE_ADAPTERS.druglikeness({"descriptors": {
        "mw": 300, "logp": 2.0, "hbd": 1, "hba": 4, "tpsa": 70, "rotatable": 4,
        "aromatic_rings": 2, "heavy_atoms": 22,
    }})["backend"] == "reference"


# ---- computed, not read ------------------------------------------------
def test_descriptors_match_published_values_for_aspirin():
    d = chem.descriptors(ASPIRIN["smiles"])
    assert d["mw"] == pytest.approx(180.16, abs=0.05)
    assert d["tpsa"] == pytest.approx(63.6, abs=0.1)
    assert d["hbd"] == 1
    assert d["heavy_atoms"] == 13


def test_descriptors_are_ignored_in_favour_of_the_structure(rdkit_tools):
    """An authored descriptor block must not override the real structure."""
    lying = {**ASPIRIN, "descriptors": {"mw": 999, "logp": 99, "hbd": 9, "hba": 9,
                                        "tpsa": 999, "rotatable": 99,
                                        "aromatic_rings": 9, "heavy_atoms": 99}}
    honest = rdkit_tools.druglikeness(lying)
    assert honest["value"]["lipinski_pass"] is True


def test_missing_smiles_fails_loudly(rdkit_tools):
    with pytest.raises(ValueError, match="no SMILES"):
        rdkit_tools.druglikeness({"candidate_id": "NO-STRUCTURE"})


def test_unparseable_smiles_fails_loudly(rdkit_tools):
    with pytest.raises(ValueError, match="could not parse SMILES"):
        rdkit_tools.druglikeness({"candidate_id": "BAD", "smiles": "C(C(C"})


# ---- real chemistry the reference backend cannot see -------------------
def test_catalog_finds_a_pains_catechol(rdkit_tools):
    catechol = {"candidate_id": "CATECHOL", "smiles": CORE + "C(=O)c1ccc(O)c(O)c1"}
    alerts = rdkit_tools.safety_alerts(catechol)["value"]["alerts"]
    assert any("catechol" in alert for alert in alerts)


def test_catalog_finds_a_reactive_michael_acceptor(rdkit_tools):
    acrylamide = {"candidate_id": "ACRYL", "smiles": CORE + "C(=O)C=C"}
    alerts = rdkit_tools.safety_alerts(acrylamide)["value"]["alerts"]
    assert any("michael" in alert for alert in alerts)


def test_a_clean_analogue_raises_no_alert(rdkit_tools):
    clean = {"candidate_id": "CLEAN", "smiles": CORE + "C(=O)COC"}
    assert rdkit_tools.safety_alerts(clean)["value"]["alerts"] == []


def test_nitro_alert_drives_the_ames_flag(rdkit_tools):
    nitro = {"candidate_id": "NITRO", "smiles": CORE + "C(=O)C[N+](=O)[O-]"}
    assert rdkit_tools.admet_risk(nitro)["value"]["ames"] == "high"
    clean = {"candidate_id": "CLEAN", "smiles": CORE + "C(=O)COC"}
    assert rdkit_tools.admet_risk(clean)["value"]["ames"] == "low"


def test_similarity_is_a_real_fingerprint_not_a_bit_list(rdkit_tools, refs):
    identical = rdkit_tools.similarity_proxy({"candidate_id": "SELF", "smiles": refs[0]["smiles"]}, refs)
    assert identical["value"]["tanimoto"] == 1.0
    assert identical["value"]["nearest"] == "REF-ACT-1"

    distant = rdkit_tools.similarity_proxy({"candidate_id": "FRAG", "smiles": "c1ccc2[nH]ccc2c1"}, refs)
    assert distant["value"]["tanimoto"] < 0.3
    assert "ECFP4" in distant["limitation"]


def test_similarity_stays_labelled_a_proxy(rdkit_tools, refs):
    result = rdkit_tools.similarity_proxy({"candidate_id": "SELF", "smiles": refs[0]["smiles"]}, refs)
    assert result["evidence_type"] == "proxy"
    assert "not measured" in result["limitation"]


def test_sa_score_separates_easy_from_hard(rdkit_tools):
    easy = rdkit_tools.synthesizability(ASPIRIN)["value"]["sa_score"]
    hard = rdkit_tools.synthesizability({
        "candidate_id": "HARD",
        "smiles": "CC1=C2C(C(=O)C3(C(CC4C(C3C(C(C2(C)C)(CC1O)O)OC(=O)c1ccccc1)(CO4)OC(C)=O)O)C)OC(=O)C(O)C(NC(=O)c1ccccc1)c1ccccc1",
    })["value"]["sa_score"]
    assert easy < hard


# ---- loop integration --------------------------------------------------
def test_every_rejection_has_a_structural_reason(pool_doc, rdkit_tools):
    result = optimize(pool_doc["pool"], pool_doc["reference_actives"], backend="rdkit")
    assert result["backend"] == "rdkit"
    reasons = {item["candidate_id"]: item["hard_fail"] for item in result["rejected"]}
    assert all(reasons.values()), "a rejection without a reason is not auditable"
    assert "structural_alert" in reasons["H2L-D1"]
    assert "ames_high_risk" in reasons["H2L-D4"]
    assert "similarity_outside_band" in reasons["H2L-D8"]
    assert "activity_evidence_unknown" in reasons["H2L-D9"]


def test_selected_candidates_are_exactly_the_labelled_good_ones(pool_doc):
    result = optimize(pool_doc["pool"], pool_doc["reference_actives"], backend="rdkit")
    good = {mol["candidate_id"] for mol in pool_doc["pool"] if mol["label_desirability"] >= 0.7}
    assert {item["candidate_id"] for item in result["candidates"]} == good


def test_method_only_run_claims_nothing(pool_doc):
    result = optimize(pool_doc["pool"], pool_doc["reference_actives"], backend="rdkit")
    assert result["run_mode"] == "METHOD_ONLY"
    assert result["therapeutic_claim"] is False
    assert result["molecule_eligibility"] is False


def test_multi_objective_beats_similarity_on_real_structures(pool_doc):
    report = run_molopt_eval(pool_doc)
    assert report["backend"] == "rdkit"
    assert report["candidate"]["selection_accuracy"] > report["baseline"]["selection_accuracy"]
    assert report["candidate"]["top_k_precision"] == 1.0
    # The improvement is supported: the paired bootstrap interval excludes zero.
    assert report["paired_bootstrap"]["ci_low"] > 0


def test_similarity_baseline_selects_reactive_liabilities(pool_doc):
    """The reason the multi-objective gate is needed, stated as a test."""
    report = run_molopt_eval(pool_doc)
    liabilities = {"H2L-D1", "H2L-D2", "H2L-D3", "H2L-D4"}
    assert liabilities & set(report["baseline"]["top_k"])
    assert not liabilities & set(report["candidate"]["top_k"])


def test_rdkit_eval_is_byte_reproducible(pool_doc):
    first = json.dumps(run_molopt_eval(pool_doc), sort_keys=True)
    second = json.dumps(run_molopt_eval(pool_doc), sort_keys=True)
    assert first == second


def test_scoring_keeps_evidence_types_separate(pool_doc, rdkit_tools):
    scored = score_molecule(pool_doc["pool"][0], pool_doc["reference_actives"], backend=rdkit_tools)
    assert scored["activity_evidence"]["type"] in {"PROXY", "MODEL", "MEASURED", "UNKNOWN"}
    assert "not measured activity" in scored["activity_evidence"]["limitation"]
