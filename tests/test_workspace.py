"""The console reads the harness, not a fixture.

Before this projection existed, `web_dongseop` rendered hand-authored
TypeScript: deleting the entire Python core would not have changed a pixel.
These tests pin the properties that make the console evidence of the harness
rather than a picture of it — the contract the frontend validates is enforced
here on the producing side, the numbers trace to packet records, and a
hypothesis that cannot advance cannot produce molecules.
"""
import json

import pytest

from h2l.server import configure_live_run_manager, route
from h2l.workspace import run_snapshot

GATED_STAGE_IDS = {"seed", "generate", "activity", "admet", "synthesis"}


def _get(path: str):
    status, _, body = route("GET", path)
    return status, json.loads(body)


@pytest.fixture(autouse=True)
def live_manager(monkeypatch):
    """Each test gets isolated volatile state and a deterministic offline Agent."""
    monkeypatch.setenv("H2L_LLM_ENABLED", "0")
    manager = configure_live_run_manager(step_interval_ms=0)
    yield manager
    manager.clear()


@pytest.fixture
def snapshots(live_manager) -> dict:
    _, payload = _get("/api/workspace/runs")
    out = {}
    for summary in payload["runs"]:
        if not summary["id"].startswith("RUN-"):
            continue
        _, snapshot = _get(f"/api/workspace/runs/{summary['id']}")
        out[snapshot["targets"][0]["symbol"]] = snapshot
    return out


def _create_and_wait(live_manager, scenario: str) -> tuple[dict, dict]:
    status, _, body = route("POST", "/api/workspace/runs", {"scenario": scenario})
    assert status == 202
    initial = json.loads(body)
    final = live_manager.wait(initial["run"]["id"])
    return initial, final


def assert_contract(snapshot: dict) -> None:
    """The invariants `domain/validateSnapshot.ts` enforces, checked at the source.

    A projection that only satisfies these in the browser is a projection that
    can ship a broken console; the producing side is where they belong.
    """
    stage_ids = {stage["id"] for stage in snapshot["stages"]}
    evidence_ids = {item["id"] for item in snapshot["evidence"]}
    artifact_ids = {artifact["id"] for artifact in snapshot["artifacts"]}

    assert len(stage_ids) == len(snapshot["stages"]), "duplicate stage id"
    assert len(artifact_ids) == len(snapshot["artifacts"]), "duplicate artifact id"
    assert [stage["ordinal"] for stage in snapshot["stages"]] == list(range(1, len(snapshot["stages"]) + 1))
    assert all(event["stageId"] in stage_ids for event in snapshot["events"])
    assert all(failure["stageId"] in stage_ids for failure in snapshot["failures"])
    for stage in snapshot["stages"]:
        assert set(stage["inputArtifactIds"]) <= artifact_ids
        assert set(stage["outputArtifactIds"]) <= artifact_ids
    for target in snapshot["targets"]:
        assert sum(factor["impact"] for factor in target["scoreFactors"]) == target["scoreAfter"]
        assert set(target["evidenceIds"]) <= evidence_ids
        for factor in target["scoreFactors"]:
            assert set(factor["evidenceIds"]) <= evidence_ids


# ---- the route ---------------------------------------------------------
def test_runs_list_covers_every_current_hypothesis():
    _, payload = _get("/api/workspace/runs")
    _, hypotheses = _get("/api/hypotheses")
    assert len(payload["runs"]) == len(hypotheses["hypotheses"]) == 2


def test_blocked_runs_are_listed_before_advancing_ones():
    """A stopped hypothesis is what the console exists to surface."""
    _, payload = _get("/api/workspace/runs")
    assert payload["runs"][0]["headline"].startswith("진행 거절")


def test_unknown_run_is_a_404():
    status, payload = _get("/api/workspace/runs/RUN-NOPE")
    assert status == 404
    assert payload["error"] == "not_found"


def test_creating_a_run_is_observable_but_does_not_change_the_registry(live_manager):
    """POST starts volatile work while the approved scientific state stays fixed.

    The browser may reconnect to this process-local progress record, but a server
    restart removes it and the scientific registry is never mutated.
    """
    _, registry_before = _get("/api/registry")
    initial, snapshot = _create_and_wait(live_manager, "failed-trial")
    _, registry_after = _get("/api/registry")
    _, listed = _get("/api/workspace/runs")

    assert initial["run"]["status"] == "queued"
    assert initial["targets"] == []
    assert initial["events"] == []
    assert snapshot["run"]["id"].startswith("LIVE-SANDBOX-")
    assert snapshot["run"]["status"] == "awaiting_review"
    assert registry_before == registry_after
    assert snapshot["run"]["id"] in {run["id"] for run in listed["runs"]}
    # Unapproved evidence can never open the molecule stage, whatever the verdict.
    assert snapshot["molecules"] == []
    assert "HARNESS-SANDBOX" in {notice["id"] for notice in snapshot["safetyNotices"]}
    assert next(item for item in snapshot["artifacts"] if item["id"] == "agent-trace")["available"] is True
    assert_contract(initial)
    assert_contract(snapshot)


def test_creating_a_run_takes_presets_and_nothing_else():
    """Ad-hoc packets belong on /api/agent/sandbox, not here.

    ``run_snapshot`` renders ``source_ref`` and ``hypothesis_id`` into the console
    and into the downloadable report, and ``validate_packet`` does not type-check
    the fields it reads. So this route accepts only server-authored presets; a
    caller-supplied packet would let unreviewed input wear registry provenance.
    """
    assert route("POST", "/api/workspace/runs", {"scenario": "nope"})[0] == 404
    assert route("POST", "/api/workspace/runs", {"packet": {"hypothesis_id": "IBD:TYK2"}})[0] == 404
    assert route("POST", "/api/workspace/runs", "not-an-object")[0] == 400
    assert route("DELETE", "/api/workspace/runs")[0] == 405


def test_a_sandbox_run_never_wears_registry_provenance(live_manager):
    """The projection's default strings assert approved-snapshot origin. A run
    computed from an unapproved packet must not inherit them — including in the
    report artifact, which leaves the console on its own."""
    _, snapshot = _create_and_wait(live_manager, "in-indication-support")
    assert snapshot["run"]["id"].startswith("LIVE-SANDBOX-")
    assert "승인된 스냅샷" not in snapshot["stages"][0]["summary"]
    # Agent actions are computed; the evidence packet they inspect remains synthetic.
    assert snapshot["stages"][0]["toolCall"]["classification"] == "computed"
    assert {item["classification"] for item in snapshot["evidence"]} == {"synthetic"}

    packet_artifact = next(a for a in snapshot["artifacts"] if a["id"] == "evidence-packet")
    assert packet_artifact["classification"] == "synthetic"
    report = next(a for a in snapshot["artifacts"] if a["id"] == "decision-report")["content"]
    assert "Provenance: SANDBOX" in report
    assert "Run: LIVE-SANDBOX-" in report


def test_approved_runs_keep_their_provenance():
    """The sandbox flag must not leak into the registry-backed projection."""
    snapshot = json.loads(route("GET", "/api/workspace/runs/RUN-IBD-TYK2-f7fde634")[2])
    assert snapshot["stages"][0]["summary"].startswith("승인된 스냅샷")
    assert snapshot["stages"][0]["toolCall"]["classification"] == "source_snapshot"
    assert {item["classification"] for item in snapshot["evidence"]} == {"source_snapshot"}
    report = next(a for a in snapshot["artifacts"] if a["id"] == "decision-report")["content"]
    assert "SANDBOX" not in report


def test_created_runs_have_unique_runtime_ids_and_reproducible_science(live_manager):
    """Two observations need unique ids; their deterministic verdict stays equal."""
    _, first = _create_and_wait(live_manager, "cross-indication")
    _, second = _create_and_wait(live_manager, "cross-indication")
    assert first["run"]["id"] != second["run"]["id"]
    assert first["targets"] == second["targets"]
    assert first["evidence"] == second["evidence"]
    assert first["molecules"] == second["molecules"] == []


def test_every_preset_reaches_the_console_contract(live_manager):
    """Each preset isolates one rule path, so the four must not collapse to one verdict."""
    _, catalog = _get("/api/scenarios")
    verdicts = {}
    for preset in catalog["scenarios"]:
        initial, snapshot = _create_and_wait(live_manager, preset["id"])
        assert initial["run"]["status"] == "queued", preset["id"]
        assert_contract(snapshot)
        verdicts[preset["id"]] = snapshot["targets"][0]["decision"]
    assert verdicts == {
        "in-indication-support": "review",
        "failed-trial": "rejected",
        "cross-indication": "insufficient",
        "context-only": "insufficient",
    }


def test_a_live_run_can_be_cancelled_before_the_first_tool(live_manager):
    live_manager.step_interval_ms = 200
    status, _, body = route("POST", "/api/workspace/runs", {"scenario": "failed-trial"})
    assert status == 202
    run_id = json.loads(body)["run"]["id"]

    cancel_status, _, cancel_body = route("POST", f"/api/workspace/runs/{run_id}/cancel")
    cancelled = json.loads(cancel_body)
    assert cancel_status == 200
    assert cancelled["run"]["status"] == "cancelled"
    assert all(stage["status"] == "cancelled" for stage in cancelled["stages"])
    assert cancelled["events"][-1]["tool"] == "cancel"
    assert live_manager.wait(run_id)["run"]["status"] == "cancelled"


def test_active_live_run_capacity_fails_closed(live_manager):
    live_manager.step_interval_ms = 200
    live_manager.max_runs = 1
    first_status, _, first_body = route("POST", "/api/workspace/runs", {"scenario": "failed-trial"})
    second_status, _, second_body = route("POST", "/api/workspace/runs", {"scenario": "cross-indication"})

    assert first_status == 202
    assert second_status == 429
    assert json.loads(second_body)["error"] == "live_run_capacity"
    route("POST", f"/api/workspace/runs/{json.loads(first_body)['run']['id']}/cancel")


def test_projection_is_byte_reproducible():
    first = route("GET", "/api/workspace/runs/RUN-IBD-TYK2-f7fde634")[2]
    second = route("GET", "/api/workspace/runs/RUN-IBD-TYK2-f7fde634")[2]
    assert first == second


def test_a_pending_snapshot_does_not_reach_the_console():
    """Invariant 1, visible in the UI: unapproved evidence changes nothing.

    The registry seeds a newer TYK2 detection that is still pending. It shows in
    the registry view, but the console must keep rendering the approved version.
    """
    _, registry = _get("/api/registry")
    tyk2 = next(group for group in registry["groups"] if group["hypothesis_id"] == "IBD:TYK2")
    approved = next(v for v in tyk2["versions"] if v["status"] == "current")
    pending = next(v for v in tyk2["versions"] if v["status"] == "pending")
    assert pending["observed_at"] > approved["observed_at"]

    _, snapshot = _get("/api/workspace/runs/RUN-IBD-TYK2-f7fde634")
    assert snapshot["run"]["createdAt"] == approved["observed_at"]
    assert approved["version_id"] in snapshot["stages"][0]["summary"]


def test_reading_the_console_does_not_move_the_decision():
    _, before = _get("/api/decision?hypothesis=IBD:TYK2")
    _get("/api/workspace/runs")
    _get("/api/workspace/runs/RUN-IBD-TYK2-f7fde634")
    _, after = _get("/api/decision?hypothesis=IBD:TYK2")
    assert before == after


# ---- contract ----------------------------------------------------------
def test_every_run_satisfies_the_console_contract(snapshots):
    for snapshot in snapshots.values():
        assert_contract(snapshot)


def test_absence_is_rendered_as_absence(snapshots):
    """The packet has no association score; the projection must not invent one."""
    for snapshot in snapshots.values():
        target = snapshot["targets"][0]
        assert target["association"] is None
        assert target["tractability"] == "Unknown"


# ---- the numbers trace to records --------------------------------------
def test_tyk2_score_reverses_and_every_deduction_names_its_evidence(snapshots):
    target = snapshots["TYK2"]["targets"][0]
    assert (target["scoreBefore"], target["scoreAfter"]) == (100, 0)
    assert target["decision"] == "rejected"

    deductions = {
        factor["evidenceIds"][0]: factor["impact"]
        for factor in target["scoreFactors"]
        if factor["impact"] < 0
    }
    assert deductions == {
        "EV-TYK2-PSO-APPROVAL": -34,   # 적응증 불일치
        "EV-TYK2-UC-PH2-FAIL": -33,    # 임상 반증
        "EV-TYK2-CD-PH2-FAIL": -33,    # 임상 반증
    }


def test_the_critic_leaves_a_genuinely_supported_case_alone(snapshots):
    """The score only moves when there is something to catch."""
    target = snapshots["DEMO-POS"]["targets"][0]
    assert (target["scoreBefore"], target["scoreAfter"]) == (100, 100)
    assert all(factor["impact"] >= 0 for factor in target["scoreFactors"])


def test_cross_indication_approval_is_not_shown_as_support(snapshots):
    polarity = {item["id"]: item["polarity"] for item in snapshots["TYK2"]["evidence"]}
    assert polarity["EV-TYK2-PSO-APPROVAL"] == "neutral"
    assert polarity["EV-TYK2-UC-PH2-FAIL"] == "conflicting"
    assert polarity["EV-TYK2-CD-PH2-FAIL"] == "conflicting"


# ---- the gate ----------------------------------------------------------
def test_no_decision_run_can_produce_molecules(snapshots):
    for snapshot in snapshots.values():
        assert snapshot["molecules"] == []
        blocked = {stage["id"] for stage in snapshot["stages"] if stage["status"] == "blocked"}
        assert GATED_STAGE_IDS <= blocked


def test_advance_still_stops_at_human_approval(snapshots):
    """ADVANCE is not adoption: the state machine parks it at AWAITING_APPROVAL."""
    snapshot = snapshots["DEMO-POS"]
    assert snapshot["targets"][0]["decision"] == "review"
    assert any(failure["id"] == "HARNESS-MOLECULE-GATE" for failure in snapshot["failures"])
    decision_stage = next(stage for stage in snapshot["stages"] if stage["id"] == "decision")
    assert "molecule_eligible=false" in decision_stage["output"]


def test_rejection_records_the_rules_that_stopped_it(snapshots):
    failures = {failure["id"] for failure in snapshots["TYK2"]["failures"]}
    assert failures == {
        "HARNESS-INDICATION_MATCH_REQUIRED",
        "HARNESS-FAILED_TRIAL_BLOCKS_ADVANCE",
        "HARNESS-MOLECULE-GATE",
    }


# ---- artifacts ---------------------------------------------------------
def test_artifacts_carry_the_real_trace_not_a_summary(snapshots):
    artifacts = {item["id"]: item for item in snapshots["TYK2"]["artifacts"]}
    trace = json.loads(artifacts["decision-trace"]["content"])
    assert trace["decision"] == "REJECT"
    assert trace["molecule_eligible"] is False
    packet = json.loads(artifacts["evidence-packet"]["content"])
    assert packet["hypothesis_id"] == "IBD:TYK2"
    assert len(packet["records"]) == 3


def test_report_states_the_non_claim(snapshots):
    report = next(a for a in snapshots["TYK2"]["artifacts"] if a["id"] == "decision-report")["content"]
    assert "No therapeutic efficacy is claimed." in report
    assert "Molecule stages were not run." in report


def test_safety_notices_disclose_the_packet_is_a_fixture(snapshots):
    for snapshot in snapshots.values():
        details = " ".join(notice["detail"] for notice in snapshot["safetyNotices"])
        assert "시드 픽스처" in details


# ---- projection unit ---------------------------------------------------
def test_projection_refuses_to_invent_a_score_without_clinical_records():
    """A packet of context-only records supports nothing, and says so."""
    decision = {
        "run_id": "0" * 16, "hypothesis_id": "IBD:CTX", "decision": "HOLD",
        "state": "HELD", "molecule_eligible": False, "evidence_ids": [], "rule_ids": ["REQUIRED_EVIDENCE_MISSING"],
        "snapshot": {"version_id": "v1", "content_hash": "abc"}, "fallback_used": False, "events": [],
        "packet": {
            "hypothesis_id": "IBD:CTX", "disease_id": "MONDO_0005265", "indication_ids": ["MONDO_0005265"],
            "target": "CTX", "observed_at": "2026-07-16T00:00:00Z",
            "records": [{
                "evidence_id": "EV-CTX-BIND", "kind": "binding", "indication": "inflammatory bowel disease",
                "indication_id": "MONDO_0005265", "outcome": "positive", "stance": "context",
                "source_ref": "fixture://ctx",
            }],
        },
    }
    snapshot = run_snapshot(decision)
    assert_contract(snapshot)
    target = snapshot["targets"][0]
    assert target["scoreAfter"] == 0
    assert target["decision"] == "insufficient"
    # A binding measurement is context, never clinical support.
    assert snapshot["evidence"][0]["polarity"] == "neutral"
