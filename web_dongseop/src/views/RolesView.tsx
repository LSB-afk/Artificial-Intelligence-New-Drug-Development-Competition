import { ShieldCheck, Users } from 'lucide-react'
import { h2lRoles } from '../data/agentSystem'

export default function RolesView() {
  const approvers = h2lRoles.filter((role) => role.canApprove.length > 0).length

  return (
    <div className="system-page">
      <header className="system-page-header">
        <div>
          <span className="system-kicker"><Users size={14} /> AI·자동화 관리</span>
          <h1>담당자 / 권한</h1>
          <p>역할별 승인 범위입니다. AI 에이전트는 제안만 하고, 고위험·규제·환자 영향 결정은 해당 범위 담당자만 승인합니다.</p>
        </div>
        <div className="system-summary-chips" aria-label="담당자 요약">
          <span><strong>{h2lRoles.length}</strong> 역할</span>
          <span><ShieldCheck size={14} /><strong>{approvers}</strong> 승인 권한</span>
        </div>
      </header>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr><th>역할</th><th>범위</th><th>승인 가능 범위</th><th>주요 책임</th><th>소속</th></tr>
          </thead>
          <tbody>
            {h2lRoles.map((role) => (
              <tr key={role.id}>
                <td><strong>{role.name}</strong><small className="cell-sub">{role.id}</small></td>
                <td><code>{role.scope}</code></td>
                <td>{role.canApprove.length ? role.canApprove.join(', ') : <span className="cell-muted">승인 권한 없음</span>}</td>
                <td className="cell-muted">{role.responsibility}</td>
                <td>{role.team}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
