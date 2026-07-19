"""Deterministic decision-state machine.

Separates a scientific judgment (``ADVANCE`` / ``HOLD`` / ``REJECT``) from the
downstream molecule step with an explicit human-approval gate. A single harness
run can reach ``AWAITING_APPROVAL`` at most; it never auto-advances to molecule
eligibility. ``HELD`` and ``REJECTED`` targets are hard-blocked from molecule
optimization (evals GC-009).
"""
from __future__ import annotations

from enum import Enum

DECISIONS = ("ADVANCE", "HOLD", "REJECT")


class State(str, Enum):
    EVIDENCE_COLLECTED = "EVIDENCE_COLLECTED"
    CHALLENGED = "CHALLENGED"
    REJECTED = "REJECTED"
    HELD = "HELD"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    MOLECULE_ELIGIBLE = "MOLECULE_ELIGIBLE"


class InvalidTransition(Exception):
    """Raised when a requested transition is not permitted."""


_DECISION_TARGET = {
    "REJECT": State.REJECTED,
    "HOLD": State.HELD,
    "ADVANCE": State.AWAITING_APPROVAL,
}


class DecisionGate:
    def challenge(self, state: State) -> State:
        if state is not State.EVIDENCE_COLLECTED:
            raise InvalidTransition(f"invalid_transition: cannot challenge from {state.value}")
        return State.CHALLENGED

    def apply_decision(self, state: State, decision: str) -> State:
        if state is not State.CHALLENGED:
            raise InvalidTransition(f"invalid_transition: cannot decide from {state.value}")
        if decision not in _DECISION_TARGET:
            raise InvalidTransition(f"invalid_transition: unknown decision {decision!r}")
        return _DECISION_TARGET[decision]

    def approve_progression(self, state: State, *, actor: str) -> State:
        if state is not State.AWAITING_APPROVAL:
            raise InvalidTransition(
                f"invalid_transition: molecule approval requires AWAITING_APPROVAL, got {state.value}"
            )
        return State.MOLECULE_ELIGIBLE

    def request_molecule_optimization(self, state: State) -> bool:
        if state is not State.MOLECULE_ELIGIBLE:
            raise InvalidTransition(
                f"invalid_transition: molecule optimization blocked from {state.value}; "
                "new_evidence_and_approval_required"
            )
        return True

    def molecule_eligible(self, state: State) -> bool:
        return state is State.MOLECULE_ELIGIBLE
