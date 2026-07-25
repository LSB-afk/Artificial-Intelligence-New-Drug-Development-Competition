"""Local-model explanation layer: offline default, fact-bounded output.

The model is allowed to rephrase decisions, never to widen them. These tests
pin the two properties that make that safe: the harness stays fully offline and
deterministic unless explicitly enabled, and any model output that introduces
facts, flips the decision, or leaks reasoning is replaced by the template.
"""
import json

import pytest

from h2l.llm import (
    MODEL_CALL_EVENT,
    LLMConfig,
    build_prompt,
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
def test_disabled_by_default_and_never_calls_the_model():
    result = explain_decision(REJECT_DECISION, LLMConfig(), generator=_boom)
    assert result["source"] == "template"
    assert result["audit"]["outcome"] == "disabled"
    assert result["audit"]["prompt_hash"] is None


def test_env_config_is_off_unless_explicitly_enabled():
    assert LLMConfig.from_env({}).enabled is False
    assert LLMConfig.from_env({"H2L_LLM_ENABLED": "0"}).enabled is False
    assert LLMConfig.from_env({"H2L_LLM_ENABLED": "1"}).enabled is True
    assert LLMConfig.from_env({"H2L_LLM_ENABLED": "true"}).enabled is True


def test_template_is_deterministic():
    first = explain_decision(REJECT_DECISION, LLMConfig(), generator=_boom)["text"]
    second = explain_decision(REJECT_DECISION, LLMConfig(), generator=_boom)["text"]
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
    assert facts["counts"] == {"evidence": 3, "contradicting": 2, "supporting": 0}
    assert facts["evidence_ids"] == REJECT_DECISION["evidence_ids"]


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


def test_rule_id_containing_advance_is_not_read_as_a_claim(facts):
    assert guard("적용 규칙은 FAILED_TRIAL_BLOCKS_ADVANCE 입니다.", facts) == []


def test_negated_disclaimer_is_not_a_claim(facts):
    assert guard("이 설명은 치료 효과를 주장하지 않습니다.", facts) == []


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
def test_clean_model_output_is_used_and_audited(facts):
    clean = "TYK2 가설은 해당 적응증에서 진행이 거절되었습니다. 반증 근거가 우세합니다."

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
    raw = "<think>숨은 추론 과정</think>TYK2 가설은 거절되었습니다."

    result = explain_decision(REJECT_DECISION, LLMConfig(enabled=True), generator=lambda p, c: raw)
    assert result["source"] == "model"
    assert "숨은 추론" not in result["text"]
    assert "<think>" not in result["text"]
