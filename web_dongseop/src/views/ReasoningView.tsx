import { AlertTriangle, BrainCircuit, Cpu, FileText, ShieldCheck, Sparkles } from 'lucide-react'
import { useState } from 'react'
import type { ExplainInput, Explanation, RunSnapshot } from '../domain/contracts'

interface ReasoningViewProps {
  snapshot: RunSnapshot
  onExplain: (input: ExplainInput) => Promise<Explanation>
}

/**
 * 판단 해설. 로컬 모델이 문장을 쓰고, 가드레일이 통과시킨 것만 표시합니다.
 * 판정·규칙·근거 ID는 결정 엔진이 계산한 값이며 해설이 바꾸지 않습니다.
 */
export default function ReasoningView({ snapshot, onExplain }: ReasoningViewProps) {
  const [explanations, setExplanations] = useState<Record<string, Explanation>>({})
  const [pending, setPending] = useState<string | null>(null)
  const [failure, setFailure] = useState<string | null>(null)

  const handleExplain = async (symbol: string) => {
    setPending(symbol)
    setFailure(null)
    try {
      const result = await onExplain({ targetSymbol: symbol, disease: snapshot.run.disease })
      setExplanations((current) => ({ ...current, [symbol]: result }))
    } catch (cause) {
      setFailure(cause instanceof Error ? cause.message : '해설을 생성하지 못했습니다.')
    } finally {
      setPending(null)
    }
  }

  const modelBacked = Object.values(explanations).filter((item) => item.source === 'model').length
  const blocked = Object.values(explanations).filter((item) => item.violations.length > 0).length

  return (
    <div className="system-page">
      <header className="system-page-header">
        <div>
          <span className="system-kicker"><BrainCircuit size={14} /> AI·자동화 관리</span>
          <h1>판단 해설</h1>
          <p>
            로컬 모델이 판정 결과를 문장으로 옮깁니다. 모델은 새로운 사실을 만들 수 없고, 출력은 숫자·근거 ID·치료
            주장 검사를 통과해야 표시됩니다. 검사에 걸리면 결정론적 문장으로 대체합니다.
          </p>
        </div>
        <div className="system-summary-chips" aria-label="해설 요약">
          <span><strong>{snapshot.targets.length}</strong> 타깃</span>
          <span><Cpu size={14} /><strong>{modelBacked}</strong> 모델 생성</span>
          <span><ShieldCheck size={14} /><strong>{blocked}</strong> 가드레일 차단</span>
        </div>
      </header>

      {failure && <div className="ops-empty"><AlertTriangle size={22} /><strong>해설을 생성하지 못했습니다.</strong><span>{failure}</span></div>}

      {snapshot.targets.length ? (
        <div className="ops-reason-list">
          {snapshot.targets.map((target) => {
            const explanation = explanations[target.symbol]
            const isPending = pending === target.symbol
            return (
              <article className="ops-reason-card" key={target.symbol}>
                <div className="ops-reason-head">
                  <div className="ops-reason-title">
                    <strong>{target.symbol}</strong>
                    <small className="cell-sub">{target.name}</small>
                  </div>
                  <button className="secondary-button" type="button" disabled={isPending} onClick={() => { void handleExplain(target.symbol) }}>
                    <Sparkles size={15} /> {isPending ? '생성 중' : explanation ? '다시 생성' : '해설 생성'}
                  </button>
                </div>

                {explanation ? (
                  <>
                    <p className="ops-reason-text">{explanation.text}</p>
                    <div className="ops-reason-meta">
                      <span className={`ops-source source-${explanation.source}`}>
                        {explanation.source === 'model' ? <Cpu size={13} /> : <FileText size={13} />}
                        {explanation.source === 'model' ? `로컬 모델 · ${explanation.model ?? '알 수 없음'}` : '결정론적 템플릿'}
                      </span>
                      <span className="ops-source source-decision">판정 {explanation.decision}</span>
                      {explanation.evidenceIds.length > 0 && (
                        <span className="cell-muted">근거 {explanation.evidenceIds.join(', ')}</span>
                      )}
                    </div>
                    {explanation.violations.length > 0 && (
                      <p className="ops-reason-guard">
                        <ShieldCheck size={13} /> 가드레일이 모델 출력을 차단했습니다: {explanation.violations.join(', ')}
                      </p>
                    )}
                    {explanation.source === 'template' && explanation.fallbackReason && (
                      <p className="ops-reason-note">{explanation.fallbackReason}</p>
                    )}
                  </>
                ) : (
                  <p className="ops-reason-note">
                    아직 해설을 생성하지 않았습니다. 판정 근거는 타깃 화면과 감사 기록에 이미 기록되어 있습니다.
                  </p>
                )}
              </article>
            )
          })}
        </div>
      ) : (
        <div className="ops-empty"><BrainCircuit size={22} /><strong>해설할 타깃이 없습니다.</strong><span>타깃 판단이 끝난 실행을 선택하세요.</span></div>
      )}
    </div>
  )
}
