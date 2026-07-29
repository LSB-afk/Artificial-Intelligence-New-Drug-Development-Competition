import { useCallback, useEffect, useRef, useState } from 'react'
import type {
  CreateRunInput,
  ExplainInput,
  RunSnapshot,
  RunSummary,
  ScenarioOption,
} from '../domain/contracts'
import { validateSnapshot } from '../domain/validateSnapshot'
import { harnessClient, isHarnessConnected } from '../services/harnessClient'

// 목록 순서는 어댑터가 정합니다. 갱신은 제자리에서 하고, 처음 보는 실행만
// 맨 앞에 붙입니다. 하네스 실행과 픽스처가 서로 자리를 뺏지 않게 하려는 것입니다.
function mergeRun(runs: RunSummary[], next: RunSummary) {
  const index = runs.findIndex((run) => run.id === next.id)
  if (index === -1) return [next, ...runs]
  const merged = [...runs]
  merged[index] = next
  return merged
}

export function useHarnessWorkspace() {
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [snapshot, setSnapshot] = useState<RunSnapshot | null>(null)
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [scenarioOptions, setScenarioOptions] = useState<ScenarioOption[]>([])
  const reconnectSeq = useRef(0)

  const acceptSnapshot = useCallback((candidate: RunSnapshot) => {
    const valid = validateSnapshot(candidate)
    setSnapshot(valid)
    setRuns((current) => mergeRun(current, valid.run))
    return valid
  }, [])

  /**
   * 하네스에 다시 물어 실행 목록과 시나리오를 갱신합니다.
   *
   * 연결 여부를 마운트 때 한 번만 확인하면, 콘솔을 열어 둔 채 서버를 켠 사용자는
   * 새로고침하기 전까지 계속 "하네스에 닿지 않습니다"를 보게 됩니다. 이미 보고
   * 있는 실행은 건드리지 않고 연결 상태만 다시 잽니다.
   */
  const reconnect = useCallback(async () => {
    // 모달을 빠르게 여닫으면 조회가 겹칩니다. 둘 다 같은 클라이언트 인스턴스를
    // 건드리므로, 늦게 끝난 응답이 먼저 끝난 응답을 덮어써야 화면과 연결 배지가
    // 서로 다른 시점을 가리키지 않습니다.
    const seq = (reconnectSeq.current += 1)
    try {
      const runList = await harnessClient.listRuns()
      if (seq !== reconnectSeq.current) return null
      setRuns(runList)
      setIsConnected(isHarnessConnected())
      // 목록 조회가 끝난 뒤에 물어야 하네스 연결 여부가 이미 정해져 있습니다.
      const options = await harnessClient.listScenarios()
      if (seq !== reconnectSeq.current) return null
      setScenarioOptions(options)
      return runList
    } catch (cause) {
      if (seq !== reconnectSeq.current) return null
      setError(cause instanceof Error ? cause.message : '실행 목록을 불러오지 못했습니다.')
      return null
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      const runList = await reconnect()
      if (cancelled || !runList) {
        if (!cancelled) setIsLoading(false)
        return
      }
      try {
        // 하네스가 계산한 실행이 있으면 그것부터 봅니다. 없으면 픽스처입니다.
        const initialRun = runList.find((run) => run.scenarioKind === 'harness-decision')
          ?? runList.find((run) => run.scenarioKind === 'evidence-review')
          ?? runList[0]
        if (initialRun) {
          const next = await harnessClient.getRun(initialRun.id)
          if (cancelled) return
          setSelectedRunId(initialRun.id)
          acceptSnapshot(next)
        }
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : '실행 목록을 불러오지 못했습니다.')
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }
    void load()
    return () => { cancelled = true }
  }, [acceptSnapshot, reconnect])

  useEffect(() => {
    if (!selectedRunId) return
    return harnessClient.subscribe(selectedRunId, (next) => {
      try {
        acceptSnapshot(next)
        setError(null)
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : '하네스 응답이 RunSnapshot 계약을 위반했습니다.')
      }
    })
  }, [acceptSnapshot, selectedRunId])

  const selectRun = useCallback(async (runId: string) => {
    setError(null)
    try {
      const next = await harnessClient.getRun(runId)
      acceptSnapshot(next)
      setSelectedRunId(runId)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '실행을 불러오지 못했습니다.')
    }
  }, [acceptSnapshot])

  const createRun = useCallback(async (input: CreateRunInput) => {
    setError(null)
    try {
      const next = acceptSnapshot(await harnessClient.createRun(input))
      setSelectedRunId(next.run.id)
      return next
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '새 실행 응답이 RunSnapshot 계약을 위반했습니다.')
      throw cause
    }
  }, [acceptSnapshot])

  const cancelRun = useCallback(async () => {
    if (!selectedRunId) return
    try {
      acceptSnapshot(await harnessClient.cancelRun(selectedRunId))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '취소 응답이 RunSnapshot 계약을 위반했습니다.')
    }
  }, [acceptSnapshot, selectedRunId])

  const markReviewed = useCallback(async () => {
    if (!selectedRunId) return
    try {
      acceptSnapshot(await harnessClient.markReviewed(selectedRunId))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '검토 응답이 RunSnapshot 계약을 위반했습니다.')
    }
  }, [acceptSnapshot, selectedRunId])

  // 해설은 스냅샷을 바꾸지 않습니다. 현재 실행을 근거로 문장만 만들어 돌려줍니다.
  const explainTarget = useCallback(async (input: ExplainInput) => {
    if (!snapshot) throw new Error('해설을 생성할 실행이 없습니다.')
    return harnessClient.explainTarget(input, snapshot)
  }, [snapshot])

  return {
    runs,
    scenarioOptions,
    snapshot,
    selectedRunId,
    isLoading,
    error,
    isConnected,
    reconnect,
    selectRun,
    createRun,
    cancelRun,
    markReviewed,
    explainTarget,
  }
}
