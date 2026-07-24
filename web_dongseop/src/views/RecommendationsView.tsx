import { FlaskConical, ArrowRight } from 'lucide-react'
import { useMemo } from 'react'
import type { RunSnapshot } from '../domain/contracts'

interface Recommendation {
  id: string
  subject: string
  action: string
  source: string
  priority: 'high' | 'medium' | 'low'
}

const priorityLabel: Record<Recommendation['priority'], string> = {
  high: '높음',
  medium: '보통',
  low: '낮음',
}

export default function RecommendationsView({ snapshot }: { snapshot: RunSnapshot }) {
  const recommendations = useMemo<Recommendation[]>(() => {
    const fromFailures = snapshot.failures
      .filter((failure) => failure.nextAction)
      .map((failure) => ({
        id: `rec-${failure.id}`,
        subject: failure.subject,
        action: failure.nextAction,
        source: failure.stage,
        priority: (failure.severity === 'critical' ? 'high' : failure.severity === 'warning' ? 'medium' : 'low') as Recommendation['priority'],
      }))
    const fromTargets = snapshot.targets
      .filter((target) => target.decision === 'review' || target.decision === 'insufficient')
      .map((target) => ({
        id: `rec-target-${target.symbol}`,
        subject: `${target.symbol} 타깃`,
        action: target.caution || '추가 근거 확보 후 재검토',
        source: '타깃 판단',
        priority: 'medium' as const,
      }))
    return [...fromFailures, ...fromTargets]
  }, [snapshot])

  const order = { high: 0, medium: 1, low: 2 }
  const sorted = [...recommendations].sort((a, b) => order[a.priority] - order[b.priority])

  return (
    <div className="system-page">
      <header className="system-page-header">
        <div>
          <span className="system-kicker"><FlaskConical size={14} /> AI·자동화 관리</span>
          <h1>실험 추천 큐</h1>
          <p>현재 실행의 중단 사유와 타깃 판단에서 파생된 다음 실험·조치 추천입니다. 확정은 사람 승인이 필요합니다.</p>
        </div>
        <div className="system-summary-chips" aria-label="추천 요약">
          <span><strong>{sorted.length}</strong> 추천</span>
          <span><strong>{sorted.filter((item) => item.priority === 'high').length}</strong> 높음</span>
        </div>
      </header>

      {sorted.length ? (
        <div className="ops-queue">
          {sorted.map((item) => (
            <div className="ops-queue-item" key={item.id}>
              <span className={`ops-priority priority-${item.priority}`}>{priorityLabel[item.priority]}</span>
              <div className="ops-queue-copy">
                <strong>{item.subject}</strong>
                <span><ArrowRight size={13} /> {item.action}</span>
              </div>
              <small className="cell-muted">{item.source}</small>
            </div>
          ))}
        </div>
      ) : (
        <div className="ops-empty"><FlaskConical size={22} /><strong>추천 항목이 없습니다.</strong><span>현재 실행에서 파생된 다음 조치가 없습니다.</span></div>
      )}
    </div>
  )
}
