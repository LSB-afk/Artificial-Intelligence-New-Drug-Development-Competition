import { Bot, CheckCircle2, ShieldCheck } from 'lucide-react'
import { h2lAgents, type H2LAgent } from '../data/agentSystem'

const statusLabel: Record<H2LAgent['status'], string> = {
  active: '운영 가능',
  guarded: '게이트 적용',
  planned: '통합 예정',
}

const teamOrder = ['Executive', 'Target Intelligence', 'Molecule Discovery', 'Governance']

export default function AgentHarnessView() {
  const activeCount = h2lAgents.filter((agent) => agent.status === 'active').length
  const guardedCount = h2lAgents.filter((agent) => agent.status !== 'active').length
  const teams = teamOrder.filter((team) => h2lAgents.some((agent) => agent.team === team))

  return (
    <div className="system-page">
      <header className="system-page-header">
        <div>
          <span className="system-kicker"><Bot size={14} /> AI·자동화 관리</span>
          <h1>신약개발 Agent 하네스</h1>
          <p>질병 근거 수집부터 분자 게이트, 감사 평가까지 담당하는 에이전트 로스터입니다. 실행은 근거·판단·승인 상태를 남깁니다.</p>
        </div>
        <div className="system-summary-chips" aria-label="Agent 하네스 요약">
          <span><strong>{h2lAgents.length}</strong> 에이전트</span>
          <span><CheckCircle2 size={14} /><strong>{activeCount}</strong> 운영 가능</span>
          <span><ShieldCheck size={14} /><strong>{guardedCount}</strong> 게이트·예정</span>
        </div>
      </header>

      {teams.map((team) => (
        <section className="ops-group" key={team}>
          <div className="ops-group-heading"><strong>{team}</strong><span>{h2lAgents.filter((agent) => agent.team === team).length}</span></div>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr><th>에이전트</th><th>역할</th><th>상태</th><th>주요 산출물</th></tr>
              </thead>
              <tbody>
                {h2lAgents.filter((agent) => agent.team === team).map((agent) => (
                  <tr key={agent.id}>
                    <td><strong>{agent.name}</strong><small className="cell-sub">{agent.id}</small></td>
                    <td>{agent.role}</td>
                    <td><span className={`ops-status status-${agent.status}`}><i />{statusLabel[agent.status]}</span></td>
                    <td className="cell-muted">{agent.outputs.join(' · ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </div>
  )
}
