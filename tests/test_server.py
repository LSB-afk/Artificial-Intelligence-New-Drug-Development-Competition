"""HTTP verification server: a read-only, JB-style console over the tested core.

Architecture mirrors JB: a static single-page frontend plus ``/api/*`` JSON.
The server seeds a demo registry (approved current + a pending version that must
not change the answer) so the registry and audit views have real content. It
never mutates scientific state from a request.
"""
import http.client
import io
import json
import threading
import urllib.error
import urllib.request
from contextlib import closing

import pytest

from h2l.console_store import ConsoleError
from h2l.server import MAX_JSON_BODY, _Handler, configure_console_store, make_server, route


def _json(path, method="GET", body=None):
    status, ctype, body = route(method, path, body)
    return status, ctype, json.loads(body)


def _app_js_function(name, next_name):
    status, _, js_body = route("GET", "/static/app.js")
    assert status == 200
    start = js_body.index(f"function {name}")
    end = js_body.index(f"function {next_name}", start)
    return js_body[start:end]


def test_health_route():
    status, _, payload = _json("/api/health")
    assert status == 200 and payload["status"] == "ok"


def test_index_is_the_hades_console_shell():
    status, ctype, body = route("GET", "/")
    assert status == 200
    assert "text/html" in ctype
    # JB-style app shell markers, rendered client-side.
    assert "H2L-Forge" in body
    assert "하데스 콘솔" in body
    assert "sync-rail" in body
    assert "primary-nav" in body
    assert 'id="ops-pulse"' in body
    assert 'id="action-dialog"' in body
    assert 'id="toast"' in body
    assert 'aria-live="polite"' in body
    assert "repository-summary" in body
    assert "demo-operations" in body
    assert 'src="static/app.js"' in body


def test_static_css_and_js_are_served_with_console_contract():
    css_status, css_ctype, css_body = route("GET", "/static/styles.css")
    assert css_status == 200
    assert "text/css" in css_ctype
    assert "--corporate-green" in css_body  # JB design tokens reused verbatim
    assert ".ops-pulse" in css_body
    assert ".pulse-step" in css_body
    assert "prefers-reduced-motion" in css_body
    assert "data-label" in css_body

    js_status, js_ctype, js_body = route("GET", "/static/app.js")
    assert js_status == 200
    assert "javascript" in js_ctype
    assert "GET /api/console" not in js_body
    assert 'fetch("/api/console"' in js_body
    assert "function escapeHtml" in js_body
    assert "showModal()" in js_body
    assert "showToast" in js_body
    assert 'data-action="' in js_body
    assert 'role="alert"' in js_body
    assert '<small>${escapeHtml(item.detail)}</small>' in js_body
    assert (
        'dialog.querySelector(".dialog-body input:not([type=\\"hidden\\"]), '
        '.dialog-body select, .dialog-body textarea")'
    ) in js_body
    assert 'data-action="task-filter"' in js_body
    assert 'aria-label="태스크 상태 필터"' in js_body
    assert "currentAgentContext" in js_body
    assert "formatDuration" in js_body
    assert "renderRunLog" in js_body
    assert "sortApprovals" in js_body
    for endpoint in (
        "/api/projects",
        "/api/tasks",
        "/api/tasks/${id}/checkout",
        "/api/tasks/${id}/release",
        "/api/agents/${id}/pause",
        "/api/agents/${id}/resume",
        "/api/runs/${id}/retry",
        "/api/approvals/${id}/${decision}",
    ):
        assert endpoint in js_body
    for action in (
        "reload",
        "create-project",
        "edit-project",
        "project-status",
        "create-task",
        "edit-task",
        "task-status",
        "checkout-task",
        "release-task",
        "pause-agent",
        "resume-agent",
        "retry-run",
        "decide-approval",
    ):
        assert f'action === "{action}"' in js_body


def test_app_js_dialog_and_escaping_contracts_are_static_guarded():
    status, _, js_body = route("GET", "/static/app.js")
    assert status == 200
    submit_start = js_body.index("async function submitDialog")
    submit_end = js_body.index("function projectForm", submit_start)
    submit_body = js_body[submit_start:submit_end]
    assert "await loadConsole" not in submit_body
    assert "showToast(\"작업이 저장되었습니다.\")" not in submit_body
    assert "dialog.close();" in submit_body
    assert "showToast(\"작업이 완료되었습니다.\")" in js_body
    assert "await loadConsole({ focus: true });" in js_body
    assert "detail: escapeHtml" not in js_body


def test_app_js_declares_all_management_views():
    status, _, body = route("GET", "/static/app.js")
    assert status == 200
    for view in ("dashboard", "projects", "tasks", "agents", "runs", "costs", "approvals", "activity"):
        assert view in body


def test_command_palette_and_theme_controls_are_wired():
    _, _, html = route("GET", "/")
    assert 'id="command-palette"' in html
    assert 'data-action="command-palette"' in html
    assert 'data-action="toggle-theme"' in html
    assert "hades-theme" in html  # inline pre-paint theme init avoids a flash

    _, _, js = route("GET", "/static/app.js")
    assert "function openPalette" in js
    assert "function toggleTheme" in js
    assert "function onGlobalKeydown" in js
    assert 'action === "command-palette"' in js
    assert 'action === "toggle-theme"' in js
    assert "hades-theme" in js

    _, _, css = route("GET", "/static/styles.css")
    assert "#command-palette" in css
    assert ".cmdk-item" in css
    assert '[data-theme="dark"]' in css


def test_blocked_task_resume_uses_checkout_dialog_and_creates_a_new_run():
    actions = _app_js_function("taskActions", "renderAgents")
    assert (
        'task.status === "blocked") '
        'actions.push(actionButton("checkout-task", task.id, "재개 체크아웃", "primary"))'
    ) in actions
    assert 'task.status === "blocked") actions.push(actionButton("task-status"' not in actions

    checkout = _app_js_function("openCheckoutTask", "openPauseAgent")
    assert 'mutate(`/api/tasks/${id}/checkout`, "POST"' in checkout
    assert "expected_statuses: [task.status]" in checkout
    assert 'run_id: formValue(form, "run_id")' in checkout


def test_checkout_form_locks_existing_assignee_but_selects_for_unassigned_tasks():
    checkout_form = _app_js_function("checkoutForm", "mutate")
    open_dialog = _app_js_function("openDialog", "submitDialog")
    assert "const assigneeControl = task.assignee_agent_id" in checkout_form
    assert '현재 담당 에이전트: ${nameFor("agents", task.assignee_agent_id)}' in checkout_form
    assert 'type="hidden" name="agent_id" value="${escapeHtml(task.assignee_agent_id)}"' in checkout_form
    assert '<select name="agent_id" required>' in checkout_form
    assert "${assigneeControl}" in checkout_form
    assert checkout_form.index('type="hidden" name="agent_id"') < checkout_form.index('name="run_id" required')
    assert (
        'dialog.querySelector(".dialog-body input:not([type=\\"hidden\\"]), '
        '.dialog-body select, .dialog-body textarea")'
    ) in open_dialog


def test_task_create_form_only_offers_initial_statuses():
    status_options = _app_js_function("taskStatusOptions", "taskForm")
    assert 'if (mode === "create") return ["backlog", "todo"];' in status_options

    create_dialog = _app_js_function("openCreateTask", "openEditTask")
    assert 'taskForm({ status: "backlog", priority: "medium" }, "create")' in create_dialog


def test_task_edit_keeps_checkout_ownership_read_only():
    task_form = _app_js_function("taskForm", "noteForm")
    assert 'name="assignee_agent_id"' not in task_form
    assert "현재 담당 에이전트" in task_form
    assert 'nameFor("agents", task.assignee_agent_id)' in task_form

    task_payload = _app_js_function("taskPayload", "openCheckoutTask")
    assert "assignee_agent_id" not in task_payload

    edit_dialog = _app_js_function("openEditTask", "taskPayload")
    assert 'taskForm(task, "edit")' in edit_dialog
    assert "담당 변경은 체크아웃/릴리스로 수행합니다." in edit_dialog


def test_checked_out_task_edit_keeps_project_attribution_read_only():
    project_control = _app_js_function("taskProjectControl", "taskStatusOptions")
    assert 'mode === "edit" && task.checkout_run_id' in project_control
    assert '현재 프로젝트: ${nameFor("projects", task.project_id)}' in project_control
    assert 'type="hidden" name="project_id" value="${escapeHtml(task.project_id)}"' in project_control
    assert '<select name="project_id" required>' in project_control

    task_form = _app_js_function("taskForm", "noteForm")
    assert "${taskProjectControl(task, mode)}" in task_form


def test_task_edit_only_resumes_in_review_with_an_active_checkout():
    active_checkout = _app_js_function("hasActiveCheckout", "taskActions")
    for checkout_contract in (
        "task.checkout_run_id",
        "task.assignee_agent_id",
        '["queued", "running"].includes(run.status)',
        "run.task_id === task.id",
        "run.agent_id === task.assignee_agent_id",
        "run.project_id === task.project_id",
    ):
        assert checkout_contract in active_checkout

    status_options = _app_js_function("taskStatusOptions", "taskForm")
    assert 'backlog: ["backlog", "todo"]' in status_options
    assert 'todo: ["todo"]' in status_options
    assert 'blocked: ["blocked"]' in status_options
    assert 'task.status === "in_review" && hasActiveCheckout(task)' in status_options
    assert 'options.splice(1, 0, "in_progress")' in status_options

    actions = _app_js_function("taskActions", "renderAgents")
    assert 'if (task.status === "in_review" && hasActiveCheckout(task))' in actions


def test_mobile_compact_rows_use_single_column_grid():
    status, _, css_body = route("GET", "/static/styles.css")
    assert status == 200
    mobile_start = css_body.index("@media (max-width: 760px)")
    mobile_body = css_body[mobile_start:]
    assert ".attention-row,\n  .compact-row" in mobile_body
    assert "grid-template-columns: minmax(0, 1fr);" in mobile_body


def test_status_rail_reports_pending_and_approved():
    status, _, payload = _json("/api/status")
    assert status == 200
    assert payload["approved_count"] >= 1
    assert payload["pending_count"] >= 1  # a detected-but-unapproved version exists
    assert payload["ruleset"]


def test_decision_default_rejects_tyk2_ibd():
    status, _, payload = _json("/api/decision?hypothesis=IBD:TYK2")
    assert status == 200
    assert payload["decision"] == "REJECT"
    assert payload["molecule_eligible"] is False


def test_decision_positive_branch_awaits_approval():
    status, _, payload = _json("/api/decision?hypothesis=IBD:DEMO-POS")
    assert status == 200
    assert payload["decision"] == "ADVANCE"
    assert payload["state"] == "AWAITING_APPROVAL"
    assert payload["molecule_eligible"] is False  # advance never auto-grants eligibility


def test_registry_shows_pending_not_changing_current():
    status, _, payload = _json("/api/registry")
    assert status == 200
    tyk2 = [g for g in payload["groups"] if g["hypothesis_id"] == "IBD:TYK2"][0]
    statuses = [v["status"] for v in tyk2["versions"]]
    assert "current" in statuses
    assert "pending" in statuses
    assert sum(s == "current" for s in statuses) == 1


def test_events_are_present():
    status, _, payload = _json("/api/events")
    assert status == 200
    assert len(payload["events"]) >= 1
    assert {"event_type", "occurred_at", "target_id"}.issubset(payload["events"][0])


def test_eval_route_reports_candidate_ready():
    status, _, payload = _json("/api/eval")
    assert status == 200
    assert payload["candidate"]["readiness"] is True
    assert payload["baseline"]["readiness"] is False


def test_unknown_route_is_404():
    status, _, _ = route("GET", "/does-not-exist")
    assert status == 404


def test_console_snapshot_exposes_management_entities(tmp_path):
    configure_console_store(tmp_path / "hades.json")
    status, _, payload = _json("/api/console")
    assert status == 200
    assert {"projects", "tasks", "agents", "runs", "approvals", "activity", "costs"}.issubset(payload)


def test_management_collection_routes_return_raw_lists_and_cost_summary(tmp_path):
    configure_console_store(tmp_path / "hades.json")
    for path in ("/api/projects", "/api/tasks", "/api/agents", "/api/runs", "/api/approvals", "/api/activity"):
        status, _, payload = _json(path)
        assert status == 200
        assert isinstance(payload, list)

    status, _, payload = _json("/api/costs")
    assert status == 200
    assert {"total_cost_cents", "by_agent", "by_project"}.issubset(payload)


def test_project_create_and_patch_routes_append_activity(tmp_path):
    configure_console_store(tmp_path / "hades.json")
    snapshot = _json("/api/console")[2]
    before = len(snapshot["activity"])
    agent_id = snapshot["agents"][0]["id"]

    status, _, body = route(
        "POST",
        "/api/projects",
        {
            "name": "관리 API 검증",
            "description": "HTTP route test",
            "status": "planned",
            "lead_agent_id": agent_id,
            "actor": "tester",
        },
    )
    project = json.loads(body)
    assert status == 201
    assert project["name"] == "관리 API 검증"

    status, _, body = route("PATCH", f"/api/projects/{project['id']}", {"status": "active", "operator": "tester"})
    updated = json.loads(body)
    assert status == 200
    assert updated["status"] == "active"
    assert len(_json("/api/activity")[2]) == before + 2


def test_task_create_and_checkout_routes(tmp_path):
    configure_console_store(tmp_path / "hades.json")
    snapshot = _json("/api/console")[2]
    status, _, body = route(
        "POST",
        "/api/tasks",
        {
            "project_id": snapshot["projects"][0]["id"],
            "title": "회귀 테스트 실행",
            "status": "todo",
            "priority": "high",
        },
    )
    task = json.loads(body)
    assert status == 201
    status, _, body = route(
        "POST",
        f"/api/tasks/{task['id']}/checkout",
        {
            "agent_id": snapshot["agents"][0]["id"],
            "expected_statuses": ["todo"],
            "run_id": "run-http-test",
        },
    )
    assert status == 200
    assert json.loads(body)["status"] == "in_progress"


def test_task_create_rejects_checkout_run_id_route(tmp_path):
    configure_console_store(tmp_path / "hades.json")
    snapshot = _json("/api/console")[2]
    project_id = snapshot["projects"][0]["id"]
    run_id = snapshot["runs"][0]["id"]

    status, _, body = route("POST", "/api/tasks", {"project_id": project_id, "title": "bad", "run_id": run_id})
    payload = json.loads(body)

    assert status == 409
    assert payload["error"] == "checkout_fields_readonly"
    assert payload["details"]["fields"] == ["checkout_run_id"]


def test_task_patch_release_and_checkout_conflict_routes(tmp_path):
    configure_console_store(tmp_path / "hades.json")
    snapshot = _json("/api/console")[2]
    task_id = next(task["id"] for task in snapshot["tasks"] if task["status"] == "todo")
    agent_id = snapshot["agents"][0]["id"]

    status, _, body = route("PATCH", f"/api/tasks/{task_id}", {"description": "updated by route"})
    assert status == 200
    assert json.loads(body)["description"] == "updated by route"

    status, _, _ = route(
        "POST",
        f"/api/tasks/{task_id}/checkout",
        {"agent_id": agent_id, "expected_statuses": ["backlog"], "run_id": "run-conflict-test"},
    )
    assert status == 409

    status, _, _ = route(
        "POST",
        f"/api/tasks/{task_id}/checkout",
        {"agent_id": agent_id, "expected_statuses": ["todo"], "run_id": "run-release-test"},
    )
    assert status == 200
    status, _, body = route("POST", f"/api/tasks/{task_id}/release", {"operator": "tester"})
    released = json.loads(body)
    assert status == 200
    assert released["status"] == "todo"
    assert released["assignee_agent_id"] is None

    runs = _json("/api/runs")[2]
    run = next(item for item in runs if item["id"] == "run-release-test")
    assert run["status"] == "cancelled"
    assert run["finished_at"] is not None
    assert run["duration_ms"] >= 0
    assert run["next_action"] == "checkout released"


def test_task_patch_cannot_enter_in_progress_without_checkout(tmp_path):
    configure_console_store(tmp_path / "hades.json")
    snapshot = _json("/api/console")[2]
    project_id = snapshot["projects"][0]["id"]
    task_id = next(task["id"] for task in snapshot["tasks"] if task["status"] == "todo")
    agent_id = snapshot["agents"][0]["id"]

    status, _, body = route(
        "POST",
        "/api/tasks",
        {
            "project_id": project_id,
            "title": "bad direct start",
            "status": "in_progress",
            "assignee_agent_id": agent_id,
        },
    )
    payload = json.loads(body)
    assert status == 409
    assert payload["error"] == "checkout_required"

    status, _, body = route("PATCH", f"/api/tasks/{task_id}", {"status": "in_progress"})
    payload = json.loads(body)

    assert status == 409
    assert payload["error"] == "checkout_required"
    assert payload["details"]["from"] == "todo"
    assert payload["details"]["to"] == "in_progress"

    blocked_id = next(task["id"] for task in snapshot["tasks"] if task["status"] == "blocked")
    status, _, body = route("PATCH", f"/api/tasks/{blocked_id}", {"status": "in_progress"})
    payload = json.loads(body)
    assert status == 409
    assert payload["error"] == "checkout_required"


def test_task_patch_can_resume_with_active_matching_checkout(tmp_path):
    configure_console_store(tmp_path / "hades.json")
    snapshot = _json("/api/console")[2]
    task_id = next(task["id"] for task in snapshot["tasks"] if task["status"] == "todo")
    agent_id = snapshot["agents"][0]["id"]

    status, _, _ = route(
        "POST",
        f"/api/tasks/{task_id}/checkout",
        {"agent_id": agent_id, "expected_statuses": ["todo"], "run_id": "run-route-resume"},
    )
    assert status == 200
    status, _, _ = route("PATCH", f"/api/tasks/{task_id}", {"status": "in_review"})
    assert status == 200
    status, _, body = route(
        "PATCH",
        f"/api/tasks/{task_id}",
        {"status": "in_progress", "assignee_agent_id": agent_id, "checkout_run_id": "run-route-resume"},
    )
    resumed = json.loads(body)
    assert status == 200
    assert resumed["status"] == "in_progress"

    status, _, body = route("PATCH", f"/api/tasks/{task_id}", {"checkout_run_id": "demo-run-failed"})
    payload = json.loads(body)
    assert status == 409
    assert payload["error"] == "checkout_fields_readonly"


def test_task_patch_review_done_and_blocked_update_run_ledger(tmp_path):
    store = configure_console_store(tmp_path / "hades.json")
    snapshot = _json("/api/console")[2]
    task_id = next(task["id"] for task in snapshot["tasks"] if task["status"] == "todo")
    agent_id = snapshot["agents"][0]["id"]

    status, _, _ = route(
        "POST",
        f"/api/tasks/{task_id}/checkout",
        {"agent_id": agent_id, "expected_statuses": ["todo"], "run_id": "run-route-done"},
    )
    assert status == 200
    status, _, _ = route("PATCH", f"/api/tasks/{task_id}", {"status": "in_review"})
    assert status == 200
    reviewed_run = next(run for run in _json("/api/runs")[2] if run["id"] == "run-route-done")
    assert reviewed_run["status"] == "running"
    assert reviewed_run["finished_at"] is None

    status, _, body = route("PATCH", f"/api/tasks/{task_id}", {"status": "done"})
    completed = json.loads(body)
    done_run = next(run for run in _json("/api/runs")[2] if run["id"] == "run-route-done")
    assert status == 200
    assert completed["completed_at"] is not None
    assert done_run["status"] == "succeeded"
    assert done_run["duration_ms"] >= 0
    assert done_run["result"] == "task completed"
    assert done_run["next_action"] == "done"

    second = store.create_task(
        {"project_id": snapshot["projects"][0]["id"], "title": "route blocker", "status": "todo"},
        "operator",
    )
    status, _, _ = route(
        "POST",
        f"/api/tasks/{second['id']}/checkout",
        {"agent_id": agent_id, "expected_statuses": ["todo"], "run_id": "run-route-blocked"},
    )
    assert status == 200
    status, _, body = route("PATCH", f"/api/tasks/{second['id']}", {"status": "blocked"})
    blocked = json.loads(body)
    blocked_run = next(run for run in _json("/api/runs")[2] if run["id"] == "run-route-blocked")
    assert status == 200
    assert blocked["status"] == "blocked"
    assert blocked_run["status"] == "failed"
    assert blocked_run["duration_ms"] >= 0
    assert blocked_run["error"] == "task blocked"
    assert blocked_run["next_action"] == "resolve blocker"

    status, _, body = route("POST", "/api/runs/run-route-blocked/retry", {"actor": "ops"})
    retried = json.loads(body)
    assert status == 201
    assert retried["status"] == "queued"
    assert retried["retry_of_run_id"] == "run-route-blocked"


def test_task_patch_terminal_run_and_bad_link_safety(tmp_path):
    store = configure_console_store(tmp_path / "hades.json")
    snapshot = _json("/api/console")[2]
    task_id = next(task["id"] for task in snapshot["tasks"] if task["status"] == "todo")
    agent_id = snapshot["agents"][0]["id"]

    status, _, _ = route(
        "POST",
        f"/api/tasks/{task_id}/checkout",
        {"agent_id": agent_id, "expected_statuses": ["todo"], "run_id": "run-route-terminal"},
    )
    assert status == 200
    status, _, _ = route("PATCH", f"/api/tasks/{task_id}", {"status": "in_review"})
    assert status == 200
    state = store._read()
    terminal = next(run for run in state["runs"] if run["id"] == "run-route-terminal")
    terminal.update(
        {
            "status": "succeeded",
            "finished_at": "2026-07-19T00:00:09Z",
            "duration_ms": 9000,
            "result": "already terminal",
            "next_action": "archived",
            "log": ["terminal before route done"],
        }
    )
    store._write(state)

    status, _, _ = route("PATCH", f"/api/tasks/{task_id}", {"status": "done"})
    terminal_after = next(run for run in _json("/api/runs")[2] if run["id"] == "run-route-terminal")
    assert status == 200
    assert terminal_after["result"] == "already terminal"
    assert terminal_after["next_action"] == "archived"
    assert terminal_after["duration_ms"] == 9000

    broken = store.create_task(
        {"project_id": snapshot["projects"][0]["id"], "title": "broken review", "status": "todo"},
        "operator",
    )
    claimed = store.checkout_task(broken["id"], agent_id, ["todo"], "run-route-missing", "operator")
    store.update_task(claimed["id"], {"status": "in_review"}, "operator")
    state = store._read()
    state["runs"] = [run for run in state["runs"] if run["id"] != "run-route-missing"]
    store._write(state)
    before = _json("/api/console")[2]

    status, _, body = route("PATCH", f"/api/tasks/{broken['id']}", {"status": "done"})
    payload = json.loads(body)
    after = _json("/api/console")[2]

    assert status == 409
    assert payload["error"] == "checkout_run_missing"
    assert next(task for task in after["tasks"] if task["id"] == broken["id"]) == next(
        task for task in before["tasks"] if task["id"] == broken["id"]
    )
    assert len(after["activity"]) == len(before["activity"])


def test_task_patch_rejects_project_change_while_checkout_link_is_retained(tmp_path):
    configure_console_store(tmp_path / "hades.json")
    snapshot = _json("/api/console")[2]
    original_project_id = snapshot["projects"][0]["id"]
    task_id = next(task["id"] for task in snapshot["tasks"] if task["status"] == "todo")
    agent_id = snapshot["agents"][0]["id"]
    status, _, body = route("POST", "/api/projects", {"name": "Other project", "status": "active"})
    other_project_id = json.loads(body)["id"]
    assert status == 201

    status, _, _ = route(
        "POST",
        f"/api/tasks/{task_id}/checkout",
        {"agent_id": agent_id, "expected_statuses": ["todo"], "run_id": "run-route-project-lock"},
    )
    assert status == 200
    status, _, _ = route("PATCH", f"/api/tasks/{task_id}", {"status": "in_review"})
    assert status == 200
    before = _json("/api/console")[2]

    status, _, body = route("PATCH", f"/api/tasks/{task_id}", {"project_id": other_project_id})
    payload = json.loads(body)
    after = _json("/api/console")[2]

    assert status == 409
    assert payload["error"] == "checkout_project_readonly"
    assert payload["details"] == {"project_id": original_project_id, "checkout_run_id": "run-route-project-lock"}
    assert next(task for task in after["tasks"] if task["id"] == task_id) == next(
        task for task in before["tasks"] if task["id"] == task_id
    )
    assert next(run for run in after["runs"] if run["id"] == "run-route-project-lock") == next(
        run for run in before["runs"] if run["id"] == "run-route-project-lock"
    )

    status, _, _ = route("PATCH", f"/api/tasks/{task_id}", {"status": "in_progress"})
    assert status == 200
    status, _, _ = route("POST", f"/api/tasks/{task_id}/release", {"operator": "tester"})
    assert status == 200
    status, _, body = route("PATCH", f"/api/tasks/{task_id}", {"project_id": other_project_id})
    assert status == 200
    assert json.loads(body)["project_id"] == other_project_id


def test_task_routes_validate_labels(tmp_path):
    configure_console_store(tmp_path / "hades.json")
    snapshot = _json("/api/console")[2]
    project_id = snapshot["projects"][0]["id"]
    task_id = next(task["id"] for task in snapshot["tasks"] if task["status"] == "todo")

    status, _, body = route("POST", "/api/tasks", {"project_id": project_id, "title": "labels", "labels": [" a "]})
    assert status == 201
    assert json.loads(body)["labels"] == ["a"]

    status, _, body = route("PATCH", f"/api/tasks/{task_id}", {"labels": [" backend "]})
    assert status == 200
    assert json.loads(body)["labels"] == ["backend"]

    for method, path, body_payload in (
        ("POST", "/api/tasks", {"project_id": project_id, "title": "bad", "labels": "backend"}),
        ("POST", "/api/tasks", {"project_id": project_id, "title": "bad", "labels": [""]}),
        ("PATCH", f"/api/tasks/{task_id}", {"labels": {"name": "backend"}}),
        ("PATCH", f"/api/tasks/{task_id}", {"labels": ["backend", 3]}),
    ):
        status, _, body = route(method, path, body_payload)
        payload = json.loads(body)
        assert status == 400
        assert payload["error"] == "invalid_labels"


def test_agent_pause_resume_routes(tmp_path):
    configure_console_store(tmp_path / "hades.json")
    agent_id = _json("/api/console")[2]["agents"][0]["id"]

    status, _, body = route("POST", f"/api/agents/{agent_id}/pause", {"reason": "manual hold", "actor": "ops"})
    assert status == 200
    assert json.loads(body)["status"] == "paused"

    status, _, body = route("POST", f"/api/agents/{agent_id}/resume", {"actor": "ops"})
    assert status == 200
    assert json.loads(body)["status"] == "idle"


def test_run_retry_preserves_original_and_returns_created(tmp_path):
    configure_console_store(tmp_path / "hades.json")
    failed_run = next(run for run in _json("/api/runs")[2] if run["status"] == "failed")

    status, _, body = route("POST", f"/api/runs/{failed_run['id']}/retry", {"actor": "ops"})
    retried = json.loads(body)
    assert status == 201
    assert retried["status"] == "queued"
    assert retried["retry_of_run_id"] == failed_run["id"]

    runs = _json("/api/runs")[2]
    original = next(run for run in runs if run["id"] == failed_run["id"])
    assert original["status"] == "failed"


def test_approval_action_routes_and_terminal_conflict(tmp_path):
    for action, expected_status in (
        ("approve", "approved"),
        ("reject", "rejected"),
        ("request-revision", "revision_requested"),
    ):
        configure_console_store(tmp_path / f"{action}.json")
        approval = next(item for item in _json("/api/approvals")[2] if item["status"] == "pending")
        status, _, body = route(
            "POST",
            f"/api/approvals/{approval['id']}/{action}",
            {"note": "route decision", "actor": "reviewer"},
        )
        assert status == 200
        assert json.loads(body)["status"] == expected_status

    status, _, body = route(
        "POST",
        f"/api/approvals/{approval['id']}/reject",
        {"note": "late", "actor": "reviewer"},
    )
    payload = json.loads(body)
    assert status == 409
    assert {"error", "message", "details"}.issubset(payload)


def test_management_structured_errors(tmp_path):
    configure_console_store(tmp_path / "hades.json")
    status, _, body = route("DELETE", "/api/tasks")
    assert status == 405
    assert json.loads(body)["error"] == "method_not_allowed"

    status, _, body = route("PATCH", "/api/tasks/missing", {"description": "x"})
    assert status == 404
    assert {"error", "message", "details"}.issubset(json.loads(body))

    status, _, body = route("POST", "/api/tasks", ["not", "object"])
    assert status == 400
    assert json.loads(body)["error"] == "invalid_payload"

    status, _, body = route("POST", "/api/projects", {"name": "bad", "status": "invalid"})
    assert status == 400
    assert json.loads(body)["error"] == "invalid_enum"


def test_management_route_wrong_method_matrix_returns_405(tmp_path):
    configure_console_store(tmp_path / "hades.json")
    snapshot = _json("/api/console")[2]
    task_id = snapshot["tasks"][0]["id"]
    agent_id = snapshot["agents"][0]["id"]
    run_id = snapshot["runs"][0]["id"]
    approval_id = snapshot["approvals"][0]["id"]

    cases = [
        ("POST", "/api/console"),
        ("PATCH", "/api/console"),
        ("PATCH", "/api/tasks"),
        ("PATCH", f"/api/tasks/{task_id}/checkout"),
        ("PATCH", f"/api/tasks/{task_id}/release"),
        ("PATCH", f"/api/agents/{agent_id}/pause"),
        ("PATCH", f"/api/agents/{agent_id}/resume"),
        ("PATCH", f"/api/runs/{run_id}/retry"),
        ("PATCH", f"/api/approvals/{approval_id}/approve"),
    ]

    for method, path in cases:
        status, ctype, body = route(method, path, {})
        payload = json.loads(body)
        assert status == 405, (method, path, payload)
        assert "application/json" in ctype
        assert payload["error"] == "method_not_allowed"
        assert {"message", "details"}.issubset(payload)


def test_management_action_routes_wrong_method_get_returns_405(tmp_path):
    configure_console_store(tmp_path / "hades.json")
    snapshot = _json("/api/console")[2]
    task_id = snapshot["tasks"][0]["id"]
    agent_id = snapshot["agents"][0]["id"]
    run_id = snapshot["runs"][0]["id"]
    approval_id = snapshot["approvals"][0]["id"]

    paths = [
        f"/api/tasks/{task_id}/checkout",
        f"/api/tasks/{task_id}/release",
        f"/api/agents/{agent_id}/pause",
        f"/api/agents/{agent_id}/resume",
        f"/api/runs/{run_id}/retry",
        f"/api/approvals/{approval_id}/approve",
        f"/api/approvals/{approval_id}/reject",
        f"/api/approvals/{approval_id}/request-revision",
    ]

    for path in paths:
        status, ctype, body = route("GET", path)
        payload = json.loads(body)
        assert status == 405, (path, payload)
        assert "application/json" in ctype
        assert payload["error"] == "method_not_allowed"
        assert {"message", "details"}.issubset(payload)


def test_checkout_rejects_invalid_expected_statuses_payloads(tmp_path):
    configure_console_store(tmp_path / "hades.json")
    snapshot = _json("/api/console")[2]
    task_id = next(task["id"] for task in snapshot["tasks"] if task["status"] == "todo")
    agent_id = snapshot["agents"][0]["id"]

    for expected_statuses in ([], "todo", ["todo", 3], [""], [None]):
        status, _, body = route(
            "POST",
            f"/api/tasks/{task_id}/checkout",
            {
                "agent_id": agent_id,
                "expected_statuses": expected_statuses,
                "run_id": f"run-{type(expected_statuses).__name__}",
            },
        )
        payload = json.loads(body)
        assert status == 400
        assert payload["error"] == "invalid_expected_statuses"


def test_negative_content_length_is_rejected():
    handler = object.__new__(_Handler)
    handler.headers = {"Content-Length": "-1"}
    handler.rfile = io.BytesIO(b"")

    with pytest.raises(ConsoleError) as error:
        handler._read_json()

    assert error.value.status == 400
    assert error.value.code == "invalid_content_length"


def test_server_serves_over_a_real_socket():
    server = make_server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        with closing(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=5)) as resp:
            assert resp.status == 200
            assert json.loads(resp.read())["status"] == "ok"
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_real_http_post_creates_project(tmp_path):
    configure_console_store(tmp_path / "hades.json")
    server = make_server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        data = json.dumps({"name": "real post"}).encode("utf-8")
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/projects",
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with closing(urllib.request.urlopen(request, timeout=5)) as resp:
            assert resp.status == 201
            assert json.loads(resp.read())["name"] == "real post"
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_real_http_json_errors_are_structured(tmp_path):
    configure_console_store(tmp_path / "hades.json")
    server = make_server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        malformed = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/projects",
            data=b"{",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(malformed, timeout=5)
        except urllib.error.HTTPError as error:
            assert error.code == 400
            assert json.loads(error.read())["error"] == "invalid_json"
        else:
            raise AssertionError("malformed JSON request should fail")

        non_object = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/projects",
            data=b'["not-object"]',
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(non_object, timeout=5)
        except urllib.error.HTTPError as error:
            assert error.code == 400
            assert json.loads(error.read())["error"] == "invalid_payload"
        else:
            raise AssertionError("non-object JSON request should fail")

        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        try:
            conn.putrequest("POST", "/api/projects")
            conn.putheader("Content-Type", "application/json")
            conn.putheader("Content-Length", str(MAX_JSON_BODY + 1))
            conn.putheader("Expect", "100-continue")
            conn.endheaders()
            resp = conn.getresponse()
            assert resp.status == 413
            assert json.loads(resp.read())["error"] == "payload_too_large"
        finally:
            conn.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_real_http_unsupported_methods_return_structured_json(tmp_path):
    configure_console_store(tmp_path / "hades.json")
    server = make_server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        try:
            for method in ("DELETE", "PUT"):
                conn.request(method, "/api/tasks")
                resp = conn.getresponse()
                payload = json.loads(resp.read())
                assert resp.status == 405
                assert resp.getheader("Content-Type").startswith("application/json")
                assert payload["error"] == "method_not_allowed"

            conn.request("HEAD", "/api/tasks")
            resp = conn.getresponse()
            assert resp.status == 405
            assert resp.getheader("Content-Type").startswith("application/json")
        finally:
            conn.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
