---
name: evaluate-h2l-runs
description: H2L-Forge 실행을 골든 케이스, 결정 정확도, 반증 회수율, unsafe advance, snapshot fallback, 재현성 기준으로 평가한다. 하네스 변경 후 회귀평가와 ablation을 수행할 때 사용한다.
---

# H2L 실행 평가

## 절차

1. 실행 artifact와 평가 plane을 분리하고 평가가 과학적 상태를 수정하지 못하게 한다.
2. `evals/cases.jsonl`, `evals/decision_cases.json`, `evals/golden-cases.md`를 로드한다.
3. 결정 상태, molecule eligibility, 필수·금지 문구, source coverage를 검증한다.
4. support-only baseline과 contradiction-aware candidate를 같은 seed로 비교한다.
5. API 장애, snapshot 누락, 해시 변조, similarity-only activity 사례를 실행한다.
6. 실패 케이스를 숨기지 않고 재현 명령과 artifact ID를 남긴다.

## 핵심 불변식

- IBD/TYK2 고정 사례는 승인 적응증 불일치와 실패 임상을 반영해 `REJECT` 또는 reviewed `HOLD`여야 한다.
- 기각된 타깃은 `molecule_eligible=false`여야 한다.
- 유효한 pinned snapshot이 있으면 API 5xx를 공개된 fallback으로 복구해야 한다.

결과를 통과 수, 실패 수, 안전 위반, 지표와 임계치로 요약한다.
