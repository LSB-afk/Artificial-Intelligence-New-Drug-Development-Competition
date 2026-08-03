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
 * 파이썬 하네스(:8765)의 실행 API를 앞에 두고, 나머지는 모의
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
 * 새 계산 실행은 서버 메모리에만 잠시 유지됩니다. 브라우저는 실행이 끝날 때까지
 * 상태를 조회하고, 취소는 서버의 실제 Agent 작업에 전달합니다. 검토 표시는 아직
 * 브라우저 세션에만 남으며 어떤 동작도 과학 registry를 변경하지 않습니다.
 */

const REQUEST_TIMEOUT_MS = 8_000
const POLL_INTERVAL_MS = 200
const activeRunStatuses = new Set(['queued', 'running'])

function isActive(snapshot: RunSnapshot) {
  return activeRunStatuses.has(snapshot.run.status)
}

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
  /** 시나리오를 눌러 만든 휘발성 실행의 최신 스냅샷. */
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
      // 서버가 다시 응답했는데 목록에 없다면 재시작 또는 보관 한도 만료로 사라진
      // 휘발성 실행입니다. 오프라인 동안에는 보존하되, 서버의 최신 목록을 받은
      // 뒤까지 과거 실행을 실제 실행처럼 남겨 두지는 않습니다.
      for (const runId of this.sandboxRuns.keys()) {
        if (!this.harnessIds.has(runId)) this.sandboxRuns.delete(runId)
      }
    }
    const fixtures = await this.fallback.listRuns()
    const sandbox = [...this.sandboxRuns.values()].map((snapshot) => structuredClone(snapshot.run))
    // 연결된 서버의 요약을 우선하고 같은 휘발성 실행이 로컬 캐시에도 있을 때는
    // 한 번만 표시합니다. 서버가 잠시 끊기면 로컬 최신 상태는 그대로 남습니다.
    const seen = new Set<string>()
    return [...harnessSummaries, ...sandbox, ...fixtures].filter((run) => {
      if (seen.has(run.id)) return false
      seen.add(run.id)
      return true
    })
  }

  async getRun(runId: string): Promise<RunSnapshot> {
    const sandboxed = this.sandboxRuns.get(runId)
    if (sandboxed && !isActive(sandboxed)) return structuredClone(sandboxed)
    // 픽스처 실행까지 백엔드에 물어보지 않습니다. 소유자가 누구인지는 목록에서 이미 정해졌습니다.
    if (!this.harnessIds.has(runId)) return this.fallback.getRun(runId)

    const cached = this.cache.get(runId)
    if (cached && !isActive(cached)) return structuredClone(cached)

    const snapshot = await requestJson<RunSnapshot>(`/api/workspace/runs/${encodeURIComponent(runId)}`)
    if (snapshot?.run?.id !== runId) {
      throw new Error(`하네스가 실행을 돌려주지 않았습니다: ${runId}`)
    }
    // 계약 위반은 조용히 넘기지 않습니다. 잘못된 모양이 그럴듯하게 그려지는 것보다
    // 오류로 드러나는 편이 낫습니다.
    const valid = validateSnapshot(snapshot)
    this.cache.set(runId, valid)
    if (sandboxed || isActive(valid) || runId.startsWith('LIVE-')) this.sandboxRuns.set(runId, valid)
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
    this.harnessIds.add(valid.run.id)
    this.sandboxRuns.set(valid.run.id, valid)
    return structuredClone(valid)
  }

  async cancelRun(runId: string): Promise<RunSnapshot> {
    if (this.isHarnessOwned(runId)) {
      const current = this.sandboxRuns.get(runId) ?? this.cache.get(runId)
      if (current && isActive(current)) {
        const snapshot = await requestJson<RunSnapshot>(`/api/workspace/runs/${encodeURIComponent(runId)}/cancel`, {
          method: 'POST',
        })
        if (!snapshot?.run?.id) throw new Error(lastErrorMessage ?? `하네스 실행을 취소하지 못했습니다: ${runId}`)
        const valid = validateSnapshot(snapshot)
        this.sandboxRuns.set(runId, valid)
        this.cache.set(runId, valid)
        return structuredClone(valid)
      }
      return this.getRun(runId)
    }
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
    if (!this.isHarnessOwned(runId)) return this.fallback.subscribe(runId, listener)

    const known = this.sandboxRuns.get(runId) ?? this.cache.get(runId)
    if (known && !isActive(known)) return () => {}

    let disposed = false
    let inFlight = false
    let timer: number | undefined

    const stop = () => {
      disposed = true
      if (timer !== undefined) window.clearInterval(timer)
    }
    const poll = async () => {
      if (disposed || inFlight) return
      const latest = this.sandboxRuns.get(runId) ?? this.cache.get(runId)
      if ((latest && !isActive(latest)) || !this.isHarnessOwned(runId)) {
        stop()
        return
      }
      inFlight = true
      try {
        const snapshot = await requestJson<RunSnapshot>(`/api/workspace/runs/${encodeURIComponent(runId)}`)
        if (disposed || snapshot?.run?.id !== runId) return
        const valid = validateSnapshot(snapshot)
        this.sandboxRuns.set(runId, valid)
        this.cache.set(runId, valid)
        listener(structuredClone(valid))
        if (!isActive(valid)) stop()
      } catch {
        // 계약 오류와 일시적인 연결 실패는 다음 조회에서 다시 확인합니다.
        // 최종적으로 표시할 오류는 상태 훅의 listener 검증이 담당합니다.
      } finally {
        inFlight = false
      }
    }

    timer = window.setInterval(() => { void poll() }, POLL_INTERVAL_MS)
    void poll()
    return stop
  }
}
