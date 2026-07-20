import { AlertTriangle, ArrowRight, Ban, CheckCircle2, FlaskConical, Wrench } from 'lucide-react'
import type { FailureRecord } from '../domain/contracts'

const kindIcons = {
  Target: FlaskConical,
  Molecule: AlertTriangle,
  Tool: Wrench,
  Policy: Ban,
}

export default function FailuresView({ failures }: { failures: FailureRecord[] }) {
  if (failures.length === 0) {
    return (
      <section className="empty-state-panel">
        <CheckCircle2 size={28} />
        <h2>이 실행에는 기록된 실패나 정책 중단이 없습니다.</h2>
        <p>합성 UI fixture의 정상 렌더링 상태입니다. 실제 하네스에서는 실패 원인과 다음 행동이 같은 계약으로 들어옵니다.</p>
      </section>
    )
  }

  const targetCount = failures.filter((failure) => failure.kind === 'Target').length
  const toolCount = failures.filter((failure) => failure.kind === 'Tool').length
  const policyCount = failures.filter((failure) => failure.kind === 'Policy').length

  return (
    <section className="table-panel failure-panel">
      <div className="panel-heading">
        <div><h2>실패와 미실행 기록</h2></div>
        <div className="heading-note">결과를 만들지 않은 이유도 감사 대상입니다.</div>
      </div>
      <div className="failure-summary-strip">
        <div><strong>{failures.length}</strong><span>전체 기록</span></div>
        <div><strong>{targetCount}</strong><span>타깃 기각</span></div>
        <div><strong>{policyCount}</strong><span>정책 중단</span></div>
        <div><strong>{toolCount}</strong><span>도구 장애</span></div>
        <div className="recovery-note"><Ban size={18} /><span>가짜 후속 결과를 만들지 않았습니다.</span></div>
      </div>
      <div className="failure-list">
        {failures.map((failure) => {
          const Icon = kindIcons[failure.kind]
          return (
            <article className={`failure-row severity-${failure.severity}`} key={failure.id}>
              <div className="failure-kind"><Icon size={18} /><span>{failure.kind}</span></div>
              <div className="failure-subject"><strong>{failure.subject}</strong><span>{failure.stage} · {failure.time}</span></div>
              <div className="failure-reason"><span>중단 이유</span><p>{failure.reason}</p></div>
              <ArrowRight className="failure-arrow" size={18} />
              <div className="failure-action"><span>다음 행동</span><p>{failure.nextAction}</p></div>
            </article>
          )
        })}
      </div>
    </section>
  )
}
