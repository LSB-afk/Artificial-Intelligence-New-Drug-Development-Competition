"""The preset scenarios and the non-persisting sandbox.

Two properties carry the feature. Each preset has to actually fire the rule its
label names, or the buttons teach a reviewer something false. And an ad-hoc
packet has to stay outside the approved set, or the input box becomes a way to
launder unreviewed evidence into the harness.
"""
from __future__ import annotations

import copy
import json

import pytest

from h2l.agent import run_agent
from h2l.llm import LLMConfig
from h2l.scenarios import (
    MAX_RECORDS,
    SCENARIOS,
    PacketRejected,
    sandbox_tools,
    scenario_catalog,
    validate_packet,
)
from h2l.server import route

OFFLINE = LLMConfig.offline()


def _decide(packet: dict) -> dict:
    return sandbox_tools(packet).decision(packet["hypothesis_id"])


def _scenario(scenario_id: str) -> dict:
    return next(item for item in SCENARIOS if item["id"] == scenario_id)


# ---- presets -----------------------------------------------------------
def test_every_preset_reaches_a_different_verdict_or_ruleset():
    """Four buttons that all produce the same outcome would teach nothing."""
    outcomes = set()
    for scenario in SCENARIOS:
        decision = _decide(scenario["packet"])
        outcomes.add((decision["decision"], tuple(decision["rule_ids"])))
    assert len(outcomes) == len(SCENARIOS)


@pytest.mark.parametrize(
    "scenario_id,decision,rule_ids",
    [
        ("in-indication-support", "ADVANCE", []),
        ("failed-trial", "REJECT", ["FAILED_TRIAL_BLOCKS_ADVANCE"]),
        ("cross-indication", "HOLD", ["INDICATION_MATCH_REQUIRED", "REQUIRED_EVIDENCE_MISSING"]),
        ("context-only", "HOLD", ["REQUIRED_EVIDENCE_MISSING"]),
    ],
)
def test_preset_fires_the_rule_its_label_claims(scenario_id, decision, rule_ids):
    result = _decide(_scenario(scenario_id)["packet"])
    assert result["decision"] == decision
    assert result["rule_ids"] == rule_ids


def test_the_expectation_text_matches_what_the_harness_computes():
    """The label a reviewer reads has to survive comparison with the output."""
    for scenario in SCENARIOS:
        result = _decide(scenario["packet"])
        assert result["decision"] in scenario["expectation"]
        for rule in result["rule_ids"]:
            assert rule in scenario["expectation"], f"{scenario['id']} hides rule {rule}"


def test_context_only_records_never_count_as_clinical_support():
    """Binding and similarity are proxies; the preset exists to show that."""
    packet = _scenario("context-only")["packet"]
    assert all(record["outcome"] == "positive" for record in packet["records"])
    assert _decide(packet)["decision"] == "HOLD"


def test_catalog_is_a_copy_so_a_caller_cannot_edit_the_presets():
    catalog = scenario_catalog()
    catalog[0]["label"] = "mutated"
    assert scenario_catalog()[0]["label"] != "mutated"


# ---- the gate holds for unapproved input -------------------------------
def test_an_advancing_ad_hoc_packet_still_cannot_reach_molecule_optimization():
    """The safety property that lets untrusted packets in at all.

    Nobody approved this evidence, so even a clean ADVANCE has to stop at
    AWAITING_APPROVAL. If this ever returns True, the input box became a way to
    promote unreviewed evidence.
    """
    decision = _decide(_scenario("in-indication-support")["packet"])
    assert decision["decision"] == "ADVANCE"
    assert decision["molecule_eligible"] is False
    assert decision["state"] == "AWAITING_APPROVAL"


def test_the_sandbox_refuses_optimize_molecules_on_an_advancing_packet():
    tools = sandbox_tools(_scenario("in-indication-support")["packet"])
    observation = tools.optimize_molecules("DEMO:SUPPORT")
    assert observation["refused"] is True


def test_a_sandbox_run_leaves_the_registry_untouched():
    """Two runs of different packets must not see each other."""
    before = json.loads(route("GET", "/api/hypotheses")[2])["hypotheses"]
    for scenario in SCENARIOS:
        run_agent(scenario["packet"]["hypothesis_id"], sandbox_tools(scenario["packet"]), OFFLINE)
    after = json.loads(route("GET", "/api/hypotheses")[2])["hypotheses"]
    assert before == after
    assert not any(item["hypothesis_id"].startswith("DEMO:") for item in after)


def test_the_sandbox_only_knows_its_own_packet():
    tools = sandbox_tools(_scenario("failed-trial")["packet"])
    assert tools.known_ids() == ["DEMO:FAILED"]


# ---- validation --------------------------------------------------------
@pytest.mark.parametrize(
    "mutate,fragment",
    [
        (lambda p: p.pop("records"), "records"),
        (lambda p: p.pop("target"), "target"),
        (lambda p: p.update(records=[]), "records"),
        (lambda p: p.update(records=["not an object"]), "records[0]"),
        (lambda p: p.update(records=[{"kind": "trial"}]), "evidence_id"),
        (lambda p: p.update(indication_ids=[]), "indication_ids"),
        (lambda p: p.update(indication_ids="FIX:DEMO"), "indication_ids"),
        (lambda p: p.update(hypothesis_id="   "), "hypothesis_id"),
        (lambda p: p.update(target=42), "target"),
    ],
)
def test_a_malformed_packet_is_named_not_crashed(mutate, fragment):
    packet = copy.deepcopy(_scenario("failed-trial")["packet"])
    mutate(packet)
    with pytest.raises(PacketRejected) as caught:
        validate_packet(packet)
    assert fragment in str(caught.value)


def test_a_packet_that_is_not_an_object_is_rejected():
    for value in ([], "packet", None, 7):
        with pytest.raises(PacketRejected):
            validate_packet(value)


def test_record_count_is_bounded_so_the_prompt_stays_readable():
    packet = copy.deepcopy(_scenario("failed-trial")["packet"])
    packet["records"] = [dict(packet["records"][0], evidence_id=f"EV-{i}") for i in range(MAX_RECORDS + 1)]
    with pytest.raises(PacketRejected) as caught:
        validate_packet(packet)
    assert str(MAX_RECORDS) in str(caught.value)


def test_every_preset_passes_its_own_validator():
    for scenario in SCENARIOS:
        assert validate_packet(scenario["packet"]) is scenario["packet"]


# ---- routes ------------------------------------------------------------
def test_scenarios_route_serves_every_preset():
    status, _, body = route("GET", "/api/scenarios")
    assert status == 200
    payload = json.loads(body)["scenarios"]
    assert [item["id"] for item in payload] == [item["id"] for item in SCENARIOS]
    assert all(item["packet"]["records"] for item in payload)


def test_sandbox_route_runs_the_loop_over_a_submitted_packet(monkeypatch):
    monkeypatch.setenv("H2L_LLM_ENABLED", "0")
    packet = _scenario("failed-trial")["packet"]
    status, _, body = route("POST", "/api/agent/sandbox", {"packet": packet})
    assert status == 200
    payload = json.loads(body)
    assert payload["sandbox"] is True
    assert payload["goal"] == "DEMO:FAILED"
    assert payload["decision"]["decision"] == "REJECT"
    assert payload["decision"]["rule_ids"] == ["FAILED_TRIAL_BLOCKS_ADVANCE"]
    assert payload["steps"], "the loop should have run at least one step"


def test_sandbox_route_refuses_molecule_optimization_it_was_asked_to_run(monkeypatch):
    """The fail-closed demo has to survive on caller-supplied evidence too."""
    monkeypatch.setenv("H2L_LLM_ENABLED", "0")
    status, _, body = route("POST", "/api/agent/sandbox", {"packet": _scenario("failed-trial")["packet"]})
    payload = json.loads(body)
    refused = [step for step in payload["steps"] if step["refused"]]
    assert refused, "the fixed policy proposes optimize_molecules; the gate must refuse it"
    assert any(step["action"] == "optimize_molecules" for step in refused)


def test_sandbox_route_rejects_a_bad_packet_with_a_usable_message(monkeypatch):
    monkeypatch.setenv("H2L_LLM_ENABLED", "0")
    status, _, body = route("POST", "/api/agent/sandbox", {"packet": {"hypothesis_id": "X"}})
    assert status == 400
    assert json.loads(body)["error"] == "invalid_packet"


def test_sandbox_route_rejects_a_non_object_body(monkeypatch):
    monkeypatch.setenv("H2L_LLM_ENABLED", "0")
    status, _, body = route("POST", "/api/agent/sandbox", ["not", "an", "object"])
    assert status == 400
    assert json.loads(body)["error"] == "invalid_body"


def test_sandbox_route_rejects_a_get(monkeypatch):
    monkeypatch.setenv("H2L_LLM_ENABLED", "0")
    status, _, _ = route("GET", "/api/agent/sandbox")
    assert status == 405


def test_sandbox_run_is_byte_reproducible_with_the_model_off(monkeypatch):
    monkeypatch.setenv("H2L_LLM_ENABLED", "0")
    packet = _scenario("cross-indication")["packet"]
    first = route("POST", "/api/agent/sandbox", {"packet": packet})[2]
    second = route("POST", "/api/agent/sandbox", {"packet": packet})[2]
    assert first == second
