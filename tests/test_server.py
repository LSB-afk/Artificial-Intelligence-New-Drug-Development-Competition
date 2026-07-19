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
from h2l.server import _Handler, configure_console_store, make_server, route


def _json(path, method="GET", body=None):
    status, ctype, body = route(method, path, body)
    return status, ctype, json.loads(body)


def test_health_route():
    status, _, payload = _json("/api/health")
    assert status == 200 and payload["status"] == "ok"


def test_index_is_the_static_shell():
    status, ctype, body = route("GET", "/")
    assert status == 200
    assert "text/html" in ctype
    # JB-style app shell markers, rendered client-side.
    assert "H2L-Forge" in body
    assert "sync-rail" in body
    assert "primary-nav" in body
    assert 'src="static/app.js"' in body


def test_static_css_and_js_are_served():
    css_status, css_ctype, css_body = route("GET", "/static/styles.css")
    assert css_status == 200
    assert "text/css" in css_ctype
    assert "--corporate-green" in css_body  # JB design tokens reused verbatim

    js_status, js_ctype, js_body = route("GET", "/static/app.js")
    assert js_status == 200
    assert "javascript" in js_ctype


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

    status, _, body = route("GET", "/api/tasks/missing")
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

        too_large = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/projects",
            data=b'{"padding":"' + (b"x" * (1024 * 1024 + 1)) + b'"}',
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(too_large, timeout=5)
        except urllib.error.HTTPError as error:
            assert error.code == 413
            assert json.loads(error.read())["error"] == "payload_too_large"
        else:
            raise AssertionError("oversized JSON request should fail")
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
