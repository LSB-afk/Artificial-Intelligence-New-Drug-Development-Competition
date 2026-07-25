import type { Explanation, ExplainInput, RunSnapshot, TargetSnapshot } from '../domain/contracts'

/**
 * 판단 해설 어댑터.
 *
 * 파이썬 하네스(:8765)의 읽기 전용 `/api/explain`을 호출해 로컬 LLM 해설을
 * 가져오되, 서버가 없거나 응답이 늦거나 가드레일에 걸리면 스냅샷만으로
 * 결정론적 문장을 만들어 돌려줍니다. 콘솔은 어떤 경우에도 빈 화면이 되지
 * 않고, 사용자는 출처 칩으로 둘을 구분합니다.
 *
 * 해설은 사실을 만들지 않습니다. 판정·규칙·근거 ID는 모두 이미 계산된 값입니다.
 */

const REQUEST_TIMEOUT_MS = 45_000

/** 콘솔 질병 ID → 파이썬 하네스 가설 접두사. 없으면 백엔드를 호출하지 않습니다. */
const HYPOTHESIS_PREFIX: Record<string, string> = {
  MONDO_0005265: 'IBD',
}

const decisionLabel: Record<TargetSnapshot['decision'], string> = {
  review: '검토 필요',
  rejected: '진행 거절',
  insufficient: '근거 부족',
  reference_only: '참고용',
  demo_only: '데모 전용',
}

interface ExplainResponse {
  decision?: string
  explanation?: {
    text?: string
    source?: string
    model?: string | null
    fallback_reason?: string | null
    violations?: string[]
  }
  facts?: {
    rule_ids?: string[]
    evidence_ids?: string[]
  }
}

export function hypothesisIdFor(diseaseId: string, symbol: string): string | null {
  const prefix = HYPOTHESIS_PREFIX[diseaseId]
  return prefix ? `${prefix}:${symbol}` : null
}

/** 스냅샷 값만으로 만드는 결정론적 해설. 네트워크가 없어도 항상 성공합니다. */
export function renderLocalExplanation(target: TargetSnapshot, snapshot: RunSnapshot): string {
  const label = decisionLabel[target.decision] ?? target.decision
  const conflicting = snapshot.evidence.filter((item) => item.polarity === 'conflicting').length
  const gate = target.decision === 'rejected' ? '분자 최적화 단계로 진행할 수 없습니다' : '사람 검토 후에만 다음 단계로 넘어갑니다'
  return (
    `${target.symbol}(${target.name}) 타깃은 ${snapshot.run.disease} 맥락에서 ${label}로 분류되었습니다. ` +
    `이 실행이 참조한 근거는 ${snapshot.evidence.length}건이고 이 가운데 ${conflicting}건이 반증입니다. ` +
    `판단 근거: ${target.rationale} 주의: ${target.caution} ` +
    `따라서 ${gate}. 이 문장은 스냅샷 값에서 결정론적으로 생성되었으며 치료 효과를 주장하지 않습니다.`
  )
}

function localExplanation(
  target: TargetSnapshot,
  snapshot: RunSnapshot,
  fallbackReason: string,
): Explanation {
  return {
    targetSymbol: target.symbol,
    text: renderLocalExplanation(target, snapshot),
    source: 'template',
    model: null,
    fallbackReason,
    violations: [],
    decision: decisionLabel[target.decision] ?? target.decision,
    ruleIds: [],
    evidenceIds: target.evidenceIds,
    generatedAt: new Date().toISOString(),
  }
}

export async function requestExplanation(input: ExplainInput, snapshot: RunSnapshot): Promise<Explanation> {
  const target = snapshot.targets.find((item) => item.symbol === input.targetSymbol)
  if (!target) throw new Error(`타깃을 찾을 수 없습니다: ${input.targetSymbol}`)

  const hypothesisId = hypothesisIdFor(snapshot.run.diseaseId, target.symbol)
  if (!hypothesisId) {
    return localExplanation(target, snapshot, '이 질병 스냅샷에 매핑된 하네스 가설이 없습니다.')
  }

  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  try {
    const response = await fetch(`/api/explain?hypothesis=${encodeURIComponent(hypothesisId)}`, {
      signal: controller.signal,
    })
    if (!response.ok) {
      // 하네스가 꺼져 있으면 개발 프록시가 5xx를 돌려줍니다. 둘을 구분해서 표시합니다.
      const reason = response.status >= 500
        ? '하네스 서버가 응답하지 않습니다 (오프라인 폴백).'
        : `하네스가 요청을 거부했습니다 (HTTP ${response.status}).`
      return localExplanation(target, snapshot, reason)
    }
    const payload = (await response.json()) as ExplainResponse
    const explanation = payload.explanation
    if (!explanation?.text) {
      return localExplanation(target, snapshot, '하네스가 해설을 반환하지 않았습니다.')
    }
    return {
      targetSymbol: target.symbol,
      text: explanation.text,
      source: explanation.source === 'model' ? 'model' : 'template',
      model: explanation.model ?? null,
      fallbackReason: explanation.fallback_reason ?? null,
      violations: explanation.violations ?? [],
      decision: payload.decision ?? decisionLabel[target.decision] ?? target.decision,
      ruleIds: payload.facts?.rule_ids ?? [],
      evidenceIds: payload.facts?.evidence_ids ?? target.evidenceIds,
      generatedAt: new Date().toISOString(),
    }
  } catch {
    return localExplanation(target, snapshot, '하네스 서버에 연결할 수 없습니다 (오프라인 폴백).')
  } finally {
    window.clearTimeout(timer)
  }
}
