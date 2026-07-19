"""Offline decision replay: evidence adapter, critic, and harness.

Determinism contract (design spec acceptance #4): a run is a pure function of
the approved snapshot payload plus the ruleset version. No wall-clock, no
network, no randomness on the decision path. Two runs of the same input
serialize to byte-identical JSON.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol

from h2l import RULESET_VERSION
from h2l.registry import SnapshotRegistry, content_hash
from h2l.state_machine import DecisionGate, State
import hashlib

REQUIRED_PACKET_FIELDS = ("hypothesis_id", "disease_id", "indication_ids", "target", "observed_at", "records")
CONTEXT_KINDS = ("binding", "similarity", "prediction")
NEGATIVE_OUTCOMES = ("failed", "negative")


class SnapshotRequired(Exception):
    """No approved snapshot exists for the hypothesis."""


class SnapshotMismatch(Exception):
    """Stored content hash does not match the payload; abort without mutating."""


# ---- Evidence adapters -------------------------------------------------
@dataclass
class EvidenceSnapshot:
    payload: dict
    version_id: str
    content_hash: str
    fallback_used: bool = False
    retries: int = 0


class EvidenceAdapter(Protocol):
    def load(self, hypothesis_id: str) -> EvidenceSnapshot: ...


class SnapshotEvidenceAdapter:
    """Reads the approved ``current`` version and verifies its content hash."""

    def __init__(self, registry: SnapshotRegistry):
        self.registry = registry

    def load(self, hypothesis_id: str) -> EvidenceSnapshot:
        version = self.registry.current(hypothesis_id)
        if version is None:
            raise SnapshotRequired(hypothesis_id)
        payload = version["payload"]
        _validate_schema(payload)
        if content_hash(payload) != version["content_hash"]:
            raise SnapshotMismatch(version["version_id"])
        return EvidenceSnapshot(
            payload=payload,
            version_id=version["version_id"],
            content_hash=version["content_hash"],
        )


class FallbackEvidenceAdapter:
    """Snapshot-first fallback: try the live source under a bounded retry
    budget, and on failure replay the pinned snapshot (evals GC-010)."""

    def __init__(self, *, live, snapshot: SnapshotEvidenceAdapter, max_retries: int = 2):
        self.live = live
        self.snapshot = snapshot
        self.max_retries = max_retries

    def load(self, hypothesis_id: str) -> EvidenceSnapshot:
        attempts = 0
        while attempts <= self.max_retries:
            try:
                snap = self.live.load(hypothesis_id)
                snap.retries = attempts
                return snap
            except Exception:  # bounded retry over recoverable live failures
                attempts += 1
        snap = self.snapshot.load(hypothesis_id)
        snap.fallback_used = True
        snap.retries = attempts
        return snap


def _validate_schema(payload: dict) -> None:
    missing = [f for f in REQUIRED_PACKET_FIELDS if f not in payload]
    if missing:
        raise SnapshotMismatch(f"missing packet fields: {missing}")


# ---- Critics -----------------------------------------------------------
@dataclass
class CriticVerdict:
    decision: str  # ADVANCE | HOLD | REJECT
    rule_ids: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)


class ClinicalContradictionCritic:
    """Indication-aware disconfirmation.

    Rules:
    - INDICATION_MATCH_REQUIRED: positive evidence for a different indication is
      context only; it is never transferred as support for this disease.
    - FAILED_TRIAL_BLOCKS_ADVANCE: a failed trial in this indication -> REJECT.
    - REQUIRED_EVIDENCE_MISSING: no in-indication support and no contradiction -> HOLD.
    - Measured binding / similarity / prediction records are context, never
      clinical validation.
    """

    def evaluate(self, packet: dict) -> CriticVerdict:
        indication_ids = set(packet.get("indication_ids", []))
        supporting, contradicting, cross_indication = [], [], []

        for record in packet["records"]:
            eid = record["evidence_id"]
            if record.get("kind") in CONTEXT_KINDS:
                continue  # measured/predicted/proxy -> context, not clinical support
            in_indication = record.get("indication_id") in indication_ids
            if not in_indication:
                cross_indication.append(eid)
            elif record.get("outcome") in NEGATIVE_OUTCOMES:
                contradicting.append(eid)
            elif record.get("outcome") == "positive":
                supporting.append(eid)

        rule_ids: list[str] = []
        if cross_indication:
            rule_ids.append("INDICATION_MATCH_REQUIRED")

        if contradicting:
            rule_ids.append("FAILED_TRIAL_BLOCKS_ADVANCE")
            return CriticVerdict("REJECT", rule_ids, contradicting + cross_indication)
        if not supporting:
            rule_ids.append("REQUIRED_EVIDENCE_MISSING")
            return CriticVerdict("HOLD", rule_ids, cross_indication)
        return CriticVerdict("ADVANCE", rule_ids, supporting)


class SupportOnlyCritic:
    """Ablation baseline: counts any positive record as support and ignores
    indication mismatch and contradictions. Used only in the evaluation plane
    to quantify the contradiction critic's contribution."""

    def evaluate(self, packet: dict) -> CriticVerdict:
        positives = [r["evidence_id"] for r in packet["records"] if r.get("outcome") == "positive"]
        if positives:
            return CriticVerdict("ADVANCE", ["SUPPORT_ONLY"], positives)
        return CriticVerdict("HOLD", ["REQUIRED_EVIDENCE_MISSING"], [])


# ---- Harness -----------------------------------------------------------
@dataclass
class DecisionResult:
    run_id: str
    hypothesis_id: str
    decision: str
    state: str
    molecule_eligible: bool
    evidence_ids: list[str]
    rule_ids: list[str]
    snapshot: Optional[dict]
    fallback_used: bool
    events: list[dict]

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "hypothesis_id": self.hypothesis_id,
            "decision": self.decision,
            "state": self.state,
            "molecule_eligible": self.molecule_eligible,
            "evidence_ids": list(self.evidence_ids),
            "rule_ids": list(self.rule_ids),
            "snapshot": self.snapshot,
            "fallback_used": self.fallback_used,
            "events": list(self.events),
        }


class DrugDiscoveryHarness:
    def __init__(self, adapter, critic, gate: Optional[DecisionGate] = None, *, ruleset_version: str = RULESET_VERSION):
        self.adapter = adapter
        self.critic = critic
        self.gate = gate or DecisionGate()
        self.ruleset_version = ruleset_version

    def run(self, hypothesis_id: str, *, budget: dict) -> DecisionResult:
        if not budget or budget.get("max_tool_calls", 0) <= 0:
            raise ValueError("budget.max_tool_calls must be positive")

        events: list[dict] = []
        try:
            snap = self.adapter.load(hypothesis_id)
        except SnapshotRequired:
            return self._closed_hold(hypothesis_id, events)

        events.append(_event(len(events), "EvidenceSnapshotLoaded", snap.version_id))
        if snap.fallback_used:
            events.append(_event(len(events), "SnapshotFallbackUsed", snap.version_id))

        verdict = self.critic.evaluate(snap.payload)
        events.append(_event(len(events), "CriticVerdict", verdict.decision))

        state = self.gate.challenge(State.EVIDENCE_COLLECTED)
        state = self.gate.apply_decision(state, verdict.decision)
        events.append(_event(len(events), "DecisionApplied", state.value))

        return DecisionResult(
            run_id=_run_id(hypothesis_id, snap.content_hash, self.ruleset_version),
            hypothesis_id=hypothesis_id,
            decision=verdict.decision,
            state=state.value,
            molecule_eligible=self.gate.molecule_eligible(state),
            evidence_ids=verdict.evidence_ids,
            rule_ids=verdict.rule_ids,
            snapshot={"version_id": snap.version_id, "content_hash": snap.content_hash},
            fallback_used=snap.fallback_used,
            events=events,
        )

    def _closed_hold(self, hypothesis_id: str, events: list[dict]) -> DecisionResult:
        events.append(_event(len(events), "SnapshotRequired", hypothesis_id))
        state = self.gate.apply_decision(self.gate.challenge(State.EVIDENCE_COLLECTED), "HOLD")
        return DecisionResult(
            run_id=_run_id(hypothesis_id, "", self.ruleset_version),
            hypothesis_id=hypothesis_id,
            decision="HOLD",
            state=state.value,
            molecule_eligible=False,
            evidence_ids=[],
            rule_ids=["SNAPSHOT_REQUIRED"],
            snapshot=None,
            fallback_used=False,
            events=events,
        )


def _event(seq: int, event_type: str, detail: str) -> dict:
    return {"seq": seq, "event_type": event_type, "detail": detail}


def _run_id(hypothesis_id: str, content_hash_value: str, ruleset_version: str) -> str:
    key = f"{hypothesis_id}|{content_hash_value}|{ruleset_version}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
