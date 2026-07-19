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

    updated_agent = store.set_agent_status(agent["id"], "busy", "checkout", "operator")
    assert updated_agent["status"] == "busy"
    claimed = store.checkout_task(task["id"], agent["id"], ["todo"], "run-demo", "operator")
    released = store.release_task(claimed["id"], "operator")
    assert released["status"] == "todo"
    assert released["assignee_id"] is None
    assert released["run_id"] is None

    failed_run = next(item for item in store.snapshot()["runs"] if item["status"] == "failed")
    retried = store.retry_run(failed_run["id"], "operator")
    assert retried["status"] == "queued"
    assert retried["retry_of"] == failed_run["id"]

    costs = store.cost_summary()
    assert costs["total_usd"] > 0
    assert costs["currency"] == "USD"


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
    updated = store.update_task(task["id"], {"priority": "critical", "status": "blocked"}, "operator")
    assert updated["priority"] == "critical"
    assert updated["status"] == "blocked"
