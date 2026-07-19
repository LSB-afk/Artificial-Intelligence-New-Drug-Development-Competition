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


def test_release_task_cancels_active_checkout_run_before_clearing_links(tmp_path):
    store = HadesConsoleStore(tmp_path / "console.json")
    snapshot = store.snapshot()
    task = next(item for item in snapshot["tasks"] if item["status"] == "todo")
    agent = snapshot["agents"][0]

    claimed = store.checkout_task(task["id"], agent["id"], ["todo"], "run-release-cancel", "operator")
    before_activity = len(store.snapshot()["activity"])
    released = store.release_task(claimed["id"], "operator")
    after = store.snapshot()
    run = next(item for item in after["runs"] if item["id"] == "run-release-cancel")

    assert released["status"] == "todo"
    assert released["assignee_agent_id"] is None
    assert released["checkout_run_id"] is None
    assert run["status"] == "cancelled"
    assert run["finished_at"] is not None
    assert run["duration_ms"] >= 0
    assert run["next_action"] == "checkout released"
    assert "checkout released by operator" in run["log"]
    assert len(after["activity"]) == before_activity + 1
    assert after["activity"][-1]["action"] == "release_task"
    assert after["activity"][-1]["run_id"] == "run-release-cancel"


def test_release_task_does_not_rewrite_terminal_checkout_run(tmp_path):
    store = HadesConsoleStore(tmp_path / "console.json")
    state = store.snapshot()
    task = next(item for item in state["tasks"] if item["status"] == "todo")
    agent = state["agents"][0]
    claimed = store.checkout_task(task["id"], agent["id"], ["todo"], "run-terminal-release", "operator")
    state = store._read()
    run = next(item for item in state["runs"] if item["id"] == "run-terminal-release")
    run.update(
        {
            "status": "succeeded",
            "finished_at": "2026-07-19T00:00:05Z",
            "duration_ms": 5000,
            "next_action": "complete",
            "log": ["done"],
        }
    )
    store._write(state)

    store.release_task(claimed["id"], "operator")
    released_run = next(item for item in store.snapshot()["runs"] if item["id"] == "run-terminal-release")

    assert released_run["status"] == "succeeded"
    assert released_run["finished_at"] == "2026-07-19T00:00:05Z"
    assert released_run["duration_ms"] == 5000
    assert released_run["next_action"] == "complete"
    assert released_run["log"] == ["done"]


def test_release_task_rejects_missing_checkout_run_without_mutation(tmp_path):
    store = HadesConsoleStore(tmp_path / "console.json")
    state = store.snapshot()
    task = next(item for item in state["tasks"] if item["status"] == "todo")
    agent = state["agents"][0]
    claimed = store.checkout_task(task["id"], agent["id"], ["todo"], "run-missing-release", "operator")
    state = store._read()
    state["runs"] = [run for run in state["runs"] if run["id"] != "run-missing-release"]
    store._write(state)

    before = store.snapshot()
    with pytest.raises(ConsoleError) as error:
        store.release_task(claimed["id"], "operator")
    after = store.snapshot()

    assert error.value.status == 409
    assert error.value.code == "checkout_run_missing"
    assert next(item for item in after["tasks"] if item["id"] == claimed["id"]) == next(
        item for item in before["tasks"] if item["id"] == claimed["id"]
    )
    assert not any(run["id"] == "run-missing-release" for run in after["runs"])
    assert len(after["activity"]) == len(before["activity"])


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


def test_task_labels_are_validated_and_normalized(tmp_path):
    store = HadesConsoleStore(tmp_path / "console.json")
    project = store.snapshot()["projects"][0]

    created = store.create_task(
        {"project_id": project["id"], "title": "labels", "labels": [" frontend ", "api"]},
        "operator",
    )
    assert created["labels"] == ["frontend", "api"]

    updated = store.update_task(created["id"], {"labels": [" urgent "]}, "operator")
    assert updated["labels"] == ["urgent"]

    for labels in ("urgent", {"name": "urgent"}, ["ok", ""], ["ok", 3], ["ok", "   "]):
        with pytest.raises(ConsoleError) as error:
            store.create_task({"project_id": project["id"], "title": "bad labels", "labels": labels}, "operator")
        assert error.value.status == 400
        assert error.value.code == "invalid_labels"

        with pytest.raises(ConsoleError) as error:
            store.update_task(created["id"], {"labels": labels}, "operator")
        assert error.value.status == 400
        assert error.value.code == "invalid_labels"


def test_create_task_rejects_checkout_run_id(tmp_path):
    store = HadesConsoleStore(tmp_path / "console.json")
    snapshot = store.snapshot()
    project = snapshot["projects"][0]
    existing_run = snapshot["runs"][0]

    for field in ("checkout_run_id", "run_id"):
        with pytest.raises(ConsoleError) as error:
            store.create_task(
                {
                    "project_id": project["id"],
                    "title": "bad checkout link",
                    field: existing_run["id"],
                },
                "operator",
            )
        assert error.value.status == 409
        assert error.value.code == "checkout_fields_readonly"
        assert error.value.details["fields"] == ["checkout_run_id"]


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
    snapshot = store.snapshot()
    task = next(item for item in snapshot["tasks"] if item["status"] == "todo")
    blocked = next(item for item in snapshot["tasks"] if item["status"] == "blocked")
    project = snapshot["projects"][0]
    agent = snapshot["agents"][0]

    with pytest.raises(ConsoleError) as error:
        store.create_task(
            {
                "project_id": project["id"],
                "title": "bad direct start",
                "status": "in_progress",
                "assignee_agent_id": agent["id"],
            },
            "operator",
        )
    assert error.value.status == 409
    assert error.value.code == "checkout_required"

    with pytest.raises(ConsoleError) as error:
        store.update_task(task["id"], {"status": "done"}, "operator")
    assert error.value.status == 409
    assert store.snapshot()["tasks"][0]["status"] == "todo"

    with pytest.raises(ConsoleError) as error:
        store.update_task(task["id"], {"status": "in_progress"}, "operator")
    assert error.value.status == 409
    assert error.value.code == "checkout_required"

    with pytest.raises(ConsoleError) as error:
        store.update_task(blocked["id"], {"status": "in_progress"}, "operator")
    assert error.value.status == 409
    assert error.value.code == "checkout_required"

    with pytest.raises(ConsoleError) as error:
        store.release_task(task["id"], "operator")
    assert error.value.status == 409


def test_task_update_can_resume_in_progress_with_active_matching_checkout(tmp_path):
    store = HadesConsoleStore(tmp_path / "console.json")
    snapshot = store.snapshot()
    task = next(item for item in snapshot["tasks"] if item["status"] == "todo")
    agent = snapshot["agents"][0]

    claimed = store.checkout_task(task["id"], agent["id"], ["todo"], "run-resume", "operator")
    reviewed = store.update_task(claimed["id"], {"status": "in_review"}, "operator")
    resumed = store.update_task(
        reviewed["id"],
        {
            "status": "in_progress",
            "assignee_agent_id": agent["id"],
            "checkout_run_id": "run-resume",
        },
        "operator",
    )

    assert resumed["status"] == "in_progress"
    assert resumed["assignee_agent_id"] == agent["id"]
    assert resumed["checkout_run_id"] == "run-resume"

    with pytest.raises(ConsoleError) as error:
        store.update_task(resumed["id"], {"assignee_agent_id": "demo-agent-reviewer"}, "operator")
    assert error.value.status == 409
    assert error.value.code == "checkout_fields_readonly"

    with pytest.raises(ConsoleError) as error:
        store.update_task(resumed["id"], {"checkout_run_id": "demo-run-failed"}, "operator")
    assert error.value.status == 409
    assert error.value.code == "checkout_fields_readonly"


def test_task_review_keeps_checkout_run_active_and_done_closes_it(tmp_path):
    store = HadesConsoleStore(tmp_path / "console.json")
    snapshot = store.snapshot()
    task = next(item for item in snapshot["tasks"] if item["status"] == "todo")
    agent = snapshot["agents"][0]

    claimed = store.checkout_task(task["id"], agent["id"], ["todo"], "run-review-done", "operator")
    reviewed = store.update_task(claimed["id"], {"status": "in_review"}, "operator")
    after_review = store.snapshot()
    review_run = next(item for item in after_review["runs"] if item["id"] == "run-review-done")
    before_done_activity = len(after_review["activity"])

    assert reviewed["status"] == "in_review"
    assert reviewed["checkout_run_id"] == "run-review-done"
    assert review_run["status"] == "running"
    assert review_run["finished_at"] is None
    assert review_run["duration_ms"] is None

    completed = store.update_task(reviewed["id"], {"status": "done"}, "operator")
    after_done = store.snapshot()
    done_run = next(item for item in after_done["runs"] if item["id"] == "run-review-done")

    assert completed["status"] == "done"
    assert completed["completed_at"] is not None
    assert done_run["status"] == "succeeded"
    assert done_run["finished_at"] is not None
    assert done_run["duration_ms"] >= 0
    assert done_run["result"] == "task completed"
    assert done_run["next_action"] == "done"
    assert "task completed by operator" in done_run["log"]
    assert len(after_done["activity"]) == before_done_activity + 1
    assert after_done["activity"][-1]["action"] == "update_task"
    assert after_done["activity"][-1]["run_id"] == "run-review-done"


def test_task_blocked_closes_checkout_run_failed_and_retryable(tmp_path):
    store = HadesConsoleStore(tmp_path / "console.json")
    snapshot = store.snapshot()
    task = next(item for item in snapshot["tasks"] if item["status"] == "todo")
    agent = snapshot["agents"][0]

    claimed = store.checkout_task(task["id"], agent["id"], ["todo"], "run-blocked", "operator")
    before_activity = len(store.snapshot()["activity"])
    blocked = store.update_task(claimed["id"], {"status": "blocked"}, "operator")
    after_blocked = store.snapshot()
    blocked_run = next(item for item in after_blocked["runs"] if item["id"] == "run-blocked")

    assert blocked["status"] == "blocked"
    assert blocked_run["status"] == "failed"
    assert blocked_run["finished_at"] is not None
    assert blocked_run["duration_ms"] >= 0
    assert blocked_run["error"] == "task blocked"
    assert blocked_run["next_action"] == "resolve blocker"
    assert "task blocked by operator" in blocked_run["log"]
    assert len(after_blocked["activity"]) == before_activity + 1
    assert after_blocked["activity"][-1]["run_id"] == "run-blocked"

    retried = store.retry_run("run-blocked", "operator")
    assert retried["status"] == "queued"
    assert retried["retry_of_run_id"] == "run-blocked"


def test_task_done_preserves_terminal_linked_run_and_allows_legacy_unlinked_review(tmp_path):
    store = HadesConsoleStore(tmp_path / "console.json")
    snapshot = store.snapshot()
    task = next(item for item in snapshot["tasks"] if item["status"] == "todo")
    agent = snapshot["agents"][0]
    claimed = store.checkout_task(task["id"], agent["id"], ["todo"], "run-terminal-done", "operator")
    reviewed = store.update_task(claimed["id"], {"status": "in_review"}, "operator")
    state = store._read()
    run = next(item for item in state["runs"] if item["id"] == "run-terminal-done")
    run.update(
        {
            "status": "succeeded",
            "finished_at": "2026-07-19T00:00:07Z",
            "duration_ms": 7000,
            "result": "already terminal",
            "next_action": "archived",
            "log": ["terminal before task done"],
        }
    )
    store._write(state)

    completed = store.update_task(reviewed["id"], {"status": "done"}, "operator")
    terminal_run = next(item for item in store.snapshot()["runs"] if item["id"] == "run-terminal-done")

    assert completed["status"] == "done"
    assert terminal_run["status"] == "succeeded"
    assert terminal_run["finished_at"] == "2026-07-19T00:00:07Z"
    assert terminal_run["duration_ms"] == 7000
    assert terminal_run["result"] == "already terminal"
    assert terminal_run["next_action"] == "archived"
    assert terminal_run["log"] == ["terminal before task done"]

    legacy = store.create_task(
        {"project_id": snapshot["projects"][0]["id"], "title": "legacy review", "status": "todo"},
        "operator",
    )
    state = store._read()
    legacy_task = next(item for item in state["tasks"] if item["id"] == legacy["id"])
    legacy_task["status"] = "in_review"
    store._write(state)
    legacy_completed = store.update_task(legacy["id"], {"status": "done"}, "operator")
    assert legacy_completed["status"] == "done"
    assert legacy_completed["checkout_run_id"] is None


def test_task_terminal_transitions_reject_missing_or_mismatched_checkout_run_without_mutation(tmp_path):
    store = HadesConsoleStore(tmp_path / "console.json")
    snapshot = store.snapshot()
    task = next(item for item in snapshot["tasks"] if item["status"] == "todo")
    agent = snapshot["agents"][0]
    claimed = store.checkout_task(task["id"], agent["id"], ["todo"], "run-missing-terminal", "operator")
    reviewed = store.update_task(claimed["id"], {"status": "in_review"}, "operator")
    state = store._read()
    state["runs"] = [run for run in state["runs"] if run["id"] != "run-missing-terminal"]
    store._write(state)
    before_missing = store.snapshot()

    with pytest.raises(ConsoleError) as error:
        store.update_task(reviewed["id"], {"status": "done"}, "operator")
    after_missing = store.snapshot()

    assert error.value.status == 409
    assert error.value.code == "checkout_run_missing"
    assert next(item for item in after_missing["tasks"] if item["id"] == reviewed["id"]) == next(
        item for item in before_missing["tasks"] if item["id"] == reviewed["id"]
    )
    assert len(after_missing["activity"]) == len(before_missing["activity"])

    mismatch_task = store.create_task(
        {"project_id": snapshot["projects"][0]["id"], "title": "mismatched block", "status": "todo"},
        "operator",
    )
    claimed = store.checkout_task(mismatch_task["id"], agent["id"], ["todo"], "run-mismatch-block", "operator")
    state = store._read()
    run = next(item for item in state["runs"] if item["id"] == "run-mismatch-block")
    run["agent_id"] = "demo-agent-reviewer"
    store._write(state)
    before_mismatch = store.snapshot()

    with pytest.raises(ConsoleError) as error:
        store.update_task(claimed["id"], {"status": "blocked"}, "operator")
    after_mismatch = store.snapshot()

    assert error.value.status == 409
    assert error.value.code == "inconsistent_checkout"
    assert next(item for item in after_mismatch["tasks"] if item["id"] == claimed["id"]) == next(
        item for item in before_mismatch["tasks"] if item["id"] == claimed["id"]
    )
    assert next(item for item in after_mismatch["runs"] if item["id"] == "run-mismatch-block") == next(
        item for item in before_mismatch["runs"] if item["id"] == "run-mismatch-block"
    )
    assert len(after_mismatch["activity"]) == len(before_mismatch["activity"])


def test_task_project_change_is_rejected_while_checkout_link_is_retained(tmp_path):
    store = HadesConsoleStore(tmp_path / "console.json")
    snapshot = store.snapshot()
    project = snapshot["projects"][0]
    other_project = store.create_project({"name": "Other project", "status": "active"}, "operator")
    task = next(item for item in snapshot["tasks"] if item["status"] == "todo")
    agent = snapshot["agents"][0]

    claimed = store.checkout_task(task["id"], agent["id"], ["todo"], "run-project-lock", "operator")
    reviewed = store.update_task(claimed["id"], {"status": "in_review"}, "operator")
    before = store.snapshot()

    with pytest.raises(ConsoleError) as error:
        store.update_task(reviewed["id"], {"project_id": other_project["id"]}, "operator")
    after = store.snapshot()

    assert error.value.status == 409
    assert error.value.code == "checkout_project_readonly"
    assert error.value.details == {"project_id": project["id"], "checkout_run_id": "run-project-lock"}
    assert next(item for item in after["tasks"] if item["id"] == reviewed["id"]) == next(
        item for item in before["tasks"] if item["id"] == reviewed["id"]
    )
    assert next(item for item in after["runs"] if item["id"] == "run-project-lock") == next(
        item for item in before["runs"] if item["id"] == "run-project-lock"
    )

    resumed = store.update_task(reviewed["id"], {"status": "in_progress"}, "operator")
    released = store.release_task(resumed["id"], "operator")
    moved = store.update_task(released["id"], {"project_id": other_project["id"]}, "operator")
    assert moved["project_id"] == other_project["id"]


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
