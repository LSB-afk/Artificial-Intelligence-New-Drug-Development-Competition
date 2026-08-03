"""Projection of a decision run into the web console's ``RunSnapshot`` contract.

``web_dongseop`` renders a run as stages, evidence, targets, molecules,
failures, events, and artifacts. Until now that shape was authored by hand in
TypeScript, so the console looked identical whether or not the Python core
existed. This module closes that gap: it derives the same shape from a real
``DrugDiscoveryHarness`` result and the approved evidence packet it was decided
from.

What the projection may and may not do:

- Every field traces to the decision result, the packet, or a rule stated here.
  Where the packet has no value (an Open Targets association score, a
  tractability call), the projection emits ``None``/``"Unknown"`` and the
  console renders absence. It does not invent a number to fill a column.
- The operational score is a *coverage* figure, not a scientific target score.
  It is defined below and computed from record counts only.
- The projection is read-only and deterministic: timestamps come from the
  packet's ``observed_at``, never the wall clock, so two requests for the same
  hypothesis serialize to byte-identical JSON.

The score, stated once so the console never has to guess:

    scoreBefore  100 when the support-only baseline critic would ADVANCE, else 0.
    scoreAfter   100 minus one deduction per clinical record the contradiction
                 critic cannot count as in-indication support. The deductions
                 split 100 evenly across the clinical records, so the factor
                 list always sums to ``scoreAfter`` and every deduction names
                 the rule and the evidence id that caused it.
"""
from __future__ import annotations

import json

from h2l import RULESET_VERSION
from h2l.replay import CONTEXT_KINDS, NEGATIVE_OUTCOMES, SupportOnlyCritic

SCENARIO_KIND = "harness-decision"

# Display labels. These name things for a human reader; they do not add facts.
DISEASE_LABELS = {"MONDO_0005265": "Inflammatory bowel disease"}
KIND_LABELS = {
    "approval": "규제 승인",
    "trial": "임상시험",
    "genetic": "유전 근거",
    "binding": "결합 측정",
    "similarity": "구조 유사도",
    "prediction": "모델 예측",
}
OUTCOME_LABELS = {"positive": "긍정", "failed": "실패", "negative": "부정"}
DECISION_LABELS = {
    "ADVANCE": "진행 검토",
    "HOLD": "보류",
    "REJECT": "진행 거절",
}
# A harness ADVANCE is not an adopted target: the state machine parks it at
# AWAITING_APPROVAL. The console decision vocabulary reflects that.
TARGET_DECISIONS = {"ADVANCE": "review", "HOLD": "insufficient", "REJECT": "rejected"}
RULE_TEXT = {
    "INDICATION_MATCH_REQUIRED": "다른 적응증의 근거는 이 적응증의 지지 근거로 옮기지 않았습니다.",
    "FAILED_TRIAL_BLOCKS_ADVANCE": "이 적응증에서 실패한 임상 결과가 있어 진행을 막았습니다.",
    "REQUIRED_EVIDENCE_MISSING": "이 적응증에 직접 연결되는 지지 근거가 없습니다.",
    "SNAPSHOT_REQUIRED": "승인된 근거 스냅샷이 없어 판단을 열지 않았습니다.",
}
EVENT_STAGES = {
    "EvidenceSnapshotLoaded": "snapshot",
    "SnapshotFallbackUsed": "snapshot",
    "SnapshotRequired": "snapshot",
    "CriticVerdict": "critic",
    "DecisionApplied": "decision",
}
GATED_STAGES = [
    ("seed", "Seed 수집", "Seed Ligand"),
    ("generate", "후보 생성", "Molecule Optimizer"),
    ("activity", "활성 대리평가", "Activity Proxy"),
    ("admet", "ADMET·안전성", "ADMET / Safety"),
    ("synthesis", "합성 가능성", "Synthesis Feasibility"),
]


def _clinical(records: list[dict]) -> list[dict]:
    """Records that can carry clinical weight. Context kinds never can."""
    return [record for record in records if record.get("kind") not in CONTEXT_KINDS]


def _shares(count: int) -> list[int]:
    """Split 100 into ``count`` integers that sum to exactly 100."""
    if count <= 0:
        return []
    base, remainder = divmod(100, count)
    return [base + (1 if index < remainder else 0) for index in range(count)]


def _score_factors(packet: dict) -> tuple[int, list[dict]]:
    """Deduct one share per record the contradiction critic cannot count.

    Returns ``(score_after, factors)`` where ``sum(f["impact"]) == score_after``;
    the console asserts that invariant, so it is maintained here by construction.
    """
    records = _clinical(packet.get("records", []))
    if not records:
        return 0, [{"id": "no-clinical-evidence", "label": "임상 근거 없음", "impact": 0, "evidenceIds": []}]

    indication_ids = set(packet.get("indication_ids", []))
    factors = [
        {
            "id": "evidence-pool",
            "label": f"근거 후보 {len(records)}건",
            "impact": 100,
            "evidenceIds": [record["evidence_id"] for record in records],
        }
    ]
    score = 100
    for record, share in zip(records, _shares(len(records))):
        evidence_id = record["evidence_id"]
        outcome = (record.get("outcome") or "").strip().lower()
        in_indication = record.get("indication_id") in indication_ids
        if not in_indication:
            reason = ("indication-mismatch", f"적응증 불일치 · {record.get('indication', '기타 적응증')}")
        elif outcome in NEGATIVE_OUTCOMES:
            reason = ("clinical-contradiction", f"임상 반증 · {record.get('indication', '해당 적응증')}")
        else:
            continue  # in-indication support keeps its share
        factors.append({"id": f"{reason[0]}-{evidence_id}", "label": reason[1], "impact": -share, "evidenceIds": [evidence_id]})
        score -= share
    return score, factors


def _baseline_score(packet: dict) -> int:
    """What a support-only critic would have concluded, as a 0/100 figure.

    This is the ablation baseline already used in the evaluation plane, so the
    "before critique" number in the console is the same claim the published
    ablation measures — not a separately invented score.
    """
    return 100 if SupportOnlyCritic().evaluate(packet).decision == "ADVANCE" else 0


def _polarity(record: dict, indication_ids: set[str]) -> str:
    if record.get("kind") in CONTEXT_KINDS:
        return "neutral"
    if record.get("indication_id") not in indication_ids:
        return "neutral"
    outcome = (record.get("outcome") or "").strip().lower()
    if outcome in NEGATIVE_OUTCOMES:
        return "conflicting"
    return "supporting" if outcome == "positive" else "neutral"


def _evidence_detail(record: dict, polarity: str) -> str:
    indication = record.get("indication", "적응증 미상")
    outcome = OUTCOME_LABELS.get(record.get("outcome", ""), record.get("outcome", "미상"))
    if record.get("kind") in CONTEXT_KINDS:
        return f"{KIND_LABELS.get(record['kind'], record['kind'])}는 임상 검증이 아니라 맥락 정보입니다. 지지 근거로 셈하지 않았습니다."
    if polarity == "neutral":
        return f"{indication}은(는) 이 실행의 적응증 목록에 없습니다. 결과는 {outcome}이지만 맥락으로만 유지했습니다."
    if polarity == "conflicting":
        return f"{indication} 적응증에서 {outcome} 결과입니다. 이 가설을 약화시키는 반증으로 분류했습니다."
    return f"{indication} 적응증에서 {outcome} 결과이며 지지 근거로 셈했습니다."


def _evidence(packet: dict, sandbox: bool = False) -> list[dict]:
    indication_ids = set(packet.get("indication_ids", []))
    observed_at = str(packet.get("observed_at", ""))[:10]
    items = []
    for record in packet.get("records", []):
        polarity = _polarity(record, indication_ids)
        source_ref = record.get("source_ref", "")
        items.append(
            {
                "id": record["evidence_id"],
                "title": f"{KIND_LABELS.get(record.get('kind'), record.get('kind', '근거'))} · {record.get('indication', '적응증 미상')}",
                "detail": _evidence_detail(record, polarity),
                "source": source_ref.split("://")[0] if "://" in source_ref else "fixture",
                "sourceId": record["evidence_id"],
                "observedAt": observed_at,
                "polarity": polarity,
                "classification": "synthetic" if sandbox else "source_snapshot",
                "href": source_ref,
            }
        )
    return items


def _target(decision: dict, packet: dict) -> dict:
    score_after, factors = _score_factors(packet)
    indication_ids = set(packet.get("indication_ids", []))
    records = packet.get("records", [])
    contradicting = [r for r in _clinical(records) if r.get("indication_id") in indication_ids and r.get("outcome") in NEGATIVE_OUTCOMES]
    supporting = [r for r in _clinical(records) if r.get("indication_id") in indication_ids and r.get("outcome") == "positive"]
    context = [r for r in records if r.get("kind") in CONTEXT_KINDS]
    rules = decision.get("rule_ids", [])

    rationale = " ".join(RULE_TEXT[rule] for rule in rules if rule in RULE_TEXT) or (
        "적응증이 일치하는 지지 근거만으로 판단했습니다."
    )
    return {
        "symbol": packet.get("target", decision["hypothesis_id"]),
        "name": f"{decision['hypothesis_id']} 가설의 판정 대상",
        "rank": 1,
        # The packet carries no association score or tractability call; the
        # console renders absence rather than a placeholder number.
        "association": None,
        "tractability": "Unknown",
        "assay": f"맥락 레코드 {len(context)}건" if context else "맥락 레코드 없음",
        "clinical": f"적응증 일치 지지 {len(supporting)}건 · 반증 {len(contradicting)}건",
        "scoreBefore": _baseline_score(packet),
        "scoreAfter": score_after,
        "decision": TARGET_DECISIONS.get(decision["decision"], "insufficient"),
        "rationale": rationale,
        "caution": (
            "이 점수는 근거 커버리지 계산값이며 활성·효능 예측이 아닙니다. "
            "판정은 사람 검토를 대체하지 않습니다."
        ),
        "evidenceIds": [record["evidence_id"] for record in records],
        "scoreFactors": factors,
    }


def _stages(decision: dict, packet: dict, sandbox: bool = False) -> list[dict]:
    observed_at = packet.get("observed_at")
    eligible = decision["molecule_eligible"]
    verdict = decision["decision"]
    critic_status = "completed" if verdict == "ADVANCE" else "warning"
    gate_note = (
        "사람 승인 전까지 분자 단계 입력 계약을 열지 않았습니다."
        if verdict == "ADVANCE"
        else f"{DECISION_LABELS.get(verdict, verdict)} 판정이라 분자 단계를 차단했습니다."
    )
    stages = [
        {
            "id": "snapshot", "ordinal": 1, "label": "근거 스냅샷 적재", "agent": "Snapshot Registry",
            "status": "completed", "startedAt": observed_at, "endedAt": observed_at, "durationMs": 0,
            "summary": (
                f"저장하지 않는 임시 패킷 {(decision.get('snapshot') or {}).get('version_id', '없음')}을 적재했습니다."
                if sandbox
                else f"승인된 스냅샷 {(decision.get('snapshot') or {}).get('version_id', '없음')}을 적재했습니다."
            ),
            "output": (
                "승인 이력이 없는 패킷입니다. 레지스트리에 기록하지 않았고, 분자 단계는 어떤 판정에서도 열리지 않습니다."
                if sandbox
                else "content hash를 검증했고, 승인되지 않은 최신 버전은 판단에 쓰지 않았습니다."
            ),
            "retryCount": 0, "inputArtifactIds": [], "outputArtifactIds": ["evidence-packet"],
            "toolCall": {"name": "SnapshotEvidenceAdapter", "version": RULESET_VERSION,
                         "observedAt": str(observed_at)[:10],
                         "classification": "synthetic" if sandbox else "source_snapshot"},
        },
        {
            "id": "critic", "ordinal": 2, "label": "근거 비평", "agent": "Clinical Contradiction Critic",
            "status": critic_status, "startedAt": observed_at, "endedAt": observed_at, "durationMs": 0,
            "summary": f"적용 규칙: {', '.join(decision['rule_ids']) or '없음'}",
            "output": "적응증 일치 여부와 반증을 분리해 지지 근거를 셈했습니다. 맥락 레코드는 임상 검증으로 승격하지 않았습니다.",
            "retryCount": 0, "inputArtifactIds": ["evidence-packet"], "outputArtifactIds": ["decision-trace"],
            "toolCall": {"name": "ClinicalContradictionCritic", "version": RULESET_VERSION,
                         "classification": "computed"},
        },
        {
            "id": "decision", "ordinal": 3, "label": "결정 게이트", "agent": "Decision Gate",
            "status": "completed", "startedAt": observed_at, "endedAt": observed_at, "durationMs": 0,
            "summary": f"{DECISION_LABELS.get(verdict, verdict)} · 상태 {decision['state']}",
            "output": f"molecule_eligible={str(eligible).lower()}. {gate_note}",
            "retryCount": 0, "inputArtifactIds": ["decision-trace"], "outputArtifactIds": ["decision-trace"],
            "toolCall": {"name": "DecisionGate", "version": RULESET_VERSION,
                         "classification": "computed"},
        },
    ]
    for ordinal, (stage_id, label, agent) in enumerate(GATED_STAGES, start=4):
        stages.append(
            {
                "id": stage_id, "ordinal": ordinal, "label": label, "agent": agent, "status": "blocked",
                "summary": "결정 게이트에서 차단했습니다.",
                "output": "수치도 후보도 만들지 않았습니다. 차단된 단계는 빈 결과가 아니라 미실행입니다.",
                "retryCount": 0, "inputArtifactIds": ["decision-trace"], "outputArtifactIds": [],
            }
        )
    stages.append(
        {
            "id": "report", "ordinal": len(GATED_STAGES) + 4, "label": "판단 보고서", "agent": "Report Renderer",
            "status": "completed", "startedAt": observed_at, "endedAt": observed_at, "durationMs": 0,
            "summary": "판정, 규칙, 근거 ID를 연결한 보고서를 만들었습니다.",
            "output": "분자 섹션은 미실행으로 표기했습니다.",
            "retryCount": 0, "inputArtifactIds": ["decision-trace"], "outputArtifactIds": ["decision-report"],
            "toolCall": {"name": "workspace projection", "version": RULESET_VERSION,
                         "classification": "computed"},
        }
    )
    return stages


def _events(decision: dict, packet: dict) -> list[dict]:
    observed_at = packet.get("observed_at")
    statuses = {"CriticVerdict": "decision", "SnapshotFallbackUsed": "warning", "SnapshotRequired": "warning"}
    events = []
    for event in decision.get("events", []):
        event_type = event["event_type"]
        events.append(
            {
                "id": f"HARNESS-EVT-{event['seq']:03d}",
                "occurredAt": observed_at,
                "agent": "H2L Harness",
                "tool": event_type,
                "toolVersion": RULESET_VERSION,
                "status": statuses.get(event_type, "success"),
                "title": event_type,
                "detail": str(event.get("detail", "")),
                "durationMs": 0,
                "sourceIds": [str(event.get("detail", ""))],
                "stageId": EVENT_STAGES.get(event_type, "decision"),
            }
        )
    events.append(
        {
            "id": "HARNESS-EVT-GATE",
            "occurredAt": observed_at,
            "agent": "Decision Gate",
            "tool": "molecule_eligibility",
            "toolVersion": RULESET_VERSION,
            "status": "skipped",
            "title": "분자 단계 차단",
            "detail": f"molecule_eligible={str(decision['molecule_eligible']).lower()} · 상태 {decision['state']}",
            "durationMs": 0,
            "sourceIds": decision.get("rule_ids", []),
            "stageId": "decision",
        }
    )
    return events


def _failures(decision: dict, packet: dict) -> list[dict]:
    time_label = str(packet.get("observed_at", ""))[11:19] or "00:00:00"
    failures = [
        {
            "id": f"HARNESS-{rule}",
            "subject": packet.get("target", decision["hypothesis_id"]),
            "kind": "Target",
            "stageId": "critic",
            "stage": "근거 비평",
            "reason": RULE_TEXT.get(rule, rule),
            "nextAction": "이 적응증에 직접 연결되는 새 근거를 승인 스냅샷으로 등록한 뒤 다시 판단합니다.",
            "severity": "warning" if decision["decision"] == "REJECT" else "info",
            "time": time_label,
        }
        for rule in decision.get("rule_ids", [])
    ]
    if not decision["molecule_eligible"]:
        failures.append(
            {
                "id": "HARNESS-MOLECULE-GATE",
                "subject": f"분자 단계 {len(GATED_STAGES)}개",
                "kind": "Policy",
                "stageId": "decision",
                "stage": "결정 게이트",
                "reason": f"상태가 {decision['state']}라서 분자 단계 입력 계약이 열리지 않았습니다.",
                "nextAction": "ADVANCE 판정과 사람 승인을 모두 통과한 뒤 별도 실행으로 시작합니다.",
                "severity": "info",
                "time": time_label,
            }
        )
    return failures


def _artifacts(decision: dict, packet: dict, sandbox: bool = False) -> list[dict]:
    trace = {key: value for key, value in decision.items() if key != "packet"}
    return [
        {
            "id": "evidence-packet", "name": "normalized_evidence.json", "mimeType": "application/json",
            "classification": "synthetic" if sandbox else "source_snapshot", "available": True,
            "description": "판단에 사용한 임시 패킷 (저장되지 않음)" if sandbox else "판단에 사용한 승인 스냅샷 원본",
            "content": json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True),
        },
        {
            "id": "decision-trace", "name": "decision-trace.json", "mimeType": "application/json",
            "classification": "computed", "available": True,
            "description": "결정 결과, 규칙 ID, 근거 ID, 이벤트",
            "content": json.dumps(trace, ensure_ascii=False, indent=2, sort_keys=True),
        },
        {
            "id": "decision-report", "name": "decision-report.txt", "mimeType": "text/plain",
            "classification": "computed", "available": True,
            "description": "사람이 읽는 판단 요약",
            "content": "\n".join(
                [
                    "H2L-Forge Harness Decision",
                    # The console marks a sandbox run in its shell, but this file leaves
                    # the building on its own. It has to say so by itself.
                    *(["Provenance: SANDBOX — unapproved, unsaved packet. Not a registry decision."]
                      if sandbox else []),
                    f"Run: {_run_id(decision, sandbox)}",
                    f"Hypothesis: {decision['hypothesis_id']}",
                    f"Decision: {decision['decision']} (state {decision['state']})",
                    f"Rules: {', '.join(decision.get('rule_ids', [])) or 'none'}",
                    f"Evidence: {', '.join(decision.get('evidence_ids', [])) or 'none'}",
                    f"Molecule eligible: {str(decision['molecule_eligible']).lower()}",
                    "",
                    "Molecule stages were not run. Human review is required.",
                    "No therapeutic efficacy is claimed.",
                ]
            ),
        },
    ]


def _safety_notices(decision: dict) -> list[dict]:
    notices = [
        {
            "id": "HARNESS-COMPUTED", "level": "info", "title": "하네스가 계산한 판정",
            "detail": "이 실행의 판정, 규칙, 근거 ID는 파이썬 결정 코어가 계산한 값입니다. 서버를 끄면 이 실행은 목록에서 사라집니다.",
        },
        {
            "id": "HARNESS-FIXTURE-PACKET", "level": "warning", "title": "근거 패킷은 시드 픽스처",
            "detail": "근거 레코드는 규칙 동작을 보이기 위한 시드 픽스처이며 검증된 임상 스냅샷이 아닙니다. 효능을 주장하지 않습니다.",
        },
    ]
    if not decision["molecule_eligible"]:
        notices.append(
            {
                "id": "HARNESS-GATE", "level": "warning", "title": "분자 단계 미실행",
                "detail": f"상태 {decision['state']}에서는 분자 최적화를 열 수 없습니다. 화면의 빈 분자 목록은 실패가 아니라 차단입니다.",
            }
        )
    return notices


def _run_id(decision: dict, sandbox: bool = False) -> str:
    slug = decision["hypothesis_id"].replace(":", "-").replace("/", "-")
    # A sandbox run must not be mistaken for one of the approved runs the list
    # route serves, so the id carries the distinction everywhere it travels.
    return f"{'SANDBOX-' if sandbox else ''}RUN-{slug}-{decision['run_id'][:8]}"


def run_snapshot(decision: dict, *, sandbox: bool = False) -> dict:
    """Render a ``DrugDiscoveryHarness`` result as the console's RunSnapshot.

    ``sandbox`` marks a run computed from an unapproved, unsaved packet. It does
    not change a single decision value — it changes what the projection is
    willing to *claim* about where the evidence came from, because the default
    strings assert approved-registry provenance that a sandbox run does not have.
    """
    packet = decision.get("packet") or {}
    disease_id = packet.get("disease_id", decision["hypothesis_id"])
    observed_at = packet.get("observed_at")
    verdict = decision["decision"]
    return {
        "run": {
            "id": _run_id(decision, sandbox),
            "title": f"{packet.get('target', decision['hypothesis_id'])} 근거 판정",
            "disease": DISEASE_LABELS.get(disease_id, disease_id),
            "diseaseId": disease_id,
            "createdAt": observed_at,
            "updatedAt": observed_at,
            "durationMs": 0,
            "status": "awaiting_review",
            "mode": "live",
            "scenarioKind": SCENARIO_KIND,
            "classification": "computed",
            "reviewStatus": "pending",
            "headline": (
                f"{DECISION_LABELS.get(verdict, verdict)} · "
                f"분자 단계 {'대기' if decision['molecule_eligible'] else '미실행'}"
            ),
        },
        "stages": _stages(decision, packet, sandbox),
        "evidence": _evidence(packet, sandbox),
        "targets": [_target(decision, packet)],
        # A harness decision never produces molecules: ADVANCE parks at
        # AWAITING_APPROVAL and everything else is hard-blocked.
        "molecules": [],
        "failures": _failures(decision, packet),
        "events": _events(decision, packet),
        "artifacts": _artifacts(decision, packet, sandbox),
        "safetyNotices": _safety_notices(decision),
    }
