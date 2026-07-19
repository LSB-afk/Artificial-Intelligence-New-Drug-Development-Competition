# Eligibility-Gated Molecular Optimization Loop

> **현재 상태:** TYK2/deucravacitinib 데이터는 IBD positive lead가 아니라
> `REJECTION_DEMO`의 근거 검증 및 `METHOD_ONLY` 화학 toolchain qualification에만 사용할 수 있다.
> 과학적 molecule branch는 별도 타깃이 `ADVANCE`와 human approval을 받은 뒤 활성화한다.

## 0. Entry Gate

| Run mode / target state | Molecule generation | Therapeutic claim | Required evidence |
| --- | --- | --- | --- |
| `SCIENTIFIC` + `MOLECULE_ELIGIBLE` | Allowed within budget | Bounded hypothesis only | target decision, reviewer approval, measured/predicted/proxy labels |
| `REJECTION_DEMO` + TYK2 `REJECT/HOLD` | Blocked | Forbidden | contradiction ledger |
| `METHOD_ONLY` | Allowed for tool smoke/eval | Forbidden | persistent method-only label and lineage |

## 1. Baseline molecule set

| Source | Query | Filter | Output |
| --- | --- | --- | --- |
| ChEMBL target | `target_chembl_id=CHEMBL3553` | organism Homo sapiens, standard_type in IC50/Ki/Kd, standard_units nM, standard_relation `=` 우선 | TYK2 active ligand table |
| Reference drug | `molecule_chembl_id=CHEMBL4435170` | max_phase 4, small molecule, structure available | deucravacitinib SMILES; psoriasis approval is not IBD validation |
| Known actives | pChEMBL threshold or standard_value threshold | assay confidence and relation filter | novelty/similarity reference set |
| Negative/weak compounds | high standard_value, weak relation | optional | contrast set |

2026-07-06 API 확인값: ChEMBL status `ChEMBL_37`, TYK2 target `CHEMBL3553`, deucravacitinib `CHEMBL4435170`. 당시 기록된 TYK2 activity count 44,880은 2026-07-16 ChEMBL 500 오류로 재검증하지 못했으므로 current response snapshot 전에는 최종 주장에 사용하지 않는다. Source: https://www.ebi.ac.uk/chembl/api/data/status.json / https://www.ebi.ac.uk/chembl/api/data/target/CHEMBL3553.json / https://www.ebi.ac.uk/chembl/api/data/molecule/CHEMBL4435170.json

## 2. SELFIES/STONED mutation 적용

1. Seed SMILES를 RDKit으로 canonicalize한다.
2. SMILES -> SELFIES 변환.
3. mutation budget을 1, 2, 3 step으로 제한한다.
4. generated SELFIES -> SMILES -> RDKit sanitization.
5. reference와 Tanimoto similarity가 너무 낮으면 reject한다.
6. PAINS/reactive alert가 있으면 reject 또는 warn 처리한다.
7. unique canonical SMILES만 남긴다.

근거: STONED는 SELFIES string modification으로 training-free molecular exploration을 수행한다. DOI: https://doi.org/10.26434/chemrxiv.13383266

## 3. Objective table

| Objective | 지표 | 목표 방향 | 도구 |
| --- | --- | --- | --- |
| Validity | RDKit valid SMILES | 높일 것 | RDKit |
| Drug-likeness | QED, Lipinski, Veber | 높일 것 | RDKit |
| Activity evidence | measured assay, validated QSAR, or explicit similarity proxy | type와 uncertainty를 보존 | ChEMBL / versioned model / RDKit |
| Similarity | eligible target의 measured actives 또는 `METHOD_ONLY` reference와 Tanimoto | 사전 정의 band 유지; activity로 표현 금지 | RDKit |
| Novelty | eligible target actives와 scaffold/similarity 비교 | known과 동일/과근접 회피 | ChEMBL + RDKit |
| ADMET | hERG, AMES, DILI, CYP, Caco-2 | risk 낮출 것 | planned ADMET-AI after smoke validation |
| Synthesizability | bulk SA/RAscore, optional top-5 AiZynthFinder | 쉬울수록 좋음 | RDKit SA / planned RAscore / optional AiZynthFinder |
| Safety | PAINS, toxicophore, reactive group alert | 위험 낮출 것 | RDKit filter |

## 4. Multi-objective score

단일 점수는 ranking helper일 뿐이며 최종 선택은 Pareto front와 hard gate를 함께 사용한다.

```text
hard_fail =
  invalid_smiles
  or pains_alert
  or reactive_alert
  or activity_evidence_type == "UNKNOWN"
  or similarity_proxy_outside_predeclared_band
  or hERG_high_risk
  or AMES_high_risk
  or SA_score > 6.5

composite_score =
  0.18 * qed_norm
+ 0.12 * lipinski_veber_pass
+ 0.15 * similarity_band_score
+ 0.15 * novelty_score
+ 0.20 * admet_safety_score
+ 0.12 * synthesizability_score
+ 0.08 * evidence_trace_score
```

## 5. 후보가 좋아졌다는 증명

| 증명 항목 | 방법 | 성공 기준 |
| --- | --- | --- |
| Validity 개선 | generated set의 RDKit pass rate | 95% 이상 |
| Drug-likeness 유지/개선 | reference/seed 평균 대비 QED, Lipinski/Veber | QED 악화 0.05 이하 또는 개선 |
| Target relevance 근거 유지 | eligible target의 measured actives/QSAR 또는 명시적 proxy | evidence type과 사전 정의 기준 충족 |
| Novelty 확보 | exact duplicate/scaffold duplicate 제거 | duplicate 0 |
| ADMET risk 감소 | hERG/AMES/DILI/CYP risk weighted sum | seed 대비 risk score 감소 |
| 합성성 악화 방지 | SA/RAscore bulk gate, optional top-5 route signal | 사전 정의 gate; AiZynth 입력 <= 5 |
| traceability | every top-k molecule has source and score components | 100% |

## 6. Over-optimization 방지

- QED만 높이는 분자를 금지한다.
- similarity가 너무 낮은 "target relevance 없는" 분자를 금지한다.
- similarity가 너무 높은 "reference 복붙" 분자를 금지한다.
- known actives와 exact duplicate 또는 scaffold duplicate를 제거한다.
- ADMET 하나만 개선되고 나머지가 무너진 후보는 Pareto dominated로 제거한다.
- agent가 "활성 개선"이라고 쓰려면 QSAR/docking/assay evidence가 필요하다. MVP에서는 "activity-preserving 가능성"까지만 표현한다.

## 7. 최종 Top-k 선정

1. target eligibility 또는 `METHOD_ONLY`를 확인한다. `REJECT/HOLD`면 즉시 중단한다.
2. hard gate 통과 후보만 남긴다.
3. composite score top 30을 뽑는다.
4. Pareto front를 계산한다.
5. scaffold diversity clustering으로 같은 계열 중복을 줄인다.
6. top-k 5개를 선정한다.
7. optional AiZynthFinder는 이 5개에만 실행한다.
8. 각 후보별로 `why_selected`, `why_not_claimed`, `next_experiment`를 기록한다.

## 8. Candidate log schema

```json
{
  "run_id": "2026-07-06-ibd-tyk2-001",
  "run_mode": "METHOD_ONLY",
  "target_decision_id": null,
  "molecule_eligibility": false,
  "candidate_id": "H2L-TYK2-0001",
  "parent_molecule_chembl_id": "CHEMBL4435170",
  "smiles": "...",
  "valid": true,
  "qed": 0.61,
  "lipinski_pass": true,
  "tanimoto_to_deucravacitinib": 0.52,
  "nearest_known_tyk2_active": {"chembl_id": "...", "tanimoto": 0.71},
  "activity_evidence": {"type": "PROXY", "value": 0.71, "limitation": "similarity is not measured or predicted activity"},
  "admet": {"herg": "low", "ames": "low", "dili": "warn", "cyp3a4": "low"},
  "synthesis": {"sa_score": 4.2, "route_found": null},
  "alerts": [],
  "composite_score": 0.73,
  "decision": "top_k_candidate",
  "failure_reason": null,
  "evidence": [
    "https://www.ebi.ac.uk/chembl/explore/compound/CHEMBL4435170",
    "https://www.ebi.ac.uk/chembl/api/data/target/CHEMBL3553.json"
  ]
}
```
