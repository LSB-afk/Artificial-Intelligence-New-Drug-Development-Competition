export type TabId =
  | 'overview'
  | 'targets'
  | 'molecules'
  | 'failures'
  | 'audit'
  | 'report'

export type DataMode = 'snapshot' | 'live'
export type ScenarioKind = 'evidence-review' | 'molecule-ui-fixture'
export type DataClassification = 'source_snapshot' | 'computed' | 'synthetic'

export type RunStatus =
  | 'queued'
  | 'running'
  | 'awaiting_review'
  | 'completed'
  | 'completed_with_warnings'
  | 'failed'
  | 'cancelled'

export type StageStatus =
  | 'queued'
  | 'running'
  | 'completed'
  | 'warning'
  | 'failed'
  | 'skipped'
  | 'blocked'
  | 'cancelled'

export type Decision = 'review' | 'rejected' | 'insufficient' | 'reference_only' | 'demo_only'
export type ReviewStatus = 'pending' | 'approved' | 'changes_requested'

export interface RunSummary {
  id: string
  title: string
  disease: string
  diseaseId: string
  createdAt: string
  updatedAt: string
  durationMs: number
  status: RunStatus
  mode: DataMode
  scenarioKind: ScenarioKind
  classification: DataClassification
  reviewStatus: ReviewStatus
  headline: string
}

export interface ToolCall {
  name: string
  version: string
  modelSource?: string
  observedAt?: string
  classification: DataClassification
}

export interface StageSnapshot {
  id: string
  ordinal: number
  label: string
  agent: string
  status: StageStatus
  startedAt?: string
  endedAt?: string
  durationMs?: number
  summary: string
  output: string
  retryCount: number
  inputArtifactIds: string[]
  outputArtifactIds: string[]
  toolCall?: ToolCall
  error?: string
}

export interface EvidenceSource {
  id: string
  title: string
  detail: string
  source: string
  sourceId: string
  observedAt: string
  polarity: 'supporting' | 'conflicting' | 'neutral'
  classification: DataClassification
  href: string
}

export interface ScoreFactor {
  id: string
  label: string
  impact: number
  evidenceIds: string[]
}

export interface TargetSnapshot {
  symbol: string
  name: string
  rank: number
  association: number
  tractability: 'High' | 'Medium' | 'Low'
  assay: string
  clinical: string
  scoreBefore: number
  scoreAfter: number
  decision: Decision
  rationale: string
  caution: string
  evidenceIds: string[]
  scoreFactors: ScoreFactor[]
}

export type MoleculeStructureVariant = 'candidate-a' | 'candidate-b' | 'candidate-c' | 'candidate-d'

export interface MoleculeSnapshot {
  id: string
  name: string
  origin: 'Generated' | 'Reference'
  structure: MoleculeStructureVariant
  smiles: string
  activityProxy: number
  qed: number
  logP: number
  tpsa: number
  herg: 'Low' | 'Medium' | 'High'
  ames: 'Low' | 'Medium' | 'High'
  synthesisProxy: number
  synthesisMethod: 'SA proxy' | 'Not run'
  decision: Decision
  reason: string
  classification: DataClassification
}

export interface FailureRecord {
  id: string
  subject: string
  kind: 'Target' | 'Molecule' | 'Tool' | 'Policy'
  stageId: string
  stage: string
  reason: string
  nextAction: string
  severity: 'warning' | 'critical' | 'info'
  time: string
}

export interface RunEvent {
  id: string
  occurredAt: string
  agent: string
  tool: string
  toolVersion?: string
  status: 'success' | 'warning' | 'failed' | 'decision' | 'skipped'
  title: string
  detail: string
  durationMs?: number
  sourceIds: string[]
  stageId: string
}

export interface Artifact {
  id: string
  name: string
  mimeType: string
  classification: DataClassification
  available: boolean
  description: string
  content?: string
}

export interface SafetyNotice {
  id: string
  level: 'info' | 'warning'
  title: string
  detail: string
}

export interface RunSnapshot {
  run: RunSummary
  stages: StageSnapshot[]
  evidence: EvidenceSource[]
  targets: TargetSnapshot[]
  molecules: MoleculeSnapshot[]
  failures: FailureRecord[]
  events: RunEvent[]
  artifacts: Artifact[]
  safetyNotices: SafetyNotice[]
}

export interface ScenarioOption {
  id: ScenarioKind
  title: string
  description: string
  classification: DataClassification
  recommended?: boolean
}

export interface CreateRunInput {
  scenario: ScenarioKind
  mode: DataMode
}

export interface HarnessClient {
  listRuns(): Promise<RunSummary[]>
  getRun(runId: string): Promise<RunSnapshot>
  createRun(input: CreateRunInput): Promise<RunSnapshot>
  cancelRun(runId: string): Promise<RunSnapshot>
  markReviewed(runId: string): Promise<RunSnapshot>
  subscribe(runId: string, listener: (snapshot: RunSnapshot) => void): () => void
}
