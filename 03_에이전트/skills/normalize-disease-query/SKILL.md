---
name: normalize-disease-query
description: 질병명, 약어, 동의어를 표준 질병 ID 후보로 정규화하고 불확실성을 보존한다. H2L-Forge에서 사용자 질병 질의를 Open Targets 또는 동등한 온톨로지 ID로 변환하거나, 여러 후보 중 선택 근거를 기록해야 할 때 사용한다.
---

# 질병 질의 정규화

## 절차

1. 원문 질의, 약어, 언어, 사용자가 지정한 적응증 범위를 보존한다.
2. Open Targets 검색 또는 허용된 온톨로지 검색에서 후보 ID와 동의어를 수집한다.
3. 후보마다 이름 일치, 동의어 일치, 상·하위 질환 관계를 비교한다.
4. 단일 후보가 명확할 때만 선택하고, 그렇지 않으면 `HOLD`와 후보 목록을 반환한다.
5. 선택한 ID, 검색어, 출처, 관측일, 응답 해시를 기록한다.

## 출력

- `query_original`
- `normalized_label`
- `disease_id`
- `candidate_ids`
- `selection_reason`
- `ambiguity_flags`
- `source_ref`, `observed_at`, `snapshot_hash`

## 불변식

- 존재하지 않는 ID를 추측하지 않는다.
- IBD처럼 상위 질환과 UC/CD처럼 하위 질환을 자동으로 동일시하지 않는다.
- 불확실한 정규화 결과는 다음 타깃 단계로 자동 진행시키지 않는다.

이 저장소에서는 `docs/04_definitions.md`, `rules/data-rules.md`, `evals/golden-cases.md`를 함께 확인한다.
