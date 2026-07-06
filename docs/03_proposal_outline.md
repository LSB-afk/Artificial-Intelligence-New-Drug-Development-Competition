# 예선 제안서 작성 골격

공식 HWPX 양식은 10쪽 이내다. 아래 구조는 양식의 8개 항목에 맞춘 초안 골격이다.

## 선택 분야

- 분야 1: 자율형 가설 생성 및 검증
- 분야 2: 도구 활용 기반의 분자 최적화 루프
- 분야 4: 융합 분야

## 팀명/에이전트명

- 팀명: 미정
- 에이전트명: H2L-Forge
- 국문 키워드: 에이전틱 AI, 타깃 발굴, 분자 최적화, ADMET, 근거 검증
- 영문 키워드: Agentic AI, Target Discovery, Molecular Optimization, ADMET, Evidence Grounding

## 요약

`H2L-Forge`는 질병 입력에서 출발해 신약개발 타깃 가설을 만들고, 공개 DB와 화학 도구를 호출해 seed molecule 수집, 구조 최적화, ADMET/합성 가능성 평가까지 반복하는 분야 1+2 융합형 에이전트다. 기존 워크플로우의 병목은 타깃 가설과 분자 최적화가 서로 분리되어 연구자가 근거, 활성 데이터, 약물성, 합성 가능성을 수작업으로 연결해야 한다는 점이다. 본 시스템은 Open Targets, ChEMBL, RDKit, TDC, AiZynthFinder 등을 도구로 사용해 "왜 이 타깃인가"와 "왜 이 분자인가"를 하나의 근거 로그로 설명한다.

## 1. 필요성과 배경

핵심 문장:

> 초기 신약개발에서 가장 큰 병목 중 하나는 질병-타깃 가설의 근거 평가와 후보 분자 최적화가 분리되어 반복 검증 비용이 커진다는 점이다.

포함할 내용:

- 신약개발 초기 단계는 타깃 선정 실패, 약물성/독성 문제, 합성 가능성 부족이 누적되어 시간과 비용이 증가한다.
- 생성형 AI는 분자 후보를 만들 수 있지만, 질병-타깃 근거 없이 구조만 생성하면 과학적 타당성이 약해진다.
- 반대로 타깃 발굴만 하고 분자 최적화 루프가 없으면 실제 후보물질 설계로 이어지기 어렵다.
- 따라서 질병 근거, 타깃 tractability, 활성 데이터, 약물성, 독성, 합성 가능성을 연결하는 에이전트가 필요하다.

## 2. 에이전트 설계 및 독창성

구조:

1. Orchestrator가 질병 입력을 분석하고 작업 계획을 세운다.
2. Target Discovery Agent가 Open Targets와 문헌 근거로 후보 타깃을 수집한다.
3. Evidence Critic이 근거 강도, 다양성, tractability, assay availability를 평가한다.
4. Hypothesis Writer가 검증 가능한 질병-타깃 가설을 만든다.
5. Seed Ligand Agent가 ChEMBL에서 활성/분자 데이터를 수집한다.
6. Molecule Optimizer가 RDKit/SELFIES 기반 후보를 생성한다.
7. ADMET/Safety Agent가 약물성, 독성, 구조 경고를 평가한다.
8. Synthesis Agent가 합성 가능성 또는 synthetic accessibility를 평가한다.
9. Report Agent가 가설, 후보 분자, 근거, 실패 사유를 리포트로 만든다.

독창성:

- 타깃 가설과 분자 최적화를 분리하지 않고 폐루프로 연결한다.
- 결과가 나쁘면 같은 타깃에서 분자를 재최적화하거나, 타깃 가설 자체를 보류하고 다음 타깃으로 전환한다.
- 모든 판단은 DB ID, API 응답, descriptor, 평가 점수로 traceable하게 남긴다.

## 3. 기술적 실현 가능성

MVP 구현 범위:

- Python 기반 백엔드
- Open Targets GraphQL API로 질병-타깃 후보 수집
- ChEMBL REST API로 target/assay/activity/molecule 데이터 수집
- RDKit으로 SMILES 표준화, descriptor, QED, similarity, 구조 필터링
- TDC ADMET dataset/model을 활용한 ADMET 평가
- AiZynthFinder 또는 SA score proxy로 합성 가능성 평가
- Streamlit 또는 FastAPI + 간단 UI로 시연

현실성:

- 모든 핵심 도구가 공개 문서와 API를 제공한다.
- 예선 단계에서는 프로세스와 평가 설계를 제시하고, 본선 4주 동안 질병 1개, 타깃 1~2개, 후보 분자 5개까지 구현하는 MVP로 제한한다.
- API 크레딧을 받더라도 핵심 cheminformatics는 로컬 오픈소스 중심으로 설계해 비용을 줄인다.

## 4. 에이전트 성능 평가 체계

| 평가 대상 | 지표 |
| --- | --- |
| 타깃 발굴 | Recall@5, MRR, evidence diversity, target tractability |
| 데이터 수집 | API success rate, ID validity, assay confidence filtering pass |
| 분자 생성 | valid SMILES rate, uniqueness, novelty, similarity range |
| 분자 개선 | QED delta, ADMET risk delta, SA score threshold |
| 에이전트 자율성 | failed tool-call recovery, invalid input recovery, self-critique pass |
| 윤리/투명성 | citation verification pass, prompt/tool log completeness |

## 5. 비즈니스 및 사회적 가치

기대 효과:

- 후보 타깃 검토와 seed molecule 탐색 시간을 단축한다.
- 타깃 선정과 분자 설계를 한 화면/리포트에서 연결해 연구자 의사결정을 돕는다.
- 제약사/병원/대학 연구실의 early discovery 단계에서 반복 검토 비용을 낮춘다.
- 희귀질환이나 근거가 흩어진 질환에서도 데이터 부족을 명확히 표시해 연구 우선순위 결정을 돕는다.

정량화 후보:

- 타깃 후보 조사 시간: 수일 단위 수작업을 수분~수십분 리포트로 축소
- 후보 분자 1차 필터링: 수백 개 후보의 물성/ADMET/구조 경고 자동 계산
- 리포트 품질: 모든 타깃/분자 주장에 출처 URL 또는 DB ID 연결

## 6. 연구 윤리 및 완성도

윤리 설계:

- AI가 만든 문헌/근거는 citation verifier로 실재 여부를 확인한다.
- 유해 물질 합성 또는 실행 가능한 위험 제조 지침은 제공하지 않는다.
- 모든 후보물질은 연구 가설이며, 실험/임상 판단은 인간 연구자 검토를 요구한다.
- 프롬프트, 모델, 설정값, 도구 호출, 실패 로그를 저장한다.
- 개인정보/비공개 데이터 없이 공개 데이터 중심으로 설계한다.

## 제안서 첫 문단 후보

> H2L-Forge는 신약개발 초기 단계의 "타깃 가설"과 "분자 최적화"를 하나의 에이전틱 루프로 연결하는 AI Agent입니다. 사용자가 질병명을 입력하면 에이전트는 공개 근거 그래프와 생물활성 데이터를 기반으로 타깃 후보를 우선순위화하고, 선택된 타깃에 대해 seed molecule을 수집한 뒤 약물성, ADMET, 합성 가능성을 함께 고려하여 후보 구조를 개선합니다. 최종 결과는 단순 답변이 아니라, 질병-타깃 근거, 분자 개선 이력, 실패 원인, 후속 검증 계획이 포함된 연구자용 의사결정 리포트입니다.
