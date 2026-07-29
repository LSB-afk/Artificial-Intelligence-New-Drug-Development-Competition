import type {
  CreateRunInput,
  DataClassification,
  ExplainInput,
  Explanation,
  HarnessClient,
  RunSnapshot,
  RunSummary,
  ScenarioOption,
} from '../domain/contracts'
import { validateSnapshot } from '../domain/validateSnapshot'

/**
 * 파이썬 하네스(:8765)의 읽기 전용 실행 API를 앞에 두고, 나머지는 모의
 * 어댑터에 위임하는 클라이언트.
 *
 * 하네스가 살아 있으면 `/api/workspace/runs`가 내려준 **계산된** 실행이 목록
 * 맨 위에 오고, 하네스를 끄면 그 실행은 목록에서 사라집니다. 화면이 무엇을
 * 근거로 그려졌는지 그 자체로 드러나게 하려는 의도입니다.
 *
 * 고정 픽스처 실행은 지우지 않고 그대로 둡니다. 하네스 없이도 콘솔을 열어야
 * 하고, 분자 비교 화면처럼 아직 하네스가 만들지 못하는 상태는 픽스처로만
 * 확인할 수 있기 때문입니다. 둘은 `classification` 배지로 구분됩니다.
 *
 * 하네스는 과학 plane을 변경하지 않으므로 생성·취소·검토 처리는 모의 어댑터가
 * 계속 담당합니다. 계산된 실행에 대해서는 이 동작들이 로컬 표시 상태만 바꿉니다.
 */

const REQUEST_TIMEOUT_MS = 8_000

/** 하네스가 준 실패 사유. 없으면 null이고, 그때만 호출부가 문장을 지어냅니다. */
let lastErrorMessage: string | null = null

async function requestJson<T>(path: string, init?: RequestInit): Promise<T | null> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  lastErrorMessage = null
  try {
    const response = await fetch(path, { ...init, signal: controller.signal })
    if (!response.ok) {
      // 서버는 어떤 필드가 왜 거부됐는지 이미 적어 보냅니다. 그걸 버리면 사용자는 고칠 수 없습니다.
      const body = await response.json().catch(() => null)
      lastErrorMessage = typeof body?.message === 'string' ? body.message : null
      return null
    }
    return (await response.json()) as T
  } catch {
    return null
  } finally {
    window.clearTimeout(timer)
  }
}

/** 하네스 프리셋 하나를 모달이 그릴 수 있는 선택지로 옮깁니다. */
function toScenarioOption(preset: { id: string; label: string; expectation: string; note: string }): ScenarioOption {
  return {
    id: preset.id,
    title: preset.label,
    // 어떤 판정이 나올지를 먼저 보여야 규칙이 실행됐다는 게 확인 가능합니다.
    description: `${preset.expectation} — ${preset.note}`,
    classification: 'computed' as DataClassification,
    harnessScenarioId: preset.id,
  }
}

export class HttpHarnessClient implements HarnessClient {
  /** 마지막 목록 조회에서 하네스가 소유권을 주장한 실행 id. */
  private harnessIds = new Set<string>()
  private readonly cache = new Map<string, RunSnapshot>()
  /**
   * 시나리오를 눌러 만든 실행. 서버가 저장하지 않으므로 목록 조회로는 다시
   * 찾을 수 없고, 따라서 `listRuns`가 캐시를 비울 때 함께 지워지면 안 됩니다.
   */
  private readonly sandboxRuns = new Map<string, RunSnapshot>()
  private harnessReachable = false

  constructor(private readonly fallback: HarnessClient) {}

  /** 마지막 목록 조회에서 하네스에 닿았는지. 상태 표시에만 씁니다. */
  get isConnected() {
    return this.harnessReachable
  }

  /**
   * 이 실행을 픽스처 어댑터가 아니라 하네스가 만들었는지. `getRun`은 두 출처를
   * 서로 다르게 읽어야 해서 직접 분기하고, 나머지는 전부 여기를 지납니다.
   */
  private isHarnessOwned(runId: string) {
    return this.harnessIds.has(runId) || this.sandboxRuns.has(runId)
  }

  async listRuns(): Promise<RunSummary[]> {
    const payload = await requestJson<{ runs: RunSummary[] }>('/api/workspace/runs')
    const harnessSummaries = payload?.runs ?? []
    this.harnessReachable = Array.isArray(payload?.runs)
    // 닿지 못한 것은 "실행이 없다"가 아닙니다. 소유권까지 지우면 사용자가 지금 보고
    // 있는 계산 실행이 픽스처 어댑터로 넘어가고, 검토 처리를 누르는 순간 "실행을
    // 찾을 수 없습니다"가 됩니다. 목록 조회가 마운트 때 한 번뿐이던 시절에는 이
    // 상태가 만들어질 수 없었지만, 이제는 모달을 열 때마다 다시 조회합니다.
    if (this.harnessReachable) {
      this.harnessIds = new Set(harnessSummaries.map((run) => run.id))
      this.cache.clear()
    }
    const fixtures = await this.fallback.listRuns()
    const sandbox = [...this.sandboxRuns.values()].map((snapshot) => structuredClone(snapshot.run))
    return [...sandbox, ...harnessSummaries, ...fixtures]
  }

  async getRun(runId: string): Promise<RunSnapshot> {
    const sandboxed = this.sandboxRuns.get(runId)
    if (sandboxed) return structuredClone(sandboxed)
    // 픽스처 실행까지 백엔드에 물어보지 않습니다. 소유자가 누구인지는 목록에서 이미 정해졌습니다.
    if (!this.harnessIds.has(runId)) return this.fallback.getRun(runId)

    const cached = this.cache.get(runId)
    if (cached) return structuredClone(cached)

    const snapshot = await requestJson<RunSnapshot>(`/api/workspace/runs/${encodeURIComponent(runId)}`)
    if (snapshot?.run?.id !== runId) {
      throw new Error(`하네스가 실행을 돌려주지 않았습니다: ${runId}`)
    }
    // 계약 위반은 조용히 넘기지 않습니다. 잘못된 모양이 그럴듯하게 그려지는 것보다
    // 오류로 드러나는 편이 낫습니다.
    const valid = validateSnapshot(snapshot)
    this.cache.set(runId, valid)
    return structuredClone(valid)
  }

  async listScenarios(): Promise<ScenarioOption[]> {
    const payload = await requestJson<{ scenarios: Parameters<typeof toScenarioOption>[0][] }>('/api/scenarios')
    const presets = (payload?.scenarios ?? []).map(toScenarioOption)
    const fixtures = await this.fallback.listScenarios()
    // 계산되는 시나리오를 먼저 놓고, 첫 항목을 권장으로 표시합니다. 하네스가
    // 꺼져 있으면 픽스처가 그 자리를 가져가므로 모달은 늘 뭔가를 제시합니다.
    const options = [...presets, ...fixtures].map((option) => ({ ...option, recommended: false }))
    if (options[0]) options[0] = { ...options[0], recommended: true }
    return options
  }

  async createRun(input: CreateRunInput): Promise<RunSnapshot> {
    if (!input.harnessScenarioId) return this.fallback.createRun(input)

    const snapshot = await requestJson<RunSnapshot>('/api/workspace/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario: input.harnessScenarioId }),
    })
    if (!snapshot?.run?.id) {
      throw new Error(lastErrorMessage ?? `하네스가 시나리오를 실행하지 못했습니다: ${input.harnessScenarioId}`)
    }
    const valid = validateSnapshot(snapshot)
    this.sandboxRuns.set(valid.run.id, valid)
    return structuredClone(valid)
  }

  async cancelRun(runId: string): Promise<RunSnapshot> {
    // 계산된 실행은 이미 끝난 결정론적 재생이라 취소할 진행 상태가 없습니다.
    if (this.isHarnessOwned(runId)) return this.getRun(runId)
    return this.fallback.cancelRun(runId)
  }

  async markReviewed(runId: string): Promise<RunSnapshot> {
    if (!this.isHarnessOwned(runId)) return this.fallback.markReviewed(runId)
    // 과학 plane은 읽기 전용입니다. 검토 표시는 이 브라우저 세션에만 남습니다.
    const current = await this.getRun(runId)
    const reviewed: RunSnapshot = { ...current, run: { ...current.run, reviewStatus: 'approved' } }
    ;(this.sandboxRuns.has(runId) ? this.sandboxRuns : this.cache).set(runId, reviewed)
    return structuredClone(reviewed)
  }

  explainTarget(input: ExplainInput, snapshot: RunSnapshot): Promise<Explanation> {
    return this.fallback.explainTarget(input, snapshot)
  }

  subscribe(runId: string, listener: (snapshot: RunSnapshot) => void): () => void {
    // 계산된 실행은 결정론적이고 즉시 끝나므로 구독할 진행 상태가 없습니다.
    if (this.isHarnessOwned(runId)) return () => {}
    return this.fallback.subscribe(runId, listener)
  }
}
