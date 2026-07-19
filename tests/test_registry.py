"""SnapshotRegistry ports the JB RegulationRegistry invariant:
a detected-but-unapproved version never changes the current answer.
"""
import json

import pytest

from h2l.registry import SnapshotRegistry


def test_detect_registers_pending_without_a_current(registry_path, tyk2_packet):
    reg = SnapshotRegistry(registry_path)

    version = reg.detect("IBD:TYK2", tyk2_packet, observed_at="2026-07-16T00:00:00Z")

    assert version["status"] == "pending"
    assert reg.current("IBD:TYK2") is None


def test_approve_promotes_pending_to_current(registry_path, tyk2_packet):
    reg = SnapshotRegistry(registry_path)
    version = reg.detect("IBD:TYK2", tyk2_packet, observed_at="2026-07-16T00:00:00Z")

    reg.approve(version["version_id"], actor="reviewer", approved_at="2026-07-16T01:00:00Z")

    current = reg.current("IBD:TYK2")
    assert current["version_id"] == version["version_id"]
    assert current["status"] == "current"
    assert current["content_hash"] == version["content_hash"]


def test_new_pending_does_not_change_current(registry_path, tyk2_packet):
    reg = SnapshotRegistry(registry_path)
    v1 = reg.detect("IBD:TYK2", tyk2_packet, observed_at="2026-07-16T00:00:00Z")
    reg.approve(v1["version_id"], actor="reviewer", approved_at="2026-07-16T01:00:00Z")

    changed = dict(tyk2_packet, observed_at="2026-07-17T00:00:00Z")
    v2 = reg.detect("IBD:TYK2", changed, observed_at="2026-07-17T00:00:00Z")

    assert v2["status"] == "pending"
    assert v2["version_id"] != v1["version_id"]
    # The unapproved v2 must NOT become the answer.
    assert reg.current("IBD:TYK2")["version_id"] == v1["version_id"]


def test_approving_second_version_supersedes_the_first(registry_path, tyk2_packet):
    reg = SnapshotRegistry(registry_path)
    v1 = reg.detect("IBD:TYK2", tyk2_packet, observed_at="2026-07-16T00:00:00Z")
    reg.approve(v1["version_id"], actor="reviewer", approved_at="2026-07-16T01:00:00Z")
    changed = dict(tyk2_packet, observed_at="2026-07-17T00:00:00Z")
    v2 = reg.detect("IBD:TYK2", changed, observed_at="2026-07-17T00:00:00Z")

    reg.approve(v2["version_id"], actor="reviewer", approved_at="2026-07-17T01:00:00Z")

    assert reg.current("IBD:TYK2")["version_id"] == v2["version_id"]
    history = reg.versions("IBD:TYK2", include_history=True)
    superseded = [v for v in history if v["version_id"] == v1["version_id"]][0]
    assert superseded["status"] == "superseded"


def test_reject_records_reason_and_does_not_activate(registry_path, tyk2_packet):
    reg = SnapshotRegistry(registry_path)
    version = reg.detect("IBD:TYK2", tyk2_packet, observed_at="2026-07-16T00:00:00Z")

    reg.reject(version["version_id"], actor="reviewer", reason="source unverifiable")

    rejected = reg.versions("IBD:TYK2", include_history=True)[0]
    assert rejected["status"] == "rejected"
    assert rejected["reason"] == "source unverifiable"
    assert reg.current("IBD:TYK2") is None


def test_detect_is_content_addressed_and_idempotent(registry_path, tyk2_packet):
    reg = SnapshotRegistry(registry_path)
    first = reg.detect("IBD:TYK2", tyk2_packet, observed_at="2026-07-16T00:00:00Z")
    second = reg.detect("IBD:TYK2", tyk2_packet, observed_at="2026-07-16T00:00:00Z")

    assert first["content_hash"] == second["content_hash"]
    assert first["version_id"] == second["version_id"]
    assert len(reg.versions("IBD:TYK2", include_history=True)) == 1


def test_state_is_atomic_json_on_disk(registry_path, tyk2_packet):
    reg = SnapshotRegistry(registry_path)
    reg.detect("IBD:TYK2", tyk2_packet, observed_at="2026-07-16T00:00:00Z")

    on_disk = json.loads(registry_path.read_text(encoding="utf-8"))
    assert "versions" in on_disk and "events" in on_disk
    # No leftover temp file after an atomic replace.
    assert not registry_path.with_suffix(registry_path.suffix + ".tmp").exists()


def test_every_mutation_appends_an_audit_event(registry_path, tyk2_packet):
    reg = SnapshotRegistry(registry_path)
    version = reg.detect("IBD:TYK2", tyk2_packet, observed_at="2026-07-16T00:00:00Z")
    reg.approve(version["version_id"], actor="reviewer", approved_at="2026-07-16T01:00:00Z")

    events = reg.events()
    types = [e["event_type"] for e in events]
    assert "EvidenceVersionDetected" in types
    assert "EvidenceVersionApproved" in types
    for event in events:
        assert set(["event_id", "occurred_at", "actor", "event_type", "target_id"]).issubset(event)
