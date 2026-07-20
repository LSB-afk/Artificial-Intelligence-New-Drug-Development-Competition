import { AlertTriangle, ArrowDownRight, ExternalLink, FlaskConical, ShieldCheck } from 'lucide-react'
import { useMemo } from 'react'
import StatusBadge from '../components/StatusBadge'
import type { EvidenceSource, TargetSnapshot } from '../domain/contracts'

interface TargetsProps {
  targets: TargetSnapshot[]
  evidence: EvidenceSource[]
  selectedSymbol: string
  onSelect: (symbol: string) => void
}

export default function TargetsView({ targets, evidence, selectedSymbol, onSelect }: TargetsProps) {
  const selected = targets.find((target) => target.symbol === selectedSymbol) ?? targets[0]
  const selectedEvidence = useMemo(
    () => selected ? evidence.filter((item) => selected.evidenceIds.includes(item.id)) : [],
    [evidence, selected],
  )

  if (!selected) {
    return (
      <section className="empty-state-panel">
        <FlaskConical size={26} />
        <h2>이 실행은 타깃 연구 결과를 포함하지 않습니다.</h2>
        <p>분자 비교 UI fixture는 화면 동작 확인용 합성 데이터입니다. 타깃 판단은 IBD 근거 검토 실행에서 확인하세요.</p>
      </section>
    )
  }

  return (
    <div className="data-split-view">
      <section className="table-panel">
        <div className="panel-heading">
          <div><h2>타깃 우선순위</h2></div>
          <div className="heading-note">출처 점수와 내부 운영 점수를 분리해 표시</div>
        </div>
        <div className="table-scroll">
          <table className="data-table target-table">
            <thead><tr><th>순위</th><th>타깃</th><th>연관 점수</th><th>Tractability</th><th>Assay</th><th>임상 근거</th><th>판단</th></tr></thead>
            <tbody>
              {targets.map((target) => (
                <tr
                  className={selected.symbol === target.symbol ? 'is-selected' : ''}
                  key={target.symbol}
                  onClick={() => onSelect(target.symbol)}
                >
                  <td className="rank-cell">{target.rank}</td>
                  <td>
                    <button className="row-select-button" type="button" aria-pressed={selected.symbol === target.symbol} onClick={(event) => { event.stopPropagation(); onSelect(target.symbol) }}>
                      <strong className="target-symbol">{target.symbol}</strong><span className="target-name">{target.name}</span>
                    </button>
                  </td>
                  <td><div className="metric-with-bar"><strong>{target.association.toFixed(4)}</strong><span><i style={{ width: `${target.association * 100}%` }} /></span></div></td>
                  <td><span className={`tractability tract-${target.tractability.toLowerCase()}`}>{target.tractability}</span></td>
                  <td>{target.assay}</td><td>{target.clinical}</td><td><StatusBadge status={target.decision} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="table-caption"><AlertTriangle size={14} />Association score는 출처 값이고, 비평 전후 점수는 다음 행동을 위한 계산값입니다.</div>
      </section>

      <aside className="inspector-panel">
        <div className="inspector-header">
          <div><h2>{selected.symbol}</h2><p>{selected.name}</p></div>
          <StatusBadge status={selected.decision} />
        </div>
        <div className="score-change-card">
          <div><span>비평 전</span><strong>{selected.scoreBefore}</strong></div><ArrowDownRight size={20} />
          <div><span>비평 후</span><strong>{selected.scoreAfter}</strong></div><span className="score-delta">{selected.scoreAfter - selected.scoreBefore}</span>
        </div>
        <div className="inspector-section score-factor-section">
          <h3><ShieldCheck size={16} /> 점수 산정 내역</h3>
          <div className="factor-list">
            {selected.scoreFactors.map((factor) => <div key={factor.id}><span>{factor.label}</span><strong className={factor.impact < 0 ? 'is-negative' : 'is-positive'}>{factor.impact > 0 ? '+' : ''}{factor.impact}</strong></div>)}
          </div>
        </div>
        <div className="inspector-section"><h3><ShieldCheck size={16} /> 판단 근거</h3><p>{selected.rationale}</p></div>
        <div className="inspector-section caution-section"><h3><AlertTriangle size={16} /> 해석 주의</h3><p>{selected.caution}</p></div>
        <div className="inspector-section">
          <h3><FlaskConical size={16} /> 연결된 근거</h3>
          <div className="inspector-sources">
            {selectedEvidence.length > 0 ? selectedEvidence.map((item) => (
              <a href={item.href} key={item.id} target="_blank" rel="noreferrer">
                <span className={`source-polarity ${item.polarity}`}>{item.polarity === 'supporting' ? '지지' : item.polarity === 'conflicting' ? '반증' : '중립'}</span>
                <div><strong>{item.title}</strong><small>{item.source} · {item.sourceId}</small></div><ExternalLink size={13} />
              </a>
            )) : <p className="empty-copy">현재 스냅샷에 연결된 상세 근거가 없습니다.</p>}
          </div>
        </div>
      </aside>
    </div>
  )
}
