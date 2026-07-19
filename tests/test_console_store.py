import pytest

from h2l.console_store import ConsoleError, HadesConsoleStore, seed_console_data


def test_store_seeds_and_persists(tmp_path):
    path = tmp_path / "console.json"
    store = HadesConsoleStore(path)
    first = store.snapshot()
    assert first["overview"]["project_count"] >= 1
    created = store.create_task(
        {
            "project_id": first["projects"][0]["id"],
            "title": "정적 앱 셸 검증",
            "status": "todo",
            "priority": "high",
        },
        actor="test-user",
    )
    reloaded = HadesConsoleStore(path).snapshot()
    assert any(task["id"] == created["id"] for task in reloaded["tasks"])


def test_checkout_is_atomic(tmp_path):
    store = HadesConsoleStore(tmp_path / "console.json")
    task = next(item for item in store.snapshot()["tasks"] if item["status"] == "todo")
    agent = store.snapshot()["agents"][0]
    claimed = store.checkout_task(task["id"], agent["id"], ["todo"], "run-test", "operator")
    assert claimed["status"] == "in_progress"
    with pytest.raises(ConsoleError) as error:
        store.checkout_task(task["id"], "other-agent", ["todo"], "run-other", "operator")
    assert error.value.status == 409


def test_checkout_rejects_existing_run_id_without_mutation(tmp_path):
    store = HadesConsoleStore(tmp_path / "console.json")
    snapshot = store.snapshot()
    task = next(item for item in snapshot["tasks"] if item["status"] == "todo")
    agent = snapshot["agents"][0]
    existing_run = next(item for item in snapshot["runs"] if item["id"] == "demo-run-failed")
    before_activity = len(snapshot["activity"])

    with pytest.raises(ConsoleError) as error:
        store.checkout_task(task["id"], agent["id"], ["todo"], existing_run["id"], "operator")

    assert error.value.status == 409
    after = store.snapshot()
    unchanged_task = next(item for item in after["tasks"] if item["id"] == task["id"])
    unchanged_run = next(item for item in after["runs"] if item["id"] == existing_run["id"])
    assert unchanged_task == task
    assert unchanged_run == existing_run
    assert len(after["runs"]) == len(snapshot["runs"])
    assert len(after["activity"]) == before_activity


def test_approval_decision_is_terminal(tmp_path):
    store = HadesConsoleStore(tmp_path / "console.json")
    approval = next(item for item in store.snapshot()["approvals"] if item["status"] == "pending")
    decided = store.decide_approval(approval["id"], "approve", "운영 범위 확인", "reviewer")
    assert decided["status"] == "approved"
    with pytest.raises(ConsoleError) as error:
        store.decide_approval(approval["id"], "reject", "late", "reviewer")
    assert error.value.status == 409


def test_agent_release_retry_and_cost_summary(tmp_path):
    store = HadesConsoleStore(tmp_path / "console.json")
    snapshot = store.snapshot()
    agent = snapshot["agents"][0]
    task = next(item for item in snapshot["tasks"] if item["status"] == "todo")

    updated_agent = store.set_agent_status(agent["id"], "running", "checkout", "operator")
    assert updated_agent["status"] == "running"
    claimed = store.checkout_task(task["id"], agent["id"], ["todo"], "run-demo", "operator")
    released = store.release_task(claimed["id"], "operator")
    assert released["status"] == "todo"
    assert released["assignee_agent_id"] is None
    assert released["checkout_run_id"] is None

    failed_run = next(item for item in store.snapshot()["runs"] if item["status"] == "failed")
    retried = store.retry_run(failed_run["id"], "operator")
    assert retried["status"] == "queued"
    assert retried["retry_of_run_id"] == failed_run["id"]

    costs = store.cost_summary()
    assert costs["total_cost_cents"] > 0
    assert costs["total_tokens"] > 0


def test_validation_rejects_bad_references_and_enums(tmp_path):
    store = HadesConsoleStore(tmp_path / "console.json")
    with pytest.raises(ConsoleError) as error:
        store.create_task(
            {
                "project_id": "missing",
                "title": "bad",
                "status": "todo",
                "priority": "high",
            },
            actor="operator",
        )
    assert error.value.status == 404

    project = store.snapshot()["projects"][0]
    with pytest.raises(ConsoleError) as error:
        store.update_project(project["id"], {"status": "invalid"}, "operator")
    assert error.value.status == 400


def test_seed_list_and_update_interfaces(tmp_path):
    seed = seed_console_data()
    assert seed["projects"][0]["source"] == "demo"

    store = HadesConsoleStore(tmp_path / "console.json")
    projects = store.list_entities("projects")
    project = store.update_project(projects[0]["id"], {"status": "paused"}, "operator")
    assert project["status"] == "paused"

    task = store.snapshot()["tasks"][0]
    updated = store.update_task(task["id"], {"priority": "critical", "description": "updated"}, "operator")
    assert updated["priority"] == "critical"
    assert updated["description"] == "updated"


def test_seed_uses_canonical_schema_and_enums(tmp_path):
    store = HadesConsoleStore(tmp_path / "console.json")
    snapshot = store.snapshot()

    assert {project["status"] for project in snapshot["projects"]} <= {
        "planned",
        "active",
        "paused",
        "completed",
        "cancelled",
    }
    assert {task["status"] for task in snapshot["tasks"]} <= {
        "backlog",
        "todo",
        "in_progress",
        "in_review",
        "blocked",
        "done",
    }
    assert {agent["status"] for agent in snapshot["agents"]} <= {
        "idle",
        "running",
        "paused",
        "error",
        "terminated",
    }
    assert {run["status"] for run in snapshot["runs"]} <= {"queued", "running", "succeeded", "failed", "cancelled"}

    assert {
        "id",
        "name",
        "description",
        "status",
        "goal",
        "target_date",
        "lead_agent_id",
        "color",
        "created_at",
        "updated_at",
    } <= set(snapshot["projects"][0])
    assert {
        "id",
        "project_id",
        "title",
        "description",
        "status",
        "priority",
        "assignee_agent_id",
        "checkout_run_id",
        "labels",
        "created_at",
        "updated_at",
        "started_at",
        "completed_at",
    } <= set(snapshot["tasks"][0])
    assert {
        "id",
        "name",
        "role",
        "title",
        "status",
        "capabilities",
        "reports_to",
        "budget_monthly_cents",
        "spent_monthly_cents",
        "last_heartbeat_at",
        "pause_reason",
        "created_at",
        "updated_at",
    } <= set(snapshot["agents"][0])
    assert {
        "id",
        "task_id",
        "project_id",
        "agent_id",
        "status",
        "invocation_source",
        "started_at",
        "finished_at",
        "duration_ms",
        "result",
        "error",
        "next_action",
        "usage",
        "cost_cents",
        "log",
    } <= set(snapshot["runs"][0])
    assert {
        "id",
        "agent_id",
        "task_id",
        "project_id",
        "run_id",
        "provider",
        "model",
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
        "cost_cents",
        "occurred_at",
    } <= set(snapshot["cost_events"][0])
    assert {
        "id",
        "type",
        "title",
        "status",
        "requested_by",
        "payload",
        "decision_note",
        "decided_by",
        "decided_at",
        "created_at",
        "updated_at",
    } <= set(snapshot["approvals"][0])
    assert {
        "id",
        "actor_type",
        "actor_id",
        "action",
        "entity_type",
        "entity_id",
        "run_id",
        "details",
        "created_at",
    } <= set(snapshot["activity"][0])


def test_task_lifecycle_rejects_invalid_transitions_and_unowned_in_progress(tmp_path):
    store = HadesConsoleStore(tmp_path / "console.json")
    task = next(item for item in store.snapshot()["tasks"] if item["status"] == "todo")

    with pytest.raises(ConsoleError) as error:
        store.update_task(task["id"], {"status": "done"}, "operator")
    assert error.value.status == 409
    assert store.snapshot()["tasks"][0]["status"] == "todo"

    with pytest.raises(ConsoleError) as error:
        store.update_task(task["id"], {"status": "in_progress"}, "operator")
    assert error.value.status == 409

    with pytest.raises(ConsoleError) as error:
        store.release_task(task["id"], "operator")
    assert error.value.status == 409


def test_request_revision_and_activity_are_canonical_and_append_only(tmp_path):
    path = tmp_path / "console.json"
    store = HadesConsoleStore(path)
    approval = next(item for item in store.snapshot()["approvals"] if item["status"] == "pending")
    before = len(store.snapshot()["activity"])

    decided = store.decide_approval(approval["id"], "request-revision", "범위 재확인", "reviewer")

    assert decided["status"] == "revision_requested"
    assert decided["decision_note"] == "범위 재확인"
    reloaded = HadesConsoleStore(path).snapshot()
    assert len(reloaded["activity"]) == before + 1
    event = reloaded["activity"][-1]
    assert event["actor_type"] == "user"
    assert event["actor_id"] == "reviewer"
    assert event["action"] == "request_revision_approval"
    assert event["entity_type"] == "approval"
    assert event["entity_id"] == approval["id"]


def test_retry_preserves_terminal_run_and_records_one_activity_event(tmp_path):
    store = HadesConsoleStore(tmp_path / "console.json")
    failed_run = next(item for item in store.snapshot()["runs"] if item["status"] == "failed")
    before = store.snapshot()

    retried = store.retry_run(failed_run["id"], "operator")
    after = store.snapshot()

    original = next(item for item in after["runs"] if item["id"] == failed_run["id"])
    assert original["status"] == "failed"
    assert retried["status"] == "queued"
    assert retried["retry_of_run_id"] == failed_run["id"]
    assert len(after["runs"]) == len(before["runs"]) + 1
    assert len(after["activity"]) == len(before["activity"]) + 1
    assert after["activity"][-1]["action"] == "retry_run"


def test_cost_summary_includes_token_cents_and_attribution(tmp_path):
    store = HadesConsoleStore(tmp_path / "console.json")
    cost = store.snapshot()["cost_events"][0]

    summary = store.cost_summary()

    assert summary["total_cost_cents"] == cost["cost_cents"]
    assert summary["total_tokens"] == cost["input_tokens"] + cost["cached_input_tokens"] + cost["output_tokens"]
    assert summary["by_agent"][cost["agent_id"]]["cost_cents"] == cost["cost_cents"]
    assert summary["by_project"][cost["project_id"]]["cost_cents"] == cost["cost_cents"]
    assert summary["utilization"]["spent_cents"] >= cost["cost_cents"]
    assert summary["utilization"]["budget_cents"] >= summary["utilization"]["spent_cents"]


def test_each_mutation_appends_exactly_one_activity_event(tmp_path):
    store = HadesConsoleStore(tmp_path / "console.json")

    def assert_one_event(operation):
        before = len(store.snapshot()["activity"])
        result = operation()
        after = len(store.snapshot()["activity"])
        assert after == before + 1
        return result

    agent_id = store.snapshot()["agents"][0]["id"]
    project = assert_one_event(
        lambda: store.create_project(
            {"name": "운영 검증", "status": "planned", "lead_agent_id": agent_id},
            "operator",
        )
    )
    assert_one_event(lambda: store.update_project(project["id"], {"status": "active"}, "operator"))
    task = assert_one_event(
        lambda: store.create_task(
            {"project_id": project["id"], "title": "활동 로그 검증", "status": "todo", "priority": "medium"},
            "operator",
        )
    )
    assert_one_event(lambda: store.update_task(task["id"], {"description": "canonical activity"}, "operator"))
    assert_one_event(lambda: store.checkout_task(task["id"], agent_id, ["todo"], "activity-run", "operator"))
    assert_one_event(lambda: store.release_task(task["id"], "operator"))
    assert_one_event(lambda: store.set_agent_status(agent_id, "paused", "manual hold", "operator"))
    approval = next(item for item in store.snapshot()["approvals"] if item["status"] == "pending")
    assert_one_event(lambda: store.decide_approval(approval["id"], "approve", "ok", "operator"))
    failed_run = next(item for item in store.snapshot()["runs"] if item["status"] == "failed")
    assert_one_event(lambda: store.retry_run(failed_run["id"], "operator"))
