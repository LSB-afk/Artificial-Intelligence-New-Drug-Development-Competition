---
name: optimize-eligible-molecules
description: 게이트를 통과한 타깃의 seed molecule에서 유효 구조를 생성하고 활성 근거, 약물성, 안전성, 합성성을 함께 고려해 후보를 순위화한다. H2L-Forge의 제한된 분자 최적화 루프를 실행할 때 사용한다.
---

# 적격 분자 최적화

## 절차

1. `molecule_eligible=true`와 reviewer 승인을 확인한다.
2. RDKit으로 구조를 표준화하고 sanitization, canonicalization을 수행한다.
3. seed 근처에서 SELFIES/STONED 또는 사전 승인된 변형 규칙으로 후보를 만든다.
4. 활성 근거를 `measured`, `validated_qsar`, `similarity_proxy`로 구분한다.
5. QED, Lipinski-like descriptor, PAINS/alert, 유사도, ADMET, 합성성으로 Pareto 순위를 계산한다.
6. 탈락 후보와 원인을 failure ledger에 남긴다.

## 표현 규칙

- Tanimoto 유사도만 있으면 활성 개선 또는 결합 예측이라고 쓰지 않는다.
- QED 개선을 치료 효능 개선으로 표현하지 않는다.
- seed 대비 변화와 사용한 모델·버전·불확실성을 함께 보고한다.

후보 수와 변형 횟수에 상한을 두고, top-k만 다음 검증 단계로 전달한다.
