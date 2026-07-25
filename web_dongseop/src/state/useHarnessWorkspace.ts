import { useCallback, useEffect, useState } from 'react'
import type { CreateRunInput, ExplainInput, RunSnapshot, RunSummary } from '../domain/contracts'
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

  const acceptSnapshot = useCallback((candidate: RunSnapshot) => {
    const valid = validateSnapshot(candidate)
    setSnapshot(valid)
    setRuns((current) => mergeRun(current, valid.run))
    return valid
  }, [])

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const runList = await harnessClient.listRuns()
        if (cancelled) return
        setRuns(runList)
        setIsConnected(isHarnessConnected())
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
  }, [acceptSnapshot])

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
    snapshot,
    selectedRunId,
    isLoading,
    error,
    isConnected,
    selectRun,
    createRun,
    cancelRun,
    markReviewed,
    explainTarget,
  }
}
