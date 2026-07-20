import {
  AlertTriangle,
  ArrowDown,
  ArrowRight,
  Ban,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Database,
  ExternalLink,
  FileText,
  LoaderCircle,
  MinusCircle,
  ShieldOff,
  XCircle,
} from 'lucide-react'
import StatusBadge from '../components/StatusBadge'
import type { RunSnapshot, StageStatus } from '../domain/contracts'
import { formatDuration } from '../lib/format'

interface OverviewProps {
  snapshot: RunSnapshot
  selectedStageId: string
  onSelectStage: (id: string) => void
  onOpenTargets: () => void
}

const terminalStatuses: StageStatus[] = ['completed', 'warning', 'failed', 'skipped', 'blocked', 'cancelled']

function StageIcon({ status }: { status: StageStatus }) {
  if (status === 'completed') return <CheckCircle2 size={13} />
  if (status === 'warning') return <AlertTriangle size={13} />
  if (status === 'running') return <LoaderCircle className="spin" size={13} />
  if (status === 'skipped') return <MinusCircle size={13} />
  if (status === 'blocked' || status === 'cancelled') return <Ban size={13} />
  if (status === 'failed') return <XCircle size={13} />
  return <Clock3 size={13} />
}

export default function OverviewView({ snapshot, selectedStageId, onSelectStage, onOpenTargets }: OverviewProps) {
  const { stages, evidence, targets, run } = snapshot
  const selectedStage = stages.find((stage) => stage.id === selectedStageId) ?? stages[0]
  const focusTarget = targets.find((target) => target.symbol === 'TYK2')
  const focusEvidence = focusTarget
    ? evidence.filter((item) => focusTarget.evidenceIds.includes(item.id))
    : evidence
  const supporting = focusEvidence.filter((item) => item.polarity === 'supporting')
  const conflicting = focusEvidence.filter((item) => item.polarity === 'conflicting')
  const processed = stages.filter((stage) => terminalStatuses.includes(stage.status)).length
  const showDecision = Boolean(focusTarget && (selectedStage.id === 'critic' || selectedStage.id === 'decision'))

  return (
    <div className="workspace-grid">
      <section className="stage-panel" aria-label="하네스 단계">
        <div className="panel-heading compact-heading">
          <div><span className="eyebrow">Harness pipeline</span><h2>실행 단계</h2></div>
          <span className="completion-count">{processed}/{stages.length}</span>
        </div>
        <div className="stage-list">
          {stages.map((stage, index) => (
            <button
              aria-current={selectedStage.id === stage.id ? 'step' : undefined}
              className={`stage-item${selectedStage.id === stage.id ? ' is-active' : ''}`}
              key={stage.id}
              onClick={() => onSelectStage(stage.id)}
              type="button"
            >
              <span className={`stage-marker stage-${stage.status}`}><StageIcon status={stage.status} /></span>
              <span className="stage-copy"><strong>{stage.label}</strong><small>{stage.agent}</small></span>
              <span className="stage-duration">{formatDuration(stage.durationMs)}</span>
              {index < stages.length - 1 && <span className="stage-connector" />}
            </button>
          ))}
        </div>
      </section>

      <main className="decision-panel">
        <div className="panel-heading">
          <div><span className="eyebrow">Selected stage</span><h2>{selectedStage.label}</h2></div>
          <StatusBadge status={selectedStage.status} />
        </div>

        {showDecision && focusTarget ? (
          <>
            <div className="decision-summary">
              <div className="decision-kicker"><AlertTriangle size={16} />적응증별 임상 근거가 최초 판단과 충돌</div>
              <h3>TYK2는 이 IBD 실행의 분자 최적화 대상으로 진행하지 않습니다.</h3>
              <p>화학적 접근 가능성과 IBD 적응증의 유효성은 별개입니다. 지지 근거와 반증을 분리해 운영 점수를 다시 계산했습니다.</p>
            </div>

            <div className="score-reversal" aria-label="TYK2 점수 변화">
              <div className="score-block before"><span>비평 전 운영 점수</span><strong>{focusTarget.scoreBefore}</strong><small>연관성·tractability·활성 자료</small></div>
              <div className="score-arrow"><ArrowRight size={20} /><span>{focusTarget.scoreAfter - focusTarget.scoreBefore}</span></div>
              <div className="score-block after"><span>근거 비평 후</span><strong>{focusTarget.scoreAfter}</strong><small>IBD 임상 반증 반영</small></div>
              <div className="decision-stamp"><span>결정</span><strong>기각</strong></div>
            </div>

            <div className="score-attribution" aria-label="점수 산정 내역">
              <div className="attribution-heading"><strong>점수 산정 내역</strong><span>합계 {focusTarget.scoreAfter}</span></div>
              {focusTarget.scoreFactors.map((factor) => (
                <div className={factor.impact < 0 ? 'is-negative' : 'is-positive'} key={factor.id}>
                  <span>{factor.label}</span><strong>{factor.impact > 0 ? '+' : ''}{factor.impact}</strong>
                </div>
              ))}
            </div>

            <div className="evidence-columns">
              <div className="evidence-column supportive">
                <div className="column-title"><CheckCircle2 size={16} /><strong>지지 근거</strong><span>{supporting.length}</span></div>
                {supporting.map((item) => <div className="evidence-row" key={item.id}><div><strong>{item.title}</strong><p>{item.detail}</p></div><span>지지 · {item.source}</span></div>)}
              </div>
              <div className="evidence-divider"><ArrowDown size={16} /></div>
              <div className="evidence-column conflicting">
                <div className="column-title"><AlertTriangle size={16} /><strong>반증</strong><span>{conflicting.length}</span></div>
                {conflicting.map((item) => <div className="evidence-row" key={item.id}><div><strong>{item.title}</strong><p>{item.detail}</p></div><span>반증 · {item.source}</span></div>)}
              </div>
            </div>

            <div className="next-action">
              <div className="next-action-icon"><ShieldOff size={18} /></div>
              <div><span>게이트 결과</span><strong>채택 타깃이 없어 seed부터 합성 평가까지 실행하지 않았습니다.</strong></div>
              <button className="text-button" type="button" onClick={onOpenTargets}>타깃 비교 <ChevronRight size={15} /></button>
            </div>
          </>
        ) : (
          <div className={`generic-stage-output generic-${selectedStage.status}`}>
            <div className="generic-icon">{selectedStage.status === 'skipped' ? <ShieldOff size={24} /> : selectedStage.id === 'report' ? <FileText size={24} /> : <Database size={24} />}</div>
            <span className="eyebrow">{selectedStage.agent}</span>
            <h3>{selectedStage.summary}</h3>
            <p>{selectedStage.output}</p>
            <dl className="stage-contract-grid">
              <div><dt>Stage ID</dt><dd><code>{selectedStage.id}</code></dd></div>
              <div><dt>소요 시간</dt><dd>{formatDuration(selectedStage.durationMs)}</dd></div>
              <div><dt>재시도</dt><dd>{selectedStage.retryCount}회</dd></div>
              <div><dt>산출물</dt><dd>{selectedStage.outputArtifactIds.length}개</dd></div>
              <div><dt>도구</dt><dd>{selectedStage.toolCall?.name ?? '미호출'}</dd></div>
              <div><dt>데이터 분류</dt><dd>{selectedStage.toolCall?.classification ?? '해당 없음'}</dd></div>
            </dl>
          </div>
        )}
      </main>

      <aside className="source-panel" aria-label="근거 출처">
        <div className="panel-heading compact-heading">
          <div><span className="eyebrow">Provenance</span><h2>근거와 출처</h2></div>
          <span className="source-total">{focusEvidence.length}</span>
        </div>
        <div className={`snapshot-notice notice-${run.classification}`}>
          <Database size={16} />
          <div><strong>{run.classification === 'synthetic' ? '합성 UI 데이터' : '저장된 출처 스냅샷'}</strong><span>{run.mode === 'live' ? 'Live adapter' : 'Snapshot adapter'}</span></div>
        </div>
        <div className="source-list">
          {focusEvidence.length > 0 ? focusEvidence.map((item) => (
            <a className="source-item" href={item.href} key={item.id} target="_blank" rel="noreferrer">
              <span className={`source-polarity ${item.polarity}`}>{item.polarity === 'supporting' ? '지지' : item.polarity === 'conflicting' ? '반증' : '중립'}</span>
              <div><strong>{item.source}</strong><span>{item.sourceId}</span><small>관측일 {item.observedAt}</small></div>
              <ExternalLink size={14} />
            </a>
          )) : <div className="empty-inline">이 실행에는 외부 근거가 없습니다.</div>}
        </div>
        <div className="source-footnote"><AlertTriangle size={14} />Association score는 근거 가용성 지표이며 생물학적 확신도가 아닙니다.</div>
      </aside>
    </div>
  )
}
