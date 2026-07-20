import { initialSnapshots } from '../data/demoScenarios'
import type {
  CreateRunInput,
  HarnessClient,
  RunSnapshot,
  RunSummary,
  StageStatus,
} from '../domain/contracts'
import { validateSnapshot } from '../domain/validateSnapshot'

type SnapshotListener = (snapshot: RunSnapshot) => void

const clone = <T,>(value: T): T => structuredClone(value)
let runSequence = 0

function buildRunId(input: CreateRunInput) {
  const prefix = input.scenario === 'evidence-review' ? 'IBD' : 'UI'
  const stamp = new Date().toISOString().replace(/\D/g, '').slice(4, 17)
  runSequence += 1
  return `RUN-${prefix}-${stamp}-${String(runSequence).padStart(2, '0')}`
}

export class MockHarnessClient implements HarnessClient {
  private readonly snapshots = new Map<string, RunSnapshot>()
  private readonly listeners = new Map<string, Set<SnapshotListener>>()
  private readonly timers = new Map<string, number[]>()

  constructor() {
    initialSnapshots.forEach((snapshot) => this.snapshots.set(snapshot.run.id, clone(validateSnapshot(snapshot))))
  }

  async listRuns(): Promise<RunSummary[]> {
    return [...this.snapshots.values()]
      .map((snapshot) => clone(snapshot.run))
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
  }

  async getRun(runId: string): Promise<RunSnapshot> {
    const snapshot = this.snapshots.get(runId)
    if (!snapshot) throw new Error(`실행을 찾을 수 없습니다: ${runId}`)
    return clone(snapshot)
  }

  async createRun(input: CreateRunInput): Promise<RunSnapshot> {
    const template = initialSnapshots.find((item) => item.run.scenarioKind === input.scenario)
    if (!template) throw new Error(`지원하지 않는 시나리오입니다: ${input.scenario}`)

    const now = new Date()
    let runId = buildRunId(input)
    while (this.snapshots.has(runId)) runId = buildRunId(input)
    const snapshot = clone(template)
    snapshot.run = {
      ...snapshot.run,
      id: runId,
      createdAt: now.toISOString(),
      updatedAt: now.toISOString(),
      durationMs: 0,
      mode: input.mode,
      status: 'queued',
      reviewStatus: 'pending',
    }
    snapshot.stages = snapshot.stages.map((stage) => ({
      ...stage,
      status: 'queued',
      startedAt: undefined,
      endedAt: undefined,
      durationMs: undefined,
    }))
    snapshot.evidence = []
    snapshot.targets = []
    snapshot.molecules = []
    snapshot.events = []
    snapshot.failures = []
    snapshot.artifacts = snapshot.artifacts.map((artifact) => ({ ...artifact, available: false }))

    this.snapshots.set(runId, validateSnapshot(snapshot))
    this.emit(runId)
    this.simulate(runId, template)
    return clone(snapshot)
  }

  async cancelRun(runId: string): Promise<RunSnapshot> {
    const snapshot = this.requireSnapshot(runId)
    this.clearTimers(runId)
    snapshot.run.status = 'cancelled'
    snapshot.run.updatedAt = new Date().toISOString()
    snapshot.stages = snapshot.stages.map((stage) => {
      if (stage.status === 'running' || stage.status === 'queued') return { ...stage, status: 'cancelled' }
      return stage
    })
    this.emit(runId)
    return clone(snapshot)
  }

  async markReviewed(runId: string): Promise<RunSnapshot> {
    const snapshot = this.requireSnapshot(runId)
    snapshot.run.reviewStatus = 'approved'
    if (snapshot.run.status === 'awaiting_review') snapshot.run.status = 'completed_with_warnings'
    snapshot.run.updatedAt = new Date().toISOString()
    this.emit(runId)
    return clone(snapshot)
  }

  subscribe(runId: string, listener: SnapshotListener) {
    const listeners = this.listeners.get(runId) ?? new Set<SnapshotListener>()
    listeners.add(listener)
    this.listeners.set(runId, listeners)
    return () => {
      listeners.delete(listener)
      if (listeners.size === 0) this.listeners.delete(runId)
    }
  }

  private simulate(runId: string, template: RunSnapshot) {
    const terminalStatuses = template.stages.map((stage) => stage.status)
    const startedAt = Date.now()
    const timers: number[] = []

    const schedule = (callback: () => void, delay: number) => {
      timers.push(window.setTimeout(callback, delay))
    }

    schedule(() => {
      const snapshot = this.requireSnapshot(runId)
      snapshot.run.status = 'running'
      snapshot.stages[0] = { ...snapshot.stages[0], status: 'running', startedAt: new Date().toISOString() }
      this.emit(runId)
    }, 180)

    template.stages.forEach((templateStage, index) => {
      const finishDelay = 650 + index * 520
      schedule(() => {
        const snapshot = this.requireSnapshot(runId)
        if (snapshot.run.status === 'cancelled') return

        const status = terminalStatuses[index] as StageStatus
        snapshot.stages[index] = {
          ...templateStage,
          status,
          startedAt: snapshot.stages[index].startedAt ?? new Date().toISOString(),
          endedAt: new Date().toISOString(),
          durationMs: Date.now() - startedAt,
        }

        const next = snapshot.stages[index + 1]
        if (next) {
          snapshot.stages[index + 1] = {
            ...next,
            status: terminalStatuses[index + 1] === 'skipped' ? 'queued' : 'running',
            startedAt: new Date().toISOString(),
          }
        }

        snapshot.events = clone(template.events.filter((event) => {
          const stage = template.stages.find((item) => item.id === event.stageId)
          return stage ? stage.ordinal <= templateStage.ordinal : false
        }))
        snapshot.failures = clone(template.failures.filter((failure) => {
          const stage = template.stages.find((item) => item.id === failure.stageId)
          return stage ? stage.ordinal <= templateStage.ordinal : false
        }))
        if (template.run.scenarioKind === 'evidence-review' && templateStage.ordinal >= 3) {
          snapshot.evidence = clone(template.evidence)
          snapshot.targets = clone(template.targets)
        }
        if (template.run.scenarioKind === 'molecule-ui-fixture' && templateStage.ordinal >= 6) {
          snapshot.molecules = clone(template.molecules)
        }
        const producedArtifactIds = new Set(snapshot.stages.slice(0, index + 1).flatMap((stage) => stage.outputArtifactIds))
        snapshot.artifacts = template.artifacts.map((artifact) => ({
          ...clone(artifact),
          available: artifact.available && producedArtifactIds.has(artifact.id),
        }))
        snapshot.run.durationMs = Date.now() - startedAt
        snapshot.run.updatedAt = new Date().toISOString()

        if (index === template.stages.length - 1) {
          snapshot.run.status = template.run.status
          snapshot.evidence = clone(template.evidence)
          snapshot.targets = clone(template.targets)
          snapshot.molecules = clone(template.molecules)
          snapshot.artifacts = clone(template.artifacts)
          snapshot.run.headline = template.run.headline
          this.clearTimers(runId)
        }
        this.emit(runId)
      }, finishDelay)
    })

    this.timers.set(runId, timers)
  }

  private requireSnapshot(runId: string) {
    const snapshot = this.snapshots.get(runId)
    if (!snapshot) throw new Error(`실행을 찾을 수 없습니다: ${runId}`)
    return snapshot
  }

  private emit(runId: string) {
    const snapshot = this.requireSnapshot(runId)
    this.listeners.get(runId)?.forEach((listener) => listener(clone(snapshot)))
  }

  private clearTimers(runId: string) {
    this.timers.get(runId)?.forEach((timer) => window.clearTimeout(timer))
    this.timers.delete(runId)
  }
}
