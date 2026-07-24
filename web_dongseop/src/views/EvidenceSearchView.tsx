import { BookOpen, ExternalLink, Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { EvidenceSource } from '../domain/contracts'

const polarityLabel: Record<EvidenceSource['polarity'], string> = {
  supporting: '지지',
  conflicting: '반증',
  neutral: '중립',
}

export default function EvidenceSearchView({ evidence }: { evidence: EvidenceSource[] }) {
  const [query, setQuery] = useState('')

  const visible = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) return evidence
    return evidence.filter((item) =>
      [item.title, item.detail, item.source, item.sourceId].join(' ').toLowerCase().includes(normalized),
    )
  }, [evidence, query])

  const supporting = evidence.filter((item) => item.polarity === 'supporting').length
  const conflicting = evidence.filter((item) => item.polarity === 'conflicting').length

  return (
    <div className="system-page">
      <header className="system-page-header">
        <div>
          <span className="system-kicker"><BookOpen size={14} /> AI·자동화 관리</span>
          <h1>근거 / 논문 검색</h1>
          <p>현재 실행이 참조한 출처 스냅샷을 검색합니다. 지지와 반증 근거를 관측일·출처 ID와 함께 확인하세요.</p>
        </div>
        <div className="system-summary-chips" aria-label="근거 요약">
          <span><strong>{evidence.length}</strong> 근거</span>
          <span><strong>{supporting}</strong> 지지</span>
          <span><strong>{conflicting}</strong> 반증</span>
        </div>
      </header>

      <label className="skill-search ops-search"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="제목, 출처, 근거 ID 검색" /></label>

      {visible.length ? (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr><th>근거</th><th>출처</th><th>구분</th><th>관측일</th><th>링크</th></tr>
            </thead>
            <tbody>
              {visible.map((item) => (
                <tr key={item.id}>
                  <td><strong>{item.title}</strong><small className="cell-sub">{item.detail}</small></td>
                  <td>{item.source}<small className="cell-sub">{item.sourceId}</small></td>
                  <td><span className={`ops-polarity polarity-${item.polarity}`}>{polarityLabel[item.polarity]}</span></td>
                  <td className="cell-muted">{item.observedAt}</td>
                  <td><a className="ops-link" href={item.href} target="_blank" rel="noreferrer"><ExternalLink size={13} /> 열기</a></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="ops-empty"><Search size={22} /><strong>검색 결과가 없습니다.</strong><span>다른 제목이나 출처 ID로 검색하세요.</span></div>
      )}
    </div>
  )
}
