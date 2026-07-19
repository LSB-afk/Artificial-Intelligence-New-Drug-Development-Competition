"""Atomic JSON store for the Hades management console.

Seeded records are deterministic repository-derived demo management data. They
are operational fixtures only, not biological or drug-design assertions.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path


PROJECT_STATUSES = {"planned", "active", "paused", "completed", "cancelled"}
TASK_STATUSES = {"backlog", "todo", "in_progress", "in_review", "blocked", "done"}
TASK_PRIORITIES = {"low", "medium", "high", "critical"}
AGENT_STATUSES = {"idle", "running", "paused", "error", "terminated"}
RUN_STATUSES = {"queued", "running", "succeeded", "failed", "cancelled"}
APPROVAL_ACTIONS = {
    "approve": ("approved", "approve_approval"),
    "reject": ("rejected", "reject_approval"),
    "request-revision": ("revision_requested", "request_revision_approval"),
}
TASK_TRANSITIONS = {
    "backlog": {"todo"},
    "todo": {"in_progress"},
    "in_progress": {"in_review", "blocked"},
    "blocked": {"in_progress"},
    "in_review": {"in_progress", "done"},
    "done": set(),
}


class ConsoleError(ValueError):
    def __init__(self, code: str, message: str, status: int = 400, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}


def seed_console_data() -> dict:
    seeded_at = "2026-07-19T00:00:00Z"
    return {
        "schema_version": 2,
        "projects": [
            {
                "id": "demo-project-hades-console",
                "name": "Hades Console",
                "description": "Demo repository operations console for deterministic harness management.",
                "status": "active",
                "goal": "Coordinate repository console work without changing scientific decisions.",
                "target_date": "2026-07-31",
                "lead_agent_id": "demo-agent-runner",
                "color": "#0f766e",
                "source": "demo",
                "created_at": seeded_at,
                "updated_at": seeded_at,
            }
        ],
        "tasks": [
            {
                "id": "demo-task-static-shell",
                "project_id": "demo-project-hades-console",
                "title": "정적 콘솔 셸 검증",
                "description": "Demo task for validating the static app shell.",
                "status": "todo",
                "priority": "high",
                "assignee_agent_id": None,
                "checkout_run_id": None,
                "labels": ["demo", "repository"],
                "source": "demo",
                "created_at": seeded_at,
                "updated_at": seeded_at,
                "started_at": None,
                "completed_at": None,
            },
            {
                "id": "demo-task-registry-replay",
                "project_id": "demo-project-hades-console",
                "title": "오프라인 레지스트리 리플레이 확인",
                "description": "Demo task showing a failed repository replay awaiting retry.",
                "status": "blocked",
                "priority": "medium",
                "assignee_agent_id": "demo-agent-reviewer",
                "checkout_run_id": "demo-run-failed",
                "labels": ["demo", "repository"],
                "source": "demo",
                "created_at": seeded_at,
                "updated_at": seeded_at,
                "started_at": seeded_at,
                "completed_at": None,
            },
        ],
        "agents": [
            {
                "id": "demo-agent-runner",
                "name": "Demo Runner",
                "role": "executor",
                "title": "Repository task runner",
                "status": "idle",
                "capabilities": ["tests", "static-console"],
                "reports_to": None,
                "budget_monthly_cents": 50000,
                "spent_monthly_cents": 125,
                "last_heartbeat_at": seeded_at,
                "pause_reason": None,
                "source": "demo",
                "created_at": seeded_at,
                "updated_at": seeded_at,
            },
            {
                "id": "demo-agent-reviewer",
                "name": "Demo Reviewer",
                "role": "reviewer",
                "title": "Repository review lane",
                "status": "error",
                "capabilities": ["review", "replay"],
                "reports_to": "demo-agent-runner",
                "budget_monthly_cents": 25000,
                "spent_monthly_cents": 0,
                "last_heartbeat_at": seeded_at,
                "pause_reason": "seeded failed run awaiting retry",
                "source": "demo",
                "created_at": seeded_at,
                "updated_at": seeded_at,
            },
        ],
        "runs": [
            {
                "id": "demo-run-failed",
                "task_id": "demo-task-registry-replay",
                "project_id": "demo-project-hades-console",
                "agent_id": "demo-agent-reviewer",
                "status": "failed",
                "invocation_source": "demo",
                "started_at": seeded_at,
                "finished_at": seeded_at,
                "duration_ms": 1250,
                "result": None,
                "error": "Demo repository replay failed fixture.",
                "next_action": "retry",
                "usage": {"input_tokens": 1000, "cached_input_tokens": 250, "output_tokens": 500},
                "cost_cents": 125,
                "log": ["demo replay started", "demo replay failed"],
                "retry_of_run_id": None,
                "source": "demo",
            }
        ],
        "approvals": [
            {
                "id": "demo-approval-console-scope",
                "type": "deployment",
                "title": "Hades Console operational scope",
                "status": "pending",
                "requested_by": "demo-agent-runner",
                "payload": {"project_id": "demo-project-hades-console", "scope": "repository management demo"},
                "decision_note": None,
                "decided_by": None,
                "decided_at": None,
                "source": "demo",
                "created_at": seeded_at,
                "updated_at": seeded_at,
            }
        ],
        "cost_events": [
            {
                "id": "demo-cost-console-bootstrap",
                "agent_id": "demo-agent-runner",
                "task_id": "demo-task-registry-replay",
                "project_id": "demo-project-hades-console",
                "run_id": "demo-run-failed",
                "provider": "demo",
                "model": "repository-fixture",
                "input_tokens": 1000,
                "cached_input_tokens": 250,
                "output_tokens": 500,
                "cost_cents": 125,
                "source": "demo",
                "occurred_at": seeded_at,
            }
        ],
        "activity": [
            {
                "id": "demo-activity-seed",
                "actor_type": "system",
                "actor_id": "seed",
                "action": "seed",
                "entity_type": "store",
                "entity_id": "demo",
                "run_id": None,
                "details": {"schema_version": 2, "source": "demo"},
                "created_at": seeded_at,
            }
        ],
    }


class HadesConsoleStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.RLock()
        if not self.path.exists():
            self._write(seed_console_data())

    def snapshot(self) -> dict:
        with self._lock:
            state = self._read()
            state["costs"] = self._cost_summary(state)
            state["overview"] = self._overview(state)
            return _clone(state)

    def list_entities(self, kind):
        state = self.snapshot()
        if kind not in state or not isinstance(state[kind], list):
            raise ConsoleError("unknown_entity_kind", f"Unknown entity kind: {kind}", 404)
        return state[kind]

    def create_project(self, payload, actor):
        with self._lock:
            state = self._read()
            now = _now()
            project = {
                "id": payload.get("id") or _new_id("project"),
                "name": _required(payload, "name"),
                "description": payload.get("description", ""),
                "status": payload.get("status", "planned"),
                "goal": payload.get("goal", ""),
                "target_date": payload.get("target_date"),
                "lead_agent_id": payload.get("lead_agent_id"),
                "color": payload.get("color", "#0f766e"),
                "source": payload.get("source", "user"),
                "created_at": now,
                "updated_at": now,
            }
            _validate_enum("status", project["status"], PROJECT_STATUSES)
            _ensure_absent(state["projects"], project["id"], "project")
            self._validate_project_links(state, project)
            state["projects"].append(project)
            self._activity(state, actor, "create_project", "project", project["id"])
            self._write(state)
            return _clone(project)

    def update_project(self, id, payload, actor):
        with self._lock:
            state = self._read()
            project = self._get(state, "projects", id, "project")
            allowed = {"name", "description", "status", "goal", "target_date", "lead_agent_id", "color"}
            _validate_keys(payload, allowed)
            next_project = dict(project)
            next_project.update(payload)
            _validate_enum("status", next_project["status"], PROJECT_STATUSES)
            self._validate_project_links(state, next_project)
            project.update(next_project)
            project["updated_at"] = _now()
            self._activity(state, actor, "update_project", "project", id)
            self._write(state)
            return _clone(project)

    def create_task(self, payload, actor):
        with self._lock:
            state = self._read()
            now = _now()
            task = {
                "id": payload.get("id") or _new_id("task"),
                "project_id": _required(payload, "project_id"),
                "title": _required(payload, "title"),
                "description": payload.get("description", ""),
                "status": payload.get("status", "backlog"),
                "priority": payload.get("priority", "medium"),
                "assignee_agent_id": payload.get("assignee_agent_id", payload.get("assignee_id")),
                "checkout_run_id": payload.get("checkout_run_id", payload.get("run_id")),
                "labels": list(payload.get("labels", [])),
                "source": payload.get("source", "user"),
                "created_at": now,
                "updated_at": now,
                "started_at": payload.get("started_at"),
                "completed_at": payload.get("completed_at"),
            }
            _validate_enum("status", task["status"], TASK_STATUSES)
            _validate_enum("priority", task["priority"], TASK_PRIORITIES)
            _ensure_absent(state["tasks"], task["id"], "task")
            self._validate_task_links(state, task)
            self._validate_task_state(task)
            state["tasks"].append(task)
            self._activity(state, actor, "create_task", "task", task["id"])
            self._write(state)
            return _clone(task)

    def update_task(self, id, payload, actor):
        with self._lock:
            state = self._read()
            task = self._get(state, "tasks", id, "task")
            allowed = {
                "project_id",
                "title",
                "description",
                "status",
                "priority",
                "assignee_agent_id",
                "checkout_run_id",
                "labels",
                "started_at",
                "completed_at",
            }
            payload = _canonical_task_payload(payload)
            _validate_keys(payload, allowed)
            next_task = dict(task)
            next_task.update(payload)
            _validate_enum("status", next_task["status"], TASK_STATUSES)
            _validate_enum("priority", next_task["priority"], TASK_PRIORITIES)
            if next_task["status"] != task["status"]:
                _validate_task_transition(task["status"], next_task["status"])
            self._validate_task_links(state, next_task)
            self._validate_task_state(next_task)
            if next_task["status"] == "done" and task["status"] != "done":
                next_task["completed_at"] = next_task.get("completed_at") or _now()
            task.update(next_task)
            task["updated_at"] = _now()
            self._activity(state, actor, "update_task", "task", id, run_id=task.get("checkout_run_id"))
            self._write(state)
            return _clone(task)

    def checkout_task(self, id, agent_id, expected_statuses, run_id, actor):
        with self._lock:
            state = self._read()
            task = self._get(state, "tasks", id, "task")
            if task["status"] not in set(expected_statuses):
                raise ConsoleError(
                    "task_status_conflict",
                    f"Task {id} has status {task['status']}",
                    409,
                    {"expected_statuses": list(expected_statuses), "actual_status": task["status"]},
                )
            if task.get("assignee_agent_id") and task["assignee_agent_id"] != agent_id:
                raise ConsoleError("task_already_assigned", f"Task {id} is already assigned", 409)
            _validate_task_transition(task["status"], "in_progress")
            self._get(state, "agents", agent_id, "agent")
            now = _now()
            task["status"] = "in_progress"
            task["assignee_agent_id"] = agent_id
            task["checkout_run_id"] = run_id
            task["started_at"] = task.get("started_at") or now
            task["updated_at"] = now
            if not _find(state["runs"], run_id):
                state["runs"].append(_run_record(run_id, task, agent_id, "running", "checkout", now))
            self._activity(state, actor, "checkout_task", "task", id, run_id=run_id, details={"agent_id": agent_id})
            self._write(state)
            return _clone(task)

    def release_task(self, id, actor):
        with self._lock:
            state = self._read()
            task = self._get(state, "tasks", id, "task")
            if task["status"] != "in_progress" or not task.get("assignee_agent_id"):
                raise ConsoleError(
                    "task_not_releasable",
                    f"Task {id} must be in_progress and assigned before release",
                    409,
                    {"status": task["status"], "assignee_agent_id": task.get("assignee_agent_id")},
                )
            run_id = task.get("checkout_run_id")
            task["status"] = "todo"
            task["assignee_agent_id"] = None
            task["checkout_run_id"] = None
            task["updated_at"] = _now()
            self._activity(state, actor, "release_task", "task", id, run_id=run_id)
            self._write(state)
            return _clone(task)

    def set_agent_status(self, id, status, reason, actor):
        with self._lock:
            state = self._read()
            agent = self._get(state, "agents", id, "agent")
            _validate_enum("status", status, AGENT_STATUSES)
            agent["status"] = status
            agent["pause_reason"] = reason if status in {"paused", "error"} else None
            agent["last_heartbeat_at"] = _now()
            agent["updated_at"] = agent["last_heartbeat_at"]
            self._activity(state, actor, "set_agent_status", "agent", id, details={"status": status})
            self._write(state)
            return _clone(agent)

    def retry_run(self, id, actor):
        with self._lock:
            state = self._read()
            run = self._get(state, "runs", id, "run")
            if run["status"] not in {"failed", "cancelled"}:
                raise ConsoleError("run_not_retryable", f"Run {id} is not retryable", 409, {"status": run["status"]})
            now = _now()
            retry = _run_record(
                _new_id("run"),
                {"id": run["task_id"], "project_id": run["project_id"]},
                run["agent_id"],
                "queued",
                "retry",
                now,
                retry_of_run_id=id,
            )
            state["runs"].append(retry)
            self._activity(state, actor, "retry_run", "run", retry["id"], details={"retry_of_run_id": id})
            self._write(state)
            return _clone(retry)

    def decide_approval(self, id, action, note, actor):
        with self._lock:
            state = self._read()
            approval = self._get(state, "approvals", id, "approval")
            if approval["status"] != "pending":
                raise ConsoleError(
                    "approval_terminal",
                    f"Approval {id} is already {approval['status']}",
                    409,
                    {"status": approval["status"]},
                )
            if action not in APPROVAL_ACTIONS:
                raise ConsoleError("invalid_approval_action", f"Invalid approval action: {action}", 400)
            status, activity_action = APPROVAL_ACTIONS[action]
            now = _now()
            approval["status"] = status
            approval["decision_note"] = note
            approval["decided_by"] = actor
            approval["decided_at"] = now
            approval["updated_at"] = now
            self._activity(state, actor, activity_action, "approval", id)
            self._write(state)
            return _clone(approval)

    def cost_summary(self):
        with self._lock:
            return _clone(self._cost_summary(self._read()))

    def _read(self):
        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write(self, state):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, self.path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    def _get(self, state, collection, id, label):
        item = _find(state[collection], id)
        if not item:
            raise ConsoleError(f"{label}_not_found", f"{label.title()} not found: {id}", 404)
        return item

    def _validate_project_links(self, state, project):
        if project.get("lead_agent_id") is not None:
            self._get(state, "agents", project["lead_agent_id"], "agent")

    def _validate_task_links(self, state, task):
        self._get(state, "projects", task["project_id"], "project")
        if task.get("assignee_agent_id") is not None:
            self._get(state, "agents", task["assignee_agent_id"], "agent")
        if task.get("checkout_run_id") is not None:
            self._get(state, "runs", task["checkout_run_id"], "run")

    def _validate_task_state(self, task):
        if task["status"] == "in_progress" and not task.get("assignee_agent_id"):
            raise ConsoleError("task_missing_assignee", "in_progress task requires an assigned agent", 409)

    def _activity(self, state, actor, action, entity_type, entity_id, run_id=None, details=None):
        state["activity"].append(
            {
                "id": _new_id("activity"),
                "actor_type": "user",
                "actor_id": actor,
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "run_id": run_id,
                "details": details or {},
                "created_at": _now(),
            }
        )

    def _overview(self, state):
        return {
            "project_count": len(state["projects"]),
            "task_count": len(state["tasks"]),
            "todo_task_count": len([task for task in state["tasks"] if task["status"] == "todo"]),
            "pending_approval_count": len([item for item in state["approvals"] if item["status"] == "pending"]),
            "active_agent_count": len([agent for agent in state["agents"] if agent["status"] in {"idle", "running"}]),
        }

    def _cost_summary(self, state):
        by_agent = {}
        by_project = {}
        totals = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "cost_cents": 0}
        for event in state.get("cost_events", []):
            input_tokens = int(event.get("input_tokens", 0))
            cached_tokens = int(event.get("cached_input_tokens", 0))
            output_tokens = int(event.get("output_tokens", 0))
            cost_cents = int(event.get("cost_cents", 0))
            totals["input_tokens"] += input_tokens
            totals["cached_input_tokens"] += cached_tokens
            totals["output_tokens"] += output_tokens
            totals["cost_cents"] += cost_cents
            _add_cost_bucket(by_agent, event["agent_id"], input_tokens, cached_tokens, output_tokens, cost_cents)
            _add_cost_bucket(by_project, event["project_id"], input_tokens, cached_tokens, output_tokens, cost_cents)

        budget_cents = sum(int(agent.get("budget_monthly_cents", 0)) for agent in state["agents"])
        spent_cents = sum(int(agent.get("spent_monthly_cents", 0)) for agent in state["agents"])
        total_tokens = totals["input_tokens"] + totals["cached_input_tokens"] + totals["output_tokens"]
        return {
            "currency": "USD",
            "total_cost_cents": totals["cost_cents"],
            "total_tokens": total_tokens,
            "input_tokens": totals["input_tokens"],
            "cached_input_tokens": totals["cached_input_tokens"],
            "output_tokens": totals["output_tokens"],
            "event_count": len(state.get("cost_events", [])),
            "utilization": {
                "budget_cents": budget_cents,
                "spent_cents": spent_cents,
                "remaining_cents": budget_cents - spent_cents,
                "utilization_pct": round((spent_cents / budget_cents) * 100, 2) if budget_cents else 0,
            },
            "by_agent": by_agent,
            "by_project": by_project,
        }


def _run_record(id, task, agent_id, status, invocation_source, now, retry_of_run_id=None):
    return {
        "id": id,
        "task_id": task["id"],
        "project_id": task["project_id"],
        "agent_id": agent_id,
        "status": status,
        "invocation_source": invocation_source,
        "started_at": now if status == "running" else None,
        "finished_at": None,
        "duration_ms": None,
        "result": None,
        "error": None,
        "next_action": None,
        "usage": {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0},
        "cost_cents": 0,
        "log": [],
        "retry_of_run_id": retry_of_run_id,
        "source": "user",
    }


def _add_cost_bucket(buckets, id, input_tokens, cached_tokens, output_tokens, cost_cents):
    bucket = buckets.setdefault(
        id,
        {
            "input_tokens": 0,
            "cached_input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cost_cents": 0,
            "event_count": 0,
        },
    )
    bucket["input_tokens"] += input_tokens
    bucket["cached_input_tokens"] += cached_tokens
    bucket["output_tokens"] += output_tokens
    bucket["total_tokens"] += input_tokens + cached_tokens + output_tokens
    bucket["cost_cents"] += cost_cents
    bucket["event_count"] += 1


def _canonical_task_payload(payload):
    payload = dict(payload)
    if "assignee_id" in payload:
        payload["assignee_agent_id"] = payload.pop("assignee_id")
    if "run_id" in payload:
        payload["checkout_run_id"] = payload.pop("run_id")
    return payload


def _validate_task_transition(current, target):
    if target not in TASK_TRANSITIONS.get(current, set()):
        raise ConsoleError(
            "invalid_task_transition",
            f"Cannot transition task from {current} to {target}",
            409,
            {"from": current, "to": target},
        )


def _clone(value):
    return json.loads(json.dumps(value, ensure_ascii=False))


def _find(items, id):
    return next((item for item in items if item["id"] == id), None)


def _new_id(prefix):
    return f"{prefix}-{uuid.uuid4().hex}"


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _required(payload, key):
    value = payload.get(key)
    if value in (None, ""):
        raise ConsoleError("missing_field", f"Missing required field: {key}", 400, {"field": key})
    return value


def _validate_enum(field, value, allowed):
    if value not in allowed:
        raise ConsoleError("invalid_enum", f"Invalid {field}: {value}", 400, {"field": field, "allowed": sorted(allowed)})


def _validate_keys(payload, allowed):
    extra = sorted(set(payload) - allowed)
    if extra:
        raise ConsoleError("unknown_fields", f"Unknown fields: {', '.join(extra)}", 400, {"fields": extra})


def _ensure_absent(items, id, label):
    if _find(items, id):
        raise ConsoleError(f"{label}_exists", f"{label.title()} already exists: {id}", 409)
