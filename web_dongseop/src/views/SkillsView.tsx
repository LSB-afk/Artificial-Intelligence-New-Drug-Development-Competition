import { Boxes, CheckCircle2, FileCode2, LockKeyhole, Search, ShieldCheck, UserRoundCog } from 'lucide-react'
import { useMemo, useState } from 'react'
import { agentById, h2lSkills, skillCategories, type H2LSkill, type SkillCategory } from '../data/agentSystem'

const statusLabel: Record<H2LSkill['status'], string> = {
  ready: '사용 가능',
  guarded: '승인 필요',
  planned: '통합 예정',
}

export default function SkillsView() {
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState<'전체' | SkillCategory>('전체')
  const [selectedId, setSelectedId] = useState(h2lSkills[0].id)

  const visible = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    return h2lSkills.filter((skill) => {
      const categoryMatch = category === '전체' || skill.category === category
      const queryMatch = !normalized || [skill.id, skill.name, skill.description, ...skill.capabilities].join(' ').toLowerCase().includes(normalized)
      return categoryMatch && queryMatch
    })
  }, [category, query])

  const selected = h2lSkills.find((skill) => skill.id === selectedId) ?? visible[0] ?? h2lSkills[0]
  const readyCount = h2lSkills.filter((skill) => skill.status === 'ready').length
  const ownerNames = selected.ownerIds.map((id) => agentById(id)?.name).filter(Boolean)

  return (
    <div className="system-page skills-system-page">
      <header className="system-page-header">
        <div>
          <span className="system-kicker"><Boxes size={14} /> Project skill catalog</span>
          <h1>AI 에이전트 스킬</h1>
          <p>실제 <code>03_에이전트/skills</code> 패키지와 담당 에이전트, 실행 경계를 연결한 프로젝트 카탈로그입니다.</p>
        </div>
        <div className="system-summary-chips" aria-label="스킬 요약">
          <span><strong>{h2lSkills.length}</strong> 전체 스킬</span>
          <span><CheckCircle2 size={14} /><strong>{readyCount}</strong> 사용 가능</span>
          <span><LockKeyhole size={14} /><strong>{h2lSkills.length - readyCount}</strong> 게이트·예정</span>
        </div>
      </header>

      <div className="skill-toolbar">
        <label className="skill-search"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="스킬 이름, 기능, ID 검색" /></label>
        <div className="skill-category-tabs" aria-label="스킬 카테고리">
          {skillCategories.map((item) => <button aria-pressed={category === item} className={category === item ? 'is-active' : ''} key={item} type="button" onClick={() => setCategory(item)}>{item}</button>)}
        </div>
      </div>

      <div className="skill-studio-layout">
        <aside className="skill-folder-rail">
          <div className="skill-rail-heading"><strong>카테고리</strong><span>{h2lSkills.length}</span></div>
          {skillCategories.map((item) => {
            const count = item === '전체' ? h2lSkills.length : h2lSkills.filter((skill) => skill.category === item).length
            return <button className={category === item ? 'is-active' : ''} key={item} type="button" onClick={() => setCategory(item)}><span>{item}</span><small>{count}</small></button>
          })}
          <div className="skill-source-note"><FileCode2 size={16} /><div><strong>Repository managed</strong><span>SKILL.md + openai.yaml</span></div></div>
        </aside>

        <section className="skill-discovery-panel">
          <div className="skill-panel-heading"><div><strong>{category === '전체' ? '전체 스킬' : category}</strong><span>{visible.length}개 표시</span></div><small>카드를 선택해 세부 계약을 확인하세요.</small></div>
          {visible.length ? (
            <div className="skill-card-grid">
              {visible.map((skill) => {
                const isSelected = skill.id === selected.id
                return (
                  <button className={`skill-catalog-card${isSelected ? ' is-selected' : ''}`} data-testid={`skill-card-${skill.id}`} key={skill.id} type="button" onClick={() => setSelectedId(skill.id)}>
                    <span className="skill-card-icon" style={{ background: skill.accent }}>{skill.id[0].toUpperCase()}</span>
                    <span className="skill-card-main"><span className="skill-card-title"><strong>{skill.name}</strong><em className={`skill-status status-${skill.status}`}>{statusLabel[skill.status]}</em></span><code>{skill.id}</code><p>{skill.description}</p></span>
                    <span className="skill-card-footer"><em>{skill.category}</em><span><UserRoundCog size={13} /> {skill.ownerIds.length} agents</span><small>{skill.version}</small></span>
                  </button>
                )
              })}
            </div>
          ) : <div className="skill-empty"><Search size={22} /><strong>검색 결과가 없습니다.</strong><span>다른 이름이나 카테고리로 검색하세요.</span></div>}
        </section>

        <aside className="skill-detail-panel">
          <div className="skill-detail-heading"><span className="skill-card-icon" style={{ background: selected.accent }}>{selected.id[0].toUpperCase()}</span><div><small>{selected.category}</small><h2>{selected.name}</h2><code>{selected.id}</code></div></div>
          <div className={`skill-detail-status status-${selected.status}`}><span /><strong>{statusLabel[selected.status]}</strong><small>{selected.version}</small></div>
          <p className="skill-detail-description">{selected.description}</p>
          <section><h3>담당 에이전트</h3><div className="skill-owner-list">{ownerNames.map((name) => <span key={name}><UserRoundCog size={13} />{name}</span>)}</div></section>
          <section><h3>핵심 기능</h3><ul>{selected.capabilities.map((item) => <li key={item}><CheckCircle2 size={13} />{item}</li>)}</ul></section>
          <section className="skill-guardrail"><h3><ShieldCheck size={15} /> 실행 경계</h3><p>{selected.guardrail}</p></section>
          <section><h3>저장소 출처</h3><code className="skill-source-path">{selected.sourcePath}</code></section>
        </aside>
      </div>
    </div>
  )
}
