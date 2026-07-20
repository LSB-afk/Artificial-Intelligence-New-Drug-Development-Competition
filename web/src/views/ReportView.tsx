import { AlertTriangle, Ban, CheckCircle2, Clock3, Download, FileText, FlaskConical, ShieldCheck } from 'lucide-react'
import StatusBadge from '../components/StatusBadge'
import type { Artifact, RunSnapshot } from '../domain/contracts'
import { downloadText, formatDateTime } from '../lib/format'

function buildReport(snapshot: RunSnapshot) {
  const target = snapshot.targets.find((item) => item.symbol === 'TYK2')
  if (snapshot.run.scenarioKind === 'molecule-ui-fixture') {
    return [
      'H2L-Forge UI Fixture Summary',
      `Run: ${snapshot.run.id}`,
      'Classification: SYNTHETIC',
      '',
      'Purpose: Validate molecule comparison interface states.',
      'Scientific decision: None.',
      'AiZynthFinder route search: Not run.',
      '',
      ...snapshot.molecules.map((item) => `${item.id} | QED ${item.qed} | activity proxy ${item.activityProxy} | demo only`),
    ].join('\n')
  }

  return [
    'H2L-Forge Evidence Review',
    `Run: ${snapshot.run.id}`,
    `Disease: ${snapshot.run.disease} (${snapshot.run.diseaseId})`,
    '',
    `Decision: ${target?.symbol ?? 'Target'} ${target?.decision ?? 'not evaluated'}`,
    `Operating score: ${target?.scoreBefore ?? '-'} -> ${target?.scoreAfter ?? '-'}`,
    'Molecule stages: Not run because no target passed the decision gate.',
    'Human review: Required.',
  ].join('\n')
}

function artifactContent(artifact: Artifact, snapshot: RunSnapshot) {
  if (artifact.id === 'audit-trail') return JSON.stringify({ run: snapshot.run, events: snapshot.events, failures: snapshot.failures }, null, 2)
  if (artifact.id === 'decision-report') return buildReport(snapshot)
  return artifact.content ?? ''
}

export default function ReportView({ snapshot }: { snapshot: RunSnapshot }) {
  const { run, targets, evidence, molecules, artifacts, safetyNotices } = snapshot
  const focusTarget = targets.find((target) => target.symbol === 'TYK2')
  const focusEvidence = focusTarget ? evidence.filter((item) => focusTarget.evidenceIds.includes(item.id)) : []
  const supporting = focusEvidence.filter((item) => item.polarity === 'supporting')
  const conflicting = focusEvidence.filter((item) => item.polarity === 'conflicting')
  const availableArtifacts = artifacts.filter((artifact) => artifact.available)
  const isFixture = run.scenarioKind === 'molecule-ui-fixture'
  const isPending = !isFixture && !focusTarget
  const isRunActive = run.status === 'queued' || run.status === 'running'

  const downloadReport = () => downloadText(`${run.id}-report.txt`, buildReport(snapshot))
  const downloadArtifact = (artifact: Artifact) => downloadText(artifact.name, artifactContent(artifact, snapshot), `${artifact.mimeType};charset=utf-8`)

  return (
    <div className={`report-layout${isFixture ? ' is-fixture-report' : ''}`}>
      <section className="report-document">
        <div className="report-title-row">
          <div className="report-mark">H2L</div>
          <div><span className="eyebrow">{isFixture ? 'Interface fixture summary' : 'Research decision report'}</span><h2>{run.title}</h2><p>{run.id} · {run.diseaseId} · {formatDateTime(run.createdAt)}</p></div>
          <button className="primary-button" type="button" onClick={downloadReport} disabled={isRunActive}><Download size={16} /> TXT 다운로드</button>
        </div>

        {isFixture ? (
          <div className="report-verdict fixture-verdict">
            <div className="report-verdict-icon"><FlaskConical size={22} /></div>
            <div><span>데이터 분류</span><h3>이 실행은 분자 비교 UI를 검증하는 합성 fixture입니다.</h3><p>후보 채택, 타깃 검증, ADMET 예측, 합성 경로 탐색의 결과로 해석할 수 없습니다.</p></div>
            <strong>SYNTHETIC</strong>
          </div>
        ) : isPending ? (
          <div className="report-verdict pending-verdict">
            <div className="report-verdict-icon"><Clock3 size={22} /></div>
            <div><span>판단 대기</span><h3>근거 비평과 타깃 결정이 아직 완료되지 않았습니다.</h3><p>결정 이벤트가 도착하기 전에는 타깃 결론이나 분자 단계 결과를 표시하지 않습니다.</p></div>
            <strong>PENDING</strong>
          </div>
        ) : (
          <div className="report-verdict">
            <div className="report-verdict-icon"><ShieldCheck size={22} /></div>
            <div><span>핵심 판단</span><h3>TYK2는 이 IBD 실행의 최적화 대상으로 진행하지 않습니다.</h3><p>적응증별 임상 반증을 반영했고, 채택 타깃이 없어 분자 단계는 실행하지 않았습니다.</p></div>
            <strong>REJECTED</strong>
          </div>
        )}

        {!isFixture && focusTarget && (
          <section className="report-section">
            <div className="report-section-title"><span>01</span><div><h3>결정 근거</h3><p>지지와 반증을 함께 보존했습니다.</p></div></div>
            <div className="report-evidence-grid">
              <div><CheckCircle2 size={17} /><strong>지지 {supporting.length}건</strong><p>{supporting.map((item) => item.title).join(', ')}</p></div>
              <div><AlertTriangle size={17} /><strong>반증 {conflicting.length}건</strong><p>{conflicting.map((item) => item.title).join(', ')}</p></div>
            </div>
          </section>
        )}

        <section className="report-section">
          <div className="report-section-title"><span>{isFixture ? '01' : '02'}</span><div><h3>{isFixture ? 'fixture 레코드' : '분자 단계 결과'}</h3><p>{isFixture ? '화면 상태 확인용 합성 값입니다.' : '결정 게이트 이후의 실행 상태입니다.'}</p></div></div>
          {isFixture ? (
            <div className="fixture-record-list">
              {molecules.map((molecule) => <div key={molecule.id}><strong>{molecule.id}</strong><span>QED {molecule.qed.toFixed(2)}</span><span>활성 proxy {molecule.activityProxy.toFixed(2)}</span><StatusBadge status="demo_only" /></div>)}
            </div>
          ) : isPending ? (
            <div className="not-run-block pending-output"><Clock3 size={20} /><div><strong>결정 게이트 대기</strong><span>분자 단계의 실행 여부가 아직 정해지지 않았습니다.</span></div></div>
          ) : (
            <div className="not-run-block"><Ban size={20} /><div><strong>후보물질 없음</strong><span>seed 수집, 후보 생성, 활성 대리평가, ADMET, 합성 가능성을 실행하지 않았습니다.</span></div></div>
          )}
        </section>

        <section className="report-section limitations-section">
          <div className="report-section-title"><span>{isFixture ? '02' : '03'}</span><div><h3>한계와 검토 조건</h3><p>화면이 보여주는 범위를 명시합니다.</p></div></div>
          <ul>{safetyNotices.map((notice) => <li key={notice.id}><strong>{notice.title}:</strong> {notice.detail}</li>)}{isFixture && <li><strong>합성 평가:</strong> SA proxy만 표시했으며 AiZynthFinder 경로 탐색은 실행하지 않았습니다.</li>}</ul>
        </section>
      </section>

      <aside className="report-aside">
        <div className="panel-heading compact-heading"><div><span className="eyebrow">Available artifacts</span><h2>실제 산출물</h2></div></div>
        {availableArtifacts.length > 0 ? availableArtifacts.map((artifact) => (
          <button className="artifact-row" type="button" key={artifact.id} onClick={() => downloadArtifact(artifact)}>
            <FileText size={16} /><span><strong>{artifact.name}</strong><small>{artifact.description}</small></span><Download size={14} />
          </button>
        )) : <div className="empty-artifacts">실행이 끝나면 사용 가능한 산출물만 표시됩니다.</div>}
        <div className="human-review"><ShieldCheck size={17} /><div><strong>{run.reviewStatus === 'approved' ? 'Human review recorded' : 'Human review required'}</strong><span>{run.reviewStatus === 'approved' ? '이 프로토타입에 검토 완료 상태가 기록되었습니다.' : '실험 또는 임상 판단을 대체하지 않습니다.'}</span></div></div>
      </aside>
    </div>
  )
}
