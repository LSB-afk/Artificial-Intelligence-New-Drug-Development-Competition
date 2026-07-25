import { useCallback, useEffect, useState } from 'react'
import type { CreateRunInput, ExplainInput, RunSnapshot, RunSummary } from '../domain/contracts'
import { validateSnapshot } from '../domain/validateSnapshot'
import { harnessClient } from '../services/harnessClient'

function mergeRun(runs: RunSummary[], next: RunSummary) {
  return [next, ...runs.filter((run) => run.id !== next.id)]
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
}

export function useHarnessWorkspace() {
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [snapshot, setSnapshot] = useState<RunSnapshot | null>(null)
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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
        const initialRun = runList.find((run) => run.scenarioKind === 'evidence-review') ?? runList[0]
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
    selectRun,
    createRun,
    cancelRun,
    markReviewed,
    explainTarget,
  }
}
