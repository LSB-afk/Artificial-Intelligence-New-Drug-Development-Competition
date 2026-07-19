"""Offline, snapshot-first decision replay.

The harness reads an approved evidence snapshot, runs the indication-aware
Clinical Contradiction Critic, and drives the decision gate. The default path
never touches the network; a failing live adapter falls back to the pinned
snapshot and reproduces the same decision.
"""
import json

import pytest

from h2l.registry import SnapshotRegistry, content_hash
from h2l.replay import (
    ClinicalContradictionCritic,
    DrugDiscoveryHarness,
    FallbackEvidenceAdapter,
    SnapshotEvidenceAdapter,
    SnapshotMismatch,
    SnapshotRequired,
    SupportOnlyCritic,
)


def seed(registry_path, packet):
    reg = SnapshotRegistry(registry_path)
    version = reg.detect(packet["hypothesis_id"], packet, observed_at=packet["observed_at"])
    reg.approve(version["version_id"], actor="reviewer", approved_at="2026-07-16T01:00:00Z")
    return reg


BUDGET = {"max_tool_calls": 5, "max_attempts": 2}


# ---- Critic ------------------------------------------------------------
def test_critic_rejects_tyk2_ibd_on_indication_contradiction(tyk2_packet):
    verdict = ClinicalContradictionCritic().evaluate(tyk2_packet)

    assert verdict.decision == "REJECT"
    assert "INDICATION_MATCH_REQUIRED" in verdict.rule_ids
    assert "FAILED_TRIAL_BLOCKS_ADVANCE" in verdict.rule_ids
    assert "EV-TYK2-UC-PH2-FAIL" in verdict.evidence_ids


def test_measured_activity_does_not_override_contradiction(tyk2_packet, tyk2_binding):
    packet = dict(tyk2_packet)
    packet["records"] = tyk2_packet["records"] + tyk2_binding["records"]

    verdict = ClinicalContradictionCritic().evaluate(packet)

    assert verdict.decision == "REJECT"


def test_critic_holds_when_indication_support_is_missing(tyk2_packet):
    # Drop the failed trials: no in-indication support and no contradiction left.
    packet = dict(tyk2_packet)
    packet["records"] = [r for r in tyk2_packet["records"] if r["kind"] == "approval"]

    verdict = ClinicalContradictionCritic().evaluate(packet)

    assert verdict.decision == "HOLD"
    assert "REQUIRED_EVIDENCE_MISSING" in verdict.rule_ids


def test_critic_advances_with_in_indication_support_and_no_contradiction(tyk2_packet):
    packet = dict(tyk2_packet)
    packet["records"] = [
        {
            "evidence_id": "EV-SUPP-1",
            "kind": "genetic",
            "indication": "inflammatory bowel disease",
            "indication_id": "MONDO_0005265",
            "outcome": "positive",
            "stance": "support",
            "source_ref": "fixture://ibd-genetic-support",
        }
    ]

    verdict = ClinicalContradictionCritic().evaluate(packet)
    assert verdict.decision == "ADVANCE"


def test_support_only_baseline_would_unsafely_advance_tyk2_ibd(tyk2_packet):
    """The value proof: a support-only judge misses the contradiction."""
    assert SupportOnlyCritic().evaluate(tyk2_packet).decision == "ADVANCE"
    assert ClinicalContradictionCritic().evaluate(tyk2_packet).decision == "REJECT"


# ---- Harness end to end ------------------------------------------------
def test_harness_rejects_tyk2_ibd_and_blocks_molecule(registry_path, tyk2_packet):
    reg = seed(registry_path, tyk2_packet)
    harness = DrugDiscoveryHarness(SnapshotEvidenceAdapter(reg), ClinicalContradictionCritic())

    result = harness.run("IBD:TYK2", budget=BUDGET)

    assert result.decision == "REJECT"
    assert result.state == "REJECTED"
    assert result.molecule_eligible is False
    assert result.snapshot["content_hash"] == content_hash(tyk2_packet)


def test_missing_snapshot_holds_closed(registry_path):
    reg = SnapshotRegistry(registry_path)  # nothing approved
    harness = DrugDiscoveryHarness(SnapshotEvidenceAdapter(reg), ClinicalContradictionCritic())

    result = harness.run("IBD:TYK2", budget=BUDGET)

    assert result.decision == "HOLD"
    assert result.molecule_eligible is False
    assert "SNAPSHOT_REQUIRED" in result.rule_ids


def test_tampered_snapshot_aborts_without_mutating_state(registry_path, tyk2_packet):
    reg = seed(registry_path, tyk2_packet)
    # Corrupt the stored hash on disk, then reload.
    state = json.loads(registry_path.read_text(encoding="utf-8"))
    for version in state["versions"]:
        version["content_hash"] = "deadbeef"
    registry_path.write_text(json.dumps(state), encoding="utf-8")
    reg2 = SnapshotRegistry(registry_path)

    adapter = SnapshotEvidenceAdapter(reg2)
    with pytest.raises(SnapshotMismatch):
        adapter.load("IBD:TYK2")


def test_run_is_deterministic_and_byte_equivalent(registry_path, tyk2_packet):
    reg = seed(registry_path, tyk2_packet)
    harness = DrugDiscoveryHarness(SnapshotEvidenceAdapter(reg), ClinicalContradictionCritic())

    first = json.dumps(harness.run("IBD:TYK2", budget=BUDGET).to_dict(), sort_keys=True)
    second = json.dumps(harness.run("IBD:TYK2", budget=BUDGET).to_dict(), sort_keys=True)

    assert first == second


# ---- Live outage -> snapshot fallback (GC-010) -------------------------
class _AlwaysFailingLive:
    def load(self, hypothesis_id):
        raise ConnectionError("HTTP 500")


def test_live_outage_falls_back_to_snapshot(registry_path, tyk2_packet):
    reg = seed(registry_path, tyk2_packet)
    adapter = FallbackEvidenceAdapter(
        live=_AlwaysFailingLive(),
        snapshot=SnapshotEvidenceAdapter(reg),
        max_retries=2,
    )
    harness = DrugDiscoveryHarness(adapter, ClinicalContradictionCritic())

    result = harness.run("IBD:TYK2", budget=BUDGET)

    assert result.decision == "REJECT"
    assert result.fallback_used is True
    assert any(e["event_type"] == "SnapshotFallbackUsed" for e in result.events)
