---
name: decide-target-eligibility
description: 정규화·근거 수집·반증 결과를 결정 규칙에 적용해 타깃을 ADVANCE, HOLD, REJECT로 판정하고 분자 단계 진입을 통제한다. H2L-Forge의 타깃 게이트와 인간 승인 조건을 실행할 때 사용한다.
---

# 타깃 진입 판정

## 입력 조건

- 승인된 질병 정규화 결과
- 검증된 evidence snapshot과 해시
- 적응증별 contradiction review
- tractability와 assay availability

## 결정 규칙

- 현재 적응증의 중대한 실패 근거 또는 승인 적응증 불일치가 있으면 `REJECT`를 우선한다.
- 핵심 source class가 누락되거나 근거가 충돌하면 `HOLD`로 닫는다.
- 반증 검토를 통과하고 평가 기준을 충족한 경우에만 `ADVANCE`를 권고한다.
- `ADVANCE`만으로는 부족하며 인간 승인이 있어야 `molecule_eligible=true`가 된다.
- `HOLD`와 `REJECT`는 seed 검색·분자 생성·ADMET 실행을 차단한다.

## 출력

`decision`, `molecule_eligible`, 적용 규칙 ID, 지지·반증 근거 ID, reviewer 상태, 다음 행동을 반환한다.

판정을 LLM의 자유 서술로만 만들지 않는다. `rules/agent-rules.md`, `rules/data-rules.md`, `evals/decision_cases.json`의 결정 불변식을 적용한다.
