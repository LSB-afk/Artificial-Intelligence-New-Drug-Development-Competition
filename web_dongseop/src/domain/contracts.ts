export type TabId =
  | 'overview'
  | 'targets'
  | 'molecules'
  | 'failures'
  | 'audit'
  | 'report'
  | 'organization'
  | 'skills'
  | 'analysis-request'
  | 'agent-harness'
  | 'evidence-search'
  | 'recommendations'
  | 'roles'
  | 'reasoning'

export type DataMode = 'snapshot' | 'live'
/**
 * `harness-decision`은 파이썬 Agent 하네스가 실행해 `/api/workspace/runs`로 내려준
 * 실행입니다. 나머지 둘은 하네스가 없을 때도 콘솔이 동작하도록 남겨 둔 고정
 * 픽스처입니다. 이 구분은 화면에서 분류 배지로 그대로 드러납니다.
 */
export type ScenarioKind = 'evidence-review' | 'molecule-ui-fixture' | 'harness-decision'
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
  /** 출처 연관 점수. 하네스 패킷에 값이 없으면 null이며 화면은 공백을 표시합니다. */
  association: number | null
  tractability: 'High' | 'Medium' | 'Low' | 'Unknown'
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
  /** 픽스처는 `ScenarioKind`, 하네스 프리셋은 `/api/scenarios`가 준 preset id입니다. */
  id: string
  title: string
  description: string
  classification: DataClassification
  recommended?: boolean
  /**
   * 값이 있으면 파이썬 Agent 하네스가 허용된 행동과 규칙을 실행합니다. 없으면 브라우저 안의
   * 고정 픽스처를 복제할 뿐입니다. 모달의 "연결 방식"은 이 필드에서 파생됩니다.
   */
  harnessScenarioId?: string
}

export interface CreateRunInput {
  scenario: ScenarioKind
  mode: DataMode
  /** 있으면 하네스에 계산을 요청합니다. 없으면 픽스처 복제입니다. */
  harnessScenarioId?: string
}

/**
 * 해설 출처. `model`은 로컬 LLM이 작성하고 가드레일을 통과한 문장,
 * `template`은 결정론적으로 생성된 문장입니다. 두 경우 모두 사실은
 * 결정 엔진이 계산한 값이며 해설이 새로운 사실을 만들지 않습니다.
 */
export type ExplanationSource = 'model' | 'template'

export interface Explanation {
  targetSymbol: string
  text: string
  source: ExplanationSource
  model: string | null
  /** 모델 대신 템플릿을 쓴 이유. 모델 문장을 채택했으면 null입니다. */
  fallbackReason: string | null
  /** 가드레일이 잡아낸 위반 항목. 비어 있으면 검사를 통과했습니다. */
  violations: string[]
  decision: string
  ruleIds: string[]
  evidenceIds: string[]
  generatedAt: string
}

export interface ExplainInput {
  targetSymbol: string
  disease: string
}

export interface HarnessClient {
  listRuns(): Promise<RunSummary[]>
  /** 모달이 제시할 시나리오. 하네스가 닿으면 프리셋이 앞에 붙습니다. */
  listScenarios(): Promise<ScenarioOption[]>
  getRun(runId: string): Promise<RunSnapshot>
  createRun(input: CreateRunInput): Promise<RunSnapshot>
  cancelRun(runId: string): Promise<RunSnapshot>
  markReviewed(runId: string): Promise<RunSnapshot>
  explainTarget(input: ExplainInput, snapshot: RunSnapshot): Promise<Explanation>
  subscribe(runId: string, listener: (snapshot: RunSnapshot) => void): () => void
}
