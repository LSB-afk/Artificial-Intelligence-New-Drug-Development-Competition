"""DecisionGate enforces the transition table from the JB-derived design spec.

    EVIDENCE_COLLECTED --challenge-->            CHALLENGED
    CHALLENGED         --REJECT-->               REJECTED
    CHALLENGED         --HOLD-->                 HELD
    CHALLENGED         --ADVANCE-->              AWAITING_APPROVAL
    AWAITING_APPROVAL  --reviewer approval-->    MOLECULE_ELIGIBLE
    HELD / REJECTED    --molecule optimization-->BLOCKED (InvalidTransition)
"""
import pytest

from h2l.state_machine import DecisionGate, InvalidTransition, State


def test_challenge_moves_collected_to_challenged():
    gate = DecisionGate()
    assert gate.challenge(State.EVIDENCE_COLLECTED) is State.CHALLENGED


def test_challenge_from_wrong_state_is_blocked():
    gate = DecisionGate()
    with pytest.raises(InvalidTransition):
        gate.challenge(State.REJECTED)


@pytest.mark.parametrize(
    "decision,expected",
    [
        ("REJECT", State.REJECTED),
        ("HOLD", State.HELD),
        ("ADVANCE", State.AWAITING_APPROVAL),
    ],
)
def test_apply_decision_maps_to_expected_state(decision, expected):
    gate = DecisionGate()
    assert gate.apply_decision(State.CHALLENGED, decision) is expected


def test_advance_does_not_auto_grant_molecule_eligibility():
    gate = DecisionGate()
    state = gate.apply_decision(State.CHALLENGED, "ADVANCE")
    assert state is State.AWAITING_APPROVAL
    assert gate.molecule_eligible(state) is False


def test_reviewer_approval_grants_molecule_eligibility():
    gate = DecisionGate()
    state = gate.approve_progression(State.AWAITING_APPROVAL, actor="domain_reviewer")
    assert state is State.MOLECULE_ELIGIBLE
    assert gate.molecule_eligible(state) is True


def test_cannot_approve_progression_before_advance():
    gate = DecisionGate()
    with pytest.raises(InvalidTransition):
        gate.approve_progression(State.CHALLENGED, actor="domain_reviewer")


@pytest.mark.parametrize("blocked_state", [State.HELD, State.REJECTED])
def test_molecule_optimization_blocked_from_held_or_rejected(blocked_state):
    """GC-009: a rejected/held target cannot enter molecule optimization."""
    gate = DecisionGate()
    with pytest.raises(InvalidTransition) as excinfo:
        gate.request_molecule_optimization(blocked_state)
    assert "invalid_transition" in str(excinfo.value)


def test_molecule_optimization_allowed_only_when_eligible():
    gate = DecisionGate()
    assert gate.request_molecule_optimization(State.MOLECULE_ELIGIBLE) is True
