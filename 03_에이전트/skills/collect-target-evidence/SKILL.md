---
name: collect-target-evidence
description: 질병-타깃 가설의 지지 근거와 반증 근거를 공개 데이터베이스에서 수집하고 출처 스냅샷으로 정규화한다. Open Targets, ChEMBL, ClinicalTrials.gov, 논문을 이용해 추적 가능한 근거 패키지를 만들 때 사용한다.
---

# 타깃 근거 수집

## 절차

1. 정규화된 질병 ID와 타깃 식별자를 입력으로 받는다.
2. Open Targets에서 association, evidence source, tractability를 분리 수집한다.
3. ChEMBL에서 target, mechanism, indication, assay availability를 수집한다.
4. ClinicalTrials.gov와 원 논문에서 현재 적응증의 성공·실패 임상 결과를 함께 찾는다.
5. 각 레코드를 `support`, `contradiction`, `context`, `unknown` 중 하나로 분류한다.
6. 원문 ID, URL, 관측일, 응답 해시, live/cache 모드를 보존한다.

## 품질 규칙

- association score를 confidence로 표현하지 않는다.
- 다른 적응증의 승인 이력을 현재 적응증의 성공 근거로 전환하지 않는다.
- 숫자 집계는 현재 응답 스냅샷이 있을 때만 보고한다.
- 지지 근거만 수집하지 말고 반증 검색을 별도 단계로 실행한다.

## 출력

근거 레코드, 출처 매니페스트, 누락된 source class, 재시도·fallback 이벤트를 포함한 evidence package를 반환한다.

이 저장소에서는 `docs/04_sources.md`, `rules/data-rules.md`, `docs/07_architecture.md`를 기준으로 삼는다.
