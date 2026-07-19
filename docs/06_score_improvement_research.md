# H2L-Forge 점수 개선 리서치 및 제안서 강화안

작성일: 2026-07-06 KST

> **상태: 역사 자료 / 부분 superseded.** 2026-07-16의
> `05_리서치/2026-07-16_H2L-Forge_냉정평가_및_개선안.md`가 TYK2/IBD 임상 전제,
> 폐루프 독창성, TDC·AiZynthFinder 활용 계획을 교정했다. 현재 설계는 `harness.yaml`,
> `docs/07_architecture.md`, `docs/09_flow.md`, `docs/10_eval-plan.md`를 따른다.
> 아래의 “TYK2 positive demo”, “TDC ready predictor”, “generic closed-loop novelty” 문구는
> 근거 기록용으로 보존한 과거 판단이며 구현/제안서의 현재 지시가 아니다.

## 1. 핵심 결론 요약

H2L-Forge는 `IBD -> TYK2 -> deucravacitinib reference -> molecule optimization` 데모를 고정하고, 제안서 메시지를 "좋은 LLM wrapper"가 아니라 "근거-도구-검증-실패 로그가 닫힌 agentic loop"로 바꿔야 한다. 공식 대회는 에이전틱 AI 기반 신약개발 서비스를 기획하고 본선에서 실제 구현하는 것을 요구하며, 예선은 Peer Review 30%와 전문가 평가 70%로 선발한다. 근거: DAKER 공식 페이지 https://daker.ai/public/hackathons/4th-jump-ai-agentic-drug-challenge

수상권 관점의 핵심 차별점은 다음 4개다.

1. 질병-타깃 가설과 후보 분자 최적화를 한 루프로 연결한다.
2. 모든 판단에 DB ID, citation, API response, score, failure log를 남긴다.
3. Open Targets association score를 confidence로 오해하지 않고, tractability와 assay availability로 보정한다.
4. 생성 분자는 novelty만 보지 않고 validity, QED, similarity, ADMET, synthesizability, safety를 Pareto ranking한다.

## 2. 딥리서치 결과

| 구분 | 확인된 사실 | H2L-Forge 반영 |
| --- | --- | --- |
| 공식 대회 | 분야 1은 자율형 가설 생성/검증, 분야 2는 도구 활용 기반 분자 최적화 루프, 분야 4는 융합 분야다. 본선은 약 4주간 실제 AI Agent를 구현한다. | 분야 1+2 융합으로 제출하고, 본선 MVP를 4주 구현 가능한 IBD/TYK2 단일 데모로 제한한다. URL: https://daker.ai/public/hackathons/4th-jump-ai-agentic-drug-challenge |
| 역대 대회 | 제2회 우수상 후기는 데이터 부족을 MolCLR, LDS/FDS, binding affinity 보조값으로 극복했다고 설명한다. | H2L-Forge도 데이터 부족을 "agent failure condition"으로 보고 external evidence/assay availability로 보정해야 한다. URL: https://hyperlab.hits.ai/blog/2nd-JUMP-AI-KR |
| 제3회 공개 코드 | 공개 GitHub 솔루션은 실험노트, EDA, 평가 지표, 실패 실험을 기록했고, CV 과대추정 한계까지 명시했다. | 본선 보고서에 실패 로그와 split/overfit 리스크를 반드시 넣는다. URL: https://github.com/Samdo3/MAP3K5_JumpAI2025_Competition |
| ChemCrow | 18개 chemistry tool을 LLM과 결합해 chemistry task를 수행했다. hallucination 완화는 expert tool integration과 human review가 핵심이다. | LLM은 판단/계획 담당, 사실과 계산은 Open Targets/ChEMBL/RDKit/TDC/AiZynthFinder가 담당한다. DOI: https://doi.org/10.1038/s42256-024-00832-8 |
| Coscientist | 문서 검색, 코드 실행, 실험 자동화 API를 결합해 semi-autonomous experimental design/execution을 보였다. | H2L-Forge는 dry-lab 버전으로 "검색 -> 코드 실행 -> 결과 비평 -> 다음 행동"을 구현한다. DOI: https://doi.org/10.1038/s41586-023-06792-0 |
| Open Targets | GraphQL API는 단일 target/disease/association query에 적합하다. association score는 heuristic이며 confidence score가 아니다. | TYK2 선택은 score 1위라서가 아니라 small molecule tractability, ChEMBL assay density, approved drug precedent 때문에 선택한다. Docs: https://platform-docs.opentargets.org/data-access/graphql-api / https://platform-docs.opentargets.org/associations |
| ChEMBL | Web Services는 activity, assay, molecule, target 등을 제공한다. 2026-07-06 조회 기준 ChEMBL_37, 2026-05-01 release, TYK2 `CHEMBL3553`, deucravacitinib `CHEMBL4435170` 확인. | API response cache를 evidence artifact로 저장하고 seed ligand filtering 기준을 명시한다. Docs: https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services |
| Molecular generation | GuacaMol/MOSES는 validity, uniqueness, novelty, distribution/goal-directed 평가 관행을 제공한다. | leaderboard benchmark를 그대로 재현하지 말고 MVP 지표로 축소 적용한다. GuacaMol: https://github.com/BenevolentAI/guacamol / MOSES DOI: https://doi.org/10.3389/fphar.2020.565644 |
| ADMET | TDC ADMET group은 22개 dataset, scaffold split, AUROC/AUPRC/MAE/Spearman 평가를 제시한다. | hERG, AMES, DILI, CYP3A4, Caco-2를 우선 위험 축으로 둔다. URL: https://tdcommons.ai/benchmark/admet_group/overview/ |
| Synthesis | AiZynthFinder는 MCTS 기반 retrosynthesis planning 도구이며 purchasable precursor로 분해한다. | 본선에서는 route found, top route score, unsolved reason만 표시하고 실행 가능한 제조 지침은 제공하지 않는다. URL: https://molecularai.github.io/aizynthfinder/ |

## 3. 역대 수상작/공개자료/팁에서 뽑은 전략

| 항목 | 내용 | 근거 URL/DOI |
| --- | --- | --- |
| 역대 수상작의 공통 특징 | 적은 데이터 문제를 인정하고 pretraining, external signal, augmentation, weighted loss, failure analysis로 보정한다. | https://hyperlab.hits.ai/blog/2nd-JUMP-AI-KR / https://github.com/Samdo3/MAP3K5_JumpAI2025_Competition |
| 평가위원이 좋아할 가능성이 높은 요소 | 실제 API/tool이 동작하고, 결과가 DB ID와 score로 추적되며, 실패 원인을 숨기지 않는 구조. | https://daker.ai/public/hackathons/4th-jump-ai-agentic-drug-challenge / https://doi.org/10.1038/s42256-024-00832-8 |
| 감점 가능성이 높은 요소 | 단순 챗봇 설명, citation 없는 문헌 주장, target score 오해, 생성 분자를 "신약 후보"로 과장, 4주 구현 범위 과대. | https://platform-docs.opentargets.org/associations / https://doi.org/10.1038/s42256-024-00832-8 |
| 바로 반영할 개선점 | Score Improvement Agent를 도입해 평가 항목별 약점, molecule ranking, evidence coverage, hallucination risk를 자동 점검한다. | https://arxiv.org/abs/2411.15692 / https://arxiv.org/html/2408.13378v4 |

확인 불가능/추정: 제4회 대회 수상권 제안서의 실제 심사위원 선호는 공개되지 않았다. 위 전략은 공식 평가 방향과 역대 공개 후기에서 추정한 것이다.

## 4. 선행연구 비교표

| 논문/자료 | 핵심 아이디어 | 사용 도구 | Planning 방식 | Validation 방식 | Evaluation metric | 한계 | H2L-Forge 반영 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ChemCrow | LLM에 18개 chemistry tool을 붙여 synthesis/drug/material task 수행 | chemistry tools, expert functions | ReAct/tool orchestration | LLM+expert assessment, tool outputs | task success/expert eval | LLM 화학 이해 한계, 안전/IP 이슈 | LLM 판단은 tool output으로만 근거화. DOI: https://doi.org/10.1038/s42256-024-00832-8 |
| Coscientist | LLM이 문서 검색, 코드 실행, 실험 자동화 API로 화학 실험 설계/실행 | web/docs/code/lab automation | multi-step experimental design | 실험 실행 결과와 코드 결과 | task success/reaction optimization | wet-lab 장비 의존 | dry-lab closed loop: DB search -> code -> critic -> next action. DOI: https://doi.org/10.1038/s41586-023-06792-0 |
| DrugAgent DTI | Coordinator, AI, KG, Search, Reasoning agents로 DTI reasoning | pretrained model, KG, search | coordinator-based multi-agent | strict output format, evidence integration | DTI prediction/reasoning | preprint, domain 제한 | strict JSON output contract와 evidence critic 적용. URL: https://arxiv.org/html/2408.13378v4 |
| DrugAgent programming | Planner/Instructor가 drug discovery ML 구현을 자동화 | LLM agents, ML code | idea -> domain instruction -> implementation | benchmark tasks | ROC-AUC 등 | 코드 생성 중심 | Score Improvement Agent가 실험 설계와 구현 task를 생성. DOI: https://doi.org/10.48550/arXiv.2411.15692 |
| AgentD | modular LLM drug discovery pipeline | database, RAG, ADMET, binding, SMILES generation | modular task execution | ADMET/property prediction, refinement | property profiles | preprint, external API 의존 | 모듈형 agent architecture의 근거로 사용. URL: https://arxiv.org/html/2507.02925v3 |
| SELFIES/STONED | SELFIES mutation으로 training-free chemical space traversal | SELFIES, RDKit | seed mutation/search | validity/optimization/novelty | validity, property improvement | 활성/합성 보장 안 됨 | 본선 MVP의 lightweight generator. DOI: https://doi.org/10.26434/chemrxiv.13383266 |
| GuacaMol | de novo molecular design benchmark | RDKit, ChEMBL set | distribution/goal-directed generation | standardized benchmark | validity, FCD, goal score | full benchmark는 MVP에 무거움 | 평가 관행을 축소 적용. URL: https://github.com/BenevolentAI/guacamol |
| MOSES | molecular generation benchmark platform | ZINC, filters, RDKit | model comparison | scaffold test, filters | validity, uniqueness, novelty, filters, SNN, Frag, Scaff | target-specific activity 없음 | generated molecule QA checklist. DOI: https://doi.org/10.3389/fphar.2020.565644 |
| TDC ADMET | ADMET benchmark group | 22 ADMET datasets | model benchmark | scaffold split | AUROC/AUPRC/MAE/Spearman | predictor calibration 필요 | ADMET risk gate. URL: https://tdcommons.ai/benchmark/admet_group/overview/ |
| Open Targets | target-disease evidence aggregation | GraphQL/API/downloads | evidence ranking | source/type evidence | association score | score는 confidence가 아님 | Evidence Critic 필수. https://platform-docs.opentargets.org/associations |
| ChEMBL | curated bioactivity/molecule DB | REST API | target/activity retrieval | assay/activity filters | pChEMBL/activity count | assay heterogeneity | Seed Ligand Agent의 중심 DB. https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services |
| AiZynthFinder | MCTS retrosynthesis planning | policy model, stock | route search | route solved/score | route availability | setup 무거움 | optional advanced synthesis gate. https://molecularai.github.io/aizynthfinder/ |

## 5. H2L-Forge 현재 약점 진단

| 약점 | 위험 | 개선 |
| --- | --- | --- |
| 제안서가 아직 "작동하는 시스템"보다 "좋은 설계"에 가까움 | 전문가 평가에서 구현 가능성 감점 | API response sample, JSON log schema, top-k candidate table을 제안서에 넣는다. |
| TYK2 선택 논리가 association score와 tractability를 충분히 분리하지 않음 | NOD2가 1위인데 왜 TYK2인지 질문 받을 수 있음 | NOD2는 disease association strong, TYK2는 small-molecule lead loop tractable이라는 이중 기준을 명시한다. |
| 분자 생성 루프가 과장될 수 있음 | "실제 활성 개선 증명" 요구 시 취약 | target-specific activity 예측은 MVP 범위 밖으로 두고, similarity/ADMET/QED/SA의 decision-support로 제한한다. |
| hallucination guardrail이 문서상 약함 | citation 없는 타깃/논문/분자 생성 위험 | DB ID 없으면 report에 못 들어가는 hard rule 추가. |
| 평가 체계가 넓지만 pass/fail threshold가 부족 | 심사위원이 검증 가능성을 낮게 볼 수 있음 | 각 agent별 pass/warn/fail threshold를 명시한다. |

## 6. 평가 점수 개선표

| 평가 항목 | 현재 예상 점수 | 목표 점수 | 감점 요인 | 개선 전략 | 구현 난이도 | 우선순위 |
| --- | ---: | ---: | --- | --- | --- | --- |
| Agentic AI 구현성 | 14/20 | 18/20 | loop log/agent autonomy 증거 부족 | Score Improvement Agent, failure/retry log 추가 | 중 | P0 |
| 신약개발 문제 적합성 | 15/20 | 18/20 | 타깃-분자 연결 논리 보강 필요 | IBD/TYK2/NOD2 대비 논리 강화 | 중 | P0 |
| 도구 활용성 | 15/20 | 19/20 | 실제 API response artifact 부족 | Open Targets/ChEMBL/RDKit/TDC 호출 샘플 저장 | 중 | P0 |
| 자율형 가설 생성/검증 | 14/20 | 18/20 | 가설 critic threshold 부족 | evidence diversity/tractability/assay availability scoring | 중 | P0 |
| 분자 최적화 루프 | 12/20 | 17/20 | generator와 평가 지표가 추상적 | SELFIES/STONED + RDKit metrics + Pareto score | 중상 | P1 |
| 데이터/API 신뢰성 | 13/20 | 18/20 | citation verifier 미구현 | API cache, source hash, DB ID validation | 중 | P0 |
| 성능 평가 체계 | 7/10 | 9/10 | pass/fail 기준 부족 | evals/rubric.md와 golden cases | 하 | P0 |
| 독창성 | 16/20 | 19/20 | 기존 ChemCrow류와 차별성 설명 필요 | target hypothesis와 lead optimization feedback 결합을 전면화 | 하 | P0 |
| 구현 가능성 | 14/20 | 18/20 | AiZynthFinder/TDC 범위 과대 | MVP/Stretch 분리 | 하 | P0 |
| 안전/윤리성 | 7/10 | 9/10 | dual-use/synthesis guardrail 구체성 부족 | route detail suppression, human approval gate | 하 | P0 |
| 발표/시연 완성도 | 12/20 | 18/20 | UI/데모 흐름 미정 | 5분 demo script와 report template 설계 | 중 | P1 |
| 보고서 추적 가능성 | 13/20 | 19/20 | log schema 부족 | `run_id`, `source_id`, `api_response_hash`, `failure_reason` 표준화 | 중 | P0 |

## 7. Score Improvement Loop 설계

| Loop 단계 | 수행 내용 | 입력 | 출력 | 사용 도구/API | 성공 기준 | 실패 조건 | 로그 포맷 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1. 진단 | 제안서/코드/데모 상태를 평가표에 매핑 | docs, code, demo logs | weakness list | rubric | 항목별 gap 명시 | 근거 없는 점수 추정 | `diagnosis.json` |
| 2. 약점 탐지 | 낮은 점수 항목과 원인 분리 | weakness list | ranked issues | Score Improvement Agent | P0/P1/P2 산출 | 액션 불명확 | `issue_rank.json` |
| 3. 개선 가설 | "무엇을 바꾸면 점수가 오르는가" 생성 | ranked issues | hypotheses | LLM + rubric | 각 가설에 metric 연결 | metric 없는 가설 | `hypothesis_log.jsonl` |
| 4. 우선순위화 | impact/effort/risk로 선별 | hypotheses | sprint plan | rubric | P0 3개 이하 | 범위 과대 | `priority_matrix.md` |
| 5. 구현/실험 | API connector, scoring, report 수정 | sprint plan | code/docs | Open Targets, ChEMBL, RDKit | runnable artifact | API 실패 미처리 | `experiment_run.json` |
| 6. 측정 | pass/fail threshold와 before/after 비교 | outputs | metrics table | pytest, notebook, script | delta 기록 | baseline 없음 | `metrics.json` |
| 7. 실패 기록 | 실패 원인과 재시도 조건 기록 | exceptions, low metrics | failure modes | failure logger | failure reason taxonomy | 원인 누락 | `failures.jsonl` |
| 8. 다음 루프 | 다음 개선안을 자동 제안 | metrics, failures | next loop backlog | Score Improvement Agent | next action 1~3개 | 무한 반복 | `next_loop.md` |

## 8. 제안서 문장 개선안

| 제안서 섹션 | 기존 약점 | 개선 방향 | 바로 넣을 문장 |
| --- | --- | --- | --- |
| 제목 | 일반적 | agentic loop와 traceability 강조 | H2L-Forge: 근거 추적형 질병-타깃 가설 생성 및 후보 분자 최적화 에이전트 |
| 한 줄 설명 | 기능 나열 | 폐루프 가치 제시 | 질병 근거 그래프와 분자 최적화 도구를 연결해, 검증 가능한 타깃 가설과 lead 후보 개선 이력을 함께 제안하는 agentic drug discovery system |
| 문제정의 | 병목 설명이 추상적 | target hypothesis와 lead optimization 단절 명시 | 초기 신약개발의 병목은 좋은 타깃을 고르는 일과 좋은 분자를 만드는 일이 서로 다른 도구와 파일에서 끊긴다는 점이다. |
| 대회 적합성 | 분야 1+2 나열 | 분야 4 융합으로 명확화 | H2L-Forge는 분야 1의 가설 생성/검증 결과를 분야 2의 분자 최적화 objective로 전달하고, ADMET/합성성 실패를 다시 타깃 가설 검토로 되돌린다. |
| LLM wrapper 아님 | 주장만 있음 | tool ownership 분리 | LLM은 결론을 생성하지 않고 다음 행동을 선택한다. 사실 검증은 Open Targets/ChEMBL API, 화학 계산은 RDKit/TDC/AiZynthFinder가 수행한다. |
| 선행연구 차별성 | ChemCrow류와 유사해 보임 | disease-target-to-lead feedback 차별화 | ChemCrow가 chemistry tool orchestration을 보였다면, H2L-Forge는 질병-타깃 근거와 lead optimization 지표를 같은 audit trail에서 닫는 데 집중한다. |
| IBD/TYK2 논리 | TYK2 선택 질문 가능 | NOD2 vs TYK2 대비 | NOD2는 IBD association이 강하지만 small-molecule lead optimization 데모에는 TYK2가 더 적합하다. TYK2는 Open Targets에서 IBD 관련 상위권이며 ChEMBL target과 승인 reference molecule이 있어 closed-loop를 검증하기 좋다. |
| 평가 방법 | 지표 많음 | pass/fail threshold 추가 | 모든 후보는 validity, similarity band, ADMET risk, synthetic feasibility, evidence coverage의 hard gate를 통과해야 top-k에 오른다. |
| 4주 구현 가능성 | 범위 넓음 | MVP/Stretch 분리 | 본선 MVP는 IBD/TYK2 단일 데모, top 5 후보, traceable report까지로 제한하고 docking/advanced retrosynthesis는 stretch로 둔다. |
| 안전/윤리 | 일반론 | 실행형 합성 지침 제한 | 합성 경로는 route found 여부와 난이도 signal까지만 표시하며, 위험 물질 또는 실행 가능한 제조 지침은 human approval 없이 출력하지 않는다. |

## 9. 확인 불가능한 내용 / 추가 검증 필요

- 제4회 수상권 프로젝트의 실제 내부 평가 선호는 공개 전이므로 "추정"이다.
- DAKER/KHIDI PDF의 세부 평가표는 기존 로컬 문서에 반영되어 있으나, 제출 직전 공식 공지 변경 여부를 다시 확인해야 한다.
- Open Targets tractability 상세 GraphQL field는 본선 구현 중 API schema introspection으로 재확인해야 한다.
- TDC ADMET pretrained predictor 사용 가능성과 설치 호환성은 로컬 환경에서 검증해야 한다.
- AiZynthFinder는 모델/stock 다운로드와 실행 시간이 필요하므로 MVP에서는 SA score proxy를 기본값으로 둔다.
