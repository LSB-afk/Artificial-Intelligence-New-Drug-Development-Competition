import { AlertTriangle, Ban, Check, Clock3, Eye, FlaskConical, LoaderCircle, Minus, X } from 'lucide-react'
import type { Decision, RunStatus, StageStatus } from '../domain/contracts'

type BadgeStatus = RunStatus | StageStatus | Decision | 'source_snapshot' | 'computed' | 'synthetic'

const labels: Record<BadgeStatus, string> = {
  queued: '대기',
  running: '실행 중',
  awaiting_review: '검토 대기',
  completed: '완료',
  completed_with_warnings: '주의 후 완료',
  warning: '주의',
  failed: '실패',
  cancelled: '취소',
  skipped: '미실행',
  blocked: '차단',
  review: '재검토',
  rejected: '기각',
  insufficient: '데이터 부족',
  reference_only: '참조 전용',
  demo_only: 'UI 테스트',
  source_snapshot: '출처 스냅샷',
  computed: '계산값',
  synthetic: '합성 데이터',
}

function BadgeIcon({ status }: { status: BadgeStatus }) {
  if (status === 'completed') return <Check size={12} />
  if (status === 'running') return <LoaderCircle size={12} className="spin" />
  if (status === 'warning' || status === 'awaiting_review' || status === 'completed_with_warnings' || status === 'review' || status === 'insufficient') return <AlertTriangle size={12} />
  if (status === 'failed' || status === 'rejected') return <X size={12} />
  if (status === 'cancelled' || status === 'blocked') return <Ban size={12} />
  if (status === 'skipped') return <Minus size={12} />
  if (status === 'demo_only' || status === 'synthetic') return <FlaskConical size={12} />
  if (status === 'reference_only' || status === 'source_snapshot') return <Eye size={12} />
  return <Clock3 size={12} />
}

export default function StatusBadge({ status }: { status: BadgeStatus }) {
  return <span className={`status-badge status-${status}`}><BadgeIcon status={status} />{labels[status]}</span>
}
