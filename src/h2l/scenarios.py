"""Ad-hoc evidence packets: preset scenarios and a non-persisting sandbox.

The console could only run the two packets seeded into the registry at start-up,
which made the central claim untestable from outside. "It rejects an attractive
target on indication grounds" is only believable if a reviewer can hand it a
hypothesis *they* wrote and watch the rule fire. Two fixed buttons are a
picture; an input box is evidence.

The sandbox is safe by construction rather than by a new guard:

- nothing is written. The packet is served by an in-memory adapter, so the
  registry, the audit log, and the approved snapshot set are all untouched and
  a second request cannot see the first one's packet.
- nothing is approved. An ad-hoc packet has no reviewer, so even an ADVANCE
  lands in ``AWAITING_APPROVAL`` with ``molecule_eligible`` false — the existing
  gate already refuses to promote unapproved evidence, which is exactly the
  property that lets untrusted input in at all.
- every response is marked ``sandbox`` so the console can label it, and the
  packet is validated before it reaches the critic.

The presets isolate one rule path each, so pressing the four buttons in order
shows four different verdicts from four different rules rather than the same
rejection four times.
"""
from __future__ import annotations

from h2l.agent import HarnessTools
from h2l.registry import content_hash
from h2l.replay import (
    ClinicalContradictionCritic,
    DrugDiscoveryHarness,
    EvidenceSnapshot,
    REQUIRED_PACKET_FIELDS,
)

BUDGET = {"max_tool_calls": 5, "max_attempts": 2}
# Every record is rendered into the explanation prompt, so an unbounded packet
# would push the fact set past what a local 7-8B model can read. This bounds the
# prompt, not the science: no demo packet approaches it.
MAX_RECORDS = 100
# The critic compares outcomes by normalized membership; anything outside this
# vocabulary would silently degrade the verdict, so reject it at the boundary.
ALLOWED_OUTCOMES = {"positive", "failed", "negative"}


class PacketRejected(Exception):
    """The submitted packet is not a usable evidence packet."""


# ---- presets -----------------------------------------------------------
def _packet(hypothesis_id: str, target: str, indication_ids: list[str], records: list[dict]) -> dict:
    return {
        "hypothesis_id": hypothesis_id,
        "disease_id": indication_ids[0],
        "indication_ids": indication_ids,
        "target": target,
        "reference_drug": "fixture-compound",
        "observed_at": "2026-07-25T00:00:00Z",
        "records": records,
    }


SCENARIOS: list[dict] = [
    {
        "id": "in-indication-support",
        "label": "양성 근거",
        "expectation": "ADVANCE · 규칙 없음",
        "note": "적응증이 일치하는 positive 임상 1건. 통과하지만 분자 단계는 사람 승인 전까지 닫혀 있습니다.",
        "packet": _packet(
            "DEMO:SUPPORT", "DEMO-TARGET-A", ["FIX:DEMO-DISEASE"],
            [
                {
                    "evidence_id": "EV-DEMO-A-PH3-POS",
                    "kind": "trial",
                    "indication": "demo disease",
                    "indication_id": "FIX:DEMO-DISEASE",
                    "outcome": "positive",
                    "stance": "support",
                    "source_ref": "fixture://demo-in-indication-positive",
                }
            ],
        ),
    },
    {
        "id": "failed-trial",
        "label": "실패 임상",
        "expectation": "REJECT · FAILED_TRIAL_BLOCKS_ADVANCE",
        "note": "같은 적응증에서 실패한 임상 1건. 이것 하나로 진행이 막힙니다.",
        "packet": _packet(
            "DEMO:FAILED", "DEMO-TARGET-B", ["FIX:DEMO-DISEASE"],
            [
                {
                    "evidence_id": "EV-DEMO-B-PH2-FAIL",
                    "kind": "trial",
                    "indication": "demo disease",
                    "indication_id": "FIX:DEMO-DISEASE",
                    "outcome": "failed",
                    "stance": "contradict",
                    "source_ref": "fixture://demo-in-indication-failure",
                }
            ],
        ),
    },
    {
        "id": "cross-indication",
        "label": "적응증 불일치",
        "expectation": "HOLD · INDICATION_MATCH_REQUIRED + REQUIRED_EVIDENCE_MISSING",
        "note": "다른 적응증의 승인 근거뿐이라, 이 질환의 지지 근거로는 인정되지 않습니다.",
        "packet": _packet(
            "DEMO:CROSS", "DEMO-TARGET-C", ["FIX:DEMO-DISEASE"],
            [
                {
                    "evidence_id": "EV-DEMO-C-OTHER-APPROVAL",
                    "kind": "approval",
                    "indication": "other demo indication",
                    "indication_id": "FIX:OTHER-DISEASE",
                    "outcome": "positive",
                    "stance": "context",
                    "source_ref": "fixture://demo-cross-indication-approval",
                }
            ],
        ),
    },
    {
        "id": "context-only",
        "label": "맥락 근거만",
        "expectation": "HOLD · REQUIRED_EVIDENCE_MISSING",
        "note": "결합력과 유사도 측정만 있습니다. 측정값과 예측값은 맥락이지 임상 검증이 아닙니다.",
        "packet": _packet(
            "DEMO:CONTEXT", "DEMO-TARGET-D", ["FIX:DEMO-DISEASE"],
            [
                {
                    "evidence_id": "EV-DEMO-D-BINDING",
                    "kind": "binding",
                    "indication": "demo disease",
                    "indication_id": "FIX:DEMO-DISEASE",
                    "outcome": "positive",
                    "stance": "context",
                    "source_ref": "fixture://demo-binding-assay",
                },
                {
                    "evidence_id": "EV-DEMO-D-SIMILARITY",
                    "kind": "similarity",
                    "indication": "demo disease",
                    "indication_id": "FIX:DEMO-DISEASE",
                    "outcome": "positive",
                    "stance": "context",
                    "source_ref": "fixture://demo-similarity-proxy",
                },
            ],
        ),
    },
]


def scenario_catalog() -> list[dict]:
    """The presets, as the console offers them."""
    return [dict(scenario) for scenario in SCENARIOS]


# ---- validation --------------------------------------------------------
def validate_packet(packet) -> dict:
    """Check a caller-supplied packet before any of it reaches the critic.

    This is the trust boundary: the packet arrives as free-form JSON from a
    textarea. The critic indexes ``record["evidence_id"]`` directly and the
    explanation prompt serialises the whole packet, so a malformed record would
    surface as a 500 rather than a usable message. Every failure here names the
    field so the reviewer can fix their own input.
    """
    if not isinstance(packet, dict):
        raise PacketRejected("근거 패킷은 JSON 객체여야 합니다.")

    missing = [field for field in REQUIRED_PACKET_FIELDS if field not in packet]
    if missing:
        raise PacketRejected(f"필수 필드가 없습니다: {', '.join(missing)}")

    for field in ("hypothesis_id", "target", "observed_at", "disease_id"):
        if not isinstance(packet[field], str) or not packet[field].strip():
            raise PacketRejected(f"'{field}'는 비어 있지 않은 문자열이어야 합니다.")

    indications = packet["indication_ids"]
    if not isinstance(indications, list) or not indications:
        raise PacketRejected("'indication_ids'는 비어 있지 않은 배열이어야 합니다.")
    if not all(isinstance(item, str) and item.strip() for item in indications):
        raise PacketRejected("'indication_ids'의 모든 값은 비어 있지 않은 문자열이어야 합니다.")

    records = packet["records"]
    if not isinstance(records, list) or not records:
        raise PacketRejected("'records'는 비어 있지 않은 배열이어야 합니다.")
    if len(records) > MAX_RECORDS:
        raise PacketRejected(f"레코드는 최대 {MAX_RECORDS}건까지 허용됩니다. (제출: {len(records)}건)")

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise PacketRejected(f"records[{index}]는 JSON 객체여야 합니다.")
        if not isinstance(record.get("evidence_id"), str) or not record["evidence_id"].strip():
            raise PacketRejected(f"records[{index}]에 'evidence_id'가 없습니다.")
        outcome = record.get("outcome")
        if outcome is not None and (not isinstance(outcome, str) or outcome.strip().lower() not in ALLOWED_OUTCOMES):
            raise PacketRejected(f"records[{index}]의 'outcome' 값이 허용되지 않습니다: {outcome!r}")

    return packet


# ---- sandbox execution -------------------------------------------------
class _PacketAdapter:
    """Serves one unsaved packet. Deliberately not a registry.

    Going through ``SnapshotRegistry`` would mean writing the packet and calling
    ``approve`` with an invented reviewer, which is the one thing an ad-hoc run
    must not do: it would put unreviewed evidence into the approved set under a
    fake actor's name. Reading straight from memory keeps the sandbox incapable
    of granting approval rather than merely declining to.
    """

    def __init__(self, packet: dict):
        self._packet = packet
        self._hash = content_hash(packet)

    def load(self, hypothesis_id: str) -> EvidenceSnapshot:
        return EvidenceSnapshot(
            payload=self._packet,
            version_id=f"sandbox:{self._hash[:12]}",
            content_hash=self._hash,
        )


def sandbox_tools(packet: dict) -> HarnessTools:
    """Harness tools bound to one in-memory packet. Nothing is persisted."""
    hypothesis_id = packet["hypothesis_id"]
    harness = DrugDiscoveryHarness(_PacketAdapter(packet), ClinicalContradictionCritic())

    def hypotheses() -> list[dict]:
        return [{"hypothesis_id": hypothesis_id, "target": packet.get("target")}]

    def decide(requested: str) -> dict:
        result = harness.run(requested, budget=BUDGET).to_dict()
        result["packet"] = packet
        return result

    return HarnessTools(hypotheses, decide)
