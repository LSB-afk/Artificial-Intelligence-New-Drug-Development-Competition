"""Atomic JSON store for the Hades management console.

The seeded records are deterministic demo data derived from this repository's
console and evaluation workflow. They are operational fixtures only, not
biological or drug-design assertions.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path


PROJECT_STATUSES = {"active", "paused", "completed", "archived"}
TASK_STATUSES = {"todo", "in_progress", "blocked", "done", "cancelled"}
TASK_PRIORITIES = {"low", "medium", "high", "critical"}
AGENT_STATUSES = {"idle", "busy", "offline", "blocked"}
APPROVAL_ACTIONS = {"approve": "approved", "reject": "rejected"}


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
        "schema_version": 1,
        "projects": [
            {
                "id": "demo-project-hades-console",
                "name": "Hades Console",
                "status": "active",
                "description": "Demo repository operations console for deterministic harness management.",
                "source": "demo",
                "created_at": seeded_at,
                "updated_at": seeded_at,
                "created_by": "seed",
                "updated_by": "seed",
            }
        ],
        "tasks": [
            {
                "id": "demo-task-static-shell",
                "project_id": "demo-project-hades-console",
                "title": "정적 콘솔 셸 검증",
                "status": "todo",
                "priority": "high",
                "assignee_id": None,
                "run_id": None,
                "source": "demo",
                "created_at": seeded_at,
                "updated_at": seeded_at,
                "created_by": "seed",
                "updated_by": "seed",
            },
            {
                "id": "demo-task-registry-replay",
                "project_id": "demo-project-hades-console",
                "title": "오프라인 레지스트리 리플레이 확인",
                "status": "blocked",
                "priority": "medium",
                "assignee_id": "demo-agent-reviewer",
                "run_id": "demo-run-failed",
                "source": "demo",
                "created_at": seeded_at,
                "updated_at": seeded_at,
                "created_by": "seed",
                "updated_by": "seed",
            },
        ],
        "agents": [
            {
                "id": "demo-agent-runner",
                "name": "Demo Runner",
                "status": "idle",
                "reason": "seeded",
                "source": "demo",
                "updated_at": seeded_at,
                "updated_by": "seed",
            },
            {
                "id": "demo-agent-reviewer",
                "name": "Demo Reviewer",
                "status": "blocked",
                "reason": "seeded failed run awaiting retry",
                "source": "demo",
                "updated_at": seeded_at,
                "updated_by": "seed",
            },
        ],
        "runs": [
            {
                "id": "demo-run-failed",
                "task_id": "demo-task-registry-replay",
                "agent_id": "demo-agent-reviewer",
                "status": "failed",
                "retry_of": None,
                "source": "demo",
                "created_at": seeded_at,
                "updated_at": seeded_at,
                "created_by": "seed",
                "updated_by": "seed",
            }
        ],
        "approvals": [
            {
                "id": "demo-approval-console-scope",
                "project_id": "demo-project-hades-console",
                "task_id": "demo-task-static-shell",
                "status": "pending",
                "note": "Demo approval for repository console management scope.",
                "source": "demo",
                "created_at": seeded_at,
                "updated_at": seeded_at,
                "created_by": "seed",
                "updated_by": "seed",
            }
        ],
        "cost_events": [
            {
                "id": "demo-cost-console-bootstrap",
                "project_id": "demo-project-hades-console",
                "run_id": "demo-run-failed",
                "amount_usd": 1.25,
                "source": "demo",
                "created_at": seeded_at,
            }
        ],
        "audit_events": [
            {
                "id": "demo-audit-seed",
                "actor": "seed",
                "action": "seed",
                "entity_kind": "store",
                "entity_id": "demo",
                "occurred_at": seeded_at,
                "source": "demo",
                "details": {"schema_version": 1},
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
            status = payload.get("status", "active")
            _validate_enum("status", status, PROJECT_STATUSES)
            project = {
                "id": payload.get("id") or _new_id("project"),
                "name": _required(payload, "name"),
                "status": status,
                "description": payload.get("description", ""),
                "source": payload.get("source", "user"),
                "created_at": now,
                "updated_at": now,
                "created_by": actor,
                "updated_by": actor,
            }
            _ensure_absent(state["projects"], project["id"], "project")
            state["projects"].append(project)
            self._audit(state, actor, "create_project", "project", project["id"])
            self._write(state)
            return _clone(project)

    def update_project(self, id, payload, actor):
        with self._lock:
            state = self._read()
            project = self._get(state, "projects", id, "project")
            allowed = {"name", "status", "description"}
            _validate_keys(payload, allowed)
            if "status" in payload:
                _validate_enum("status", payload["status"], PROJECT_STATUSES)
            for key in allowed:
                if key in payload:
                    project[key] = payload[key]
            project["updated_at"] = _now()
            project["updated_by"] = actor
            self._audit(state, actor, "update_project", "project", id)
            self._write(state)
            return _clone(project)

    def create_task(self, payload, actor):
        with self._lock:
            state = self._read()
            project_id = _required(payload, "project_id")
            self._get(state, "projects", project_id, "project")
            status = payload.get("status", "todo")
            priority = payload.get("priority", "medium")
            _validate_enum("status", status, TASK_STATUSES)
            _validate_enum("priority", priority, TASK_PRIORITIES)
            now = _now()
            task = {
                "id": payload.get("id") or _new_id("task"),
                "project_id": project_id,
                "title": _required(payload, "title"),
                "status": status,
                "priority": priority,
                "assignee_id": payload.get("assignee_id"),
                "run_id": payload.get("run_id"),
                "source": payload.get("source", "user"),
                "created_at": now,
                "updated_at": now,
                "created_by": actor,
                "updated_by": actor,
            }
            _ensure_absent(state["tasks"], task["id"], "task")
            self._validate_task_links(state, task)
            state["tasks"].append(task)
            self._audit(state, actor, "create_task", "task", task["id"])
            self._write(state)
            return _clone(task)

    def update_task(self, id, payload, actor):
        with self._lock:
            state = self._read()
            task = self._get(state, "tasks", id, "task")
            allowed = {"project_id", "title", "status", "priority", "assignee_id", "run_id"}
            _validate_keys(payload, allowed)
            next_task = dict(task)
            for key in allowed:
                if key in payload:
                    next_task[key] = payload[key]
            _validate_enum("status", next_task["status"], TASK_STATUSES)
            _validate_enum("priority", next_task["priority"], TASK_PRIORITIES)
            self._validate_task_links(state, next_task)
            task.update(next_task)
            task["updated_at"] = _now()
            task["updated_by"] = actor
            self._audit(state, actor, "update_task", "task", id)
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
            if task.get("assignee_id") and task["assignee_id"] != agent_id:
                raise ConsoleError("task_already_assigned", f"Task {id} is already assigned", 409)
            self._get(state, "agents", agent_id, "agent")
            now = _now()
            task["status"] = "in_progress"
            task["assignee_id"] = agent_id
            task["run_id"] = run_id
            task["updated_at"] = now
            task["updated_by"] = actor
            if not _find(state["runs"], run_id):
                state["runs"].append(
                    {
                        "id": run_id,
                        "task_id": id,
                        "agent_id": agent_id,
                        "status": "running",
                        "retry_of": None,
                        "source": "user",
                        "created_at": now,
                        "updated_at": now,
                        "created_by": actor,
                        "updated_by": actor,
                    }
                )
            self._audit(state, actor, "checkout_task", "task", id, {"agent_id": agent_id, "run_id": run_id})
            self._write(state)
            return _clone(task)

    def release_task(self, id, actor):
        with self._lock:
            state = self._read()
            task = self._get(state, "tasks", id, "task")
            task["status"] = "todo"
            task["assignee_id"] = None
            task["run_id"] = None
            task["updated_at"] = _now()
            task["updated_by"] = actor
            self._audit(state, actor, "release_task", "task", id)
            self._write(state)
            return _clone(task)

    def set_agent_status(self, id, status, reason, actor):
        with self._lock:
            state = self._read()
            agent = self._get(state, "agents", id, "agent")
            _validate_enum("status", status, AGENT_STATUSES)
            agent["status"] = status
            agent["reason"] = reason
            agent["updated_at"] = _now()
            agent["updated_by"] = actor
            self._audit(state, actor, "set_agent_status", "agent", id, {"status": status})
            self._write(state)
            return _clone(agent)

    def retry_run(self, id, actor):
        with self._lock:
            state = self._read()
            run = self._get(state, "runs", id, "run")
            if run["status"] not in {"failed", "cancelled"}:
                raise ConsoleError("run_not_retryable", f"Run {id} is not retryable", 409, {"status": run["status"]})
            now = _now()
            retry = {
                "id": _new_id("run"),
                "task_id": run["task_id"],
                "agent_id": run.get("agent_id"),
                "status": "queued",
                "retry_of": id,
                "source": "user",
                "created_at": now,
                "updated_at": now,
                "created_by": actor,
                "updated_by": actor,
            }
            run["status"] = "retried"
            run["updated_at"] = now
            run["updated_by"] = actor
            state["runs"].append(retry)
            self._audit(state, actor, "retry_run", "run", id, {"retry_run_id": retry["id"]})
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
            approval["status"] = APPROVAL_ACTIONS[action]
            approval["note"] = note
            approval["decided_by"] = actor
            approval["decided_at"] = _now()
            approval["updated_at"] = approval["decided_at"]
            approval["updated_by"] = actor
            self._audit(state, actor, f"{action}_approval", "approval", id)
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

    def _validate_task_links(self, state, task):
        self._get(state, "projects", task["project_id"], "project")
        if task.get("assignee_id") is not None:
            self._get(state, "agents", task["assignee_id"], "agent")
        if task.get("run_id") is not None:
            self._get(state, "runs", task["run_id"], "run")

    def _audit(self, state, actor, action, entity_kind, entity_id, details=None):
        state["audit_events"].append(
            {
                "id": _new_id("audit"),
                "actor": actor,
                "action": action,
                "entity_kind": entity_kind,
                "entity_id": entity_id,
                "occurred_at": _now(),
                "source": "user",
                "details": details or {},
            }
        )

    def _overview(self, state):
        return {
            "project_count": len(state["projects"]),
            "task_count": len(state["tasks"]),
            "todo_task_count": len([task for task in state["tasks"] if task["status"] == "todo"]),
            "pending_approval_count": len([item for item in state["approvals"] if item["status"] == "pending"]),
            "active_agent_count": len([agent for agent in state["agents"] if agent["status"] in {"idle", "busy"}]),
        }

    def _cost_summary(self, state):
        by_project = {}
        for event in state.get("cost_events", []):
            project_id = event.get("project_id")
            by_project[project_id] = round(by_project.get(project_id, 0.0) + float(event.get("amount_usd", 0.0)), 6)
        return {
            "currency": "USD",
            "total_usd": round(sum(by_project.values()), 6),
            "by_project": by_project,
            "event_count": len(state.get("cost_events", [])),
        }


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
