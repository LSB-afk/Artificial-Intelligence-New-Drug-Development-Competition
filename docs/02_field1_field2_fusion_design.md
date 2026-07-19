# 분야 1+2 융합 설계

> **2026-07-19 교정:** 일반적인 target-to-lead 폐루프 자체는 선행연구와 겹친다.
> 현재 차별점은 적응증별 반증 검색, `ADVANCE/HOLD/REJECT`, 실패 ledger, snapshot provenance다.
> TYK2/deucravacitinib은 IBD positive target이 아니라 rejection demo이며, canonical 설계는
> `docs/05_domain-model.md`부터 `docs/10_eval-plan.md`를 따른다.

## 1. 제안명

작업명: `Hypothesis-to-Lead Agent`
에이전트명 후보: `H2L-Forge`, `LeadWeaver`, `Target2Lead Agent`

추천 에이전트명: **H2L-Forge**

## 2. 해결 문제

신약개발 초기 단계에서는 "어떤 질병-타깃 가설을 믿을 것인가"와 "그 타깃에 대해 어떤 분자를 어떻게 개선할 것인가"가 분리되어 있다. 연구자는 질병 근거, 타깃 tractability, 기존 활성 데이터, 약물성, 독성, 합성 가능성을 반복적으로 수작업 연결한다.

`H2L-Forge`는 이 단절을 줄이는 에이전틱 AI다. 질병 입력에서 출발해 타깃 가설을 만들고, 타깃별 seed molecule을 수집해 다목적 최적화하며, ADMET/합성 가능성 결과를 다시 가설 검증에 반영한다.

## 3. 분야 융합 논리

| 대회 분야 | 구현 모듈 | 산출물 |
| --- | --- | --- |
| 분야 1: 자율형 가설 생성 및 검증 | Disease-Target Hypothesis Agent, Evidence Critic, Biomarker/Validation Planner | 질병-타깃 후보, 근거 그래프, 검증 가설, confidence/risk report |
| 분야 2: 도구 활용 기반의 분자 최적화 루프 | Seed Ligand Retriever, Molecule Optimizer, ADMET/Safety Agent, Synthesis Feasibility Agent | 최적화 후보 SMILES, 물성/ADMET/합성 점수, 개선 이력 |
| 융합 | Orchestrator + Feedback Loop | 타깃 가설과 분자 후보가 함께 업데이트되는 폐루프 |

## 4. 전체 프로세스

```text
질병/적응증 입력
  -> 질병 ID 정규화(EFO/MeSH/동의어)
  -> 질병-타깃 후보 수집(Open Targets, ChEMBL, 문헌)
  -> 타깃 우선순위화(근거, tractability, 안전성, assay availability)
  -> 검증 가능한 가설 생성 + 적응증별 임상 반증 검색
  -> ADVANCE/HOLD/REJECT + human approval
  -> [ADVANCE만] molecule eligibility
  -> seed molecule 수집(ChEMBL activity, known drugs, similarity)
  -> 분자 표준화/필터링(RDKit)
  -> 구조 최적화(SELFIES/STONED 또는 scaffold-constrained mutation)
  -> ADMET/독성/약물성 평가(planned ADMET-AI, RDKit QED, PAINS/alert)
  -> 합성 가능성 평가(SA/RAscore bulk -> optional top-5 AiZynthFinder)
  -> 후보 랭킹 및 실패 원인 분석
  -> 가설 재검토: 타깃 유지, 보류, 다음 타깃 전환
  -> 근거 기반 리포트 생성
```

## 5. 에이전트 구성

| 에이전트 | 역할 | 주요 입력 | 주요 출력 |
| --- | --- | --- | --- |
| Orchestrator | 목표 분해, 작업 순서 결정, 실패 시 재시도 | 질병명, 제약조건, 평가 목표 | 실행 계획, 도구 호출 순서 |
| Disease Normalizer | 질병/표현형 ID 정규화 | 질병명, synonym | EFO/MeSH 후보, 선택 근거 |
| Target Discovery Agent | 질병 관련 타깃 후보 수집 | disease ID | 타깃 리스트, association score, evidence type |
| Evidence Critic | 지지·반증·적응증별 임상 근거 평가 | 타깃 후보, claim ledger | `ADVANCE/HOLD/REJECT`, contradiction/failure memo |
| Hypothesis Writer | 검증 가능한 신약개발 가설 작성 | 타깃, 질병, pathway, biomarker | 한 문장 가설, 검증 실험/데이터 계획 |
| Seed Ligand Agent | seed molecule 수집 | target ID, assay 조건 | ChEMBL molecule IDs, SMILES, activity table |
| Molecule Optimizer | 분자 변형과 후보 생성 | seed SMILES, objective | 후보 SMILES, novelty/similarity |
| ADMET/Safety Agent | 약물성/독성 평가 | 후보 SMILES | QED, logP, TPSA, hERG/AMES/DILI 위험 |
| Synthesis Agent | 합성 가능성 평가 | 후보 SMILES | retrosynthesis route 또는 SA proxy |
| Report Agent | 제출/시연용 근거 정리 | 전체 로그 | 결과 리포트, citation table, audit trail |

## 6. 데이터/도구 후보

| 목적 | 후보 | 사용 이유 |
| --- | --- | --- |
| 질병-타깃 근거 | Open Targets Platform GraphQL/API | disease, target, association, tractability, safety 근거를 구조화해서 가져올 수 있다. |
| 생물활성/분자 데이터 | ChEMBL Web Services | target, assay, activity, molecule, mechanism, drug indication 데이터를 API로 수집 가능하다. |
| 화학 구조 처리 | RDKit | SMILES 표준화, descriptor, QED, 구조 필터, similarity 계산에 필수다. |
| ADMET benchmark | Therapeutics Data Commons | 데이터셋과 scaffold split 평가 관행을 제공하며 ready predictor로 취급하지 않는다. |
| ADMET inference (planned) | ADMET-AI | 사전 학습 모델 경로이며 설치·버전 smoke test 후에만 구현 완료로 표시한다. |
| 분자 탐색 | SELFIES/STONED | training-free 또는 경량 분자 변형 루프를 구성하기 좋다. |
| 합성 가능성 | SA score/RAscore + optional AiZynthFinder | 전체 후보는 빠른 proxy, 최종 5개만 route feasibility로 비용을 제한한다. |
| 문헌 근거 | Europe PMC/PubMed | 타깃-질병 근거 설명과 참고문헌 검증에 사용한다. |

## 7. 타깃 우선순위 점수 설계

타깃 점수는 절대적 진실값이 아니라, 에이전트가 다음 행동을 고르는 운영 점수다.

```text
target_score =
  0.30 * evidence_strength
+ 0.20 * data_diversity
+ 0.15 * tractability
+ 0.15 * assay_availability
+ 0.10 * safety_margin
+ 0.10 * novelty_or_unmet_need
```

실패 조건:

- 근거가 한 출처에만 과도하게 의존한다.
- ChEMBL assay가 너무 적어 seed ligand가 부족하다.
- 안전성 경고가 높거나 필수 유전자/광범위 독성 리스크가 크다.
- 타깃과 질병 연결이 예측 근거만 있고 검증 가능한 설명이 약하다.

## 8. 분자 최적화 목표

최적화 목표는 단일 점수보다 Pareto ranking으로 둔다.

| 축 | 예시 지표 | 방향 |
| --- | --- | --- |
| 활성 가능성 | target QSAR score 또는 ChEMBL 근접 ligand similarity | 높임 |
| 약물성 | RDKit QED, Lipinski-like descriptors | 높임 |
| ADMET | hERG, AMES, DILI, CYP inhibition risk | 낮춤 |
| 합성 가능성 | SA/RAscore, optional top-5 AiZynthFinder route signal | 높임 |
| novelty | seed 대비 Tanimoto 범위, known compounds와 거리 | 적정 범위 |
| 안전성 | structural alerts, forbidden motifs | 위험 제거 |

## 9. 에이전트 평가 체계

### 예선 제안서용 평가

| 평가 질문 | 지표 |
| --- | --- |
| 질병-타깃 가설이 근거 기반인가? | source count, evidence type diversity, target-disease association traceability |
| 에이전트가 도구를 정확히 쓰는가? | API success rate, invalid query rate, retrieved ID validity |
| 분자 후보가 화학적으로 유효한가? | valid SMILES rate, uniqueness, novelty, RDKit sanitization pass |
| 최적화가 실제 개선을 만드는가? | QED/ADMET/Pareto score before-after delta |
| 안전/윤리를 지키는가? | citation verification pass, dangerous synthesis filter, human review flag |

### 본선 구현용 평가

1. Disease-to-target benchmark
   - 5개 질환을 선정하고 알려진 치료 타깃/임상 타깃을 일부 gold set으로 둔다.
   - 타깃 랭킹의 Recall@5, MRR, 근거 출처 다양성을 측정한다.

2. Target-to-ligand benchmark
   - ChEMBL에서 target별 known active ligands 일부를 holdout한다.
   - seed retrieval과 후보가 holdout ligand chemical neighborhood를 회복하는지 평가한다.

3. Molecule optimization benchmark
   - valid, unique, novel, QED 개선, ADMET risk 감소, SA score 악화 제한을 본다.

4. Agent autonomy benchmark
   - 잘못된 질병명, 데이터 부족 타깃, API 오류, invalid SMILES 입력 시 자기 수정 여부를 본다.

## 10. 안전 설계

- 유해 물질, 통제 물질, 고위험 합성 경로를 생성/확장하는 요청은 거부한다.
- 합성 경로는 연구용 가능성 평가 수준으로 제한하고 실행형 제조 지침으로 제공하지 않는다.
- 모든 문헌과 DB 결과는 URL/ID를 남기고, 확인 불가 참고문헌은 리포트에서 제외한다.
- AI 출력은 "후보 가설"로 표시하며 실험/임상 판단을 대체하지 않는다.
- 최종 후보는 인간 연구자가 승인해야 다음 단계로 넘어간다.

## 11. 본선 MVP 범위

4주 구현을 고려하면 MVP는 다음 정도가 현실적이다.

1. 질병 1개 입력: 예시 질환은 inflammatory bowel disease 또는 pancreatic cancer 중 선택
2. Open Targets에서 상위 타깃 10개 수집
3. Evidence Critic으로 타깃 2개 선정
4. ChEMBL에서 각 타깃 seed ligand 20~100개 수집
5. RDKit 기반 표준화/QED/descriptor/필터링
6. SELFIES 또는 RDKit 변형으로 후보 100~500개 생성
7. smoke-tested ADMET-AI 또는 명시적 limited fallback으로 위험 평가
8. 최종 후보 5개와 가설 리포트 출력
9. Streamlit/FastAPI 또는 notebook-to-report 형태로 시연

## 12. 차별화 포인트

- PharmAgents, OriGene, AI co-scientist 등 가까운 선행연구를 명시하고 폐루프 자체를 최초라고 주장하지 않는다.
- 타깃을 찾는 것보다 적응증별 반증 근거를 우선 탐색하고, 틀린 타깃을 스스로 기각하는 loop를 전면에 둔다.
- 에이전트가 "왜 이 타깃인가"와 "왜 이 분자인가"를 같은 근거 그래프에서 설명한다.
- 실패를 숨기지 않고 데이터 부족, 안전성 경고, 합성 불가 등을 다음 행동으로 연결한다.
- 예선 평가표의 6개 항목을 시스템 기능과 직접 매칭한다.
