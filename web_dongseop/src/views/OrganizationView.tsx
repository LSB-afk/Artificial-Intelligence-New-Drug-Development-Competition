import { CheckCircle2, Maximize2, Minus, Network, Plus, ShieldCheck, Sparkles } from 'lucide-react'
import { useLayoutEffect, useMemo, useRef, useState } from 'react'
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
  // zoom === null 이면 뷰포트 크기에 맞춰 자동 축소해 스크롤 없이 전부 보이게 합니다.
  const [zoom, setZoom] = useState<number | null>(null)
  const [fitScale, setFitScale] = useState(0.8)
  const viewportRef = useRef<HTMLDivElement>(null)
  const selected = agentById(selectedId) ?? h2lAgents[0]
  const directReports = useMemo(() => h2lAgents.filter((agent) => agent.parentId === selected.id), [selected.id])
  const assignedSkills = selected.skillIds.map((id) => skillById(id)).filter(Boolean)
  const edges = h2lAgents.filter((agent) => agent.parentId).map((agent) => ({ parentId: agent.parentId!, childId: agent.id }))

  // 1140x840 캔버스 전체를 담을 배율을 뷰포트 크기에서 계산합니다(스크롤 없이 전부 보이기).
  // useLayoutEffect: 첫 페인트 전에 정확한 값을 정해 80%→77% 같은 줄어드는 애니메이션을 없앱니다.
  useLayoutEffect(() => {
    const el = viewportRef.current
    if (!el) return
    const compute = () => {
      const w = el.clientWidth - 24
      const h = el.clientHeight - 24
      if (w <= 0 || h <= 0) return
      const next = Math.max(0.25, Math.min(1, Math.min(w / 1140, h / 840)))
      // 미세한 변화는 무시해 스크롤바 토글 등으로 인한 진동(덜덜 떨림)을 막습니다.
      setFitScale((prev) => (Math.abs(prev - next) > 0.004 ? next : prev))
    }
    compute()
    const observer = new ResizeObserver(compute)
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const activeZoom = zoom ?? fitScale

  return (
    <div className="system-page org-system-page">
      <header className="system-page-header">
        <div>
          <span className="system-kicker"><Network size={14} /> AI 운영 구조</span>
          <h1>H2L-Forge AI 조직도</h1>
          <p>근거 수집과 반증, 분자 게이트, 감사 평가의 책임과 인계 관계를 한 화면에서 확인합니다. 이 조직도는 <strong>설계 로스터(11개 역할)</strong>이며, 실제 백엔드 실행은 승인된 가설(현재 2건: IBD:TYK2, IBD:DEMO-POS)을 대상으로 단일 행동선택 루프를 돌립니다.</p>
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
              <button type="button" onClick={() => setZoom(Math.min(1.15, activeZoom + 0.1))} aria-label="조직도 확대"><Plus size={15} /></button>
              <button type="button" onClick={() => setZoom(Math.max(0.3, activeZoom - 0.1))} aria-label="조직도 축소"><Minus size={15} /></button>
              <button type="button" onClick={() => setZoom(null)} aria-label="화면에 맞추기"><Maximize2 size={15} /></button>
              <code>{Math.round(activeZoom * 100)}%</code>
            </div>
          </div>
          <div className="org-chart-viewport" ref={viewportRef}>
            <div className="org-chart-scaler" style={{ width: 1140 * activeZoom, height: 840 * activeZoom }}>
            <div className="org-chart-canvas" style={{ transform: `scale(${activeZoom})` }}>
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
