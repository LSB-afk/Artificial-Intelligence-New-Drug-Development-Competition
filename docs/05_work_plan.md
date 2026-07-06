# 실행 계획

## 1. 예선 제출 전

목표 마감: 2026-08-07 16:00 KST

| 단계 | 산출물 | 상태 |
| --- | --- | --- |
| 공식 요구사항 분석 | 대회 분석 문서 | 완료 |
| 분야 1+2 융합 설계 | 에이전트 설계 문서 | 완료 |
| 대표 데모 케이스 선정 | 질환 1개, 타깃 후보 2개 | 다음 작업 |
| 제안서 초안 | HWPX 양식 10쪽 이내 초안 | 다음 작업 |
| 평가표 역검토 | 예선 100점 기준 체크리스트 | 다음 작업 |
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

추천: **inflammatory bowel disease에서 small-molecule tractable target을 선별하는 데모**. 이유는 타깃 가설 생성과 분자 최적화 연결을 균형 있게 보여주기 쉽고, 데이터 부족/충분 여부를 에이전트가 판단하는 시나리오가 자연스럽다.

## 3. 본선 4주 구현 계획

| 주차 | 목표 | 산출물 |
| --- | --- | --- |
| 1주차 | 데이터 수집 파이프라인 | Open Targets/ChEMBL connector, disease-target table, ligand table |
| 2주차 | 가설 생성/비평 루프 | Target scoring, evidence report, failure handling |
| 3주차 | 분자 최적화/평가 | RDKit pipeline, candidate generation, ADMET/safety scoring |
| 4주차 | 통합 시연/보고서 | UI 또는 notebook demo, final report, presentation, deployment link |

## 4. 본선 시연 시나리오

1. 사용자가 질병명을 입력한다.
2. 에이전트가 질병 ID를 정규화하고 상위 타깃 후보를 제시한다.
3. Evidence Critic이 선택 타깃 1~2개와 보류 타깃을 설명한다.
4. ChEMBL에서 seed molecule과 assay 근거를 가져온다.
5. 후보 구조를 생성하고 약물성/ADMET/합성 가능성을 평가한다.
6. 실패 후보는 왜 탈락했는지 보여준다.
7. 최종 후보 5개와 후속 검증 계획을 리포트로 출력한다.

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
