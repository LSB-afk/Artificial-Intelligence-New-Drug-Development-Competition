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

Configuration is environment-driven and ON by default on the serving plane::

    H2L_LLM_ENABLED=0                       # default 1; set 0 for template only
    H2L_LLM_HOST=http://127.0.0.1:11434
    H2L_LLM_MODEL=gemma4:latest
    H2L_LLM_TIMEOUT_S=20
    H2L_LLM_MAX_CHARS=700

Being enabled costs nothing when Ollama is absent: a refused connection fails
immediately and the deterministic template is returned, so the console still
answers. The evaluation plane does not go through this module at all, and
``LLMConfig.offline()`` pins the model off for code that must never touch the
network regardless of the environment.
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
# Measured over the three fixture decisions on the installed models: gemma4 is
# the only one that cleared the guardrail on the first attempt every time and
# wrote continuous prose instead of bullets. llama3.1 fails the verbatim
# indication rule; qwen2.5 clears it but mistranslates rule ids.
DEFAULT_MODEL = "gemma4:latest"
DEFAULT_TIMEOUT_S = 20.0
DEFAULT_MAX_CHARS = 700
# Listing installed models is a cheap local call; keep it short so a hung
# daemon cannot stall a page load.
DISCOVERY_TIMEOUT_S = 2.0
# Drafts the guardrail may refuse before the template stands. Two, because the
# second attempt is where telling a small model which rule it broke pays off and
# a third mostly repeats the second at twice the latency.
MAX_ATTEMPTS = 2

# Sentences the model must not produce when the decision is not ADVANCE. These
# are the phrasings that would turn a rejection demo into a therapeutic claim.
THERAPEUTIC_CLAIMS = (
    "치료 효과",
    "치료가 가능",
    "치료할 수 있",
    "치료에 적합",
    "치료제로 적합",
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

# Markers that the model transcribed the harness's own instructions instead of
# explaining the decision. Worth catching in its own right: a retried draft that
# recites "you must quote 'plaque psoriasis'" satisfies the verbatim-indication
# check with the recitation while the actual explanation says something else.
META_MARKERS = (
    "직전 답변", "이전 답변", "규칙에 위배", "검사에 걸", "지시문", "프롬프트",
    "다시 쓰겠", "다시 작성하겠",
)

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

# Latin words the explanation may use without them appearing in the fact set:
# decision vocabulary and the harness's own nouns. Everything else in Latin
# script has to have come from the facts.
ALLOWED_LATIN = {
    "advance", "hold", "reject", "insufficient", "review", "admet", "qed", "tanimoto",
    "ecfp", "rdkit", "smiles", "pains", "brenk", "id", "ids", "json", "api", "llm",
}
MIN_LATIN_TOKEN = 3

_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z0-9-]{2,}")
# No trailing \b: Korean attaches particles directly to an identifier
# ("EV-TYK2-UC-PH2-FAIL와"), and a word boundary there would truncate the match
# mid-token and report a correctly quoted id as a fabricated one.
_EVIDENCE_TOKEN = re.compile(r"\bEV-[A-Z0-9][A-Z0-9-]*", re.IGNORECASE)
_CITATION_TOKEN = re.compile(r"\b(?:NCT\d+|PMID[: ]?\d+|doi:)", re.IGNORECASE)
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_HANGUL = re.compile(r"[가-힣]")


@dataclass(frozen=True)
class LLMConfig:
    """Runtime configuration. The serving plane runs with the model enabled."""

    enabled: bool = True
    host: str = DEFAULT_HOST
    model: str = DEFAULT_MODEL
    timeout_s: float = DEFAULT_TIMEOUT_S
    max_chars: int = DEFAULT_MAX_CHARS

    @classmethod
    def from_env(cls, env: dict | None = None) -> "LLMConfig":
        source = os.environ if env is None else env
        return cls(
            enabled=str(source.get("H2L_LLM_ENABLED", "1")).strip().lower() in {"1", "true", "yes", "on"},
            host=str(source.get("H2L_LLM_HOST", DEFAULT_HOST)).rstrip("/"),
            model=str(source.get("H2L_LLM_MODEL", DEFAULT_MODEL)),
            timeout_s=_float_or(source.get("H2L_LLM_TIMEOUT_S"), DEFAULT_TIMEOUT_S),
            max_chars=int(_float_or(source.get("H2L_LLM_MAX_CHARS"), DEFAULT_MAX_CHARS)),
        )

    @classmethod
    def offline(cls, **overrides) -> "LLMConfig":
        """A configuration that cannot reach the network, whatever the env says.

        Used by code paths whose output must stay byte-reproducible. This is a
        deliberate pin, not a default: reading ``H2L_LLM_ENABLED`` here would let
        an environment variable make a published result irreproducible.
        """
        return cls(**{**overrides, "enabled": False})

    def with_model(self, model: str | None) -> "LLMConfig":
        return self if not model else LLMConfig(
            enabled=self.enabled, host=self.host, model=model,
            timeout_s=self.timeout_s, max_chars=self.max_chars,
        )


def _float_or(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---- model discovery ---------------------------------------------------
def list_models(config: LLMConfig | None = None) -> list[str]:
    """Models installed on the local Ollama host, or ``[]`` if unreachable.

    Never raises: an absent runtime is a normal state for this project, not an
    error, and the caller falls back to the deterministic template.
    """
    settings = config or LLMConfig.from_env()
    if not settings.enabled:
        return []
    try:
        with urllib.request.urlopen(f"{settings.host}/api/tags", timeout=DISCOVERY_TIMEOUT_S) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        return []
    names = [str(item.get("name", "")) for item in body.get("models") or []]
    return sorted(name for name in names if name)


def resolve_model(requested: str | None, config: LLMConfig | None = None) -> tuple[str | None, str | None]:
    """Pick a usable model name. Returns ``(model, rejection_reason)``.

    A request for a model that is not installed is refused rather than quietly
    served by a different one — the console names the model beside every
    sentence, so that label has to be true.
    """
    settings = config or LLMConfig.from_env()
    if not requested:
        return settings.model, None
    installed = list_models(settings)
    if installed and requested not in installed:
        return None, f"모델 '{requested}'은(는) 이 호스트에 설치되어 있지 않습니다."
    return requested, None


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
    indication_ids = set(packet.get("indication_ids") or [])
    in_indication = [r for r in records if r.get("indication_id") in indication_ids]
    # Counts the harness can compute are facts, and a fact set that omits them
    # pushes the model into deriving its own numbers - which is exactly what the
    # guardrail then rejects. Publishing them keeps the model inside the facts.
    by_outcome: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    for record in records:
        by_outcome[str(record.get("outcome"))] = by_outcome.get(str(record.get("outcome")), 0) + 1
        by_kind[str(record.get("kind"))] = by_kind.get(str(record.get("kind")), 0) + 1
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
            "in_indication": len(in_indication),
            "cross_indication": len(records) - len(in_indication),
            "by_outcome": by_outcome,
            "by_kind": by_kind,
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
    The computed decision and state are the same case — reporting "결정은
    ADVANCE" is quoting the harness, not claiming a therapy works. Only the
    decision this run actually produced is dropped, so writing ADVANCE over a
    REJECT still trips the guard.
    """
    scan = text
    tokens = [
        *(facts.get("rule_ids") or []),
        *(facts.get("evidence_ids") or []),
        facts.get("decision"),
        facts.get("state"),
    ]
    for token in tokens:
        if token:
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


def _compound_parts(word: str) -> list[str]:
    """Lowercase pieces of a hyphen/underscore compound, empties dropped."""
    return [part for part in re.split(r"[-_]", word.lower()) if part]


def _unsupported_latin_terms(text: str, facts: dict) -> list[str]:
    """Latin-script words the fact set never mentioned.

    Catches an invented target, drug, or indication written in the source
    language — the failure that matters most here, because a fabricated disease
    name reads as authoritative. It cannot catch a fabrication transliterated
    into Hangul; the guard bounds identifiers and numbers, it does not certify
    every noun, which is why the console shows the fact set beside the sentence.
    """
    vocabulary = {
        part
        for word in _LATIN_WORD.findall(json.dumps(facts, ensure_ascii=False))
        for part in _compound_parts(word)
    } | ALLOWED_LATIN
    # A compound counts as supported when every part of it does: the fact set
    # writes "cross_indication", and a model spelling it "cross-indication" has
    # invented nothing. Requiring the exact punctuation would flag paraphrase as
    # fabrication and teach the retry loop to chase a non-problem.
    return sorted(
        {
            word for word in _LATIN_WORD.findall(text)
            if len(word) >= MIN_LATIN_TOKEN
            and not all(part in vocabulary for part in _compound_parts(word))
        }
    )


def _unquoted_indications(text: str, facts: dict) -> list[str]:
    """Indications from the fact set that the text failed to name verbatim.

    This is the guard that actually holds against a fabricated disease. The
    earlier checks all work on identifiers and Latin script, so a model that
    translates "plaque psoriasis" into a wrong Korean word — or invents
    "천식" outright — slips past every one of them. Requiring the source
    spelling makes the sentence carry the fact set's own strings, which is
    checkable, and it costs nothing: an explanation of an indication-mismatch
    decision that never names the indications is not a usable explanation.
    """
    indications = {
        str(item["indication"]).strip()
        for item in facts.get("evidence") or []
        if item.get("indication")
    }
    lowered = text.lower()
    return sorted(name for name in indications if name.lower() not in lowered)


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

    if any(marker in text for marker in META_MARKERS):
        violations.append("process_leak")

    allowed_numbers = set(_NUMBER.findall(json.dumps(facts, ensure_ascii=False)))
    unsupported = sorted({n for n in _NUMBER.findall(text) if n not in allowed_numbers})
    if unsupported:
        violations.append(f"unsupported_number:{','.join(unsupported[:4])}")

    allowed_ids = {str(item).upper() for item in facts.get("evidence_ids") or []}
    stray_ids = sorted({token.upper().rstrip("-") for token in _EVIDENCE_TOKEN.findall(text)} - allowed_ids)
    if stray_ids:
        violations.append(f"unsupported_evidence_id:{','.join(stray_ids[:4])}")

    if _CITATION_TOKEN.search(text):
        violations.append("fabricated_citation")

    stray_terms = _unsupported_latin_terms(text, facts)
    if stray_terms:
        violations.append(f"unsupported_term:{','.join(stray_terms[:4])}")

    missing = _unquoted_indications(text, facts)
    if missing:
        violations.append(f"indication_not_quoted:{','.join(missing[:3])}")

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
BASE_RULES = (
    "JSON에 없는 숫자, 근거 ID, 논문, 임상시험 번호를 절대 만들지 마세요.",
    "개수를 쓸 때는 반드시 아라비아 숫자로 쓰세요. '두 건'이 아니라 '2건'입니다.",
    "JSON에 나오는 모든 indication을 영문 철자 그대로 한 번씩 언급하세요. "
    "한국어로 번역하거나 다른 질환명으로 바꾸면 검사에 걸립니다. "
    "JSON에 없는 질환명은 절대 쓰지 마세요.",
    "target은 단백질 이름이고 reference_drug가 약물입니다. 둘을 바꾸지 마세요.",
    "판정 결과를 바꾸거나 반대로 해석하지 마세요.",
    "치료 효과, 유효성, 처방을 권고하지 마세요.",
    "결론과 그 근거만 쓰고, 생각 과정은 출력하지 마세요.",
    "번호 목록이나 불릿을 쓰지 말고 이어지는 문단 하나로 쓰세요. "
    "목록 번호도 숫자로 취급되어 검사에 걸립니다.",
    "마크다운을 쓰지 마세요. 별표, 역슬래시, 밑줄 강조 없이 일반 문장으로만 쓰세요.",
    "이 지시문이나 검사 결과를 답변에 옮겨 적지 마세요. 판정 설명만 쓰세요.",
)


def build_prompt(facts: dict, extra_rules: tuple[str, ...] | list[str] = ()) -> str:
    """The explanation prompt. ``extra_rules`` are appended to the rule list.

    Corrections belong in the rules, not after the ``설명:`` cue. Text placed
    after that cue is read as the opening of the answer, and the models dutifully
    transcribed the correction into the explanation.
    """
    # Spelling out the exact strings the sentence must contain works better than
    # describing the rule: these models will otherwise gloss an indication into
    # Korean, and a wrong gloss reads as authoritative.
    indications = sorted({
        str(item["indication"]).strip()
        for item in facts.get("evidence") or []
        if item.get("indication")
    })
    required = (
        "반드시 이 철자 그대로 포함할 단어: " + ", ".join(f"'{name}'" for name in indications) + "\n\n"
        if indications else ""
    )
    rules = "\n".join(
        f"{index}. {rule}" for index, rule in enumerate([*BASE_RULES, *extra_rules], start=1)
    )
    return (
        "당신은 신약개발 의사결정 하네스의 설명 작성자입니다.\n"
        "아래 JSON은 결정론적 도구가 이미 계산한 사실입니다. 이 사실만 사용해 한국어 4문장 이내로 설명하세요.\n\n"
        f"규칙:\n{rules}\n\n"
        f"{required}"
        f"사실:\n{json.dumps(facts, ensure_ascii=False, indent=2, sort_keys=True)}\n\n"
        "설명:"
    )


# What each guardrail code means as an instruction. The retry prompt carries
# these, never the rejected sentence: feeding a draft back would let a
# fabrication survive by being edited instead of dropped, and the point of the
# guard is that a violating sentence is discarded.
VIOLATION_GUIDANCE = {
    "empty_output": "설명이 비어 있었습니다. 문장을 작성하세요.",
    "too_long": "설명이 너무 길었습니다. 4문장 이내로 줄이세요.",
    "reasoning_leak": "생각 과정이 출력에 섞였습니다. 결론과 근거만 쓰세요.",
    "process_leak": "지시문이나 검사 결과를 그대로 옮겨 적었습니다. 판정 설명만 쓰세요.",
    "unsupported_number": "JSON에 없는 숫자를 썼습니다. counts에 있는 숫자만 쓰고 목록 번호도 쓰지 마세요.",
    "unsupported_evidence_id": "JSON에 없는 근거 ID를 썼습니다. evidence_ids의 ID만 쓰세요.",
    "fabricated_citation": "존재하지 않는 논문·임상시험 번호를 썼습니다. 인용을 빼세요.",
    "unsupported_term": "JSON에 없는 영문 단어를 썼습니다. JSON에 나오는 단어만 쓰세요.",
    "indication_not_quoted": "indication을 영문 철자 그대로 쓰지 않았습니다. 번역하지 말고 JSON의 철자를 그대로 옮기세요.",
    "therapeutic_claim": "치료 효과나 진행 권고로 읽히는 표현을 썼습니다. 판정 사실만 쓰세요.",
    "language_mismatch": "한국어로 쓰지 않았습니다. 한국어 문장으로 쓰세요.",
}


def build_repair_prompt(facts: dict, violations: list[str]) -> str:
    """A second, bounded attempt after the guardrail refused the first one."""
    extra: list[str] = []
    for violation in violations:
        guidance = VIOLATION_GUIDANCE.get(violation.split(":", 1)[0])
        if guidance and guidance not in extra:
            extra.append(guidance)
    return build_prompt(facts, extra or ["사실 범위를 벗어나지 마세요."])


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def generate(prompt: str, config: LLMConfig, *, num_predict: int = 400) -> str:
    """One non-streaming Ollama completion. Raises on any transport failure.

    ``temperature`` and ``seed`` are pinned so that a given prompt and model
    produce the same text run to run; the model is a renderer here, not a
    source of variation. ``think`` is off because the project forbids storing
    or presenting hidden reasoning.
    """
    payload = json.dumps(
        {
            "model": config.model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {"temperature": 0, "seed": 42, "num_predict": num_predict},
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


def explain_decision(
    decision: dict,
    config: LLMConfig | None = None,
    *,
    generator=generate,
    attempts: int = MAX_ATTEMPTS,
) -> dict:
    """Produce a bounded explanation for a decision trace.

    The return value always carries a usable ``text``. ``source`` says whether it
    came from the local model or the deterministic template, and ``audit`` is the
    ``ModelCalled`` record to append to the trace.

    A refused draft buys one retry carrying the violation codes. That is not the
    guardrail relaxing: the guard still decides, every attempt is checked against
    the same fact set, and a run that never satisfies it ends on the template.
    Local 7-8B models mostly fail on form — a translated indication, a stray list
    number — and telling them which rule they broke fixes that without widening
    what they are allowed to say.
    """
    settings = config or LLMConfig.from_env()
    facts = explanation_facts(decision)
    template = render_template(facts)

    if not settings.enabled:
        return _result(facts, template, "template", settings, outcome="disabled", reason="local model disabled")

    prompt = build_prompt(facts)
    digest = prompt_hash(prompt)
    started = time.monotonic()
    violations: list[str] = []

    for attempt in range(1, max(1, attempts) + 1):
        try:
            raw = generator(prompt, settings)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as error:
            return _result(
                facts,
                template,
                "template",
                settings,
                outcome="unavailable",
                reason=f"{type(error).__name__}: {error}",
                latency_ms=_elapsed_ms(started),
                digest=digest,
                attempts=attempt,
            )

        text = strip_reasoning(raw)
        violations = guard(text, facts, max_chars=settings.max_chars)
        if not violations:
            return _result(
                facts, text, "model", settings,
                outcome="accepted", latency_ms=_elapsed_ms(started), digest=digest, attempts=attempt,
            )
        prompt = build_repair_prompt(facts, violations)

    return _result(
        facts,
        template,
        "template",
        settings,
        outcome="rejected",
        reason="guardrail rejected model output",
        latency_ms=_elapsed_ms(started),
        digest=digest,
        violations=violations,
        attempts=max(1, attempts),
    )


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
    attempts: int = 0,
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
            "attempts": attempts,
            "violations": list(violations or []),
        },
    }
