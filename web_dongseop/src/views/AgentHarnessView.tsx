import { AlertTriangle, Bot, Cpu, FileText, FlaskConical, PlayCircle, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import {
  OFFLINE_ACTIONS,
  listHypotheses,
  listModels,
  listScenarios,
  runAgent,
  runSandbox,
  type AgentAction,
  type AgentRun,
  type ModelCatalog,
  type Scenario,
} from '../services/agentService'

/**
 * 신약개발 Agent 하네스.
 *
 * 이 화면은 로스터가 아니라 **실행 기록**입니다. 각 단계의 관측·거부·판정은
 * 파이썬 하네스가 결정론적으로 실행하며 쓴 값이고, 로컬 모델의 권한은 "다음에
 * 어떤 행동을 실행할지 고르는 것" 하나뿐입니다. 그래서 단계마다 모델이 골랐는지
 * 정책이 대신 골랐는지를 그대로 표시합니다 — 모델이 실제로 얼마나 운전했는지
 * 감출 이유가 없습니다.
 *
 * 게이트는 선택이 아니라 실행에서 막습니다. 거절된 타깃에 분자 최적화를
 * 제안하는 것은 허용되고, 하네스가 그것을 거부한 기록이 남습니다.
 *
 * 등록된 가설 두 건만 돌릴 수 있으면 "스스로 기각한다"는 주장을 밖에서 확인할
 * 방법이 없으므로, 판정관이 직접 쓴 근거 패킷도 같은 루프에 넣을 수 있습니다.
 * 그 패킷은 저장되지 않고 승인도 받지 않으며, 승인 기록이 없으니 판정이
 * ADVANCE여도 분자 게이트는 닫힌 채로 남습니다.
 */
export default function AgentHarnessView() {
  const [catalog, setCatalog] = useState<ModelCatalog | null>(null)
  const [hypotheses, setHypotheses] = useState<string[]>([])
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [goal, setGoal] = useState('')
  const [model, setModel] = useState('')
  const [preset, setPreset] = useState<Scenario | null>(null)
  const [draft, setDraft] = useState('')
  const [run, setRun] = useState<AgentRun | null>(null)
  const [pending, setPending] = useState(false)
  const [failure, setFailure] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      const [models, ids, presets] = await Promise.all([listModels(), listHypotheses(), listScenarios()])
      if (cancelled) return
      setCatalog(models)
      setHypotheses(ids)
      setScenarios(presets)
      setGoal((current) => current || ids[0] || '')
      setModel((current) => current || models.defaultModel || '')
    })()
    return () => { cancelled = true }
  }, [])

  const execute = async (task: () => Promise<AgentRun>) => {
    setPending(true)
    setFailure(null)
    try {
      setRun(await task())
    } catch (cause) {
      setRun(null)
      setFailure(cause instanceof Error ? cause.message : '에이전트를 실행하지 못했습니다.')
    } finally {
      setPending(false)
    }
  }

  const handleRun = () => {
    if (goal) void execute(() => runAgent(goal, model || null))
  }

  /** 붙여넣은 텍스트는 여기서 파싱합니다. 서버까지 보내고 400을 받는 것보다 빠릅니다. */
  const handleSandboxRun = () => {
    let packet: unknown
    try {
      packet = JSON.parse(draft)
    } catch (cause) {
      setRun(null)
      setFailure(`JSON을 읽지 못했습니다: ${cause instanceof Error ? cause.message : '형식 오류'}`)
      return
    }
    void execute(() => runSandbox(packet, model || null))
  }

  const applyPreset = (scenario: Scenario) => {
    setPreset(scenario)
    setDraft(JSON.stringify(scenario.packet, null, 2))
  }

  const actions: AgentAction[] = run?.actions ?? OFFLINE_ACTIONS
  const offline = catalog !== null && !catalog.reachable && run === null

  return (
    <div className="system-page">
      <header className="system-page-header">
        <div>
          <span className="system-kicker"><Bot size={14} /> AI·자동화 관리</span>
          <h1>신약개발 Agent 하네스</h1>
          <p>
            로컬 모델은 다음에 실행할 행동만 고르고, 관측과 판정은 결정론적 코드가 씁니다. 모델이 고르지 못한
            단계는 고정 정책이 대신 고르며 그 사실을 함께 기록합니다. 게이트는 선택이 아니라 실행에서 막습니다.
          </p>
        </div>
        <div className="system-summary-chips" aria-label="에이전트 실행 요약">
          <span><strong>{run ? run.steps.length : 0}</strong> 실행 단계</span>
          <span><Cpu size={14} /><strong>{run ? run.modelSelectedSteps : 0}</strong> 모델 선택</span>
          <span><ShieldCheck size={14} /><strong>{run ? run.refusedSteps.length : 0}</strong> 게이트 거부</span>
        </div>
      </header>

      <section className="ops-group">
        <div className="ops-group-heading"><strong>실행</strong><span>{catalog?.installed.length ?? 0} models</span></div>
        <div className="ops-reason-card">
          <div className="ops-reason-head">
            <div className="ops-reason-title">
              <strong>{goal || '가설 없음'}</strong>
              <small className="cell-sub">
                {catalog?.reachable
                  ? `${catalog.host} · 모델 ${catalog.installed.length}개`
                  : '하네스 오프라인'}
              </small>
            </div>
            <button className="secondary-button" type="button" disabled={pending || !goal} onClick={handleRun}>
              <PlayCircle size={15} /> {pending ? '실행 중' : run ? '다시 실행' : '에이전트 실행'}
            </button>
          </div>

          <div className="ops-reason-meta">
            <label className="ops-source source-decision">
              가설
              <select aria-label="가설 선택" value={goal} onChange={(event) => setGoal(event.target.value)} disabled={pending || !hypotheses.length}>
                {hypotheses.length ? hypotheses.map((id) => <option key={id} value={id}>{id}</option>) : <option value="">사용 가능한 가설 없음</option>}
              </select>
            </label>
            <label className="ops-source source-model">
              모델
              <select aria-label="모델 선택" value={model} onChange={(event) => setModel(event.target.value)} disabled={pending || !catalog?.installed.length}>
                {catalog?.installed.length
                  ? catalog.installed.map((name) => <option key={name} value={name}>{name}</option>)
                  : <option value="">설치된 모델 없음</option>}
              </select>
            </label>
            {run && (
              <span className={`ops-source source-${run.explanation.source}`}>
                {run.explanation.source === 'model' ? <Cpu size={13} /> : <FileText size={13} />}
                {run.explanation.source === 'model' ? `모델 문장 · ${run.explanation.model ?? '알 수 없음'}` : '결정론적 템플릿'}
              </span>
            )}
          </div>

          {catalog && !catalog.reachable && <p className="ops-reason-note">{catalog.note}</p>}
        </div>
      </section>

      <section className="ops-group">
        <div className="ops-group-heading">
          <strong>시나리오 직접 입력</strong>
          <span>{scenarios.length} 프리셋</span>
        </div>
        <div className="ops-reason-card">
          <div className="ops-reason-head">
            <div className="ops-reason-title">
              <strong>{preset ? preset.label : '근거 패킷'}</strong>
              <small className="cell-sub">
                {preset
                  ? preset.note
                  : '프리셋을 고르거나 근거 패킷 JSON을 직접 붙여넣으세요. 제출한 패킷은 저장되지 않고 승인도 받지 않습니다.'}
              </small>
            </div>
            <button
              className="secondary-button"
              type="button"
              disabled={pending || !draft.trim()}
              onClick={handleSandboxRun}
            >
              <FlaskConical size={15} /> {pending ? '실행 중' : '이 패킷으로 실행'}
            </button>
          </div>

          {scenarios.length > 0 && (
            <div className="ops-reason-meta" role="group" aria-label="프리셋 시나리오">
              {scenarios.map((scenario) => (
                <button
                  key={scenario.id}
                  type="button"
                  className="secondary-button"
                  aria-pressed={preset?.id === scenario.id}
                  disabled={pending}
                  onClick={() => applyPreset(scenario)}
                >
                  {scenario.label}
                </button>
              ))}
            </div>
          )}

          <textarea
            className="packet-input"
            aria-label="근거 패킷 JSON"
            spellCheck={false}
            value={draft}
            disabled={pending}
            placeholder={'{\n  "hypothesis_id": "MY:TARGET",\n  "disease_id": "FIX:MY-DISEASE",\n  "indication_ids": ["FIX:MY-DISEASE"],\n  "target": "MY-TARGET",\n  "observed_at": "2026-07-25T00:00:00Z",\n  "records": []\n}'}
            onChange={(event) => { setDraft(event.target.value); setPreset(null) }}
          />

          {preset && <p className="ops-reason-note">하네스가 계산할 판정: {preset.expectation}</p>}
        </div>
      </section>

      {failure && (
        <div className="ops-empty">
          <AlertTriangle size={22} /><strong>에이전트를 실행하지 못했습니다.</strong><span>{failure}</span>
        </div>
      )}

      {run && (
        <section className="ops-group">
          <div className="ops-group-heading">
            <strong>실행 기록</strong>
            <span>{run.modelSelectedSteps} model · {run.policySelectedSteps} policy</span>
          </div>
          <div className="ops-reason-list">
            {run.steps.map((step) => (
              <article className="ops-reason-card" key={step.step}>
                <div className="ops-reason-head">
                  <div className="ops-reason-title">
                    <strong>{step.step}. {step.action}</strong>
                    <small className="cell-sub">{Object.values(step.args).join(', ') || '인자 없음'}</small>
                  </div>
                  <span className={`ops-status status-${step.selectedBy === 'model' ? 'active' : 'guarded'}`}>
                    <i />{step.selectedBy === 'model' ? '모델 선택' : '정책 선택'}
                  </span>
                </div>
                <p className="ops-reason-text">{step.observation.summary}</p>
                {step.refused && (
                  <p className="ops-reason-guard">
                    <ShieldCheck size={13} /> 하네스가 이 행동의 실행을 거부했습니다.
                  </p>
                )}
                {step.selectionNote && (
                  <p className="ops-reason-note">모델 선택을 쓰지 못한 이유: {step.selectionNote}</p>
                )}
              </article>
            ))}
            {!run.steps.length && (
              <article className="ops-reason-card">
                <p className="ops-reason-note">에이전트가 첫 단계에서 종료를 선택했습니다.</p>
              </article>
            )}
          </div>
        </section>
      )}

      {run && (
        <section className="ops-group">
          <div className="ops-group-heading"><strong>판정</strong><span>{run.stoppedReason === 'finish' ? '정상 종료' : '단계 예산 소진'}</span></div>
          <div className="ops-reason-card">
            <p className="ops-reason-text">{run.explanation.text}</p>
            <div className="ops-reason-meta">
              <span className="ops-source source-decision">{run.goal}</span>
              <span className="ops-source source-decision">판정 {run.decision.decision}</span>
              <span className="ops-source source-decision">상태 {run.decision.state}</span>
              {run.sandbox && <span className="ops-source source-template">임시 패킷 · 미승인</span>}
              <span className="cell-muted">
                분자 게이트 {run.decision.moleculeEligible ? '열림 (사람 승인 필요)' : '닫힘'}
              </span>
              {run.decision.ruleIds.length > 0 && <span className="cell-muted">규칙 {run.decision.ruleIds.join(', ')}</span>}
            </div>
            {run.sandbox && (
              <p className="ops-reason-note">
                제출한 패킷으로 돌린 실행입니다. 저장되지 않았고 승인 기록이 없어 분자 최적화 단계로는 진행할 수 없습니다.
              </p>
            )}
            {run.explanation.violations.length > 0 && (
              <p className="ops-reason-guard">
                <ShieldCheck size={13} /> 가드레일이 모델 문장을 차단해 템플릿으로 대체했습니다: {run.explanation.violations.join(', ')}
              </p>
            )}
          </div>
        </section>
      )}

      <section className="ops-group">
        <div className="ops-group-heading"><strong>행동 허용 목록</strong><span>{actions.length}</span></div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr><th>행동</th><th>인자</th><th>용도</th></tr>
            </thead>
            <tbody>
              {actions.map((action) => (
                <tr key={action.action}>
                  <td><strong>{action.action}</strong></td>
                  <td className="cell-muted">{action.args.join(', ') || '—'}</td>
                  <td className="cell-muted">{action.purpose}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {offline && (
        <div className="ops-empty">
          <Bot size={22} />
          <strong>실행 기록이 없습니다.</strong>
          <span>하네스 서버(:8765)가 떠 있어야 실제 실행을 볼 수 있습니다. 위 허용 목록은 서버와 무관한 고정 사실입니다.</span>
        </div>
      )}
    </div>
  )
}
