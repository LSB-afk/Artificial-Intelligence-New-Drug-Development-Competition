"""Field-2 molecular optimization loop: tool adapters, eligibility gate,
hard gates, and a reproducible ablation showing the multi-objective candidate
beats a proxy-only baseline without any LLM weight training.
"""
import json
from pathlib import Path

import pytest

from h2l.molopt import entry_gate, optimize, score_molecule
from h2l.molopt_eval import run_molopt_eval
from h2l.tools import admet_risk, druglikeness, similarity_proxy

POOL_PATH = Path(__file__).parent / "fixtures" / "molopt" / "pool.json"


@pytest.fixture
def doc():
    return json.loads(POOL_PATH.read_text(encoding="utf-8"))


# ---- tool adapters -------------------------------------------------------

def test_tools_keep_evidence_types_separate(doc):
    mol = doc["pool"][0]
    assert druglikeness(mol)["evidence_type"] == "model"
    assert admet_risk(mol)["evidence_type"] == "model"
    assert similarity_proxy(mol, doc["reference_actives"])["evidence_type"] == "proxy"


def test_tools_are_deterministic(doc):
    mol = doc["pool"][0]
    assert druglikeness(mol) == druglikeness(mol)
    assert admet_risk(mol) == admet_risk(mol)


def test_score_molecule_flags_high_admet_risk_as_hard_fail(doc):
    decoy = next(m for m in doc["pool"] if m["candidate_id"] == "H2L-D1")
    scored = score_molecule(decoy, doc["reference_actives"])
    assert "herg_high_risk" in scored["hard_fail"]
    assert scored["activity_evidence"]["type"] != "MEASURED"


# ---- eligibility gate ----------------------------------------------------

@pytest.mark.parametrize("mode,decision", [
    ("REJECTION_DEMO", None),
    ("SCIENTIFIC", "REJECT"),
    ("SCIENTIFIC", "HOLD"),
])
def test_gate_blocks_generation(doc, mode, decision):
    result = optimize(doc["pool"], doc["reference_actives"], run_mode=mode, target_decision=decision)
    assert result["blocked"] is True
    assert result["candidates"] == []
    assert result["therapeutic_claim"] is False


def test_scientific_requires_advance(doc):
    blocked = optimize(doc["pool"], doc["reference_actives"], run_mode="SCIENTIFIC", target_decision=None)
    assert blocked["blocked"] is True
    ok = entry_gate("SCIENTIFIC", "ADVANCE")
    assert ok["blocked"] is False and ok["molecule_eligibility"] is True


# ---- optimization loop ---------------------------------------------------

def test_method_only_returns_traceable_topk(doc):
    result = optimize(doc["pool"], doc["reference_actives"], run_mode="METHOD_ONLY", top_k=5)
    assert result["blocked"] is False
    assert result["molecule_eligibility"] is False
    assert result["therapeutic_claim"] is False
    assert result["top_k"] == 5
    good_ids = {m["candidate_id"] for m in doc["pool"] if m["label_desirability"] >= 0.7}
    for candidate in result["candidates"]:
        assert candidate["candidate_id"] in good_ids  # decoys are hard-gated out
        assert candidate["why_selected"]
        assert candidate["why_not_claimed"]
        assert candidate["next_experiment"]
        assert candidate["tool_lineage"]


def test_hard_gate_rejections_are_reported(doc):
    result = optimize(doc["pool"], doc["reference_actives"], run_mode="METHOD_ONLY")
    rejected = {r["candidate_id"]: r["hard_fail"] for r in result["rejected"]}
    assert "activity_evidence_unknown" in rejected["H2L-D6"]
    assert "structural_alert" in rejected["H2L-D7"]
    assert "similarity_outside_band" in rejected["H2L-D5"]


def test_optimize_is_reproducible(doc):
    a = optimize(doc["pool"], doc["reference_actives"], run_mode="METHOD_ONLY")
    b = optimize(doc["pool"], doc["reference_actives"], run_mode="METHOD_ONLY")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_optimize_makes_no_efficacy_claim(doc):
    blob = json.dumps(optimize(doc["pool"], doc["reference_actives"], run_mode="METHOD_ONLY"), ensure_ascii=False)
    assert "완치" not in blob
    assert "부작용 없음" not in blob


# ---- ablation eval -------------------------------------------------------

def test_candidate_beats_baseline_selection_accuracy(doc):
    report = run_molopt_eval(doc)
    assert report["candidate"]["selection_accuracy"] > report["baseline"]["selection_accuracy"]
    assert report["candidate"]["top_k_precision"] > report["baseline"]["top_k_precision"]
    assert report["candidate"]["top_k_precision"] == 1.0
    assert report["eval_plane_readonly"] is True
    assert report["therapeutic_claim"] is False


def test_ablation_bootstrap_is_positive_and_reproducible(doc):
    report = run_molopt_eval(doc)
    bootstrap = report["paired_bootstrap"]
    assert bootstrap["mean_delta"] > 0
    assert bootstrap["ci_low"] > 0  # candidate significantly better
    assert json.dumps(run_molopt_eval(doc), sort_keys=True) == json.dumps(report, sort_keys=True)
