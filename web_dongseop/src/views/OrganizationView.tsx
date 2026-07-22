import { CheckCircle2, Maximize2, Minus, Network, Plus, ShieldCheck, Sparkles } from 'lucide-react'
import { useMemo, useState } from 'react'
import { agentById, h2lAgents, skillById, type H2LAgent } from '../data/agentSystem'

const NODE_W = 280
const NODE_H = 122

const nodePositions: Record<string, { x: number; y: number }> = {
  'research-director': { x: 430, y: 28 },
  'target-intelligence-lead': { x: 70, y: 208 },
  'molecule-discovery-lead': { x: 430, y: 208 },
  'governance-lead': { x: 790, y: 208 },
  'disease-normalizer': { x: 70, y: 390 },
  'evidence-scout': { x: 70, y: 530 },
  'evidence-critic': { x: 70, y: 670 },
  'molecule-optimizer': { x: 430, y: 390 },
  'safety-synthesis-verifier': { x: 430, y: 530 },
  'audit-eval-agent': { x: 790, y: 390 },
  'report-agent': { x: 790, y: 530 },
}

const statusLabel: Record<H2LAgent['status'], string> = {
  active: '운영 가능',
  guarded: '게이트 적용',
  planned: '통합 예정',
}

function connectionPath(parentId: string, childId: string) {
  const parent = nodePositions[parentId]
  const child = nodePositions[childId]
  if (!parent || !child) return ''
  const x1 = parent.x + NODE_W / 2
  const y1 = parent.y + NODE_H
  const x2 = child.x + NODE_W / 2
  const y2 = child.y
  const midY = y1 + Math.max(24, (y2 - y1) / 2)
  return `M ${x1} ${y1} L ${x1} ${midY} L ${x2} ${midY} L ${x2} ${y2}`
}

export default function OrganizationView() {
  const [selectedId, setSelectedId] = useState('research-director')
  const [zoom, setZoom] = useState(0.88)
  const selected = agentById(selectedId) ?? h2lAgents[0]
  const directReports = useMemo(() => h2lAgents.filter((agent) => agent.parentId === selected.id), [selected.id])
  const assignedSkills = selected.skillIds.map((id) => skillById(id)).filter(Boolean)
  const edges = h2lAgents.filter((agent) => agent.parentId).map((agent) => ({ parentId: agent.parentId!, childId: agent.id }))

  return (
    <div className="system-page org-system-page">
      <header className="system-page-header">
        <div>
          <span className="system-kicker"><Network size={14} /> AI 운영 구조</span>
          <h1>H2L-Forge AI 조직도</h1>
          <p>근거 수집과 반증, 분자 게이트, 감사 평가의 책임과 인계 관계를 한 화면에서 확인합니다.</p>
        </div>
        <div className="system-summary-chips" aria-label="조직 요약">
          <span><strong>{h2lAgents.length}</strong> 에이전트</span>
          <span><strong>3</strong> 전문 조직</span>
          <span><ShieldCheck size={14} /><strong>1</strong> 인간 승인 게이트</span>
        </div>
      </header>

      <div className="org-layout">
        <section className="org-chart-panel" aria-label="AI 에이전트 조직도">
          <div className="org-chart-toolbar">
            <div><strong>조직 구조</strong><span>카드를 선택해 책임과 스킬을 확인하세요.</span></div>
            <div className="org-zoom-controls" aria-label="조직도 확대 축소">
              <button type="button" onClick={() => setZoom((value) => Math.min(1.15, value + 0.1))} aria-label="조직도 확대"><Plus size={15} /></button>
              <button type="button" onClick={() => setZoom((value) => Math.max(0.58, value - 0.1))} aria-label="조직도 축소"><Minus size={15} /></button>
              <button type="button" onClick={() => setZoom(0.88)} aria-label="조직도 화면에 맞추기"><Maximize2 size={15} /></button>
              <code>{Math.round(zoom * 100)}%</code>
            </div>
          </div>
          <div className="org-chart-viewport">
            <div className="org-chart-canvas" style={{ transform: `scale(${zoom})` }}>
              <svg aria-hidden="true" viewBox="0 0 1140 840">
                {edges.map((edge) => <path key={`${edge.parentId}-${edge.childId}`} d={connectionPath(edge.parentId, edge.childId)} />)}
              </svg>
              {h2lAgents.map((agent) => {
                const position = nodePositions[agent.id]
                if (!position) return null
                const isSelected = agent.id === selected.id
                return (
                  <button
                    className={`org-agent-card status-${agent.status}${isSelected ? ' is-selected' : ''}`}
                    data-testid={`org-agent-${agent.id}`}
                    key={agent.id}
                    style={{ left: position.x, top: position.y, width: NODE_W, minHeight: NODE_H }}
                    type="button"
                    onClick={() => setSelectedId(agent.id)}
                  >
                    <span className="org-agent-icon">{agent.name.split(' ').map((part) => part[0]).join('').slice(0, 2)}</span>
                    <span className="org-agent-copy"><strong>{agent.name}</strong><small>{agent.role}</small><em>{agent.team}</em></span>
                    <span className="org-agent-status"><i />{statusLabel[agent.status]}</span>
                  </button>
                )
              })}
            </div>
          </div>
        </section>

        <aside className="org-detail-panel">
          <div className="org-detail-title">
            <span className={`org-agent-icon detail-icon status-${selected.status}`}>{selected.name.split(' ').map((part) => part[0]).join('').slice(0, 2)}</span>
            <div><small>{selected.team}</small><h2>{selected.name}</h2><p>{selected.role}</p></div>
          </div>
          <div className={`org-detail-state state-${selected.status}`}><span /><strong>{statusLabel[selected.status]}</strong></div>
          <section><h3>핵심 미션</h3><p>{selected.mission}</p></section>
          <section>
            <h3>보유 스킬 <span>{assignedSkills.length}</span></h3>
            <div className="org-skill-list">
              {assignedSkills.map((skill) => skill && <div key={skill.id}><Sparkles size={14} /><span><strong>{skill.name}</strong><code>{skill.id}</code></span></div>)}
            </div>
          </section>
          <section>
            <h3>주요 산출물</h3>
            <ul>{selected.outputs.map((output) => <li key={output}><CheckCircle2 size={13} />{output}</li>)}</ul>
          </section>
          <section>
            <h3>직속 보고 라인</h3>
            <div className="reporting-line">
              {selected.parentId && <button type="button" onClick={() => setSelectedId(selected.parentId!)}>↑ {agentById(selected.parentId)?.name}</button>}
              {directReports.map((agent) => <button type="button" key={agent.id} onClick={() => setSelectedId(agent.id)}>↓ {agent.name}</button>)}
              {!selected.parentId && directReports.length === 0 && <span>최상위 독립 에이전트</span>}
            </div>
          </section>
        </aside>
      </div>
    </div>
  )
}
