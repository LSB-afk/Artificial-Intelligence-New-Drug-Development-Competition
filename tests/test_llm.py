"""Local-model explanation layer: fact-bounded output, template fallback.

The model is allowed to rephrase decisions, never to widen them. These tests
pin the two properties that make that safe: any output that introduces facts,
flips the decision, or leaks reasoning is replaced by the template, and a path
pinned offline stays offline no matter what the environment says.

The model runs by default on the serving plane, so these tests always pass an
explicit config — a suite whose result depends on whether Ollama happens to be
installed is not a regression test.
"""
import json

import pytest

from h2l.llm import (
    MAX_ATTEMPTS,
    MODEL_CALL_EVENT,
    VIOLATION_GUIDANCE,
    LLMConfig,
    build_prompt,
    build_repair_prompt,
    explain_decision,
    explanation_facts,
    guard,
    render_template,
    strip_reasoning,
)

REJECT_DECISION = {
    "hypothesis_id": "IBD:TYK2",
    "decision": "REJECT",
    "state": "REJECTED",
    "molecule_eligible": False,
    "evidence_ids": ["EV-TYK2-UC-PH2-FAIL", "EV-TYK2-CD-PH2-FAIL", "EV-TYK2-PSO-APPROVAL"],
    "rule_ids": ["INDICATION_MATCH_REQUIRED", "FAILED_TRIAL_BLOCKS_ADVANCE"],
    "snapshot": {"version_id": "IBD:TYK2@7e070658efe3"},
    "packet": {
        "target": "TYK2",
        "reference_drug": "deucravacitinib",
        "observed_at": "2026-07-16T00:00:00Z",
        "records": [
            {
                "evidence_id": "EV-TYK2-UC-PH2-FAIL",
                "kind": "trial",
                "indication": "ulcerative colitis",
                "outcome": "failed",
                "stance": "contradict",
                "source_ref": "fixture://tyk2-uc-phase2-failed",
            },
            {
                "evidence_id": "EV-TYK2-CD-PH2-FAIL",
                "kind": "trial",
                "indication": "Crohn disease",
                "outcome": "failed",
                "stance": "contradict",
                "source_ref": "fixture://tyk2-cd-phase2-failed",
            },
            {
                "evidence_id": "EV-TYK2-PSO-APPROVAL",
                "kind": "approval",
                "indication": "plaque psoriasis",
                "outcome": "positive",
                "stance": "context",
                "source_ref": "fixture://deucravacitinib-psoriasis-approval",
            },
        ],
    },
}


@pytest.fixture
def facts() -> dict:
    return explanation_facts(REJECT_DECISION)


def _boom(prompt, config):
    raise AssertionError("the model must not be called")


# ---- offline invariant -------------------------------------------------
def test_offline_config_never_calls_the_model():
    result = explain_decision(REJECT_DECISION, LLMConfig.offline(), generator=_boom)
    assert result["source"] == "template"
    assert result["audit"]["outcome"] == "disabled"
    assert result["audit"]["prompt_hash"] is None


def test_offline_config_cannot_be_re_enabled_by_the_environment():
    """A pinned-off path stays off even where the serving default is on."""
    assert LLMConfig.offline().enabled is False
    assert LLMConfig.offline(model="llama3.1:8b").model == "llama3.1:8b"
    assert LLMConfig.offline(model="llama3.1:8b").enabled is False


def test_env_config_is_on_unless_explicitly_disabled():
    assert LLMConfig.from_env({}).enabled is True
    assert LLMConfig.from_env({"H2L_LLM_ENABLED": "1"}).enabled is True
    assert LLMConfig.from_env({"H2L_LLM_ENABLED": "true"}).enabled is True
    assert LLMConfig.from_env({"H2L_LLM_ENABLED": "0"}).enabled is False
    assert LLMConfig.from_env({"H2L_LLM_ENABLED": "off"}).enabled is False


def test_template_is_deterministic():
    first = explain_decision(REJECT_DECISION, LLMConfig.offline(), generator=_boom)["text"]
    second = explain_decision(REJECT_DECISION, LLMConfig.offline(), generator=_boom)["text"]
    assert first == second


def test_unreachable_runtime_falls_back_without_raising(facts):
    def unreachable(prompt, config):
        raise OSError("connection refused")

    result = explain_decision(REJECT_DECISION, LLMConfig(enabled=True), generator=unreachable)
    assert result["source"] == "template"
    assert result["audit"]["outcome"] == "unavailable"
    assert result["text"] == render_template(facts)


# ---- fact set ----------------------------------------------------------
def test_facts_carry_only_computed_decision_content(facts):
    assert facts["decision"] == "REJECT"
    assert facts["molecule_eligible"] is False
    assert facts["evidence_ids"] == REJECT_DECISION["evidence_ids"]


def test_counts_publish_every_tally_the_harness_can_compute(facts):
    """A count the model needs but cannot see is a count it will invent.

    Every number here is derived from the records, so publishing them widens
    what the model may say without widening what is true.
    """
    assert facts["counts"] == {
        "evidence": 3,
        "contradicting": 2,
        "supporting": 0,
        "in_indication": 0,
        "cross_indication": 3,
        "by_outcome": {"failed": 2, "positive": 1},
        "by_kind": {"trial": 2, "approval": 1},
    }


def test_prompt_contains_the_fact_set_and_no_free_text(facts):
    prompt = build_prompt(facts)
    assert json.dumps(facts, ensure_ascii=False, indent=2, sort_keys=True) in prompt
    assert "생각 과정은 출력하지 마세요" in prompt


def test_template_passes_its_own_guardrail(facts):
    assert guard(render_template(facts), facts) == []


# ---- guardrail ---------------------------------------------------------
def test_invented_numbers_are_rejected(facts):
    violations = guard("TYK2 임상에서 87% 반응률이 확인되었습니다.", facts)
    assert any(item.startswith("unsupported_number") for item in violations)


def test_invented_evidence_id_is_rejected(facts):
    violations = guard("근거 EV-TYK2-IBD-WIN 에 따르면 결과가 달라집니다.", facts)
    assert any(item.startswith("unsupported_evidence_id") for item in violations)


def test_fabricated_citation_is_rejected(facts):
    assert "fabricated_citation" in guard("NCT01234567 연구를 참고하십시오.", facts)


def test_therapeutic_claim_on_a_rejection_is_blocked(facts):
    violations = guard("TYK2는 IBD에서 치료 효과가 있으므로 진행 가능합니다.", facts)
    assert any(item.startswith("therapeutic_claim") for item in violations)


def _claims(text: str, facts: dict) -> list[str]:
    """Only the therapeutic-claim verdict, so unrelated rules cannot mask it."""
    return [item for item in guard(text, facts) if item.startswith("therapeutic_claim")]


def test_rule_id_containing_advance_is_not_read_as_a_claim(facts):
    assert _claims("적용 규칙은 FAILED_TRIAL_BLOCKS_ADVANCE 입니다.", facts) == []


def test_negated_disclaimer_is_not_a_claim(facts):
    assert _claims("이 설명은 치료 효과를 주장하지 않습니다.", facts) == []


def test_quoting_the_computed_decision_is_not_a_claim():
    """Reporting an ADVANCE the harness computed is not asserting a therapy."""
    advance = {**REJECT_DECISION, "decision": "ADVANCE", "state": "AWAITING_APPROVAL"}
    assert _claims("결정은 ADVANCE이며 승인 대기 상태입니다.", explanation_facts(advance)) == []


def test_advance_written_over_a_rejection_is_still_a_claim(facts):
    """The exemption is for the decision this run produced, not the word."""
    assert _claims("이 가설은 ADVANCE 상태로 판정되었습니다.", facts) != []


def test_instruction_transcript_is_rejected(facts):
    """A draft that recites the guard's own feedback is not an explanation.

    It also satisfies the verbatim-indication rule with the recitation, so
    without this check a retry can pass while explaining nothing.
    """
    recited = "직전 답변이 거절되어 다시 쓰겠습니다. Crohn disease, ulcerative colitis, plaque psoriasis."
    assert "process_leak" in guard(recited, facts)


def test_compound_of_fact_set_words_is_not_a_fabricated_term(facts):
    """``cross_indication`` in the facts licenses "cross-indication" in prose."""
    text = (
        "Crohn disease, ulcerative colitis, plaque psoriasis 근거는 "
        "cross-indication 관계이므로 판정이 유지됩니다."
    )
    assert [item for item in guard(text, facts) if item.startswith("unsupported_term")] == []


def test_harness_vocabulary_may_be_written_in_its_noun_form(facts):
    """The fact set stores ``stance: contradict``; prose says "contradiction".

    Measured on the four preset packets: this derivation was the only thing
    standing between a real model sentence and the template on the rejection
    scenario, and it names no scientific entity.
    """
    text = (
        "Crohn disease, ulcerative colitis, plaque psoriasis 근거 중 "
        "contradiction 항목이 판정을 결정했습니다."
    )
    assert [item for item in guard(text, facts) if item.startswith("unsupported_term")] == []


def test_allowing_harness_nouns_does_not_admit_a_fabricated_entity(facts):
    """The check still has to catch the thing it was built for.

    Widening ``ALLOWED_LATIN`` is only safe while an invented disease, drug, or
    target is still refused, so that property is pinned next to the widening.
    """
    text = (
        "Crohn disease, ulcerative colitis, plaque psoriasis 근거에 더해 "
        "sarcoidosis 임상과 fictionib 계열이 확인되었습니다."
    )
    violations = [item for item in guard(text, facts) if item.startswith("unsupported_term")]
    assert violations, "a fabricated indication and drug must still be caught"
    assert "sarcoidosis" in violations[0] and "fictionib" in violations[0]


def test_indication_translated_instead_of_quoted_is_rejected(facts):
    """The check that actually holds against a fabricated disease name."""
    violations = guard("크론병과 궤양성 대장염에서 임상이 실패했습니다.", facts)
    assert any(item.startswith("indication_not_quoted") for item in violations)


def test_reasoning_leak_is_rejected(facts):
    assert "reasoning_leak" in guard("<think>먼저 근거를 세어보자</think> 결론입니다.", facts)


def test_strip_reasoning_removes_scratchpad_blocks():
    assert strip_reasoning("<think>숨은 추론</think>\n결론만 남습니다.") == "결론만 남습니다."


def test_non_korean_output_is_rejected(facts):
    assert "language_mismatch" in guard("The target was rejected for this indication.", facts)


def test_overlong_output_is_rejected(facts):
    assert "too_long" in guard("가" * 900, facts)


def test_empty_output_is_rejected(facts):
    assert guard("   ", facts) == ["empty_output"]


# ---- model path --------------------------------------------------------
CLEAN_OUTPUT = (
    "TYK2 가설은 Crohn disease, ulcerative colitis, plaque psoriasis 범위에서 "
    "진행이 거절되었습니다. 반증 근거가 우세합니다."
)


def test_clean_model_output_is_used_and_audited(facts):
    clean = CLEAN_OUTPUT

    result = explain_decision(REJECT_DECISION, LLMConfig(enabled=True), generator=lambda p, c: clean)
    assert result["source"] == "model"
    assert result["text"] == clean
    assert result["audit"]["event_type"] == MODEL_CALL_EVENT
    assert result["audit"]["outcome"] == "accepted"
    assert result["violations"] == []


def test_violating_model_output_is_replaced_by_the_template(facts):
    hallucination = "TYK2는 치료 효과가 입증되어 진행 가능하며 NCT01234567에서 87% 반응률을 보였습니다."

    result = explain_decision(REJECT_DECISION, LLMConfig(enabled=True), generator=lambda p, c: hallucination)
    assert result["source"] == "template"
    assert result["text"] == render_template(facts)
    assert result["audit"]["outcome"] == "rejected"
    assert len(result["violations"]) >= 2


def test_audit_records_the_prompt_hash_but_never_the_prompt():
    result = explain_decision(REJECT_DECISION, LLMConfig(enabled=True), generator=lambda p, c: "판정은 거절입니다.")
    audit = result["audit"]
    assert len(audit["prompt_hash"]) == 64
    assert "prompt" not in audit
    assert "TYK2" not in json.dumps(audit)


def test_model_scratchpad_is_stripped_before_the_guardrail_runs():
    raw = f"<think>숨은 추론 과정</think>{CLEAN_OUTPUT}"

    result = explain_decision(REJECT_DECISION, LLMConfig(enabled=True), generator=lambda p, c: raw)
    assert result["source"] == "model"
    assert "숨은 추론" not in result["text"]
    assert "<think>" not in result["text"]


# ---- bounded retry -----------------------------------------------------
def test_a_refused_draft_buys_one_more_attempt():
    """The guard still decides; the model gets told which rule it broke."""
    drafts = iter(["87% 반응률이 확인되었습니다.", CLEAN_OUTPUT])
    prompts: list[str] = []

    def record(prompt, config):
        prompts.append(prompt)
        return next(drafts)

    result = explain_decision(REJECT_DECISION, LLMConfig(enabled=True), generator=record)
    assert result["source"] == "model"
    assert result["audit"]["attempts"] == 2
    assert result["violations"] == []
    assert prompts[0] != prompts[1]


def test_the_retry_prompt_names_the_broken_rule_not_the_rejected_text(facts):
    """Feeding the draft back would let a fabrication survive by being edited."""
    hallucination = "천식에 효과가 있습니다."
    repair = build_repair_prompt(facts, guard(hallucination, facts))
    assert "천식" not in repair
    assert VIOLATION_GUIDANCE["indication_not_quoted"] in repair
    assert repair.count("설명:") == 1


def test_a_run_that_never_satisfies_the_guard_ends_on_the_template(facts):
    calls = []

    def always_bad(prompt, config):
        calls.append(prompt)
        return "NCT01234567에서 87% 반응률을 보였습니다."

    result = explain_decision(REJECT_DECISION, LLMConfig(enabled=True), generator=always_bad)
    assert result["source"] == "template"
    assert result["text"] == render_template(facts)
    assert result["audit"]["outcome"] == "rejected"
    assert len(calls) == MAX_ATTEMPTS
