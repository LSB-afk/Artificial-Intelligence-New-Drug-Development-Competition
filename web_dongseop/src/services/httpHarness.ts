import type {
  CreateRunInput,
  ExplainInput,
  Explanation,
  HarnessClient,
  RunSnapshot,
  RunSummary,
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

async function getJson<T>(path: string): Promise<T | null> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  try {
    const response = await fetch(path, { signal: controller.signal })
    if (!response.ok) return null
    return (await response.json()) as T
  } catch {
    return null
  } finally {
    window.clearTimeout(timer)
  }
}

export class HttpHarnessClient implements HarnessClient {
  /** 마지막 목록 조회에서 하네스가 소유권을 주장한 실행 id. */
  private harnessIds = new Set<string>()
  private readonly cache = new Map<string, RunSnapshot>()
  private harnessReachable = false

  constructor(private readonly fallback: HarnessClient) {}

  /** 마지막 목록 조회에서 하네스에 닿았는지. 상태 표시에만 씁니다. */
  get isConnected() {
    return this.harnessReachable
  }

  async listRuns(): Promise<RunSummary[]> {
    const payload = await getJson<{ runs: RunSummary[] }>('/api/workspace/runs')
    const harnessSummaries = payload?.runs ?? []
    this.harnessReachable = Array.isArray(payload?.runs)
    this.harnessIds = new Set(harnessSummaries.map((run) => run.id))
    this.cache.clear()
    const fixtures = await this.fallback.listRuns()
    return [...harnessSummaries, ...fixtures]
  }

  async getRun(runId: string): Promise<RunSnapshot> {
    // 픽스처 실행까지 백엔드에 물어보지 않습니다. 소유자가 누구인지는 목록에서 이미 정해졌습니다.
    if (!this.harnessIds.has(runId)) return this.fallback.getRun(runId)

    const cached = this.cache.get(runId)
    if (cached) return structuredClone(cached)

    const snapshot = await getJson<RunSnapshot>(`/api/workspace/runs/${encodeURIComponent(runId)}`)
    if (snapshot?.run?.id !== runId) {
      throw new Error(`하네스가 실행을 돌려주지 않았습니다: ${runId}`)
    }
    // 계약 위반은 조용히 넘기지 않습니다. 잘못된 모양이 그럴듯하게 그려지는 것보다
    // 오류로 드러나는 편이 낫습니다.
    const valid = validateSnapshot(snapshot)
    this.cache.set(runId, valid)
    return structuredClone(valid)
  }

  createRun(input: CreateRunInput): Promise<RunSnapshot> {
    return this.fallback.createRun(input)
  }

  async cancelRun(runId: string): Promise<RunSnapshot> {
    // 계산된 실행은 이미 끝난 결정론적 재생이라 취소할 진행 상태가 없습니다.
    if (this.harnessIds.has(runId)) return this.getRun(runId)
    return this.fallback.cancelRun(runId)
  }

  async markReviewed(runId: string): Promise<RunSnapshot> {
    if (!this.harnessIds.has(runId)) return this.fallback.markReviewed(runId)
    // 과학 plane은 읽기 전용입니다. 검토 표시는 이 브라우저 세션에만 남습니다.
    const current = await this.getRun(runId)
    const reviewed: RunSnapshot = { ...current, run: { ...current.run, reviewStatus: 'approved' } }
    this.cache.set(runId, reviewed)
    return structuredClone(reviewed)
  }

  explainTarget(input: ExplainInput, snapshot: RunSnapshot): Promise<Explanation> {
    return this.fallback.explainTarget(input, snapshot)
  }

  subscribe(runId: string, listener: (snapshot: RunSnapshot) => void): () => void {
    // 계산된 실행은 결정론적이고 즉시 끝나므로 구독할 진행 상태가 없습니다.
    if (this.harnessIds.has(runId)) return () => {}
    return this.fallback.subscribe(runId, listener)
  }
}
