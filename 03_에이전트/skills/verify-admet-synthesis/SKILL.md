---
name: verify-admet-synthesis
description: 후보 분자의 RDKit 경고, ADMET-AI 예측, SA score 또는 RAscore, 제한된 AiZynthFinder 신호를 단계적으로 검증한다. 독성·약물성·합성 가능성을 과장 없이 early kill-switch로 적용할 때 사용한다.
---

# ADMET·합성성 검증

## 절차

1. RDKit descriptor와 구조 경고를 모든 후보에 적용한다.
2. 버전 고정과 smoke test를 통과한 경우에만 ADMET-AI를 실행한다.
3. hERG, AMES, DILI, CYP, Caco-2 등 지표의 모델 유형과 방향을 보존한다.
4. 전체 후보에는 SA score 또는 검증된 RAscore를 적용한다.
5. AiZynthFinder는 최종 후보 최대 5개에만 실행하고 시간 제한을 둔다.
6. predictor 미사용·실패·도메인 이탈을 숨기지 않고 `unavailable`로 기록한다.

## 안전 경계

- 합성 경로는 feasibility signal로만 사용한다.
- 실행 가능한 제조 절차, 위험 물질 합성 지침, 우회 방법을 제공하지 않는다.
- ADMET 예측을 측정 결과처럼 표현하지 않는다.

출력에는 후보별 통과 여부, 모델·버전, proxy 유형, 실패 사유를 포함한다.
