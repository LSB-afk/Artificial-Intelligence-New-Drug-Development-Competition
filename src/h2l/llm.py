"""Local-model explanation layer (Ollama), bounded by a fact-set guardrail.

The project rule is that facts and calculations come from versioned tools or
evidence records, and the LLM only selects actions and writes bounded
explanations. This module is the seam where a local model enters, and it is
built so that the model cannot widen the scientific claim surface:

- the model receives *only* the fact set already computed by the decision core,
- every generated sentence is checked back against that fact set before it is
  shown (numbers, identifiers, decision direction, therapeutic claims),
- any failure, timeout, or unreachable runtime falls back to a deterministic
  template, so the offline invariant and byte-reproducible evals still hold,
- a ``ModelCalled`` audit record is emitted with the prompt *hash*, never the
  prompt text and never hidden reasoning.

Configuration is environment-driven and OFF by default::

    H2L_LLM_ENABLED=1                       # default 0 (template only)
    H2L_LLM_HOST=http://127.0.0.1:11434
    H2L_LLM_MODEL=qwen2.5:7b-instruct
    H2L_LLM_TIMEOUT_S=20
    H2L_LLM_MAX_CHARS=700

With the default configuration this module performs no network I/O at all.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

MODEL_CALL_EVENT = "ModelCalled"

DEFAULT_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen2.5:7b-instruct"
DEFAULT_TIMEOUT_S = 20.0
DEFAULT_MAX_CHARS = 700

# Sentences the model must not produce when the decision is not ADVANCE. These
# are the phrasings that would turn a rejection demo into a therapeutic claim.
THERAPEUTIC_CLAIMS = (
    "치료 효과",
    "치료가 가능",
    "효능이 입증",
    "효과적입니다",
    "유효성이 확인",
    "임상적으로 유효",
    "권장합니다",
    "추천합니다",
    "승인 권고",
    "진행 가능",
    "진행을 권",
    "advance",
    "efficacious",
    "recommend",
)

# Markers that indicate the model leaked its scratchpad. The project forbids
# storing or presenting hidden chain-of-thought.
REASONING_MARKERS = ("<think", "</think", "reasoning:", "chain of thought", "사고 과정:")

# A claim phrase that is immediately negated is a denial, not a claim: the
# standard disclaimer "치료 효과를 주장하지 않습니다" must not trip the guard.
NEGATIONS = ("않", "없", "아니", "못", " not ", " no ")
NEGATION_WINDOW = 24

DECISION_LABELS = {
    "ADVANCE": "진행(ADVANCE)",
    "REJECT": "진행 거절(REJECT)",
    "INSUFFICIENT": "근거 부족(INSUFFICIENT)",
    "REVIEW": "검토 필요(REVIEW)",
    "HOLD": "보류(HOLD)",
}

_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_EVIDENCE_TOKEN = re.compile(r"\bEV-[A-Z0-9][A-Z0-9-]*\b", re.IGNORECASE)
_CITATION_TOKEN = re.compile(r"\b(?:NCT\d+|PMID[: ]?\d+|doi:)", re.IGNORECASE)
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_HANGUL = re.compile(r"[가-힣]")


@dataclass(frozen=True)
class LLMConfig:
    """Runtime configuration. ``enabled`` is False unless explicitly set."""

    enabled: bool = False
    host: str = DEFAULT_HOST
    model: str = DEFAULT_MODEL
    timeout_s: float = DEFAULT_TIMEOUT_S
    max_chars: int = DEFAULT_MAX_CHARS

    @classmethod
    def from_env(cls, env: dict | None = None) -> "LLMConfig":
        source = os.environ if env is None else env
        return cls(
            enabled=str(source.get("H2L_LLM_ENABLED", "0")).strip().lower() in {"1", "true", "yes", "on"},
            host=str(source.get("H2L_LLM_HOST", DEFAULT_HOST)).rstrip("/"),
            model=str(source.get("H2L_LLM_MODEL", DEFAULT_MODEL)),
            timeout_s=_float_or(source.get("H2L_LLM_TIMEOUT_S"), DEFAULT_TIMEOUT_S),
            max_chars=int(_float_or(source.get("H2L_LLM_MAX_CHARS"), DEFAULT_MAX_CHARS)),
        )


def _float_or(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---- fact set ----------------------------------------------------------
def explanation_facts(decision: dict) -> dict:
    """Reduce a decision trace to the bounded fact set the model may use.

    Anything absent here is, by construction, something the explanation is not
    allowed to assert.
    """
    packet = decision.get("packet") or {}
    records = packet.get("records") or []
    evidence = [
        {
            "evidence_id": record.get("evidence_id"),
            "kind": record.get("kind"),
            "indication": record.get("indication"),
            "outcome": record.get("outcome"),
            "stance": record.get("stance"),
            "source_ref": record.get("source_ref"),
        }
        for record in records
    ]
    contradicting = [item for item in evidence if item["stance"] == "contradict"]
    supporting = [item for item in evidence if item["stance"] == "support"]
    return {
        "hypothesis_id": decision.get("hypothesis_id"),
        "target": packet.get("target"),
        "reference_drug": packet.get("reference_drug"),
        "decision": decision.get("decision"),
        "state": decision.get("state"),
        "molecule_eligible": bool(decision.get("molecule_eligible")),
        "rule_ids": list(decision.get("rule_ids") or []),
        "evidence_ids": list(decision.get("evidence_ids") or []),
        "snapshot_version": (decision.get("snapshot") or {}).get("version_id"),
        "observed_at": packet.get("observed_at"),
        "evidence": evidence,
        "counts": {
            "evidence": len(evidence),
            "contradicting": len(contradicting),
            "supporting": len(supporting),
        },
    }


def render_template(facts: dict) -> str:
    """The deterministic explanation. Always available, never fails."""
    target = facts.get("target") or facts.get("hypothesis_id") or "대상"
    decision = facts.get("decision") or "UNKNOWN"
    label = DECISION_LABELS.get(decision, decision)
    counts = facts.get("counts") or {}
    total = counts.get("evidence", 0)
    contradicting = counts.get("contradicting", 0)
    rules = ", ".join(facts.get("rule_ids") or []) or "적용 규칙 없음"
    indications = sorted({item["indication"] for item in facts.get("evidence") or [] if item.get("indication")})
    scope = ", ".join(indications) if indications else "등록된 적응증"
    gate = "분자 최적화 단계로 진행할 수 있습니다." if facts.get("molecule_eligible") else "분자 최적화 단계로 진행할 수 없습니다."
    return (
        f"{target} 가설은 {label}로 판정되었습니다. "
        f"확인된 근거는 {scope} 범위에서 {total}건이며 이 가운데 {contradicting}건이 반증 근거입니다. "
        f"적용된 규칙은 {rules}입니다. 따라서 {gate} "
        "이 설명은 위 근거 ID와 규칙 ID에서만 작성되었으며 치료 효과를 주장하지 않습니다."
    )


# ---- output guardrail --------------------------------------------------
def strip_reasoning(text: str) -> str:
    """Remove scratchpad blocks so hidden reasoning is never stored or shown."""
    return _THINK_BLOCK.sub("", text).strip()


def _without_fact_tokens(text: str, facts: dict) -> str:
    """Drop identifiers the fact set supplied.

    Rule and evidence IDs are quoted verbatim by design, so they must not be
    read as prose: ``FAILED_TRIAL_BLOCKS_ADVANCE`` is not the word "advance",
    and its Latin letters are not evidence that the model answered in English.
    """
    scan = text
    for token in [*(facts.get("rule_ids") or []), *(facts.get("evidence_ids") or [])]:
        scan = re.sub(re.escape(str(token)), " ", scan, flags=re.IGNORECASE)
    return scan


def _asserted_claims(scan: str, _facts: dict) -> set[str]:
    """Claim phrases the text actually asserts.

    A phrase followed closely by a negation is a denial, not a claim.
    """
    scan = scan.lower()
    asserted = set()
    for phrase in THERAPEUTIC_CLAIMS:
        for match in re.finditer(re.escape(phrase.lower()), scan):
            window = scan[match.end(): match.end() + NEGATION_WINDOW]
            if not any(negation in window for negation in NEGATIONS):
                asserted.add(phrase)
                break
    return asserted


def guard(text: str, facts: dict, *, max_chars: int = DEFAULT_MAX_CHARS) -> list[str]:
    """Return the list of guardrail violations. Empty means the text is usable."""
    violations: list[str] = []
    if not text.strip():
        violations.append("empty_output")
        return violations
    if len(text) > max_chars:
        violations.append("too_long")

    lowered = text.lower()
    if any(marker in lowered for marker in REASONING_MARKERS):
        violations.append("reasoning_leak")

    allowed_numbers = set(_NUMBER.findall(json.dumps(facts, ensure_ascii=False)))
    unsupported = sorted({n for n in _NUMBER.findall(text) if n not in allowed_numbers})
    if unsupported:
        violations.append(f"unsupported_number:{','.join(unsupported[:4])}")

    allowed_ids = {str(item).upper() for item in facts.get("evidence_ids") or []}
    stray_ids = sorted({token.upper() for token in _EVIDENCE_TOKEN.findall(text)} - allowed_ids)
    if stray_ids:
        violations.append(f"unsupported_evidence_id:{','.join(stray_ids[:4])}")

    if _CITATION_TOKEN.search(text):
        violations.append("fabricated_citation")

    prose = _without_fact_tokens(text, facts)

    if facts.get("decision") != "ADVANCE" or not facts.get("molecule_eligible"):
        claimed = sorted(_asserted_claims(prose, facts))
        if claimed:
            violations.append(f"therapeutic_claim:{','.join(claimed[:3])}")

    letters = [ch for ch in prose if ch.isalpha()]
    if letters and len(_HANGUL.findall(prose)) / len(letters) < 0.3:
        violations.append("language_mismatch")

    return violations


# ---- model call --------------------------------------------------------
def build_prompt(facts: dict) -> str:
    return (
        "당신은 신약개발 의사결정 하네스의 설명 작성자입니다.\n"
        "아래 JSON은 결정론적 도구가 이미 계산한 사실입니다. 이 사실만 사용해 한국어 4문장 이내로 설명하세요.\n\n"
        "규칙:\n"
        "1. JSON에 없는 숫자, 근거 ID, 논문, 임상시험 번호를 절대 만들지 마세요.\n"
        "2. 판정 결과를 바꾸거나 반대로 해석하지 마세요.\n"
        "3. 치료 효과, 유효성, 처방을 권고하지 마세요.\n"
        "4. 결론과 그 근거만 쓰고, 생각 과정은 출력하지 마세요.\n\n"
        f"사실:\n{json.dumps(facts, ensure_ascii=False, indent=2, sort_keys=True)}\n\n"
        "설명:"
    )


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def generate(prompt: str, config: LLMConfig) -> str:
    """One non-streaming Ollama completion. Raises on any transport failure."""
    payload = json.dumps(
        {
            "model": config.model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {"temperature": 0, "seed": 42, "num_predict": 400},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{config.host}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=config.timeout_s) as response:
        body = json.loads(response.read().decode("utf-8"))
    return str(body.get("response", ""))


def explain_decision(decision: dict, config: LLMConfig | None = None, *, generator=generate) -> dict:
    """Produce a bounded explanation for a decision trace.

    The return value always carries a usable ``text``. ``source`` says whether it
    came from the local model or the deterministic template, and ``audit`` is the
    ``ModelCalled`` record to append to the trace.
    """
    settings = config or LLMConfig.from_env()
    facts = explanation_facts(decision)
    template = render_template(facts)

    if not settings.enabled:
        return _result(facts, template, "template", settings, outcome="disabled", reason="local model disabled")

    prompt = build_prompt(facts)
    digest = prompt_hash(prompt)
    started = time.monotonic()
    try:
        raw = generator(prompt, settings)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as error:
        latency = _elapsed_ms(started)
        return _result(
            facts,
            template,
            "template",
            settings,
            outcome="unavailable",
            reason=f"{type(error).__name__}: {error}",
            latency_ms=latency,
            digest=digest,
        )

    latency = _elapsed_ms(started)
    text = strip_reasoning(raw)
    violations = guard(text, facts, max_chars=settings.max_chars)
    if violations:
        return _result(
            facts,
            template,
            "template",
            settings,
            outcome="rejected",
            reason="guardrail rejected model output",
            latency_ms=latency,
            digest=digest,
            violations=violations,
        )
    return _result(facts, text, "model", settings, outcome="accepted", latency_ms=latency, digest=digest)


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _result(
    facts: dict,
    text: str,
    source: str,
    config: LLMConfig,
    *,
    outcome: str,
    reason: str | None = None,
    latency_ms: int = 0,
    digest: str | None = None,
    violations: list[str] | None = None,
) -> dict:
    return {
        "text": text,
        "source": source,
        "model": config.model if config.enabled else None,
        "host": config.host if config.enabled else None,
        "fallback_reason": reason,
        "violations": list(violations or []),
        "facts": facts,
        "audit": {
            "event_type": MODEL_CALL_EVENT,
            "model": config.model if config.enabled else None,
            "outcome": outcome,
            "prompt_hash": digest,
            "latency_ms": latency_ms,
            "violations": list(violations or []),
        },
    }
