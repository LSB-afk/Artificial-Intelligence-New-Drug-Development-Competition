export type AgentStatus = 'active' | 'guarded' | 'planned'
export type SkillStatus = 'ready' | 'guarded' | 'planned'
export type SkillCategory = '질병·근거' | '타깃 의사결정' | '분자 설계' | '검증·거버넌스'

export interface H2LAgent {
  id: string
  name: string
  role: string
  team: string
  mission: string
  status: AgentStatus
  parentId: string | null
  skillIds: string[]
  outputs: string[]
}

export interface H2LSkill {
  id: string
  name: string
  description: string
  category: SkillCategory
  status: SkillStatus
  ownerIds: string[]
  sourcePath: string
  version: string
  capabilities: string[]
  guardrail: string
  accent: string
}

export const h2lAgents: H2LAgent[] = [
  {
    id: 'research-director',
    name: 'H2L Research Director',
    role: 'Supervisor · 최종 연구 책임',
    team: 'Executive',
    mission: '질병 질의부터 보고서까지 상태 전이, 예산, 인간 승인과 중단 조건을 통제합니다.',
    status: 'active',
    parentId: null,
    skillIds: ['decide-target-eligibility', 'generate-audit-report'],
    outputs: ['run plan', 'approval gate', 'final decision'],
  },
  {
    id: 'target-intelligence-lead',
    name: 'Target Intelligence Lead',
    role: '타깃 근거 조직 리드',
    team: 'Target Intelligence',
    mission: '질병 정규화, 근거 수집, 반증 비평을 하나의 타깃 결정 패키지로 조율합니다.',
    status: 'active',
    parentId: 'research-director',
    skillIds: ['collect-target-evidence', 'challenge-target-hypothesis', 'decide-target-eligibility'],
    outputs: ['target evidence package', 'ADVANCE/HOLD/REJECT'],
  },
  {
    id: 'disease-normalizer',
    name: 'Disease Normalizer',
    role: '질병·적응증 정규화',
    team: 'Target Intelligence',
    mission: '질병명과 동의어를 표준 ID 후보로 변환하고 모호성을 다음 단계에 전달합니다.',
    status: 'active',
    parentId: 'target-intelligence-lead',
    skillIds: ['normalize-disease-query'],
    outputs: ['normalized disease', 'ambiguity flags'],
  },
  {
    id: 'evidence-scout',
    name: 'Evidence Scout',
    role: '공개 DB·문헌 근거 수집',
    team: 'Target Intelligence',
    mission: 'Open Targets, ChEMBL, 임상시험과 원 논문에서 지지·반증 근거를 함께 수집합니다.',
    status: 'active',
    parentId: 'target-intelligence-lead',
    skillIds: ['collect-target-evidence', 'manage-evidence-snapshots'],
    outputs: ['evidence records', 'source manifest'],
  },
  {
    id: 'evidence-critic',
    name: 'Evidence Critic',
    role: '적응증별 반증·결정 권고',
    team: 'Target Intelligence',
    mission: '승인 적응증 불일치와 실패 임상을 우선 검토해 유망한 가설도 기각할 수 있습니다.',
    status: 'guarded',
    parentId: 'target-intelligence-lead',
    skillIds: ['challenge-target-hypothesis', 'decide-target-eligibility'],
    outputs: ['contradiction ledger', 'decision rationale'],
  },
  {
    id: 'molecule-discovery-lead',
    name: 'Molecule Discovery Lead',
    role: '분자 루프 책임',
    team: 'Molecule Discovery',
    mission: '인간 승인까지 받은 타깃만 seed 검색과 제한된 분자 최적화 단계로 전달합니다.',
    status: 'guarded',
    parentId: 'research-director',
    skillIds: ['retrieve-seed-ligands', 'optimize-eligible-molecules'],
    outputs: ['eligible seed set', 'ranked candidates'],
  },
  {
    id: 'molecule-optimizer',
    name: 'Molecule Optimizer',
    role: '구조 생성·다목적 순위화',
    team: 'Molecule Discovery',
    mission: 'RDKit과 명시적 활성 근거 유형을 이용해 재현 가능한 후보 생성과 Pareto 순위를 수행합니다.',
    status: 'planned',
    parentId: 'molecule-discovery-lead',
    skillIds: ['retrieve-seed-ligands', 'optimize-eligible-molecules'],
    outputs: ['candidate table', 'rejection lineage'],
  },
  {
    id: 'safety-synthesis-verifier',
    name: 'Safety & Synthesis Verifier',
    role: 'ADMET·합성성 검증',
    team: 'Molecule Discovery',
    mission: 'ADMET-AI와 2단 합성성 게이트를 적용하고 미실행·실패 지표를 숨기지 않습니다.',
    status: 'planned',
    parentId: 'molecule-discovery-lead',
    skillIds: ['verify-admet-synthesis'],
    outputs: ['risk table', 'feasibility signal'],
  },
  {
    id: 'governance-lead',
    name: 'Governance & Reporting Lead',
    role: '재현성·감사·보고 책임',
    team: 'Governance',
    mission: '근거 스냅샷, 골든 케이스, 실패 기록과 최종 보고서의 추적 가능성을 보장합니다.',
    status: 'active',
    parentId: 'research-director',
    skillIds: ['manage-evidence-snapshots', 'evaluate-h2l-runs', 'generate-audit-report'],
    outputs: ['audit package', 'evaluation summary'],
  },
  {
    id: 'audit-eval-agent',
    name: 'Audit & Eval Agent',
    role: '스냅샷·골든 케이스 검증',
    team: 'Governance',
    mission: '결정 상태를 바꾸지 않는 읽기 전용 평가 plane에서 안전 불변식과 회귀를 확인합니다.',
    status: 'active',
    parentId: 'governance-lead',
    skillIds: ['manage-evidence-snapshots', 'evaluate-h2l-runs'],
    outputs: ['snapshot manifest', 'eval results'],
  },
  {
    id: 'report-agent',
    name: 'Report Agent',
    role: '판단·한계·출처 보고',
    team: 'Governance',
    mission: '지지와 반증, 중단 사유, proxy 한계와 인간 검토 상태를 연구자용 보고서로 구성합니다.',
    status: 'active',
    parentId: 'governance-lead',
    skillIds: ['generate-audit-report'],
    outputs: ['decision report', 'citation appendix'],
  },
]

export const h2lSkills: H2LSkill[] = [
  {
    id: 'normalize-disease-query',
    name: '질병 질의 정규화',
    description: '질병명·약어·동의어를 표준 질병 ID 후보로 변환하고 모호성을 보존합니다.',
    category: '질병·근거',
    status: 'ready',
    ownerIds: ['disease-normalizer'],
    sourcePath: '03_에이전트/skills/normalize-disease-query/SKILL.md',
    version: 'v1.0.0',
    capabilities: ['Open Targets 검색 후보화', '상·하위 적응증 구분', '정규화 provenance 기록'],
    guardrail: '불확실한 ID를 추측하거나 자동 확정하지 않습니다.',
    accent: '#2f6fe4',
  },
  {
    id: 'collect-target-evidence',
    name: '타깃 근거 수집',
    description: '지지·반증 근거를 Open Targets, ChEMBL, 임상시험과 원 논문에서 함께 수집합니다.',
    category: '질병·근거',
    status: 'ready',
    ownerIds: ['target-intelligence-lead', 'evidence-scout'],
    sourcePath: '03_에이전트/skills/collect-target-evidence/SKILL.md',
    version: 'v1.0.0',
    capabilities: ['association·tractability 분리', '적응증별 임상 수집', 'support·contradiction 분류'],
    guardrail: 'association score를 confidence로 표현하지 않습니다.',
    accent: '#0b8f82',
  },
  {
    id: 'challenge-target-hypothesis',
    name: '타깃 가설 반증',
    description: '유망한 가설을 적응증 불일치, 실패 임상, 안전성과 데이터 편향으로 공격합니다.',
    category: '타깃 의사결정',
    status: 'ready',
    ownerIds: ['target-intelligence-lead', 'evidence-critic'],
    sourcePath: '03_에이전트/skills/challenge-target-hypothesis/SKILL.md',
    version: 'v1.0.0',
    capabilities: ['contradiction-first 검색', '최초 전제와 반증 연결', '가설 수정 권고'],
    guardrail: '다른 적응증의 승인을 현재 질환의 성공 근거로 이전하지 않습니다.',
    accent: '#d4514a',
  },
  {
    id: 'decide-target-eligibility',
    name: '타깃 진입 판정',
    description: '근거 패키지에 결정 규칙을 적용해 ADVANCE·HOLD·REJECT와 분자 진입 여부를 확정합니다.',
    category: '타깃 의사결정',
    status: 'guarded',
    ownerIds: ['research-director', 'target-intelligence-lead', 'evidence-critic'],
    sourcePath: '03_에이전트/skills/decide-target-eligibility/SKILL.md',
    version: 'v1.0.0',
    capabilities: ['결정 규칙 적용', '인간 승인 게이트', '하위 단계 강제 차단'],
    guardrail: 'ADVANCE와 인간 승인 없이는 molecule_eligible을 허용하지 않습니다.',
    accent: '#7a58c9',
  },
  {
    id: 'retrieve-seed-ligands',
    name: '시드 리간드 검색',
    description: '적격 타깃의 ChEMBL assay와 측정 활성 데이터를 품질 기준으로 선별합니다.',
    category: '분자 설계',
    status: 'planned',
    ownerIds: ['molecule-discovery-lead', 'molecule-optimizer'],
    sourcePath: '03_에이전트/skills/retrieve-seed-ligands/SKILL.md',
    version: 'v1.0.0',
    capabilities: ['assay confidence 필터', 'endpoint·unit 정규화', 'seed 제외 ledger'],
    guardrail: '기각 타깃과 검증되지 않은 activity count를 치료적 seed로 사용하지 않습니다.',
    accent: '#2474a6',
  },
  {
    id: 'optimize-eligible-molecules',
    name: '적격 분자 최적화',
    description: '승인된 타깃에서만 구조를 생성하고 활성 근거 유형과 Pareto 목표를 보존합니다.',
    category: '분자 설계',
    status: 'planned',
    ownerIds: ['molecule-discovery-lead', 'molecule-optimizer'],
    sourcePath: '03_에이전트/skills/optimize-eligible-molecules/SKILL.md',
    version: 'v1.0.0',
    capabilities: ['RDKit 표준화', '제한된 구조 변형', '다목적 Pareto 순위'],
    guardrail: 'Tanimoto 유사도나 QED 개선을 활성·효능 개선으로 쓰지 않습니다.',
    accent: '#16845c',
  },
  {
    id: 'verify-admet-synthesis',
    name: 'ADMET·합성성 검증',
    description: 'ADMET-AI와 SA/RAscore, 제한된 top-5 역합성 신호로 후보를 검증합니다.',
    category: '분자 설계',
    status: 'planned',
    ownerIds: ['safety-synthesis-verifier'],
    sourcePath: '03_에이전트/skills/verify-admet-synthesis/SKILL.md',
    version: 'v1.0.0',
    capabilities: ['구조 경고', 'ADMET risk gate', '2단 합성성 평가'],
    guardrail: '미검증 predictor를 사용하지 않고 실행 가능한 합성 지침을 출력하지 않습니다.',
    accent: '#b86b06',
  },
  {
    id: 'manage-evidence-snapshots',
    name: '근거 스냅샷 관리',
    description: 'API 응답의 출처·관측일·쿼리·해시를 보존하고 장애 시 공개된 fallback을 수행합니다.',
    category: '검증·거버넌스',
    status: 'ready',
    ownerIds: ['evidence-scout', 'governance-lead', 'audit-eval-agent'],
    sourcePath: '03_에이전트/skills/manage-evidence-snapshots/SKILL.md',
    version: 'v1.0.0',
    capabilities: ['schema·ID 검증', 'SHA-256 manifest', 'live/cache 동일 계약'],
    guardrail: 'cache를 live로 위장하거나 승인 전 snapshot으로 판단을 바꾸지 않습니다.',
    accent: '#536b78',
  },
  {
    id: 'evaluate-h2l-runs',
    name: 'H2L 실행 평가',
    description: '골든 케이스와 안전 불변식으로 결정 정확도, 반증 회수율과 재현성을 평가합니다.',
    category: '검증·거버넌스',
    status: 'ready',
    ownerIds: ['governance-lead', 'audit-eval-agent'],
    sourcePath: '03_에이전트/skills/evaluate-h2l-runs/SKILL.md',
    version: 'v1.0.0',
    capabilities: ['골든 케이스 회귀', 'baseline ablation', 'unsafe advance 감시'],
    guardrail: '평가 plane은 과학적 판단 상태를 수정하지 않습니다.',
    accent: '#4453a6',
  },
  {
    id: 'generate-audit-report',
    name: '감사 보고서 생성',
    description: '판단, 실패, proxy 한계, 출처와 인간 검토 상태를 추적 가능한 보고서로 구성합니다.',
    category: '검증·거버넌스',
    status: 'ready',
    ownerIds: ['research-director', 'governance-lead', 'report-agent'],
    sourcePath: '03_에이전트/skills/generate-audit-report/SKILL.md',
    version: 'v1.0.0',
    capabilities: ['결정 근거 표', 'failure ledger', 'citation appendix'],
    guardrail: 'synthetic fixture와 연구 결과를 분리하고 실행하지 않은 검증을 주장하지 않습니다.',
    accent: '#18738a',
  },
]

export const skillCategories: Array<'전체' | SkillCategory> = [
  '전체',
  '질병·근거',
  '타깃 의사결정',
  '분자 설계',
  '검증·거버넌스',
]

export function agentById(id: string) {
  return h2lAgents.find((agent) => agent.id === id)
}

export function skillById(id: string) {
  return h2lSkills.find((skill) => skill.id === id)
}
