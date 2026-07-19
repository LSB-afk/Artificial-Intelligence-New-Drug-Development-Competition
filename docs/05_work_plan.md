# 실행 계획

## 1. 예선 제출 전

목표 마감: 2026-08-07 16:00 KST

| 단계 | 산출물 | 상태 |
| --- | --- | --- |
| 공식 요구사항 분석 | 대회 분석 문서 | 완료 |
| 분야 1+2 융합 설계 | 에이전트 설계 문서 | 완료 |
| negative 데모 케이스 선정 | IBD/TYK2/deucravacitinib 적응증 반증·기각 | 완료 |
| positive molecule 타깃 선정 | 동일한 임상 근거 gate를 통과한 타깃 | 미정/P0 |
| 점수 개선 리서치 | 공식/논문/공개 코드 기반 개선 문서 | 완료 |
| 평가표 역검토 | 예선/본선 기준 rubric, golden cases, failure modes | 완료 |
| 제안서 초안 | HWPX 양식 10쪽 이내 초안 | 다음 작업 |
| MVP 코드 착수 | Open Targets/ChEMBL/RDKit baseline | 다음 작업 |
| 제출 전 점검 | 파일 형식, 제출 항목, 업로드, 최종 제출 완료 | 제출 직전 |

## 2. 대표 데모 케이스 선정 기준

좋은 데모 케이스 조건:

- Open Targets에 질병-타깃 근거가 충분하다.
- ChEMBL에 해당 타깃의 bioactivity/ligand 데이터가 충분하다.
- 약물성/독성/합성 가능성 평가가 의미 있다.
- 타깃 가설과 분자 최적화를 모두 보여줄 수 있다.
- 본선 4주 안에 시연 가능한 범위다.

후보:

| 후보 질환 | 장점 | 리스크 |
| --- | --- | --- |
| inflammatory bowel disease | Open Targets 예시와도 잘 맞고 NOD2/JAK/TYK2/IL23 axis 등 근거가 풍부하다. | 면역 타깃은 small molecule/biologic 경계가 있어 타깃 선택을 잘해야 한다. |
| pancreatic ductal adenocarcinoma | unmet need가 크고 KRAS/EGFR/MEK 등 설명력이 높다. | KRAS 등 난치 타깃은 분자 최적화 난도가 높다. |
| non-small cell lung cancer | EGFR/ALK 등 ChEMBL 데이터와 임상 근거가 풍부하다. | 너무 알려진 영역이라 독창성 설명이 필요하다. |

확정한 것은 **inflammatory bowel disease에서 TYK2를 에이전트가 스스로 반증하는 negative demo**다. TYK2는 small-molecule tractability와 psoriasis 승인약 때문에 유망해 보이지만, deucravacitinib의 IBD 임상 실패와 적응증 불일치를 탐지해 `REJECT` 또는 reviewed `HOLD`로 내려야 한다. Positive molecule branch는 별도 후보가 같은 gate를 통과한 뒤 확정한다.

데모 고정값:

- Disease: inflammatory bowel disease / `MONDO_0005265`
- Negative target: TYK2 / ChEMBL `CHEMBL3553`
- Comparison targets: NOD2, IL12B, JAK2, IL23R
- Contradiction reference: deucravacitinib / `CHEMBL4435170` (psoriasis approval, IBD negative evidence)
- Positive molecule target/reference: **TBD after evidence qualification**

## 3. 본선 4주 구현 계획

| 주차 | 목표 | 산출물 |
| --- | --- | --- |
| 1주차 | 데이터 수집 파이프라인 | Open Targets/ChEMBL connector, disease-target table, ligand table |
| 2주차 | 가설 생성/반증 루프 | Claim ledger, indication-aware critic, `ADVANCE/HOLD/REJECT`, failure handling |
| 3주차 | eligibility-gated 분자 최적화/평가 | RDKit pipeline, typed activity evidence, ADMET/safety/synthesis gates |
| 4주차 | 통합 시연/보고서 | UI 또는 notebook demo, final report, presentation, deployment link |

MVP와 확장 기능 구분:

| 구분 | 포함 | 제외 또는 확장 |
| --- | --- | --- |
| MVP | Open Targets/ChEMBL/clinical snapshot, TYK2 rejection, state/audit logs, RDKit descriptor, bounded 후보 생성, planned ADMET-AI, SA/RAscore, report log | full docking, wet-lab validation, 모든 질환 일반화 |
| Stretch | 최종 5개만 AiZynthFinder feasibility, docking score, production dashboard, 자동 PPT export | 외부 비허용 LLM/API 의존 |

## 4. 본선 시연 시나리오

1. 사용자가 질병명을 입력한다.
2. 에이전트가 질병 ID를 정규화하고 상위 타깃 후보를 제시한다.
3. Clinical Contradiction Critic이 TYK2의 psoriasis 승인과 IBD 실패 근거를 분리한다.
4. Decision Engine이 TYK2를 `REJECT/HOLD`하고 molecule transition을 차단한다.
5. API 5xx를 주입해 bounded retry와 snapshot fallback을 보여준다.
6. 별도 positive target이 `ADVANCE`와 human approval을 받은 경우에만 seed molecule과 assay 근거를 가져온다.
7. 후보 구조를 생성하고 RDKit validity, activity evidence type, ADMET, SA/RAscore, optional top-5 synthesis feasibility를 평가한다.
8. 실패 후보와 타깃 feedback을 숨기지 않고 최종 리포트에 포함한다.

## 5. 제출 체크리스트

- HWPX 양식 사용
- 제안서 10쪽 이내
- 선택 분야 명확히 표시
- 팀명/에이전트명/키워드 작성
- 예선 평가 6개 항목 모두 대응
- 본선 구현 산출물까지 이어지는 범위 제시
- 출처 URL/DB ID 표기
- 연구 윤리와 안전성 포함
- DAKER 제출 탭에서 초안 저장이 아닌 최종 제출 완료 확인

## 6. 바로 다음 구현 작업

| 우선순위 | 작업 | 완료 조건 |
| --- | --- | --- |
| P0 | Positive target evidence qualification | 후보가 indication-aware clinical gate를 통과하고 reviewer `ADVANCE`를 받는다. |
| P0 | Domain event/state validator | `HOLD/REJECT`에서 molecule transition이 자동 테스트로 차단된다. |
| P0 | Snapshot-first evidence adapters | `MONDO_0005265`, TYK2 contradiction evidence와 API 5xx fallback이 lawful fixture/manifest로 재현된다. |
| P0 | Machine-readable eval runner | `evals/cases.jsonl` high-risk cases가 실행되고 100% pass gate를 적용한다. |
| P1 | RDKit/activity/ADMET/synthesis smoke | measured/predicted/proxy를 구분하고 ADMET-AI/RAscore 설치 결과를 기록한다. |
| P1 | Read-only Evaluation Agent skeleton | `evals/rubric.md`를 읽어 과학 state를 바꾸지 않는 gap report를 생성한다. |
| P1 | Proposal 10-page draft | 최신 correction과 canonical harness 내용을 HWPX 양식으로 압축한다. |
