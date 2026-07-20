import { AlertTriangle, CheckCircle2, Database, Download, FileCheck2, MinusCircle, RotateCcw, XCircle } from 'lucide-react'
import type { RunEvent, RunSnapshot } from '../domain/contracts'
import { downloadText, formatDateTime, formatDuration } from '../lib/format'

const eventIcons = {
  success: CheckCircle2,
  warning: AlertTriangle,
  failed: XCircle,
  decision: RotateCcw,
  skipped: MinusCircle,
}

function eventTime(event: RunEvent) {
  return new Intl.DateTimeFormat('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(new Date(event.occurredAt))
}

export default function AuditView({ snapshot }: { snapshot: RunSnapshot }) {
  const { events, failures, stages, evidence, run } = snapshot
  const versionedCalls = events.filter((event) => event.toolVersion).length
  const sourceReferenceCount = events.reduce((count, event) => count + event.sourceIds.length, 0)
  const retryCount = stages.reduce((count, stage) => count + stage.retryCount, 0)
  const sourceSnapshots = [...new Map(evidence.map((item) => [`${item.source}-${item.observedAt}`, item])).values()]

  const exportAudit = () => {
    downloadText(
      `${run.id}-audit.json`,
      JSON.stringify({ run, events, failures, stages }, null, 2),
      'application/json;charset=utf-8',
    )
  }

  return (
    <div className="audit-layout">
      <section className="audit-timeline-panel">
        <div className="panel-heading">
          <div><h2>실행 감사 기록</h2></div>
          <button className="icon-text-button" type="button" onClick={exportAudit}><Download size={15} /> JSON 내보내기</button>
        </div>
        <div className="audit-timeline">
          {events.length > 0 ? events.map((event) => {
            const Icon = eventIcons[event.status]
            return (
              <article className={`audit-event audit-${event.status}`} key={event.id}>
                <time dateTime={event.occurredAt}>{eventTime(event)}</time>
                <div className="audit-marker"><Icon size={15} /></div>
                <div className="audit-content">
                  <div className="audit-meta"><strong>{event.agent}</strong><span>{event.tool}{event.toolVersion ? ` · ${event.toolVersion}` : ''}</span><small>{formatDuration(event.durationMs)}</small></div>
                  <h3>{event.title}</h3><p>{event.detail}</p>
                  <div className="audit-identifiers"><code>stage:{event.stageId}</code>{event.sourceIds.map((sourceId) => <code key={sourceId}>{sourceId}</code>)}</div>
                </div>
              </article>
            )
          }) : <div className="empty-timeline"><FileCheck2 size={24} /><strong>이벤트를 기다리는 중입니다.</strong><span>실행이 시작되면 단계별 도구 호출과 결정이 여기에 추가됩니다.</span></div>}
        </div>
      </section>

      <aside className="audit-summary-panel">
        <div className="panel-heading compact-heading"><div><h2>기록된 범위</h2></div></div>
        <dl className="coverage-list audit-count-list">
          <div><dt>실행 이벤트</dt><dd>{events.length}</dd></div>
          <div><dt>버전이 있는 도구 호출</dt><dd>{versionedCalls} / {events.length}</dd></div>
          <div><dt>출처 ID 참조</dt><dd>{sourceReferenceCount}</dd></div>
          <div><dt>실패·중단 기록</dt><dd>{failures.length}</dd></div>
          <div><dt>재시도 횟수</dt><dd>{retryCount}</dd></div>
        </dl>
        <p className="coverage-disclosure">비율을 추정하지 않고 현재 이벤트 배열에서 계산 가능한 개수만 표시합니다.</p>
        <div className="snapshot-card">
          <Database size={17} />
          <div><strong>출처 관측 기준</strong>{sourceSnapshots.length > 0 ? sourceSnapshots.map((item) => <span key={item.id}>{item.source} · {item.observedAt}</span>) : <span>외부 출처 없음</span>}<small>실행 갱신 {formatDateTime(run.updatedAt)}</small></div>
        </div>
      </aside>
    </div>
  )
}
