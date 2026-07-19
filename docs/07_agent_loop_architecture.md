# H2L-Forge Agentic Closed-Loop Architecture

> **역할:** 이 문서는 세부 capability/log/retry 초안이다. 현재 권한 경계와 6-role runtime은
> `docs/07_architecture.md`가 canonical이다. 아래의 세부 agent는 독립 LLM 수를 뜻하지 않으며,
> Disease Normalizer/Target Discovery 등은 Evidence Scout의 capability로 합쳐 구현할 수 있다.

## 1. Agent Architecture 개선안

| Agent | 역할 | 입력 | 출력 | 사용하는 API/tool | 내부 판단 기준 | 실패 조건 | retry 전략 | human-in-the-loop 조건 | 로그 포맷 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Disease Normalizer | 질병명과 ontology ID 정규화 | disease text | selected disease ID, synonym set | Open Targets search | exact name, MONDO/EFO match, synonym confidence | 후보 다수/불일치 | top candidates 재질문 또는 synonym 확장 | disease ambiguity | `disease_normalization.json` |
| Target Discovery Agent | 질병 관련 target 후보 수집 | disease ID | target candidates | Open Targets associatedTargets | association score, evidence types, tractability | API 실패, target 없음 | GraphQL 재시도, downloads fallback | 근거 부족 질환 | `target_candidates.json` |
| Evidence Critic | 적응증별 target `ADVANCE/HOLD/REJECT` 권고 | target candidates + claim ledger | contradiction-aware hypotheses | Open Targets, ChEMBL indication, ClinicalTrials.gov, literature | indication match, failed trials, evidence diversity, tractability, assay availability, safety | 지지 근거만 수집/association score 단일 의존 | 반증 source class별 재수집 | `ADVANCE`, conflicting evidence | `evidence_critique.json` |
| Seed Ligand Agent | seed/reference ligand 수집 | target ID | seed ligand table | ChEMBL target/activity/molecule | assay confidence, IC50/Ki/Kd, pChEMBL, standard units, approved drug | assay 부족, units 혼재 | filter 완화/대체 target | seed 부족 | `seed_ligands.parquet`, `chembl_queries.jsonl` |
| Molecule Optimizer | 후보 구조 생성 | seed SMILES, objective | candidate SMILES | RDKit, SELFIES/STONED | validity, similarity band, uniqueness, novelty | invalid rate 높음 | mutation radius 조정, scaffold constraint | risk alert 반복 | `optimization_run.jsonl` |
| ADMET/Safety Agent | 약물성/독성/구조 경고 평가 | candidate SMILES | typed ADMET risk table | RDKit, planned ADMET-AI | hERG, AMES, DILI, CYP, Caco-2, QED, Lipinski, PAINS | predictor unavailable/unvalidated | metric unavailable + RDKit-only limited report | high toxicity top candidate | `admet_scores.parquet` |
| Synthesis Feasibility Agent | 합성 가능성 2단 평가 | candidate SMILES | SA/RAscore + optional route signal | RDKit SA, planned RAscore, top-5 AiZynthFinder | fast bulk gate, top-5 route found/score | dependency unavailable/time out | SA fallback, timeout/candidate cap | route detail 요청 | `synthesis_feasibility.jsonl` |
| Report Agent | 근거 기반 보고서 생성 | all logs | markdown/html report | local templates | every claim has source, every molecule has scores | citation missing | report block until evidence attached | final candidate approval | `report_trace.json` |
| Score Improvement Agent | 평가 기준별 개선 루프 총괄 | proposal, logs, metrics | next improvement backlog | rubric, metrics scripts | score gap, evidence coverage, feasibility risk | 근거 없는 개선안 | stricter rubric rerun | scope expansion | `score_improvement_loop.jsonl` |

## 2. Agent Capability Cards

### Agent Capability: Target Hypothesis Selection

| Field | Content |
| --- | --- |
| Trigger | disease ID가 확정되고 associated targets가 수집됨 |
| Inputs | Open Targets association rows, tractability, ChEMBL assay availability |
| Context Sources | Open Targets, ChEMBL, literature links |
| Judgment | target is `advance`, `hold`, or `compare`; confidence 0-1; rationale |
| Possible Actions | select target, ask for disease clarification, switch target, mark data-insufficient |
| Forbidden Actions | association score만으로 target 확정, citation 없는 target claim |
| Verification | target ID valid, evidence count > threshold, assay availability checked |
| Approval Needed? | confidence < 0.65 or safety concern |
| Audit Events | `target_ranked`, `target_selected`, `target_rejected` |
| Failure Modes | no ChEMBL assay, conflicting evidence, only text-mining evidence |
| Eval Cases | IBD: TYK2가 tractable해 보여도 psoriasis approval과 IBD 실패를 분리해 `REJECT/HOLD`; molecule eligibility 차단 |

### Agent Capability: Candidate Molecule Ranking

| Field | Content |
| --- | --- |
| Trigger | candidate SMILES generated |
| Inputs | seed molecule, candidate SMILES, known TYK2 actives |
| Context Sources | RDKit descriptors, ChEMBL measured activity, validated QSAR or explicit Tanimoto proxy, planned ADMET-AI, SA/RAscore, optional top-5 AiZynth |
| Judgment | candidate rank, measured/predicted/proxy/unknown type, pass/warn/fail, reason |
| Possible Actions | accept top-k, mutate again, reject, request human review |
| Forbidden Actions | invalid SMILES ranking, high-risk molecule promotion, unsupported activity claim |
| Verification | RDKit valid, similarity band, novelty check, ADMET gates |
| Approval Needed? | target `ADVANCE` and molecule eligibility, final export, route detail request |
| Audit Events | `candidate_generated`, `candidate_scored`, `candidate_rejected`, `topk_selected` |
| Failure Modes | over-optimization, unrealistic molecule, PAINS/reactive alert |
| Eval Cases | deucravacitinib analog candidates must preserve similarity while improving risk score |

## 3. Score Improvement Agent 상세 역할

| 기능 | 판단 기준 | 산출물 |
| --- | --- | --- |
| 평가 기준별 약점 탐지 | rubric 항목별 pass/warn/fail | `rubric_gap_report.md` |
| candidate ranking 개선 | top-k의 score component contribution | `ranking_delta.json` |
| report traceability 개선 | claims with source / total claims | `citation_coverage.json` |
| evidence coverage 개선 | source type diversity, DB ID validity | `evidence_matrix.csv` |
| hallucination 위험 탐지 | citation 없는 논문/타깃/분자 claim | `hallucination_flags.jsonl` |
| 구현 범위 과대 판단 | 4주 MVP effort budget 초과 여부 | `scope_risk.md` |
| 다음 실험 자동 제안 | impact x effort x risk | `next_experiments.md` |

## 4. Failure/Retry/Human Approval 규칙

| 실패 유형 | 감지 조건 | 자동 retry | human-in-the-loop |
| --- | --- | --- | --- |
| API outage | HTTP timeout/5xx | exponential backoff 3회, cache fallback | 핵심 source 전체 실패 |
| ID ambiguity | disease/target 후보 다수 | synonym 확장, exact match 우선 | confidence < 0.65 |
| Evidence conflict | association strong but tractability weak | compare target path 생성 | target 전환 판단 |
| Invalid molecule | RDKit sanitization fail | SELFIES mutation radius 축소 | invalid rate > 20% |
| ADMET risk | hERG/AMES/DILI high | candidate reject, mutate again | top-k 모두 high risk |
| Synthesis risk | route not found or SA high | SA fallback, lower rank | route detail 출력 요청 |
| Hallucination | source 없는 claim | report block, citation repair | source repair 실패 |

## 5. Python 구현 구조 개선안

```text
src/h2l_forge/
  agents/
    disease_normalizer.py
    target_discovery.py
    evidence_critic.py
    seed_ligand.py
    molecule_optimizer.py
    admet_safety.py
    synthesis_feasibility.py
    report_agent.py
    score_improvement.py
  tools/
    opentargets_client.py
    chembl_client.py
    rdkit_metrics.py
    admet_ai.py
    selfies_stoned.py
    synthesis_proxy.py
  schemas/
    run_log.py
    molecule_score.py
    target_hypothesis.py
  pipelines/
    ibd_tyk2_demo.py
  reports/
    render_markdown.py
tests/
  test_opentargets_client.py
  test_chembl_client.py
  test_rdkit_metrics.py
  test_score_contracts.py
evals/
  golden-cases.md
  rubric.md
  failure-modes.md
```

## 6. 본선 4주 로드맵

| 주차 | 목표 | 산출물 | 성공 기준 |
| --- | --- | --- | --- |
| 1주차 | API/evidence spine 구축 | Open Targets/ChEMBL clients, IBD/TYK2 cache | disease ID, target list, ligand table 재현 |
| 2주차 | target hypothesis loop | Evidence Critic, target report | NOD2/TYK2/JAK2/IL12B/IL23R 비교 리포트 |
| 3주차 | eligibility-gated molecule loop | RDKit/SELFIES, typed activity evidence, ADMET-AI smoke, SA/RAscore | valid top-k 후보, rejection lineage, before/after score |
| 4주차 | 통합 데모/보고서 | Streamlit or notebook demo, final report, slides | 5분 시연: 입력 -> target -> molecule -> report |

## 7. 지금 당장 해야 할 작업 체크리스트

- [ ] `src/h2l_forge/tools/opentargets_client.py` 구현
- [ ] `src/h2l_forge/tools/chembl_client.py` 구현
- [ ] IBD/TYK2 contradiction evidence snapshot/manifest 저장
- [ ] positive molecule target을 동일한 clinical gate로 검증
- [ ] ChEMBL TYK2 activity filter 기준 확정
- [ ] RDKit descriptor/QED/similarity baseline 구현
- [ ] SELFIES/STONED mutation prototype 구현
- [ ] read-only `Evaluation Agent`가 `evals/rubric.md`를 읽고 scientific state를 바꾸지 않는 gap report 생성
- [ ] 제안서 첫 2쪽을 "문제정의 + 차별성 + 데모 케이스" 중심으로 재작성
