import { AlertTriangle, Beaker, Clock3, Search, ShieldOff } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import MoleculeStructure from '../components/MoleculeStructure'
import StatusBadge from '../components/StatusBadge'
import type { MoleculeSnapshot, RunStatus, ScenarioKind } from '../domain/contracts'

type MoleculeFilter = 'all' | 'low-risk' | 'attention'

function RiskLabel({ value }: { value: MoleculeSnapshot['herg'] }) {
  const label = value === 'Low' ? '낮음' : value === 'Medium' ? '중간' : '높음'
  return <span className={`risk-label risk-${value.toLowerCase()}`}>{label}</span>
}

interface MoleculesViewProps {
  molecules: MoleculeSnapshot[]
  scenarioKind: ScenarioKind
  runStatus: RunStatus
  onOpenFixture: () => void
}

export default function MoleculesView({ molecules, scenarioKind, runStatus, onOpenFixture }: MoleculesViewProps) {
  const [filter, setFilter] = useState<MoleculeFilter>('all')
  const [query, setQuery] = useState('')
  const [selectedId, setSelectedId] = useState(molecules[0]?.id ?? '')

  useEffect(() => {
    if (!molecules.some((item) => item.id === selectedId)) setSelectedId(molecules[0]?.id ?? '')
  }, [molecules, selectedId])

  const visible = useMemo(() => molecules.filter((molecule) => {
    const matchesFilter = filter === 'all'
      || (filter === 'low-risk' && molecule.herg === 'Low' && molecule.ames === 'Low')
      || (filter === 'attention' && (molecule.herg !== 'Low' || molecule.ames !== 'Low'))
    const needle = query.trim().toLowerCase()
    return matchesFilter && (!needle || molecule.id.toLowerCase().includes(needle) || molecule.name.toLowerCase().includes(needle))
  }), [filter, molecules, query])

  if (molecules.length === 0) {
    const isFixtureLoading = scenarioKind === 'molecule-ui-fixture' && (runStatus === 'queued' || runStatus === 'running')
    return (
      <section className="empty-state-panel molecule-empty-state">
        {isFixtureLoading ? <Clock3 size={28} /> : <ShieldOff size={28} />}
        <span className="eyebrow">{isFixtureLoading ? 'Fixture running' : 'Molecule stages not run'}</span>
        <h2>{isFixtureLoading ? '합성 fixture 레코드를 생성하는 중입니다.' : '타깃 기각으로 분자 단계가 실행되지 않았습니다.'}</h2>
        <p>{isFixtureLoading ? '후보 생성 단계가 끝나기 전에는 분자와 proxy 수치를 표시하지 않습니다.' : '후보 생성, 활성 대리평가, ADMET, 합성 가능성 수치는 만들지 않았습니다. 이 빈 상태가 현재 실행의 올바른 결과입니다.'}</p>
        {!isFixtureLoading && <button className="secondary-button" type="button" onClick={onOpenFixture}><Beaker size={16} /> 분자 비교 UI fixture 열기</button>}
      </section>
    )
  }

  const selected = molecules.find((molecule) => molecule.id === selectedId) ?? molecules[0]

  return (
    <div className="molecule-view">
      <section className="synthetic-banner" role="note">
        <AlertTriangle size={17} />
        <div><strong>합성 UI 테스트 데이터</strong><span>아래 분자와 수치는 표, 검색, 위험 상태, RDKit 렌더링을 확인하기 위한 값이며 연구 후보가 아닙니다.</span></div>
      </section>

      <section className="table-panel molecule-table-panel">
        <div className="panel-heading molecule-heading">
          <div><span className="eyebrow">Candidate comparison fixture</span><h2>분자 비교 화면 점검</h2></div>
          <StatusBadge status="synthetic" />
        </div>
        <div className="table-toolbar">
          <div className="segmented-control" aria-label="위험 필터">
            {(['all', 'low-risk', 'attention'] as MoleculeFilter[]).map((value) => {
              const count = value === 'all' ? molecules.length : molecules.filter((item) => value === 'low-risk' ? item.herg === 'Low' && item.ames === 'Low' : item.herg !== 'Low' || item.ames !== 'Low').length
              return <button aria-pressed={filter === value} className={filter === value ? 'is-active' : ''} key={value} onClick={() => setFilter(value)} type="button">{value === 'all' ? '전체' : value === 'low-risk' ? '낮은 표시 위험' : '주의 필요'}<span>{count}</span></button>
            })}
          </div>
          <label className="search-field"><Search size={15} /><span className="sr-only">후보 ID 검색</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="후보 ID 검색" /></label>
        </div>

        <div className="table-scroll molecule-desktop-table">
          <table className="data-table molecule-table">
            <thead><tr><th>RDKit 구조</th><th>레코드</th><th>활성 대리</th><th>QED</th><th>LogP</th><th>TPSA</th><th>hERG</th><th>Ames</th><th>SA proxy</th><th>분류</th></tr></thead>
            <tbody>
              {visible.map((molecule) => (
                <tr className={selected.id === molecule.id ? 'is-selected' : ''} key={molecule.id} onClick={() => setSelectedId(molecule.id)}>
                  <td><MoleculeStructure smiles={molecule.smiles} compact label={`${molecule.id} 구조`} /></td>
                  <td>
                    <button className="row-select-button" type="button" aria-pressed={selected.id === molecule.id} onClick={(event) => { event.stopPropagation(); setSelectedId(molecule.id) }}>
                      <strong className="molecule-id">{molecule.id}</strong><span className="origin-label">{molecule.origin} · Synthetic</span>
                    </button>
                  </td>
                  <td><strong>{molecule.activityProxy.toFixed(2)}</strong><span className="proxy-label">proxy</span></td>
                  <td>{molecule.qed.toFixed(2)}</td><td>{molecule.logP.toFixed(1)}</td><td>{molecule.tpsa.toFixed(1)}</td>
                  <td><RiskLabel value={molecule.herg} /></td><td><RiskLabel value={molecule.ames} /></td>
                  <td>{molecule.synthesisProxy.toFixed(2)}</td><td><StatusBadge status={molecule.decision} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="molecule-mobile-list">
          {visible.map((molecule) => (
            <button className={selected.id === molecule.id ? 'is-selected' : ''} key={molecule.id} onClick={() => setSelectedId(molecule.id)} type="button">
              <MoleculeStructure smiles={molecule.smiles} compact label={`${molecule.id} 구조`} />
              <span><strong>{molecule.id}</strong><small>QED {molecule.qed.toFixed(2)} · Proxy {molecule.activityProxy.toFixed(2)}</small></span>
              <RiskLabel value={molecule.herg} />
            </button>
          ))}
        </div>
        {visible.length === 0 && <div className="empty-table-result">검색 조건에 맞는 합성 레코드가 없습니다.</div>}
      </section>

      <section className="molecule-inspector">
        <div className="molecule-visual">
          <div className="molecule-visual-head"><span>RDKit 2D</span><StatusBadge status="synthetic" /></div>
          <MoleculeStructure smiles={selected.smiles} label={`${selected.id} 분자 구조`} />
          <small>SMILES를 RDKit WebAssembly로 파싱해 렌더링</small>
        </div>
        <div className="molecule-detail">
          <div className="inspector-header molecule-detail-head">
            <div><span className="eyebrow">Selected fixture record</span><h2>{selected.id}</h2><p>{selected.name}</p></div>
            <StatusBadge status={selected.decision} />
          </div>
          <div className="smiles-block"><span>Input SMILES</span><code>{selected.smiles}</code></div>
          <div className="metric-grid">
            <div><span>활성 대리지표</span><strong>{selected.activityProxy.toFixed(2)}</strong><small>합성 UI 값</small></div>
            <div><span>QED</span><strong>{selected.qed.toFixed(2)}</strong><small>합성 UI 값</small></div>
            <div><span>합성 가능성</span><strong>{selected.synthesisProxy.toFixed(2)}</strong><small>{selected.synthesisMethod}</small></div>
          </div>
          <div className="synthesis-disclosure"><strong>합성 평가 범위</strong><span>SA proxy만 표시했습니다. AiZynthFinder 경로 탐색은 실행하지 않았습니다.</span></div>
          <div className="molecule-reason reason-demo_only"><AlertTriangle size={17} /><div><span>레코드 목적</span><strong>{selected.reason}</strong></div></div>
        </div>
      </section>
    </div>
  )
}
