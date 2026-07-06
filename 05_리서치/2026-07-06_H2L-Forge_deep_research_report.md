# H2L-Forge 딥서치 리포트

작성일: 2026-07-06 KST
주제: 분야 1 자율형 가설 생성/검증 + 분야 2 도구 활용 기반 분자 최적화 루프 융합
대상 에이전트: H2L-Forge, Hypothesis-to-Lead Agent

## 1. 결론 요약

H2L-Forge의 핵심 가치는 "질병-타깃 가설"과 "분자 최적화"를 분리하지 않고 하나의 폐루프로 연결하는 데 있다. 최신 선행연구와 실행 가능한 공개 도구를 기준으로 보면, 이 주제는 대회 분야 1과 분야 2를 가장 자연스럽게 융합한다.

추천 데모 케이스는 `inflammatory bowel disease`(IBD)에서 `TYK2` 중심으로 시작하는 흐름이다. Open Targets에서 IBD는 `MONDO_0005265`로 검색되고, 상위 타깃 후보가 충분히 많다. 그중 TYK2는 association 순위만 보면 9위권이지만, small molecule tractability, ChEMBL assay 밀도, 승인 약물 사례가 강해 "왜 이 타깃을 다음 최적화 루프로 넘기는가"를 설명하기 좋다.

예선 제안서에서 강조할 문장은 다음과 같다.

> H2L-Forge는 질병 근거 그래프에서 검증 가능한 타깃 가설을 만들고, 타깃별 seed molecule을 수집한 뒤 약물성, ADMET, 합성 가능성을 반복 평가해 "왜 이 타깃인가"와 "왜 이 분자인가"를 하나의 추적 가능한 연구 로그로 설명하는 에이전틱 AI다.

## 2. 리서치 질문

1. 분야 1의 자율형 가설 생성/검증과 분야 2의 분자 최적화 루프를 하나의 실행 가능한 신약개발 에이전트로 설계할 수 있는가?
2. 그 설계가 공식 데이터베이스와 현재 공개 도구만으로 예선 제안서 및 본선 MVP까지 이어질 만큼 현실적인가?
3. 대표 데모 질환과 타깃을 무엇으로 잡아야 과학적 타당성, 구현 가능성, 차별성이 균형을 이루는가?

## 3. 직접 권고

H2L-Forge는 다음 범위로 제출 방향을 고정하는 것이 좋다.

| 항목 | 권고 |
| --- | --- |
| 선택 분야 | 분야 1 + 분야 2 융합. 제출서에는 융합 분야 성격도 명시한다. |
| 데모 질환 | inflammatory bowel disease, Open Targets ID: `MONDO_0005265` |
| 1차 데모 타깃 | TYK2, Open Targets/Ensembl: `ENSG00000105397`, ChEMBL target: `CHEMBL3553` |
| 대체/비교 타깃 | NOD2, IL12B, JAK2, IL23R |
| seed molecule 근거 | ChEMBL TYK2 activity 44,880건, deucravacitinib `CHEMBL4435170` 승인 약물 사례 |
| 최적화 방식 | RDKit 표준화/QED/descriptor + SELFIES/STONED 변형 + TDC ADMET + AiZynthFinder 또는 SA score |
| 산출물 | target hypothesis report, molecule candidate table, Pareto ranking, failure log, citation/audit trail |

핵심 포인트는 "association score가 높은 타깃"만 고르지 않는 것이다. Open Targets 문서는 association score를 근거 가용성 기반 휴리스틱으로 설명하며, confidence score로 해석하지 말라고 경고한다. 따라서 H2L-Forge는 association, tractability, assay availability, safety, novelty를 함께 보는 의사결정 에이전트로 포지셔닝해야 한다.

## 4. 근거 1: 에이전틱 AI가 왜 필요한가

ChemCrow는 LLM이 단독으로 화학 문제를 풀 때 외부 지식과 전문 도구가 부족하다는 문제를 지적하고, 18개 화학 도구를 결합해 유기합성, 신약개발, 소재 설계 작업을 수행하는 화학 에이전트로 제안되었다. 이는 H2L-Forge가 LLM 자체의 화학 지식보다 DB/API/tool orchestration에 초점을 둬야 한다는 근거다.

Coscientist는 LLM 기반 시스템이 문서 검색, 코드 실행, 실험 자동화 API를 결합해 화학 실험 설계와 실행을 수행할 수 있음을 보였다. H2L-Forge는 실제 실험 자동화까지 가지 않더라도, 신약개발 초기 단계의 "문헌/DB 검색 -> 코드/모델 실행 -> 결과 해석 -> 다음 행동 결정" 구조를 구현할 수 있다.

2025년 Chemical Science 리뷰는 화학 분야 LLM 에이전트의 핵심 과제로 데이터 품질, 통합, 해석 가능성, 표준 benchmark 필요성을 제시한다. 따라서 H2L-Forge 제안서에는 "도구를 많이 붙였다"가 아니라 "각 판단을 DB ID, 점수, 실패 조건으로 검증한다"는 평가 체계를 반드시 넣어야 한다.

## 5. 근거 2: 질병-타깃 가설 생성은 Open Targets가 적합하다

Open Targets GraphQL API는 target, disease/phenotype, drug, target-disease association, search를 조회할 수 있고, 단일 질병/타깃 중심 프로토타입에는 GraphQL이 충분하다. 대규모/체계적 batch query는 data downloads나 BigQuery가 더 적합하다.

Open Targets association score는 다음처럼 해석해야 한다.

- score는 target-disease 근거를 집계한 ranking helper다.
- score가 높다고 생물학적 인과 확신이 곧바로 높다는 뜻은 아니다.
- under-studied disease나 데이터 부족 타깃은 낮은 점수라도 유망할 수 있다.
- 따라서 Evidence Critic이 source diversity, genetic evidence, clinical evidence, tractability, assay availability를 분리 평가해야 한다.

Open Targets tractability 문서는 small molecule, antibody, PROTAC 등 modality별로 binding site, high-quality ligand, 임상 후보, druggable family 여부를 제공한다. H2L-Forge는 분야 2로 넘어갈 수 있는 타깃을 고르기 위해 small molecule tractability를 필수 필터로 써야 한다.

### Open Targets API 관측값

2026-07-06에 GraphQL API로 `inflammatory bowel disease`를 검색한 결과:

```text
search("inflammatory bowel disease") -> MONDO_0005265
associatedTargets count -> 7,629
```

상위 associated targets:

| 순위 | Symbol | 설명 | Association score |
| --- | --- | --- | --- |
| 1 | NOD2 | nucleotide binding oligomerization domain containing 2 | 0.8643 |
| 2 | IL10RA | interleukin 10 receptor subunit alpha | 0.8271 |
| 3 | IL10RB | interleukin 10 receptor subunit beta | 0.8164 |
| 4 | ADAM17 | ADAM metallopeptidase domain 17 | 0.7785 |
| 5 | IL10 | interleukin 10 | 0.7635 |
| 6 | IL12B | interleukin 12B | 0.7601 |
| 7 | JAK2 | Janus kinase 2 | 0.7510 |
| 8 | ITGA4 | integrin subunit alpha 4 | 0.7422 |
| 9 | TYK2 | tyrosine kinase 2 | 0.7298 |
| 10 | IL23R | interleukin 23 receptor | 0.7068 |

TYK2 tractability 관측값:

| 항목 | 값 |
| --- | --- |
| Small molecule approved drug | true |
| Small molecule structure with ligand | true |
| Small molecule high-quality ligand | true |
| Small molecule med-quality pocket | true |
| Small molecule druggable family | true |
| Antibody approved drug | false |

해석: NOD2가 association score 1위지만, H2L-Forge 데모에서는 TYK2가 분야 2 분자 최적화 루프와 더 잘 연결된다. 이 차이를 설명하는 것이 곧 에이전트의 설계 독창성이다.

## 6. 근거 3: seed molecule과 assay는 ChEMBL이 중심이다

ChEMBL은 drug-like bioactive molecule의 수작업 큐레이션 DB이며, chemical, bioactivity, genomic data를 연결한다. Web Services는 activity, assay, molecule, target, mechanism, drug indication, similarity, substructure 등 H2L-Forge에 필요한 자원을 제공한다.

2026-07-06 API 관측:

```json
{
  "chembl_db_version": "ChEMBL_37",
  "chembl_release_date": "2026-05-01",
  "activities": 24527044,
  "compound_records": 3824604,
  "disinct_compounds": 2921148,
  "targets": 18552,
  "publications": 101100,
  "status": "UP"
}
```

TYK2 관련 관측:

```text
ChEMBL target search "tyrosine kinase 2" -> CHEMBL3553
activity count for CHEMBL3553 -> 44,880
deucravacitinib -> CHEMBL4435170, max_phase 4.0, first_approval 2022, small molecule
mechanism -> TYK2 negative allosteric modulator
```

이 데이터는 본선 MVP에서 다음을 가능하게 한다.

1. TYK2 seed ligand를 activity endpoint에서 수집한다.
2. assay confidence, standard type, standard value, relation, units를 필터링한다.
3. 승인 약물 deucravacitinib은 positive control 또는 reference scaffold로 둔다.
4. 신규 후보는 reference 대비 Tanimoto similarity, QED, ADMET, synthetic accessibility를 함께 평가한다.

## 7. 근거 4: 분자 최적화는 "생성"보다 "검증 가능한 개선 루프"가 중요하다

RDKit QED는 molecular weight, logP, TPSA, HBA/HBD, aromatic ring, rotatable bond, unwanted functionality 등 drug-likeness 관련 속성을 반영한다. 예선에서는 QED를 "절대적 성공 지표"가 아니라 빠른 후보 필터와 before-after 비교 지표로 써야 한다.

SELFIES/STONED 계열은 training-free 또는 경량 구조 변형 루프를 설계하기 좋다. 장점은 invalid SMILES 비율을 낮추고 seed 기반 근접 탐색을 빠르게 수행할 수 있다는 점이다. 단점은 단순 mutation만으로는 실제 활성, 선택성, 합성 가능성을 보장하지 못한다는 점이다.

GuacaMol과 MOSES는 molecular generation 평가에서 validity, uniqueness, novelty, distribution learning, goal-directed optimization 같은 관행을 제공한다. H2L-Forge는 이 관행을 그대로 leaderboard로 삼기보다 다음처럼 축소 적용하는 것이 현실적이다.

| 평가 축 | 본선 MVP 지표 |
| --- | --- |
| Validity | RDKit sanitization pass rate |
| Uniqueness | unique canonical SMILES 비율 |
| Novelty | seed 및 known ChEMBL compound와 similarity 범위 |
| Local optimization | QED/ADMET/Pareto score before-after delta |
| Target relevance | TYK2 known ligand chemical neighborhood 회복 여부 |

## 8. 근거 5: ADMET과 합성가능성은 early kill-switch로 둬야 한다

TDC ADMET Benchmark Group은 22개 ADMET dataset을 제공하며, scaffold split으로 train/validation/test를 나누고 binary classification에는 AUROC/AUPRC, regression에는 MAE/Spearman을 사용한다. H2L-Forge에는 다음 ADMET 축이 우선이다.

| ADMET 축 | 우선 지표 | 이유 |
| --- | --- | --- |
| Absorption | Caco2, HIA, Pgp, Bioavailability, Lipophilicity, AqSol | 경구 small molecule 가능성 판단 |
| Distribution | BBB, PPBR, VDss | CNS off-target 및 exposure 리스크 |
| Metabolism | CYP2C9/2D6/3A4 inhibition/substrate | DDI 및 대사 리스크 |
| Toxicity | hERG, AMES, DILI, LD50 | 후보 조기 탈락 기준 |

AiZynthFinder는 retrosynthetic planning 도구이며, MCTS 기반으로 분자를 purchasable precursor로 분해하고 reaction template policy로 search를 유도한다. 본선에서는 실제 합성 route 세부 실행법을 제시하기보다 다음처럼 안전하게 사용한다.

- route score 또는 solved/unsolved 여부를 합성가능성 proxy로 사용한다.
- 고위험/통제 물질/유해 합성 요청은 차단한다.
- route는 "연구용 feasibility signal"로만 보고, 실험 제조 지침으로 제공하지 않는다.

## 9. 추천 시스템 구조

```text
User disease query
  -> Disease Normalizer
     - Open Targets search
     - disease ID selection with synonyms
  -> Target Discovery Agent
     - associated targets
     - evidence type/source summary
  -> Evidence Critic
     - association score is heuristic
     - tractability, assay availability, clinical precedent, safety flags
  -> Hypothesis Writer
     - one-sentence disease-target hypothesis
     - validation plan and uncertainty
  -> Seed Ligand Agent
     - ChEMBL target/activity/assay/molecule/mechanism
     - reference molecule selection
  -> Molecule Optimizer
     - RDKit standardization
     - SELFIES/STONED or scaffold-constrained mutation
  -> ADMET/Safety Agent
     - TDC predictors or baseline model
     - RDKit alerts and descriptor filters
  -> Synthesis Agent
     - AiZynthFinder or SA score proxy
  -> Decision Loop
     - continue target, switch target, or stop
  -> Report Agent
     - evidence table, candidate table, failure log, next experiment plan
```

## 10. 평가 설계

### 10.1 예선 평가표 대응

| 대회 평가 항목 | 리포트/시스템 대응 |
| --- | --- |
| 필요성 및 문제정의 | 타깃 가설과 분자 최적화가 분리된 병목을 해결한다. |
| 설계 독창성/창의성 | association rank만 따르지 않고 tractability와 assay availability를 결합한다. |
| 기술적 실현 가능성 | Open Targets, ChEMBL, RDKit, TDC, AiZynthFinder가 모두 실행 가능한 공개 도구다. |
| 성능평가 체계 | target ranking, retrieval validity, molecular validity, ADMET delta, failure handling을 분리 측정한다. |
| 비즈니스/사회적 가치 | 초기 후보 선정 실패 비용과 반복 조사 시간을 줄인다. |
| 연구 윤리/완성도 | citation trace, human-in-the-loop, harmful synthesis guardrail을 둔다. |

### 10.2 본선 MVP 정량 지표

| 모듈 | 지표 | 목표 |
| --- | --- | --- |
| Disease normalization | correct disease ID selection | IBD -> `MONDO_0005265` |
| Target discovery | Recall@10 against known IBD-relevant targets | NOD2/JAK2/TYK2/IL23R 등 회복 |
| Target selection | evidence + tractability explanation completeness | 각 타깃별 채택/보류 사유 생성 |
| ChEMBL retrieval | valid target/activity/molecule IDs | API 응답 ID 100% trace |
| Molecule generation | valid canonical SMILES rate | 95% 이상 |
| Optimization | QED/ADMET Pareto improvement | seed 대비 개선 후보 5개 |
| Safety | harmful route/detail suppression | 위험 요청 차단 |
| Report | citation/audit coverage | 모든 주장에 source URL/DB ID |

## 11. 리스크와 대응

| 리스크 | 설명 | 대응 |
| --- | --- | --- |
| Association score 오해 | 점수를 confidence처럼 해석하면 과학적 타당성이 약해진다. | score를 evidence availability heuristic으로 명시하고 evidence type을 분리한다. |
| LLM hallucination | 존재하지 않는 논문, 분자, 타깃을 만들 수 있다. | DB ID/API response 없는 항목은 리포트에서 제외한다. |
| 분자 생성 과신 | QED가 좋아도 활성/선택성/합성성이 보장되지 않는다. | QED는 1차 필터로만 쓰고 ChEMBL similarity, ADMET, SA/AiZynthFinder를 함께 본다. |
| 안전/윤리 | 합성 route가 악용될 수 있다. | route 세부 제조 지침 금지, 위험 구조/물질 필터, human approval gate. |
| 본선 구현 범위 과대 | 전체 신약개발 자동화는 4주 MVP로 불가능하다. | IBD 1개, TYK2 중심, 후보 5개 리포트 생성으로 제한한다. |

## 12. 제안서에 바로 넣을 수 있는 문단

초기 신약개발에서는 질병-타깃 가설의 근거 평가와 후보 분자 최적화가 서로 분리되어 연구자의 반복 조사 비용이 커진다. H2L-Forge는 질병명을 입력받아 Open Targets 기반 질병-타깃 근거를 수집하고, association score를 confidence로 오해하지 않도록 evidence type, tractability, assay availability를 분리 평가한다. 이후 ChEMBL에서 타깃별 seed molecule과 assay를 수집하고, RDKit/QED, TDC ADMET, 합성가능성 proxy를 활용해 후보 구조를 다목적 최적화한다. 최종 결과는 후보 정답이 아니라, 왜 이 타깃과 분자를 다음 실험 후보로 볼 수 있는지 설명하는 traceable research report다.

## 13. 다음 작업

1. `05_리서치` 리포트를 바탕으로 `03_proposal_outline.md`의 본문을 10쪽 HWPX 제안서 초안으로 확장한다.
2. TYK2 ChEMBL activity endpoint에서 assay confidence, standard type, standard units 기준 필터 조건을 정한다.
3. RDKit 후보 생성 baseline을 만든다: seed 표준화, Morgan fingerprint, QED, Lipinski-like filter, PAINS/alert.
4. TDC ADMET 중 hERG, AMES, DILI, CYP3A4 inhibition을 우선 구현 대상으로 잡는다.
5. 본선 시연은 "NOD2가 score 1위인데 왜 TYK2를 최적화 루프로 넘기는가"를 보여주는 형태로 설계한다.

## 14. 사용한 주요 근거

| 구분 | 출처 | 리포트에서 사용한 근거 |
| --- | --- | --- |
| 공식 대회 | https://daker.ai/public/hackathons/4th-jump-ai-agentic-drug-challenge | 분야 1/2/융합, 평가 기준, 제출 맥락 |
| Open Targets GraphQL | https://platform-docs.opentargets.org/data-access/graphql-api | target/disease/drug/association/search API, POST endpoint, 단일 질병/타깃 query 근거 |
| Open Targets association | https://platform-docs.opentargets.org/associations | association score의 휴리스틱 해석, direct/indirect evidence |
| Open Targets tractability | https://platform-docs.opentargets.org/target/tractability | small molecule/antibody/PROTAC modality별 tractability 판단 |
| ChEMBL Web Services | https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services | activity, assay, molecule, target, mechanism, similarity/substructure API |
| ChEMBL homepage/status | https://www.ebi.ac.uk/chembl/ / https://www.ebi.ac.uk/chembl/api/data/status.json | ChEMBL_37, 2026-05-01 릴리스, activity/compound/target 규모 |
| RDKit QED | https://www.rdkit.org/docs/source/rdkit.Chem.QED.html | QED 속성, drug-likeness descriptor |
| TDC ADMET Benchmark | https://tdcommons.ai/benchmark/admet_group/overview/ | 22개 ADMET dataset, scaffold split, AUROC/AUPRC/MAE/Spearman |
| AiZynthFinder | https://molecularai.github.io/aizynthfinder/ | MCTS retrosynthesis, stock/policy, CLI/Jupyter interface |
| ChemCrow | https://www.nature.com/articles/s42256-024-00832-8 / https://arxiv.org/abs/2304.05376 | LLM + 18 chemistry tools, chemistry agent 선행연구 |
| Coscientist | https://www.nature.com/articles/s41586-023-06792-0 | 문서 검색, 코드 실행, 실험 자동화 API를 결합한 autonomous chemistry agent |
| Chemistry LLM/Agent Review | https://pubs.rsc.org/en/content/articlehtml/2025/sc/d4sc03921a | chemistry agent 설계, hallucination, benchmark, human-in-the-loop 필요성 |
| AgentD preprint | https://arxiv.org/html/2507.02925v1 | drug discovery modular agent, data retrieval, molecule generation, ADMET/property prediction 구조 |
| GuacaMol | https://github.com/BenevolentAI/guacamol | molecular generation benchmark 관행 |
| MOSES | https://github.com/molecularsets/moses | validity/uniqueness/novelty 등 molecular generation 평가 관행 |
| SELFIES/STONED | https://pmc.ncbi.nlm.nih.gov/articles/PMC8153210/ | SELFIES 기반 구조 탐색/최적화 아이디어 |

