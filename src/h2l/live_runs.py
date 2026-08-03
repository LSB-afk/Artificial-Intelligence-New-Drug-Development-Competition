"""Process-local live execution state for the web research console.

The scientific registry remains read-only. These records are volatile serving
state: they let the browser observe a real ``run_agent`` invocation as it moves
through validated actions, and they disappear when the server restarts.
"""
from __future__ import annotations

import copy
import json
import threading
import time
import uuid
from collections import OrderedDict
from datetime import datetime, timezone

from h2l import RULESET_VERSION
from h2l.agent import run_agent
from h2l.workspace import run_snapshot

ACTIVE_STATUSES = {"queued", "running"}
TERMINAL_STATUSES = {"awaiting_review", "completed", "completed_with_warnings", "failed", "cancelled"}

ACTION_STAGES = (
    {
        "id": "list_hypotheses", "label": "가설 목록 확인", "agent": "Agent Controller",
        "inputs": [], "outputs": [],
    },
    {
        "id": "inspect_evidence", "label": "승인 근거 검사", "agent": "Snapshot Evidence Tool",
        "inputs": [], "outputs": ["evidence-packet"],
    },
    {
        "id": "critique", "label": "근거 비평", "agent": "Clinical Contradiction Critic",
        "inputs": ["evidence-packet"], "outputs": ["decision-trace"],
    },
    {
        "id": "check_molecule_gate", "label": "분자 게이트 확인", "agent": "Decision Gate",
        "inputs": ["decision-trace"], "outputs": [],
    },
    {
        "id": "optimize_molecules", "label": "분자 최적화 요청", "agent": "Molecule Gate",
        "inputs": ["decision-trace"], "outputs": [],
    },
    {
        "id": "whatif_missing_evidence", "label": "판정 변경 조건 계산", "agent": "Counterfactual Tool",
        "inputs": ["decision-trace"], "outputs": [],
    },
    {
        "id": "report", "label": "판단 보고서", "agent": "Explanation Renderer",
        "inputs": ["decision-trace"], "outputs": ["agent-trace", "decision-report"],
    },
)

STAGE_BY_ACTION = {item["id"]: item for item in ACTION_STAGES}
FAILURE_STAGE_MAP = {"critic": "critique", "decision": "check_molecule_gate"}


class LiveRunCancelled(RuntimeError):
    pass


class LiveRunNotFound(KeyError):
    pass


class LiveRunCapacity(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _clone(value):
    return copy.deepcopy(value)


def _stage_shell() -> list[dict]:
    return [
        {
            "id": spec["id"],
            "ordinal": index,
            "label": spec["label"],
            "agent": spec["agent"],
            "status": "queued",
            "summary": "실행 순서를 기다리고 있습니다.",
            "output": "이 단계의 실제 도구 호출이 시작되면 결과가 갱신됩니다.",
            "retryCount": 0,
            "inputArtifactIds": list(spec["inputs"]),
            "outputArtifactIds": list(spec["outputs"]),
            "toolCall": {
                "name": spec["id"],
                "version": RULESET_VERSION,
                "classification": "computed",
            },
        }
        for index, spec in enumerate(ACTION_STAGES, start=1)
    ]


def _artifact_shell(template: dict) -> list[dict]:
    artifacts = []
    for artifact in template["artifacts"]:
        item = _clone(artifact)
        item["available"] = False
        item.pop("content", None)
        artifacts.append(item)
    artifacts.append(
        {
            "id": "agent-trace",
            "name": "agent-trace.json",
            "mimeType": "application/json",
            "classification": "computed",
            "available": False,
            "description": "허용 목록에서 선택하고 하네스가 실행한 실제 Agent 행동 기록",
        }
    )
    return artifacts


def _replace_report_run_id(content: str, run_id: str) -> str:
    lines = content.splitlines()
    return "\n".join(f"Run: {run_id}" if line.startswith("Run: ") else line for line in lines)


class LiveRunManager:
    """Bounded, thread-safe store of volatile agent runs."""

    def __init__(self, *, step_interval_ms: int = 550, max_runs: int = 20):
        self.step_interval_ms = max(0, int(step_interval_ms))
        self.max_runs = max(1, int(max_runs))
        self._lock = threading.RLock()
        self._jobs: OrderedDict[str, dict] = OrderedDict()

    def create(self, packet: dict, *, scenario_id: str, tools, config, notices: list[dict] | None = None) -> dict:
        goal = packet["hypothesis_id"]
        decision = tools.decision(goal)
        template = run_snapshot(decision, sandbox=True)
        created_at = _now()
        run_id = f"LIVE-{template['run']['id']}-{uuid.uuid4().hex[:8]}"
        pacing_notice = {
            "id": "HARNESS-EVENT-PACING",
            "level": "info",
            "title": "실행 이벤트 표시 간격",
            "detail": (
                f"로컬 규칙은 매우 빨리 끝나므로 단계 변화를 확인할 수 있게 이벤트 공개를 "
                f"{self.step_interval_ms}ms 간격으로 조절합니다. 이 간격은 실제 도구 계산 시간이 아닙니다."
            ),
        }
        snapshot = {
            "run": {
                **template["run"],
                "id": run_id,
                "createdAt": created_at,
                "updatedAt": created_at,
                "durationMs": 0,
                "status": "queued",
                "headline": f"실행 대기 · {scenario_id}",
            },
            "stages": _stage_shell(),
            "evidence": [],
            "targets": [],
            "molecules": [],
            "failures": [],
            "events": [],
            "artifacts": _artifact_shell(template),
            "safetyNotices": [pacing_notice, *(notices or [])],
        }
        job = {
            "snapshot": snapshot,
            "template": template,
            "packet": _clone(packet),
            "tools": tools,
            "config": config,
            "cancel": threading.Event(),
            "created_monotonic": time.monotonic(),
            "trace": None,
        }
        with self._lock:
            self._prune_locked()
            if len(self._jobs) >= self.max_runs:
                raise LiveRunCapacity(f"active live run limit reached: {self.max_runs}")
            self._jobs[run_id] = job
        initial = _clone(snapshot)
        thread = threading.Thread(target=self._execute, args=(run_id, job), daemon=True, name=f"h2l-{run_id[-8:]}")
        thread.start()
        return initial

    def get(self, run_id: str) -> dict:
        with self._lock:
            job = self._jobs.get(run_id)
            if job is None:
                raise LiveRunNotFound(run_id)
            return _clone(job["snapshot"])

    def summaries(self) -> list[dict]:
        with self._lock:
            return [_clone(job["snapshot"]["run"]) for job in reversed(self._jobs.values())]

    def cancel(self, run_id: str) -> dict:
        with self._lock:
            job = self._jobs.get(run_id)
            if job is None:
                raise LiveRunNotFound(run_id)
            snapshot = job["snapshot"]
            if snapshot["run"]["status"] in TERMINAL_STATUSES:
                return _clone(snapshot)
            job["cancel"].set()
            now = _now()
            snapshot["run"].update(
                status="cancelled",
                updatedAt=now,
                durationMs=int((time.monotonic() - job["created_monotonic"]) * 1000),
                headline="사용자가 실행을 취소했습니다.",
            )
            current_stage = next((stage for stage in snapshot["stages"] if stage["status"] == "running"), None)
            for stage in snapshot["stages"]:
                if stage["status"] in {"queued", "running"}:
                    stage["status"] = "cancelled"
                    stage["endedAt"] = now
                    stage["summary"] = "사용자 요청으로 실행을 중단했습니다."
                    stage["output"] = "이 단계에서는 새 결과를 만들지 않았습니다."
            snapshot["events"].append(
                {
                    "id": f"LIVE-EVT-{len(snapshot['events']) + 1:03d}",
                    "occurredAt": now,
                    "agent": "Operator",
                    "tool": "cancel",
                    "toolVersion": RULESET_VERSION,
                    "status": "warning",
                    "title": "실행 취소",
                    "detail": "사용자가 진행 중인 임시 실행을 취소했습니다.",
                    "durationMs": 0,
                    "sourceIds": [],
                    "stageId": current_stage["id"] if current_stage else snapshot["stages"][0]["id"],
                }
            )
            return _clone(snapshot)

    def wait(self, run_id: str, *, timeout: float = 5.0) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            snapshot = self.get(run_id)
            if snapshot["run"]["status"] not in ACTIVE_STATUSES:
                return snapshot
            time.sleep(0.005)
        raise TimeoutError(f"live run did not finish: {run_id}")

    def clear(self) -> None:
        with self._lock:
            for job in self._jobs.values():
                job["cancel"].set()
            self._jobs.clear()

    def _execute(self, run_id: str, job: dict) -> None:
        try:
            if self._wait_or_cancel(job, min(self.step_interval_ms, 250)):
                raise LiveRunCancelled()

            def observe(event: dict) -> None:
                if job["cancel"].is_set():
                    raise LiveRunCancelled()
                if event["type"] == "action_started":
                    self._action_started(run_id, job, event)
                    if self._wait_or_cancel(job, self.step_interval_ms):
                        raise LiveRunCancelled()
                elif event["type"] == "action_completed":
                    self._action_completed(run_id, job, event)
                elif event["type"] == "finalizing":
                    self._finalizing(run_id, job)
                    if self._wait_or_cancel(job, self.step_interval_ms):
                        raise LiveRunCancelled()

            trace = run_agent(
                job["packet"]["hypothesis_id"],
                job["tools"],
                job["config"],
                observer=observe,
            )
            if job["cancel"].is_set():
                raise LiveRunCancelled()
            decision = job["tools"].decision(job["packet"]["hypothesis_id"])
            self._complete(run_id, job, trace, run_snapshot(decision, sandbox=True))
        except LiveRunCancelled:
            # ``cancel`` already published a terminal snapshot. A cancellation
            # that arrived before the API handler read it is published here.
            if run_id in self._jobs:
                self.cancel(run_id)
        except Exception as error:  # serving-plane failure; scientific state is untouched
            self._fail(run_id, job, error)

    def _wait_or_cancel(self, job: dict, milliseconds: int) -> bool:
        if milliseconds <= 0:
            return job["cancel"].is_set()
        return job["cancel"].wait(milliseconds / 1000)

    def _action_started(self, run_id: str, job: dict, event: dict) -> None:
        with self._lock:
            if self._jobs.get(run_id) is not job:
                raise LiveRunCancelled()
            snapshot = job["snapshot"]
            stage = next(stage for stage in snapshot["stages"] if stage["id"] == event["action"])
            now = _now()
            snapshot["run"].update(status="running", updatedAt=now, headline=f"{stage['label']} 실행 중")
            stage.update(
                status="running",
                startedAt=now,
                summary=f"{event['selected_by'] == 'model' and '모델' or '고정 정책'}이 이 행동을 선택했습니다.",
                output="검증된 인자로 하네스 도구를 호출하고 있습니다.",
            )
            stage["toolCall"]["modelSource"] = event["selected_by"]

    def _action_completed(self, run_id: str, job: dict, event: dict) -> None:
        with self._lock:
            if self._jobs.get(run_id) is not job:
                raise LiveRunCancelled()
            snapshot = job["snapshot"]
            stage = next(stage for stage in snapshot["stages"] if stage["id"] == event["action"])
            now = _now()
            observation = event["observation"]
            stage.update(
                status="blocked" if event["refused"] else "completed",
                endedAt=now,
                durationMs=event["duration_ms"],
                summary=observation["summary"],
                output=json.dumps(observation["data"], ensure_ascii=False, sort_keys=True),
            )
            snapshot["run"].update(
                updatedAt=now,
                durationMs=int((time.monotonic() - job["created_monotonic"]) * 1000),
            )
            if event["action"] == "inspect_evidence":
                snapshot["evidence"] = _clone(job["template"]["evidence"])
                self._publish_artifact(snapshot, job["template"], "evidence-packet")
            elif event["action"] == "critique":
                # A model may validly choose critique before inspect_evidence.
                # Publish every source referenced by the target in the same
                # atomic snapshot so the web contract never sees dangling ids.
                snapshot["evidence"] = _clone(job["template"]["evidence"])
                self._publish_artifact(snapshot, job["template"], "evidence-packet")
                snapshot["targets"] = _clone(job["template"]["targets"])
                snapshot["failures"] = self._mapped_failures(job["template"])
                self._publish_artifact(snapshot, job["template"], "decision-trace")
            snapshot["events"].append(
                {
                    "id": f"LIVE-EVT-{len(snapshot['events']) + 1:03d}",
                    "occurredAt": now,
                    "agent": stage["agent"],
                    "tool": event["action"],
                    "toolVersion": RULESET_VERSION,
                    "status": "warning" if event["refused"] else "success",
                    "title": f"{stage['label']} {'차단' if event['refused'] else '완료'}",
                    "detail": observation["summary"],
                    "durationMs": event["duration_ms"],
                    "sourceIds": [],
                    "stageId": stage["id"],
                }
            )

    def _finalizing(self, run_id: str, job: dict) -> None:
        with self._lock:
            if self._jobs.get(run_id) is not job:
                raise LiveRunCancelled()
            snapshot = job["snapshot"]
            stage = next(stage for stage in snapshot["stages"] if stage["id"] == "report")
            now = _now()
            stage.update(
                status="running",
                startedAt=now,
                summary="결정 사실과 Agent trace를 보고서로 정리하고 있습니다.",
                output="설명 가드레일과 출처 표시를 확인하고 있습니다.",
            )
            snapshot["run"].update(status="running", updatedAt=now, headline="판단 보고서 생성 중")

    def _complete(self, run_id: str, job: dict, trace: dict, template: dict) -> None:
        with self._lock:
            if self._jobs.get(run_id) is not job or job["cancel"].is_set():
                raise LiveRunCancelled()
            progress = job["snapshot"]
            now = _now()
            for stage in progress["stages"]:
                if stage["id"] == "report":
                    stage.update(
                        status="completed",
                        endedAt=now,
                        durationMs=0,
                        summary="판정, 규칙, 근거 ID와 Agent trace를 연결한 보고서를 만들었습니다.",
                        output="모델 선택과 정책 대체 여부를 포함한 감사 기록을 함께 보존했습니다.",
                    )
                elif stage["status"] in {"queued", "running"}:
                    stage.update(
                        status="skipped",
                        endedAt=now,
                        summary="이번 Agent 실행에서 선택되지 않은 행동입니다.",
                        output="선택되지 않은 행동은 실행 결과로 간주하지 않습니다.",
                    )

            artifacts = _clone(template["artifacts"])
            for artifact in artifacts:
                artifact["available"] = True
                if artifact["id"] == "decision-report" and artifact.get("content"):
                    artifact["content"] = _replace_report_run_id(artifact["content"], run_id)
            artifacts.append(
                {
                    "id": "agent-trace",
                    "name": "agent-trace.json",
                    "mimeType": "application/json",
                    "classification": "computed",
                    "available": True,
                    "description": "허용 목록에서 선택하고 하네스가 실행한 실제 Agent 행동 기록",
                    "content": json.dumps(trace, ensure_ascii=False, indent=2, sort_keys=True),
                }
            )
            progress["events"].append(
                {
                    "id": f"LIVE-EVT-{len(progress['events']) + 1:03d}",
                    "occurredAt": now,
                    "agent": "Explanation Renderer",
                    "tool": "report",
                    "toolVersion": RULESET_VERSION,
                    "status": "decision",
                    "title": "판단 보고서 완료",
                    "detail": f"Agent {trace['step_count']}단계의 실행 기록과 최종 판정을 연결했습니다.",
                    "durationMs": 0,
                    "sourceIds": trace["decision"]["rule_ids"],
                    "stageId": "report",
                }
            )
            template_notices = _clone(template["safetyNotices"])
            progress["run"].update(
                status=template["run"]["status"],
                updatedAt=now,
                durationMs=int((time.monotonic() - job["created_monotonic"]) * 1000),
                headline=f"{template['run']['headline']} · Agent {trace['step_count']}단계",
            )
            progress.update(
                evidence=_clone(template["evidence"]),
                targets=_clone(template["targets"]),
                molecules=[],
                failures=self._mapped_failures(template),
                artifacts=artifacts,
                safetyNotices=[*progress["safetyNotices"], *template_notices],
            )
            job["trace"] = trace

    def _fail(self, run_id: str, job: dict, error: Exception) -> None:
        with self._lock:
            if self._jobs.get(run_id) is not job:
                return
            snapshot = job["snapshot"]
            if snapshot["run"]["status"] == "cancelled":
                return
            now = _now()
            current = next((stage for stage in snapshot["stages"] if stage["status"] == "running"), None)
            if current:
                current.update(status="failed", endedAt=now, error=f"{type(error).__name__}: {error}")
            for stage in snapshot["stages"]:
                if stage["status"] == "queued":
                    stage["status"] = "skipped"
            snapshot["run"].update(
                status="failed",
                updatedAt=now,
                durationMs=int((time.monotonic() - job["created_monotonic"]) * 1000),
                headline="하네스 실행이 실패했습니다.",
            )
            snapshot["safetyNotices"].append(
                {
                    "id": "HARNESS-RUNTIME-FAILED",
                    "level": "warning",
                    "title": "실행 오류",
                    "detail": f"{type(error).__name__}: {error}",
                }
            )

    def _publish_artifact(self, snapshot: dict, template: dict, artifact_id: str) -> None:
        source = next(item for item in template["artifacts"] if item["id"] == artifact_id)
        index = next(index for index, item in enumerate(snapshot["artifacts"]) if item["id"] == artifact_id)
        snapshot["artifacts"][index] = _clone(source)

    def _mapped_failures(self, template: dict) -> list[dict]:
        failures = _clone(template["failures"])
        for failure in failures:
            failure["stageId"] = FAILURE_STAGE_MAP.get(failure["stageId"], failure["stageId"])
        return failures

    def _prune_locked(self) -> None:
        while len(self._jobs) >= self.max_runs:
            removable = next(
                (run_id for run_id, job in self._jobs.items() if job["snapshot"]["run"]["status"] not in ACTIVE_STATUSES),
                None,
            )
            if removable is None:
                break
            self._jobs.pop(removable, None)
