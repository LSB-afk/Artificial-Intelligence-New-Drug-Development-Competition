/**
 * 에이전트 실행 어댑터.
 *
 * 파이썬 하네스(:8765)의 `/api/models`, `/api/agent/run`을 호출해 **실제 실행
 * 기록**을 가져옵니다. 이 화면이 보여주는 단계·관측·거부는 모두 하네스가
 * 실행하며 만든 값이고, 프런트엔드는 어떤 사실도 만들지 않습니다.
 *
 * 모델의 권한은 "다음에 어떤 행동을 실행할지 고르는 것" 하나뿐입니다. 관측과
 * 판정은 결정론적 코드가 씁니다. 그래서 각 단계는 모델이 골랐는지(`model`)
 * 고정 정책이 골랐는지(`policy`)를 함께 기록합니다.
 *
 * 하네스가 꺼져 있으면 실행 기록 대신 행동 허용 목록만 보여줍니다. 허용 목록은
 * 서버가 떠 있든 아니든 참인 사실이라 오프라인에서도 화면이 비지 않습니다.
 */

const REQUEST_TIMEOUT_MS = 180_000
const MODELS_TIMEOUT_MS = 5_000

export interface AgentAction {
  action: string
  args: string[]
  purpose: string
}

export interface AgentObservation {
  summary: string
  data: Record<string, unknown>
  refused: boolean
}

export interface AgentStep {
  step: number
  action: string
  args: Record<string, string>
  /** 이 단계를 모델이 골랐는지, 고정 정책이 대신 골랐는지. */
  selectedBy: 'model' | 'policy'
  /** 정책으로 넘어간 이유. 모델이 골랐으면 null입니다. */
  selectionNote: string | null
  observation: AgentObservation
  refused: boolean
}

export interface AgentRun {
  goal: string
  modelEnabled: boolean
  model: string | null
  steps: AgentStep[]
  modelSelectedSteps: number
  policySelectedSteps: number
  refusedSteps: number[]
  finished: boolean
  stoppedReason: string
  /** 제출한 임시 패킷으로 돌린 실행인지. 저장되지 않고 승인도 받지 않은 근거입니다. */
  sandbox: boolean
  decision: { decision: string; state: string; moleculeEligible: boolean; ruleIds: string[] }
  explanation: { text: string; source: 'model' | 'template'; model: string | null; violations: string[] }
  actions: AgentAction[]
}

/** 판정관이 버튼 하나로 넣어볼 수 있는 근거 패킷. 하나씩 다른 규칙을 건드립니다. */
export interface Scenario {
  id: string
  label: string
  /** 이 패킷이 어떤 판정과 규칙을 내는지. 하네스 테스트가 실제 출력과 대조합니다. */
  expectation: string
  note: string
  packet: Record<string, unknown>
}

export interface ModelCatalog {
  enabled: boolean
  host: string
  installed: string[]
  defaultModel: string | null
  reachable: boolean
  note: string
}

/** 하네스가 없을 때 보여줄 행동 허용 목록. `agent.ACTIONS`와 같은 순서입니다. */
export const OFFLINE_ACTIONS: AgentAction[] = [
  { action: 'list_hypotheses', args: [], purpose: '등록된 가설과 타깃 목록을 확인한다.' },
  { action: 'inspect_evidence', args: ['hypothesis_id'], purpose: '승인된 근거 스냅샷의 레코드 구성을 확인한다.' },
  { action: 'critique', args: ['hypothesis_id'], purpose: '적응증 일치와 반증 규칙으로 가설을 비평하고 판정을 받는다.' },
  { action: 'check_molecule_gate', args: ['hypothesis_id'], purpose: '분자 최적화 단계가 열려 있는지 게이트 상태를 확인한다.' },
  { action: 'optimize_molecules', args: ['hypothesis_id'], purpose: '분자 최적화를 요청한다. 게이트가 닫혀 있으면 하네스가 거부한다.' },
  { action: 'whatif_missing_evidence', args: ['hypothesis_id'], purpose: '판정을 바꾸려면 어떤 근거가 필요한지 규칙에서 역산한다.' },
  { action: 'finish', args: [], purpose: '목표에 답할 수 있으면 종료한다.' },
]

export const OFFLINE_CATALOG: ModelCatalog = {
  enabled: false,
  host: '',
  installed: [],
  defaultModel: null,
  reachable: false,
  note: '하네스 서버에 연결할 수 없습니다. 행동 허용 목록만 표시합니다.',
}

async function request<T>(path: string, timeoutMs: number, init?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetch(path, { ...init, signal: controller.signal })
    if (!response.ok) {
      const detail = await response.json().catch(() => null)
      throw new Error(
        (detail as { message?: string } | null)?.message ??
          (response.status >= 500
            ? '하네스 서버가 응답하지 않습니다 (오프라인).'
            : `하네스가 요청을 거부했습니다 (HTTP ${response.status}).`),
      )
    }
    return (await response.json()) as T
  } finally {
    window.clearTimeout(timer)
  }
}

function getJson<T>(path: string, timeoutMs: number): Promise<T> {
  return request<T>(path, timeoutMs)
}

function postJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, REQUEST_TIMEOUT_MS, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

interface ModelsResponse {
  enabled?: boolean
  host?: string
  installed?: string[]
  default?: string | null
  reachable?: boolean
  note?: string
}

/** 설치된 모델 목록. 하네스가 없으면 오프라인 카탈로그를 돌려줍니다. */
export async function listModels(): Promise<ModelCatalog> {
  try {
    const payload = await getJson<ModelsResponse>('/api/models', MODELS_TIMEOUT_MS)
    return {
      enabled: payload.enabled ?? false,
      host: payload.host ?? '',
      installed: payload.installed ?? [],
      defaultModel: payload.default ?? null,
      reachable: payload.reachable ?? false,
      note: payload.note ?? '',
    }
  } catch {
    return OFFLINE_CATALOG
  }
}

interface AgentRunResponse {
  goal: string
  model_enabled: boolean
  model: string | null
  steps: Array<{
    step: number
    action: string
    args: Record<string, string>
    selected_by: string
    selection_note: string | null
    observation: AgentObservation
    refused: boolean
  }>
  model_selected_steps: number
  policy_selected_steps: number
  refused_steps: number[]
  finished: boolean
  stopped_reason: string
  sandbox?: boolean
  decision: { decision: string; state: string; molecule_eligible: boolean; rule_ids: string[] }
  explanation: { text: string; source: string; model: string | null; violations: string[] }
  actions: AgentAction[]
}

function toRun(payload: AgentRunResponse): AgentRun {
  return {
    goal: payload.goal,
    modelEnabled: payload.model_enabled,
    model: payload.model,
    steps: (payload.steps ?? []).map((step) => ({
      step: step.step,
      action: step.action,
      args: step.args,
      selectedBy: step.selected_by === 'model' ? 'model' : 'policy',
      selectionNote: step.selection_note,
      observation: step.observation,
      refused: step.refused,
    })),
    modelSelectedSteps: payload.model_selected_steps,
    policySelectedSteps: payload.policy_selected_steps,
    refusedSteps: payload.refused_steps ?? [],
    finished: payload.finished,
    stoppedReason: payload.stopped_reason,
    sandbox: payload.sandbox ?? false,
    decision: {
      decision: payload.decision.decision,
      state: payload.decision.state,
      moleculeEligible: payload.decision.molecule_eligible,
      ruleIds: payload.decision.rule_ids ?? [],
    },
    explanation: {
      text: payload.explanation.text,
      source: payload.explanation.source === 'model' ? 'model' : 'template',
      model: payload.explanation.model,
      violations: payload.explanation.violations ?? [],
    },
    actions: payload.actions ?? OFFLINE_ACTIONS,
  }
}

/**
 * 등록된 가설 하나에 대해 에이전트 루프를 실행합니다.
 *
 * 실패를 삼키지 않습니다. 실행 기록은 "하네스가 이렇게 실행했다"는 주장이라
 * 서버가 없을 때 그럴듯한 대체본을 만들면 안 됩니다. 호출자가 오류를 표시합니다.
 */
export async function runAgent(hypothesisId: string, model?: string | null): Promise<AgentRun> {
  const query = new URLSearchParams({ hypothesis: hypothesisId })
  if (model) query.set('model', model)
  return toRun(await getJson<AgentRunResponse>(`/api/agent/run?${query.toString()}`, REQUEST_TIMEOUT_MS))
}

/**
 * 제출한 근거 패킷으로 같은 루프를 돌립니다.
 *
 * 하네스는 이 패킷을 저장하지도 승인하지도 않습니다. 승인 기록이 없으니 판정이
 * ADVANCE로 나와도 분자 게이트는 닫힌 채로 남습니다 — 입력창이 미검토 근거를
 * 승인된 집합으로 밀어 넣는 통로가 되지 않는 이유입니다.
 */
export async function runSandbox(packet: unknown, model?: string | null): Promise<AgentRun> {
  const response = await postJson<AgentRunResponse>('/api/agent/sandbox', { packet, model: model || null })
  return toRun(response)
}

interface ScenarioResponse {
  scenarios?: Scenario[]
}

/** 프리셋 시나리오. 하네스가 없으면 빈 목록이고, 화면은 버튼을 감춥니다. */
export async function listScenarios(): Promise<Scenario[]> {
  try {
    return (await getJson<ScenarioResponse>('/api/scenarios', MODELS_TIMEOUT_MS)).scenarios ?? []
  } catch {
    return []
  }
}

interface HypothesisResponse {
  hypotheses?: Array<{ hypothesis_id: string; target?: string }>
}

export async function listHypotheses(): Promise<string[]> {
  try {
    const payload = await getJson<HypothesisResponse>('/api/hypotheses', MODELS_TIMEOUT_MS)
    return (payload.hypotheses ?? []).map((item) => item.hypothesis_id)
  } catch {
    return []
  }
}
