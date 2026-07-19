# 예선 제안서 작성 골격

공식 HWPX 양식은 10쪽 이내다. 아래 구조는 양식의 8개 항목에 맞춘 초안 골격이다.

## 선택 분야

- 분야 1: 자율형 가설 생성 및 검증
- 분야 2: 도구 활용 기반의 분자 최적화 루프
- 분야 4: 융합 분야

## 팀명/에이전트명

- 팀명: 미정
- 에이전트명: H2L-Forge
- 제안 제목: H2L-Forge: 적응증별 근거를 스스로 반증하는 질병-타깃 의사결정 및 분자 최적화 에이전트
- 한 줄 설명: 유망해 보이는 타깃도 임상·적응증 근거로 다시 의심해 `ADVANCE/HOLD/REJECT`를 결정하고, 통과한 타깃에만 재현 가능한 분자 검증 루프를 연결하는 신약개발 에이전트
- 국문 키워드: 에이전틱 AI, 타깃 발굴, 분자 최적화, ADMET, 근거 검증
- 영문 키워드: Agentic AI, Target Discovery, Molecular Optimization, ADMET, Evidence Grounding

## 요약

`H2L-Forge`는 질병 입력에서 출발해 지지 근거와 반증 근거를 함께 수집하고, 적응증별 임상 결과를 검토한 뒤 타깃을 `ADVANCE/HOLD/REJECT`로 분류하는 분야 1+2 융합형 에이전트다. `ADVANCE`와 인간 승인까지 받은 타깃만 seed molecule 수집과 구조 최적화 단계로 보낸다. Open Targets, ChEMBL, ClinicalTrials.gov/문헌, RDKit, planned ADMET-AI, SA score/RAscore와 선택적 top-5 AiZynthFinder를 사용하고, 모든 판단을 source ID, snapshot hash, rule, failure log로 설명한다.

대표 negative demo는 inflammatory bowel disease, IBD(`MONDO_0005265`)에서 시작한다. TYK2(`CHEMBL3553`)는 tractability와 psoriasis 승인약 deucravacitinib(`CHEMBL4435170`) 때문에 처음에는 매력적으로 보이지만, 에이전트가 적응증 불일치와 IBD 2상 실패 근거를 찾아 `REJECT` 또는 검토가 필요한 `HOLD`로 내린다. 이 장면이 오류 인지·수정과 근거 반증의 핵심 시연이다. Positive molecule branch의 타깃은 같은 gate를 통과한 뒤 별도로 확정하며, 현재는 미정이다.

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
9. Report Agent가 가설, 결정 상태, 후보 분자, 근거, 실패 사유, 예산을 리포트로 만든다.
10. 별도 read-only Evaluation Agent가 평가 기준별 약점과 다음 실험을 제안하되 과학적 상태·랭킹·승인에는 개입하지 않는다.

독창성:

- PharmAgents, OriGene, AI co-scientist 등 선행연구를 명시하고 일반적인 폐루프 자체를 최초라고 주장하지 않는다.
- 차별점은 적응증별 반증 검색, 실패 ledger, `ADVANCE/HOLD/REJECT` 상태, reviewer gate를 파이프라인의 중심에 둔다는 점이다.
- 결과가 나쁘면 같은 타깃에서 무한 재최적화하지 않고 chemical accessibility를 하향해 타깃 가설을 보류하거나 다음 타깃 검토로 전환한다.
- 모든 판단은 DB ID, API 응답, descriptor, 평가 점수로 traceable하게 남긴다.
- 단순 LLM wrapper가 아니라 각 agent가 API response, 구조 descriptor, ADMET score, failure log를 입력으로 받아 다음 행동을 바꾸는 상태 기반 시스템이다.

## 3. 기술적 실현 가능성

MVP 구현 범위:

- Python 기반 백엔드
- Open Targets GraphQL API로 질병-타깃 후보 수집
- ChEMBL REST API로 target/assay/activity/molecule 데이터 수집
- RDKit으로 SMILES 표준화, descriptor, QED, similarity, 구조 필터링
- ADMET-AI를 planned pretrained inference path로 두고 버전·설치 smoke test 전에는 구현 완료라고 주장하지 않는다.
- 전체 후보는 SA score 또는 RAscore로 빠르게 거르고, 선택적 AiZynthFinder는 최종 5개에만 사용한다.
- Open Targets/ChEMBL/clinical evidence는 snapshot-first로 저장해 API 장애에도 재현한다.
- Streamlit 또는 FastAPI + 간단 UI로 시연

현실성:

- 모든 핵심 도구가 공개 문서와 API를 제공한다.
- 예선 단계에서는 프로세스와 평가 설계를 제시하고, 본선 4주 동안 질병 1개, 타깃 1~2개, 후보 분자 5개까지 구현하는 MVP로 제한한다.
- API 크레딧을 받더라도 핵심 cheminformatics는 로컬 오픈소스 중심으로 설계해 비용을 줄인다.
- MVP 범위는 IBD/TYK2/deucravacitinib negative demo, `ADVANCE/HOLD/REJECT` 및 API fallback 재현, 별도 evidence-qualified positive target 1개의 top-k 리포트까지로 제한한다. Positive target이 gate를 통과하지 못하면 분자 단계가 막힌 사실을 그대로 보고한다. Docking, wet-lab validation, full retrosynthesis 자동화는 확장 기능으로 둔다.

## 4. 에이전트 성능 평가 체계

| 평가 대상 | 지표 |
| --- | --- |
| 타깃 발굴 | Recall@5, MRR, evidence diversity, target tractability |
| 데이터 수집 | API success rate, ID validity, assay confidence filtering pass |
| 분자 생성 | valid SMILES rate, uniqueness, novelty, similarity range |
| 분자 개선 | target eligibility, RDKit validity, measured/predicted/proxy label, QED/ADMET/SA delta |
| 에이전트 자율성 | failed tool-call recovery, invalid input recovery, self-critique pass |
| 윤리/투명성 | citation verification pass, prompt/tool log completeness |
| 반증 능력 | TYK2 IBD 실패 근거 3/3 탐지, invalid auto-advance 0 |
| 점수 개선 | read-only rubric gap count, evidence coverage delta, candidate ranking audit |

## 5. 비즈니스 및 사회적 가치

기대 효과:

- 후보 타깃 검토와 seed molecule 탐색 시간을 단축한다.
- 타깃 선정과 분자 설계를 한 화면/리포트에서 연결해 연구자 의사결정을 돕는다.
- 제약사/병원/대학 연구실의 early discovery 단계에서 반복 검토 비용을 낮춘다.
- 희귀질환이나 근거가 흩어진 질환에서도 데이터 부족을 명확히 표시해 연구 우선순위 결정을 돕는다.

정량화 후보:

- 타깃 후보 조사 시간: 동일한 고정 시나리오를 수작업/에이전트로 각 3회 측정한 뒤에만 절감 수치를 제시
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

> H2L-Forge는 유망한 타깃을 더 많이 만드는 데서 멈추지 않고, 그 타깃이 현재 적응증에서 틀렸을 가능성을 먼저 검증하는 AI Agent입니다. IBD/TYK2 사례에서 에이전트는 높은 연관성과 tractability 뒤에 숨은 적응증 불일치와 임상 실패를 찾아 타깃을 스스로 기각합니다. 같은 검증을 통과한 타깃만 분자 최적화로 보내며, 최종 결과는 지지·반증 근거, 결정 상태, 실패 원인, 도구·예산 로그, 후속 검증 계획이 포함된 연구자용 의사결정 리포트입니다.
