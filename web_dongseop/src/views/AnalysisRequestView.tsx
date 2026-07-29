import { Activity, Beaker, FileSearch, Play, Sparkles } from 'lucide-react'
import type { ScenarioOption } from '../domain/contracts'

interface AnalysisRequestViewProps {
  scenarioOptions: ScenarioOption[]
  onStartRun: (option: ScenarioOption) => void
  isCreating: boolean
  isConnected: boolean
  startError: string | null
}

export default function AnalysisRequestView({ scenarioOptions, onStartRun, isCreating, isConnected, startError }: AnalysisRequestViewProps) {
  const liveCount = scenarioOptions.filter((option) => option.harnessScenarioId).length
  return (
    <div className="system-page">
      <header className="system-page-header">
        <div>
          <span className="system-kicker"><Sparkles size={14} /> AI·자동화 관리</span>
          <h1>AI 분석 요청</h1>
          <p>시나리오를 선택해 근거 기반 분석을 실행합니다. 자유 질병 입력은 실제 정규화 API 연결 후 활성화됩니다.</p>
        </div>
        <div className="system-summary-chips" aria-label="요청 요약">
          <span><strong>{scenarioOptions.length}</strong> 시나리오</span>
          <span>{isConnected ? `하네스 연결 · 계산 ${liveCount}건` : '하네스 미연결 · 픽스처만'}</span>
        </div>
      </header>

      {startError && <div className="modal-scope scope-synthetic" role="alert"><span>실행 실패</span><p>{startError}</p></div>}

      <div className="ops-request-grid">
        {scenarioOptions.map((option) => (
          <article className={`ops-request-card scope-${option.classification}`} key={option.id}>
            <div className="ops-request-icon">{option.harnessScenarioId ? <Activity size={20} /> : option.id === 'evidence-review' ? <FileSearch size={20} /> : <Beaker size={20} />}</div>
            <div className="ops-request-copy">
              <strong>{option.title}{option.recommended && <em className="ops-tag">권장</em>}</strong>
              <p>{option.description}</p>
            </div>
            <button className="primary-button" type="button" disabled={isCreating} onClick={() => onStartRun(option)}>
              <Play size={15} /> {isCreating ? '시작 중' : '분석 실행'}
            </button>
          </article>
        ))}
      </div>
    </div>
  )
}
