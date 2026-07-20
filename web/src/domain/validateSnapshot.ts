import type { RunSnapshot } from './contracts'

function invariant(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`RunSnapshot 계약 위반: ${message}`)
}

export function validateSnapshot(snapshot: RunSnapshot) {
  const stageIds = new Set(snapshot.stages.map((stage) => stage.id))
  const evidenceIds = new Set(snapshot.evidence.map((item) => item.id))
  const artifactIds = new Set(snapshot.artifacts.map((artifact) => artifact.id))

  invariant(stageIds.size === snapshot.stages.length, `${snapshot.run.id}에 중복 stage ID가 있습니다.`)
  invariant(artifactIds.size === snapshot.artifacts.length, `${snapshot.run.id}에 중복 artifact ID가 있습니다.`)
  invariant(snapshot.stages.every((stage, index) => stage.ordinal === index + 1), `${snapshot.run.id}의 stage ordinal이 연속적이지 않습니다.`)
  invariant(snapshot.events.every((event) => stageIds.has(event.stageId)), `${snapshot.run.id} 이벤트에 존재하지 않는 stage ID가 있습니다.`)
  invariant(snapshot.failures.every((failure) => stageIds.has(failure.stageId)), `${snapshot.run.id} 실패 기록에 존재하지 않는 stage ID가 있습니다.`)
  invariant(snapshot.stages.every((stage) => [...stage.inputArtifactIds, ...stage.outputArtifactIds].every((id) => artifactIds.has(id))), `${snapshot.run.id} 단계에 존재하지 않는 artifact ID가 연결되어 있습니다.`)

  snapshot.targets.forEach((target) => {
    const scoreSum = target.scoreFactors.reduce((sum, factor) => sum + factor.impact, 0)
    invariant(scoreSum === target.scoreAfter, `${target.symbol} 점수 요인의 합 ${scoreSum}이 최종 점수 ${target.scoreAfter}와 다릅니다.`)
    invariant(target.evidenceIds.every((id) => evidenceIds.has(id)), `${target.symbol}에 존재하지 않는 evidence ID가 연결되어 있습니다.`)
    invariant(target.scoreFactors.every((factor) => factor.evidenceIds.every((id) => evidenceIds.has(id))), `${target.symbol} 점수 요인에 존재하지 않는 evidence ID가 있습니다.`)
  })

  const hasFinalOutputs = snapshot.run.status === 'awaiting_review' || snapshot.run.status === 'completed' || snapshot.run.status === 'completed_with_warnings'

  if (snapshot.run.scenarioKind === 'evidence-review' && hasFinalOutputs) {
    const tyk2 = snapshot.targets.find((target) => target.symbol === 'TYK2')
    invariant(tyk2?.decision === 'rejected', 'IBD 근거 검토에서 TYK2가 기각 상태가 아닙니다.')
    invariant(snapshot.molecules.length === 0, '기각된 TYK2 실행에 분자 결과가 포함되어 있습니다.')
    const gatedStages = ['seed', 'generate', 'activity', 'admet', 'synthesis']
    invariant(gatedStages.every((id) => {
      const status = snapshot.stages.find((stage) => stage.id === id)?.status
      return status === 'skipped' || status === 'blocked'
    }), '분자 단계가 결정 게이트 이후 미실행 상태가 아닙니다.')
  }

  if (snapshot.run.scenarioKind === 'molecule-ui-fixture' && hasFinalOutputs) {
    invariant(snapshot.run.classification === 'synthetic', '분자 UI fixture의 실행 분류가 synthetic이 아닙니다.')
    invariant(snapshot.molecules.length > 0, '분자 UI fixture에 표시할 레코드가 없습니다.')
    invariant(snapshot.molecules.every((molecule) => molecule.classification === 'synthetic' && molecule.decision === 'demo_only'), '분자 UI fixture에 연구 결과처럼 보이는 레코드가 있습니다.')
  }

  return snapshot
}
