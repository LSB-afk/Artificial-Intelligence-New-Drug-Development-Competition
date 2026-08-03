"""Bounded action-selection loop: the model chooses, the harness executes.

`llm.py` lets a local model rephrase a decision that was already made. This
module is the other half of the project rule — "the LLM selects actions and
writes bounded explanations" — and it is the part that makes the system an
agent rather than a report generator.

The split of authority is the whole design:

- The model may pick **which** action runs next, from a fixed allow-list, with
  arguments that must name entities the registry actually holds. It may not
  produce a result, a number, an evidence id, or a verdict.
- The harness **executes** the chosen action with deterministic code and writes
  the observation. Every fact in the trace comes from that execution.
- The gate is enforced at execution, not at selection. The agent is free to
  propose molecule optimization on a rejected target; the harness refuses and
  records the refusal. A plan is allowed to be wrong — a *run* is not.

Failure modes are absorbed, not raised. An unreachable model, unparseable
output, an invented action name, or an invented hypothesis id all fall through
to a deterministic policy for that step, and the substitution is recorded so a
reviewer can see how much of the run the model actually drove. With the model
off the entire run is the policy, which makes it byte-reproducible.

Nothing here stores prompt text or hidden reasoning: the audit record carries a
prompt hash, the chosen action, and the validation outcome.
"""
from __future__ import annotations

import json
import time

from h2l.llm import LLMConfig, explain_decision, generate, prompt_hash

ACTION_EVENT = "ActionSelected"
DEFAULT_MAX_STEPS = 7
# Action selection emits a short JSON object; a large budget only invites prose.
SELECTION_NUM_PREDICT = 120

def _first_json_object(raw: str) -> str:
    """Slice the first complete ``{...}`` out of a completion.

    Brace matching has to be balanced and string-aware: every useful proposal
    nests ``args``, so a lazy regex would cut at the inner brace and turn valid
    output into a parse failure.
    """
    start = raw.find("{")
    if start < 0:
        raise ActionRejected("JSON 객체를 찾을 수 없습니다.")
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(raw)):
        char = raw[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return raw[start: index + 1]
    raise ActionRejected("JSON 객체가 닫히지 않았습니다.")

# The complete set of things the agent is allowed to do, with the arguments each
# one requires. Anything outside this table is not an action the agent can take.
ACTIONS: dict[str, dict] = {
    "list_hypotheses": {
        "args": (),
        "purpose": "등록된 가설과 타깃 목록을 확인한다.",
    },
    "inspect_evidence": {
        "args": ("hypothesis_id",),
        "purpose": "승인된 근거 스냅샷의 레코드 구성을 확인한다.",
    },
    "critique": {
        "args": ("hypothesis_id",),
        "purpose": "적응증 일치와 반증 규칙으로 가설을 비평하고 판정을 받는다.",
    },
    "check_molecule_gate": {
        "args": ("hypothesis_id",),
        "purpose": "분자 최적화 단계가 열려 있는지 게이트 상태를 확인한다.",
    },
    "optimize_molecules": {
        "args": ("hypothesis_id",),
        "purpose": "분자 최적화를 요청한다. 게이트가 닫혀 있으면 하네스가 거부한다.",
    },
    "whatif_missing_evidence": {
        "args": ("hypothesis_id",),
        "purpose": "판정을 바꾸려면 어떤 근거가 필요한지 규칙에서 역산한다.",
    },
    "finish": {
        "args": (),
        "purpose": "목표에 답할 수 있으면 종료한다.",
    },
}


class ActionRejected(Exception):
    """The proposed action is not one the agent may take, or is malformed."""


# ---- tool surface ------------------------------------------------------
class HarnessTools:
    """Deterministic execution of the allow-listed actions.

    Takes the two callables the decision core already exposes so the loop can
    be exercised without an HTTP server.
    """

    def __init__(self, hypotheses, decide):
        self._hypotheses = hypotheses
        self._decide = decide

    def known_ids(self) -> list[str]:
        return [item["hypothesis_id"] for item in self._hypotheses()]

    def decision(self, hypothesis_id: str) -> dict:
        """The full decision trace, for callers that summarise a finished run."""
        return self._decide(hypothesis_id)

    # -- actions --
    def list_hypotheses(self) -> dict:
        items = self._hypotheses()
        return _observation(
            f"등록된 가설 {len(items)}건: " + ", ".join(item["hypothesis_id"] for item in items),
            {"hypotheses": items},
        )

    def inspect_evidence(self, hypothesis_id: str) -> dict:
        packet = self._decide(hypothesis_id).get("packet") or {}
        records = packet.get("records") or []
        indication_ids = set(packet.get("indication_ids") or [])
        in_indication = [r for r in records if r.get("indication_id") in indication_ids]
        return _observation(
            f"레코드 {len(records)}건 중 {len(in_indication)}건이 이 적응증에 해당합니다.",
            {
                "record_count": len(records),
                "in_indication_count": len(in_indication),
                "records": [
                    {
                        "evidence_id": r.get("evidence_id"),
                        "kind": r.get("kind"),
                        "indication": r.get("indication"),
                        "outcome": r.get("outcome"),
                        "in_indication": r.get("indication_id") in indication_ids,
                    }
                    for r in records
                ],
            },
        )

    def critique(self, hypothesis_id: str) -> dict:
        decision = self._decide(hypothesis_id)
        return _observation(
            f"판정 {decision['decision']} · 상태 {decision['state']} · 규칙 "
            + (", ".join(decision.get("rule_ids") or []) or "없음"),
            {
                "decision": decision["decision"],
                "state": decision["state"],
                "rule_ids": list(decision.get("rule_ids") or []),
                "evidence_ids": list(decision.get("evidence_ids") or []),
            },
        )

    def check_molecule_gate(self, hypothesis_id: str) -> dict:
        decision = self._decide(hypothesis_id)
        eligible = bool(decision["molecule_eligible"])
        return _observation(
            f"분자 게이트 {'열림' if eligible else '닫힘'} · 상태 {decision['state']}",
            {"molecule_eligible": eligible, "state": decision["state"], "decision": decision["decision"]},
        )

    def optimize_molecules(self, hypothesis_id: str) -> dict:
        """Refuses unless the gate is open. This is the fail-closed path."""
        decision = self._decide(hypothesis_id)
        if not decision["molecule_eligible"]:
            reason = (
                f"상태가 {decision['state']}이므로 분자 최적화를 실행하지 않았습니다. "
                f"적용 규칙: {', '.join(decision.get('rule_ids') or []) or '결정 게이트'}."
            )
            return _observation(reason, {"state": decision["state"], "decision": decision["decision"]}, refused=True)
        # An open gate still means a human approved the progression; the loop
        # does not grant that approval, so there is nothing to run unattended.
        return _observation(
            "분자 게이트는 열려 있으나 실행에는 사람 승인 기록이 필요합니다.",
            {"state": decision["state"], "requires_human_approval": True},
            refused=True,
        )

    def whatif_missing_evidence(self, hypothesis_id: str) -> dict:
        """What would have to change for the verdict to move. Computed, not guessed."""
        decision = self._decide(hypothesis_id)
        packet = decision.get("packet") or {}
        records = packet.get("records") or []
        indication_ids = set(packet.get("indication_ids") or [])
        rules = set(decision.get("rule_ids") or [])

        requirements = []
        blocking = [
            r["evidence_id"] for r in records
            if r.get("indication_id") in indication_ids and r.get("outcome") in {"failed", "negative"}
        ]
        cross = [r["evidence_id"] for r in records if r.get("indication_id") not in indication_ids]
        if "FAILED_TRIAL_BLOCKS_ADVANCE" in rules:
            requirements.append(f"이 적응증의 실패 임상 {len(blocking)}건({', '.join(blocking)})이 철회되거나 반박되어야 합니다.")
        if "INDICATION_MATCH_REQUIRED" in rules:
            requirements.append(f"다른 적응증 레코드 {len(cross)}건은 이 적응증 레코드로 대체되어야 합니다.")
        if "REQUIRED_EVIDENCE_MISSING" in rules:
            requirements.append("이 적응증에 일치하는 positive 레코드가 최소 1건 필요합니다.")
        if not requirements:
            requirements.append("현재 규칙 기준으로 추가 요건이 없습니다.")

        return _observation(
            " ".join(requirements),
            {
                "requirements": requirements,
                "blocking_evidence_ids": blocking,
                "cross_indication_evidence_ids": cross,
                "still_requires_human_approval": True,
            },
        )


def _observation(summary: str, data: dict, *, refused: bool = False) -> dict:
    return {"summary": summary, "data": data, "refused": refused}


# ---- selection ---------------------------------------------------------
def action_catalog() -> list[dict]:
    return [
        {"action": name, "args": list(spec["args"]), "purpose": spec["purpose"]}
        for name, spec in ACTIONS.items()
    ]


def _signature(name: str, args: dict) -> str:
    return f"{name}:{json.dumps(args, sort_keys=True, ensure_ascii=False)}"


def validate_action(proposal: dict, known_ids: list[str], steps: list[dict] | None = None) -> tuple[str, dict]:
    """Check a proposed action against the allow-list. Raises ``ActionRejected``.

    Two checks carry the weight. The hypothesis check refuses a target the
    registry does not hold, so an invented identifier never reaches a tool that
    would have to interpret it. The repeat check refuses an action whose exact
    result is already in the transcript: without it a model that cannot tell it
    has finished will re-run the same observation until the budget is gone,
    which is the failure mode `llama3.1:8b` shows on this task.
    """
    if not isinstance(proposal, dict):
        raise ActionRejected("제안이 객체가 아닙니다.")
    name = proposal.get("action")
    if name not in ACTIONS:
        raise ActionRejected(f"허용되지 않은 행동입니다: {name!r}")

    raw_args = proposal.get("args") or {}
    if not isinstance(raw_args, dict):
        raise ActionRejected("args가 객체가 아닙니다.")

    required = ACTIONS[name]["args"]
    args = {}
    for key in required:
        value = raw_args.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ActionRejected(f"필수 인자 누락: {key}")
        args[key] = value.strip()

    if "hypothesis_id" in args and args["hypothesis_id"] not in known_ids:
        raise ActionRejected(f"레지스트리에 없는 가설입니다: {args['hypothesis_id']}")

    if name != "finish" and _signature(name, args) in {_signature(s["action"], s["args"]) for s in steps or []}:
        raise ActionRejected(f"이미 관측한 행동입니다: {name}")
    return name, args


def parse_proposal(raw: str) -> dict:
    """Pull the first JSON object out of a completion, tolerating stray prose."""
    try:
        return json.loads(_first_json_object(raw or ""))
    except json.JSONDecodeError as error:
        raise ActionRejected(f"JSON 파싱 실패: {error.msg}") from error


def build_selection_prompt(goal: str, steps: list[dict], remaining: int) -> str:
    history = [
        {"action": step["action"], "args": step["args"], "observation": step["observation"]["summary"]}
        for step in steps
    ]
    return (
        "당신은 신약개발 의사결정 하네스의 행동 선택기입니다.\n"
        "당신은 결과를 만들지 않습니다. 다음에 실행할 행동 하나만 고르면 하네스가 실행합니다.\n\n"
        f"목표: 가설 '{goal}'을 판정하고, 분자 단계로 갈 수 있는지 확인한다.\n"
        f"남은 단계: {remaining}\n\n"
        f"선택 가능한 행동:\n{json.dumps(action_catalog(), ensure_ascii=False, indent=2)}\n\n"
        f"지금까지의 관측:\n{json.dumps(history, ensure_ascii=False, indent=2)}\n\n"
        "규칙:\n"
        "1. 위 목록에 있는 action 이름만 쓰세요.\n"
        "2. hypothesis_id는 관측에 등장한 값만 쓰세요. 새로 만들지 마세요.\n"
        "3. 이미 관측한 행동은 다시 고르지 마세요. 같은 행동을 반복하면 거부됩니다.\n"
        "4. 목표에 답할 수 있으면 즉시 finish를 고르세요.\n"
        "5. 설명 없이 JSON 객체 하나만 출력하세요.\n\n"
        '형식: {"action": "...", "args": {"hypothesis_id": "..."}}\n\n'
        "선택:"
    )


def policy_action(goal: str, steps: list[dict]) -> tuple[str, dict]:
    """The deterministic plan, used as fallback and as the model-off baseline.

    It proposes molecule optimization even on a target that cannot have it. That
    is deliberate: proposing the pipeline's goal is a planner's job, and refusing
    it is the gate's job. Putting the check in the planner would hide the gate.
    """
    plan: list[tuple[str, dict]] = [
        ("list_hypotheses", {}),
        ("inspect_evidence", {"hypothesis_id": goal}),
        ("critique", {"hypothesis_id": goal}),
        ("check_molecule_gate", {"hypothesis_id": goal}),
        ("optimize_molecules", {"hypothesis_id": goal}),
        ("whatif_missing_evidence", {"hypothesis_id": goal}),
    ]
    done = {(step["action"], json.dumps(step["args"], sort_keys=True)) for step in steps}
    for name, args in plan:
        if (name, json.dumps(args, sort_keys=True)) not in done:
            return name, args
    return "finish", {}


def select_action(goal, steps, tools, config, *, remaining, generator) -> dict:
    """Choose the next action. Returns the choice plus how it was reached."""
    if not config.enabled:
        name, args = policy_action(goal, steps)
        return {"action": name, "args": args, "selected_by": "policy",
                "reason": "local model disabled", "audit": None}

    prompt = build_selection_prompt(goal, steps, remaining)
    digest = prompt_hash(prompt)
    started = time.monotonic()
    try:
        raw = generator(prompt, config, num_predict=SELECTION_NUM_PREDICT)
        name, args = validate_action(parse_proposal(raw), tools.known_ids(), steps)
        outcome, reason = "accepted", None
    except ActionRejected as error:
        name, args = policy_action(goal, steps)
        outcome, reason = "rejected", str(error)
    except Exception as error:  # transport, timeout, decode - all recoverable
        name, args = policy_action(goal, steps)
        outcome, reason = "unavailable", f"{type(error).__name__}: {error}"

    return {
        "action": name,
        "args": args,
        "selected_by": "model" if outcome == "accepted" else "policy",
        "reason": reason,
        "audit": {
            "event_type": ACTION_EVENT,
            "model": config.model,
            "outcome": outcome,
            "prompt_hash": digest,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "action": name,
        },
    }


# ---- loop --------------------------------------------------------------
def run_agent(
    goal: str,
    tools: HarnessTools,
    config: LLMConfig | None = None,
    *,
    max_steps: int = DEFAULT_MAX_STEPS,
    generator=generate,
    observer=None,
) -> dict:
    """Run the loop until the agent finishes or the step budget is spent.

    ``observer`` receives bounded lifecycle events for serving-plane progress
    displays. It sees action names, validated arguments, selection provenance,
    deterministic observations, and elapsed milliseconds, never prompts or
    hidden reasoning. The core does not catch observer exceptions: a caller may
    use one to cancel an in-flight run before the next tool executes.
    """
    settings = config or LLMConfig.from_env()
    known = tools.known_ids()
    if goal not in known:
        raise ValueError(f"unknown hypothesis: {goal}")

    steps: list[dict] = []
    audits: list[dict] = []
    finished = False

    while len(steps) < max_steps:
        remaining = max_steps - len(steps)
        choice = select_action(goal, steps, tools, settings, remaining=remaining, generator=generator)
        if choice["audit"]:
            audits.append(choice["audit"])
        if choice["action"] == "finish":
            finished = True
            break

        step_number = len(steps) + 1
        if observer:
            observer(
                {
                    "type": "action_started",
                    "step": step_number,
                    "action": choice["action"],
                    "args": choice["args"],
                    "selected_by": choice["selected_by"],
                    "selection_note": choice["reason"],
                }
            )
        handler = getattr(tools, choice["action"])
        action_started = time.monotonic()
        observation = handler(**choice["args"])
        duration_ms = max(0, int((time.monotonic() - action_started) * 1000))
        step = {
            "step": step_number,
            "action": choice["action"],
            "args": choice["args"],
            "selected_by": choice["selected_by"],
            "selection_note": choice["reason"],
            "observation": observation,
            "refused": observation["refused"],
        }
        steps.append(step)
        if observer:
            observer({"type": "action_completed", **step, "duration_ms": duration_ms})

    if observer:
        observer({"type": "finalizing", "step_count": len(steps)})
    decision = tools.decision(goal)
    explanation = explain_decision(decision, settings)
    model_steps = sum(1 for step in steps if step["selected_by"] == "model")
    result = {
        "goal": goal,
        "model_enabled": settings.enabled,
        "model": settings.model if settings.enabled else None,
        "max_steps": max_steps,
        "steps": steps,
        "step_count": len(steps),
        "model_selected_steps": model_steps,
        "policy_selected_steps": len(steps) - model_steps,
        "refused_steps": [step["step"] for step in steps if step["refused"]],
        "finished": finished,
        "stopped_reason": "finish" if finished else "step_budget_exhausted",
        "decision": {
            "decision": decision["decision"],
            "state": decision["state"],
            "molecule_eligible": decision["molecule_eligible"],
            "rule_ids": list(decision.get("rule_ids") or []),
        },
        "explanation": {
            "text": explanation["text"],
            "source": explanation["source"],
            "model": explanation["model"],
            "violations": explanation["violations"],
        },
        "audit": audits + [explanation["audit"]],
    }
    if observer:
        observer({"type": "completed", "step_count": len(steps)})
    return result
