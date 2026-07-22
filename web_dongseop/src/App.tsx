import {
  Activity,
  AlertOctagon,
  Beaker,
  BookOpenCheck,
  Boxes,
  CheckCircle2,
  Clock3,
  Database,
  FileSearch,
  FileText,
  FlaskConical,
  History,
  LayoutDashboard,
  ListChecks,
  Menu,
  Network,
  Play,
  Plus,
  Radio,
  ShieldCheck,
  Square,
  X,
} from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import StatusBadge from './components/StatusBadge'
import { scenarioOptions } from './data/demoScenarios'
import type { ScenarioKind, StageStatus, TabId } from './domain/contracts'
import { formatDateTime, formatDuration, formatTime } from './lib/format'
import { useHarnessWorkspace } from './state/useHarnessWorkspace'
import AuditView from './views/AuditView'
import FailuresView from './views/FailuresView'
import MoleculesView from './views/MoleculesView'
import OverviewView from './views/OverviewView'
import OrganizationView from './views/OrganizationView'
import ReportView from './views/ReportView'
import SkillsView from './views/SkillsView'
import TargetsView from './views/TargetsView'

const tabs: Array<{ id: TabId; label: string; icon: typeof LayoutDashboard }> = [
  { id: 'overview', label: '개요', icon: LayoutDashboard },
  { id: 'targets', label: '타깃', icon: FileSearch },
  { id: 'molecules', label: '분자', icon: Beaker },
  { id: 'failures', label: '중단 기록', icon: AlertOctagon },
  { id: 'audit', label: '감사 기록', icon: ListChecks },
  { id: 'report', label: '보고서', icon: FileText },
]

const terminalStatuses: StageStatus[] = ['completed', 'warning', 'failed', 'skipped', 'blocked', 'cancelled']

function LiveElapsed({ startedAt }: { startedAt: string }) {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    setNow(Date.now())
    const timer = window.setInterval(() => setNow(Date.now()), 250)
    return () => window.clearInterval(timer)
  }, [startedAt])

  const startedAtMs = new Date(startedAt).getTime()
  return <>{formatDuration(Number.isNaN(startedAtMs) ? 0 : Math.max(0, now - startedAtMs))}</>
}

function App() {
  const {
    runs, snapshot, selectedRunId, isLoading, error,
    selectRun, createRun, cancelRun, markReviewed,
  } = useHarnessWorkspace()
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [selectedStageId, setSelectedStageId] = useState('critic')
  const [selectedTarget, setSelectedTarget] = useState('TYK2')
  const [selectedScenario, setSelectedScenario] = useState<ScenarioKind>('evidence-review')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([])
  const dialogRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (!snapshot) return
    const runningStage = snapshot.stages.find((stage) => stage.status === 'running')
    const hasSelectedStage = snapshot.stages.some((stage) => stage.id === selectedStageId)
    if (runningStage) setSelectedStageId(runningStage.id)
    else if (!hasSelectedStage) setSelectedStageId(snapshot.stages[0]?.id ?? '')

    if (snapshot.targets.length > 0 && !snapshot.targets.some((target) => target.symbol === selectedTarget)) {
      setSelectedTarget(snapshot.targets.find((target) => target.symbol === 'TYK2')?.symbol ?? snapshot.targets[0].symbol)
    }
  }, [selectedStageId, selectedTarget, snapshot])

  useEffect(() => {
    if (!isModalOpen) return
    const dialog = dialogRef.current
    const previousFocus = document.activeElement as HTMLElement | null
    const focusableSelector = 'button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
    const focusables = () => Array.from(dialog?.querySelectorAll<HTMLElement>(focusableSelector) ?? [])
    window.requestAnimationFrame(() => focusables()[0]?.focus())

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsModalOpen(false)
        return
      }
      if (event.key !== 'Tab') return
      const items = focusables()
      if (items.length === 0) return
      const first = items[0]
      const last = items[items.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      previousFocus?.focus()
    }
  }, [isModalOpen])

  const metrics = useMemo(() => {
    if (!snapshot) return null
    const processed = snapshot.stages.filter((stage) => terminalStatuses.includes(stage.status)).length
    const completed = snapshot.stages.filter((stage) => stage.status === 'completed').length
    const warnings = snapshot.stages.filter((stage) => stage.status === 'warning').length
    const skipped = snapshot.stages.filter((stage) => stage.status === 'skipped' || stage.status === 'blocked').length
    const rejected = snapshot.targets.filter((target) => target.decision === 'rejected').length
    const review = snapshot.targets.filter((target) => target.decision === 'review' || target.decision === 'insufficient').length
    return { processed, completed, warnings, skipped, rejected, review }
  }, [snapshot])

  const handleCreate = async () => {
    setIsCreating(true)
    try {
      const next = await createRun({ scenario: selectedScenario, mode: 'snapshot' })
      setSelectedStageId(next.stages[0]?.id ?? '')
      setSelectedTarget(next.targets.find((target) => target.symbol === 'TYK2')?.symbol ?? next.targets[0]?.symbol ?? '')
      setActiveTab(selectedScenario === 'molecule-ui-fixture' ? 'molecules' : 'overview')
      setIsModalOpen(false)
    } finally {
      setIsCreating(false)
    }
  }

  const handleSelectRun = async (runId: string) => {
    await selectRun(runId)
    setActiveTab('overview')
    setIsSidebarOpen(false)
  }

  const openMoleculeFixture = async () => {
    const fixtureRun = runs.find((run) => run.scenarioKind === 'molecule-ui-fixture' && run.status !== 'running')
    if (fixtureRun) await selectRun(fixtureRun.id)
    else await createRun({ scenario: 'molecule-ui-fixture', mode: 'snapshot' })
    setActiveTab('molecules')
  }

  const handleTabKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
    let nextIndex = index
    if (event.key === 'ArrowRight') nextIndex = (index + 1) % tabs.length
    else if (event.key === 'ArrowLeft') nextIndex = (index - 1 + tabs.length) % tabs.length
    else if (event.key === 'Home') nextIndex = 0
    else if (event.key === 'End') nextIndex = tabs.length - 1
    else return
    event.preventDefault()
    setActiveTab(tabs[nextIndex].id)
    tabRefs.current[nextIndex]?.focus()
  }

  const renderActiveView = () => {
    if (activeTab === 'organization') return <OrganizationView />
    if (activeTab === 'skills') return <SkillsView />
    if (!snapshot) return null
    if (activeTab === 'targets') return <TargetsView targets={snapshot.targets} evidence={snapshot.evidence} selectedSymbol={selectedTarget} onSelect={setSelectedTarget} />
    if (activeTab === 'molecules') return <MoleculesView molecules={snapshot.molecules} scenarioKind={snapshot.run.scenarioKind} runStatus={snapshot.run.status} onOpenFixture={() => { void openMoleculeFixture() }} />
    if (activeTab === 'failures') return <FailuresView failures={snapshot.failures} />
    if (activeTab === 'audit') return <AuditView snapshot={snapshot} />
    if (activeTab === 'report') return <ReportView snapshot={snapshot} />
    return <OverviewView snapshot={snapshot} selectedStageId={selectedStageId} onSelectStage={setSelectedStageId} onOpenTargets={() => setActiveTab('targets')} />
  }

  if (isLoading) {
    return <main className="app-loading"><Activity className="spin" size={22} /><strong>하네스 스냅샷을 불러오는 중입니다.</strong></main>
  }

  if (!snapshot || !metrics) {
    return <main className="app-loading app-error"><AlertOctagon size={22} /><strong>{error ?? '표시할 실행이 없습니다.'}</strong></main>
  }

  const { run } = snapshot
  const isRunning = run.status === 'running' || run.status === 'queued'
  const runningStage = snapshot.stages.find((stage) => stage.status === 'running')
  const activityStage = runningStage ?? snapshot.stages.find((stage) => stage.status === 'queued')
  const activityStageIndex = activityStage
    ? snapshot.stages.findIndex((stage) => stage.id === activityStage.id)
    : -1
  const progressUnits = metrics.processed + (isRunning && activityStage ? 0.45 : 0)
  const progressPercent = Math.min(100, snapshot.stages.length
    ? (progressUnits / snapshot.stages.length) * 100
    : 0)
  const monitorActive = ['overview', 'targets', 'molecules', 'failures'].includes(activeTab)
  const isSystemView = activeTab === 'organization' || activeTab === 'skills'
  const systemViewLabel = activeTab === 'organization' ? 'AI 조직도' : '에이전트 스킬'
  const selectedScenarioOption = scenarioOptions.find((option) => option.id === selectedScenario) ?? scenarioOptions[0]

  return (
    <div className={`app-shell${isRunning ? ' is-running' : ''}`}>
      <aside className={`sidebar${isSidebarOpen ? ' is-open' : ''}`}>
        <div className="brand-row">
          <div className="brand-mark">H2L</div>
          <div className="brand-copy"><strong>H2L-Forge</strong><span>신약개발 워크벤치</span></div>
          <button className="mobile-close icon-button" type="button" onClick={() => setIsSidebarOpen(false)} aria-label="메뉴 닫기"><X size={18} /></button>
        </div>
        <button className="new-run-button" type="button" onClick={() => setIsModalOpen(true)}><Plus size={16} /> 새 실행</button>

        <nav className="sidebar-nav" aria-label="주요 메뉴">
          <button aria-current={monitorActive ? 'page' : undefined} className={monitorActive ? 'is-active' : ''} type="button" onClick={() => setActiveTab('overview')}><Activity size={17} /> 실행 모니터</button>
          <button aria-current={activeTab === 'audit' ? 'page' : undefined} className={activeTab === 'audit' ? 'is-active' : ''} type="button" onClick={() => setActiveTab('audit')}><History size={17} /> 감사 기록</button>
          <button aria-current={activeTab === 'report' ? 'page' : undefined} className={activeTab === 'report' ? 'is-active' : ''} type="button" onClick={() => setActiveTab('report')}><BookOpenCheck size={17} /> 산출물</button>
        </nav>

        <div className="sidebar-section-heading"><span>AI 운영</span><span>11 agents</span></div>
        <nav className="sidebar-nav" aria-label="AI 조직과 스킬">
          <button aria-current={activeTab === 'organization' ? 'page' : undefined} className={activeTab === 'organization' ? 'is-active' : ''} type="button" onClick={() => { setActiveTab('organization'); setIsSidebarOpen(false) }}><Network size={17} /> AI 조직도</button>
          <button aria-current={activeTab === 'skills' ? 'page' : undefined} className={activeTab === 'skills' ? 'is-active' : ''} type="button" onClick={() => { setActiveTab('skills'); setIsSidebarOpen(false) }}><Boxes size={17} /> 에이전트 스킬</button>
        </nav>

        <div className="sidebar-section-heading"><span>최근 실행</span><span>{runs.length}</span></div>
        <div className="recent-runs">
          {runs.map((item) => (
            <button
              aria-current={selectedRunId === item.id ? 'true' : undefined}
              className={`${selectedRunId === item.id ? 'is-selected' : ''}${item.status === 'running' || item.status === 'queued' ? ' is-live' : ''}`}
              key={item.id}
              type="button"
              onClick={() => { void handleSelectRun(item.id) }}
            >
              <span className={`run-dot run-${item.status}`} />
              <div><strong>{item.title}</strong><small>{item.id}</small></div>
              <time dateTime={item.createdAt}>{formatTime(item.createdAt)}</time>
            </button>
          ))}
        </div>

        <div className="sidebar-footer">
          <div className="prototype-note"><Radio size={16} /><div><strong>모의 하네스 연결</strong><span>RunSnapshot 계약 · v1</span></div></div>
        </div>
      </aside>

      {isSidebarOpen && <button className="sidebar-scrim" type="button" aria-label="메뉴 닫기" onClick={() => setIsSidebarOpen(false)} />}

      <div className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button className="mobile-menu icon-button" type="button" onClick={() => setIsSidebarOpen(true)} aria-label="메뉴 열기"><Menu size={19} /></button>
            <span>{isSystemView ? 'AI 운영' : '실행'}</span><span className="breadcrumb-separator">/</span><strong>{isSystemView ? systemViewLabel : run.id}</strong>
          </div>
          <div className="topbar-actions"><span className="adapter-state"><Database size={14} /> 스냅샷 연결</span><div className="avatar" aria-label="사용자 프로필">VS</div></div>
        </header>

        {!isSystemView && <div className={`context-banner context-${run.classification}`} role="note">
          {run.classification === 'synthetic' ? <FlaskConical size={16} /> : <Database size={16} />}
          <strong>{run.classification === 'synthetic' ? '합성 UI fixture' : '저장된 출처 스냅샷'}</strong>
          <span>{run.classification === 'synthetic' ? '연구 결과가 아니며 화면 동작 확인에만 사용합니다.' : '현재 외부 API를 조회한 결과가 아닙니다. 관측일과 출처 ID를 함께 확인하세요.'}</span>
        </div>}
        {error && <div className="error-banner" role="alert"><AlertOctagon size={15} />{error}</div>}

        {!isSystemView && <section className="run-header">
          <div className="run-title-block">
            <div className="run-title-line"><h1>{run.title}</h1><StatusBadge status={run.status} /></div>
            <div className="run-subtitle"><code>{run.diseaseId}</code><span>{run.disease}</span><span>시작 {formatDateTime(run.createdAt)}</span></div>
          </div>
          <div className="run-actions">
            {isRunning ? (
              <button className="secondary-button danger-button" type="button" onClick={() => { void cancelRun() }}><Square size={15} /> 실행 취소</button>
            ) : (
              <button className="secondary-button" type="button" onClick={() => { void markReviewed() }} disabled={run.reviewStatus === 'approved'}><ShieldCheck size={16} /> {run.reviewStatus === 'approved' ? '검토 완료' : '검토 완료 처리'}</button>
            )}
            <button className="primary-button" type="button" onClick={() => setIsModalOpen(true)}><Play size={16} /> 새 실행</button>
          </div>
        </section>}

        {!isSystemView && isRunning && (
          <div className="run-activity-banner" role="status" aria-live="polite">
            <span className="activity-pulse" aria-hidden="true"><Activity size={17} /></span>
            <div className="activity-copy">
              <strong>{run.status === 'queued' ? '실행 준비 중' : `${activityStage?.label ?? '하네스'} 실행 중`}</strong>
              <span>{activityStage
                ? `${activityStage.agent} · ${activityStageIndex + 1}/${snapshot.stages.length} 단계`
                : '작업 큐에서 실행을 준비하고 있습니다.'}</span>
            </div>
            <div className="activity-progress" aria-label={`전체 진행률 ${Math.round(progressPercent)}%`}>
              <i style={{ width: `${progressPercent}%` }}><span /></i>
            </div>
            <strong className="activity-percent">{Math.round(progressPercent)}%</strong>
          </div>
        )}

        {!isSystemView && <section className="run-metrics" aria-label="실행 요약">
          <div className={isRunning ? 'live-metric' : undefined}><span>단계 처리</span><strong>{metrics.processed}/{snapshot.stages.length}</strong><div className={`progress-track${isRunning ? ' is-live' : ''}`}><i style={{ width: `${progressPercent}%` }} /></div><small>완료 {metrics.completed} · 주의 {metrics.warnings} · 미실행 {metrics.skipped}</small></div>
          <div className={isRunning ? 'live-metric' : undefined}><span>실행 시간</span><strong>{isRunning ? <LiveElapsed startedAt={run.createdAt} /> : formatDuration(run.durationMs)}</strong><small><Clock3 size={13} /> {isRunning ? `${activityStage?.label ?? '하네스'} 처리 중` : `갱신 ${formatDateTime(run.updatedAt)}`}</small></div>
          <div><span>타깃 판단</span><strong>{snapshot.targets.length ? `기각 ${metrics.rejected} · 검토 ${metrics.review}` : '해당 없음'}</strong><small>채택된 타깃 0</small></div>
          <div><span>분자 출력</span><strong>{snapshot.molecules.length ? `${snapshot.molecules.length}개 UI fixture` : '0개 · 미실행'}</strong><small>{snapshot.molecules.length ? '모두 합성 테스트 레코드' : '결정 게이트에서 중단'}</small></div>
          <div><span>데이터 분류</span><strong>{run.classification === 'synthetic' ? '합성 데이터' : '출처 스냅샷'}</strong><small>{run.mode === 'snapshot' ? '모의 연결' : '실시간 연결'}</small></div>
        </section>}

        {!isSystemView && <nav className="tabbar" role="tablist" aria-label="실행 상세 화면">
          {tabs.map((tab, index) => {
            const Icon = tab.icon
            const count = tab.id === 'failures' ? snapshot.failures.length : tab.id === 'molecules' ? snapshot.molecules.length : undefined
            return (
              <button
                aria-controls={`panel-${tab.id}`}
                aria-selected={activeTab === tab.id}
                className={activeTab === tab.id ? 'is-active' : ''}
                id={`tab-${tab.id}`}
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                onKeyDown={(event) => handleTabKeyDown(event, index)}
                ref={(element) => { tabRefs.current[index] = element }}
                role="tab"
                tabIndex={activeTab === tab.id ? 0 : -1}
                type="button"
              >
                <Icon size={15} />{tab.label}{count !== undefined && <span className={`tab-count${tab.id === 'failures' && count > 0 ? ' warning-count' : ''}`}>{count}</span>}
              </button>
            )
          })}
        </nav>}

        <div aria-labelledby={isSystemView ? undefined : `tab-${activeTab}`} className={`content-area${isSystemView ? ' system-content-area' : ''}`} id={`panel-${activeTab}`} role={isSystemView ? undefined : 'tabpanel'}>{renderActiveView()}</div>
      </div>

      {isModalOpen && (
        <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) setIsModalOpen(false) }}>
          <section className="start-modal" ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby="start-title" aria-describedby="start-description">
            <div className="modal-header">
              <div><h2 id="start-title">새 실행 시작</h2></div>
              <button className="icon-button" type="button" onClick={() => setIsModalOpen(false)} aria-label="닫기"><X size={18} /></button>
            </div>
            <p className="modal-intro" id="start-description">현재 프로토타입에서 검증할 고정 시나리오를 선택하세요. 자유 입력은 실제 정규화 API가 연결된 뒤 활성화합니다.</p>
            <fieldset className="scenario-fieldset">
              <legend>실행 시나리오</legend>
              {scenarioOptions.map((option) => (
                <button aria-pressed={selectedScenario === option.id} className={selectedScenario === option.id ? 'is-selected' : ''} key={option.id} type="button" onClick={() => setSelectedScenario(option.id)}>
                  {option.id === 'evidence-review' ? <FileSearch size={19} /> : <Beaker size={19} />}
                  <div><strong>{option.title}{option.recommended && <small>권장</small>}</strong><span>{option.description}</span></div>
                  {selectedScenario === option.id && <CheckCircle2 size={18} />}
                </button>
              ))}
            </fieldset>
            <fieldset className="mode-fieldset">
              <legend>연결 방식</legend>
              <button className="is-selected" type="button"><Database size={18} /><div><strong>Mock snapshot adapter</strong><span>고정 데이터와 실행 상태 전환을 재현합니다.</span></div><CheckCircle2 size={18} /></button>
              <button type="button" disabled><Activity size={18} /><div><strong>실제 하네스 API</strong><span>백엔드 계약 구현 후 활성화됩니다.</span></div></button>
            </fieldset>
            <div className={`modal-scope scope-${selectedScenarioOption.classification}`}><span>실행 범위</span><p>{selectedScenarioOption.description}</p></div>
            <div className="modal-actions"><button className="secondary-button" type="button" onClick={() => setIsModalOpen(false)}>취소</button><button className="primary-button" type="button" onClick={() => { void handleCreate() }} disabled={isCreating}><Play size={16} /> {isCreating ? '시작 중' : '실행 시작'}</button></div>
          </section>
        </div>
      )}
    </div>
  )
}

export default App
