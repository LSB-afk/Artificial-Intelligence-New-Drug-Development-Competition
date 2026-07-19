# H2L-Forge Evaluation Rubric

| 항목 | Pass | Warn | Fail |
| --- | --- | --- | --- |
| Agentic AI 구현성 | 판단→도구→검증→복구/중단→다음 상태가 bounded event로 남음 | 재시도/검증/상태 중 하나 약함 | LLM 답변만 있음 |
| 신약개발 문제 적합성 | 적응증별 임상 근거가 target progression을 실제로 차단/허용함 | 생물학/화학 중 한쪽만 state에 영향 | 용어만 신약개발이고 판단 규칙이 없음 |
| 도구 활용성 | Open Targets/ChEMBL/clinical sources/RDKit와 검증된 ADMET·합성 도구가 typed contract와 fallback으로 분업 | 계획 도구의 runtime 검증이 미완료이나 명시됨 | 도구 이름만 나열하거나 TDC를 즉시 predictor로 오기 |
| 자율형 가설 생성/검증 | 지지 근거와 반증 근거를 수집하고 `ADVANCE/HOLD/REJECT`를 올바르게 선택 | association/tractability 중심, 임상 gate 약함 | 근거 없는 target 선택 또는 indication transfer |
| 분자 최적화 루프 | eligible target/mode, validity, lineage, activity type, ADMET, SA/RAscore, top-5 synthesis gate가 반복 개선에 반영 | 단발 평가는 가능하나 target feedback 약함 | 생성만 하거나 rejected target에서 실행 |
| 과학적 주장 보정 | measured/predicted/proxy/unknown이 100% 구분되고 한계가 보임 | 일부 모호 | similarity를 activity로 주장하거나 molecule을 drug로 표현 |
| 데이터/API 신뢰성 | 모든 최종 claim에 URL/DB ID/date/hash와 cache/live 상태 | 일부 누락 | citation hallucination 또는 cache를 live로 표현 |
| 성능 평가 체계 | 분모·threshold·baseline이 있고 critical case 100% 기준 | 지표는 있으나 자동 실행 미구현 | 측정 불가능하거나 실패 기준 없음 |
| 독창성 | 선행연구를 인용하고 indication-aware 반증, failure ledger, critic ablation으로 차별화 | 차별점이 일반적 | closed loop 자체를 최초/유일로 주장 |
| 구현 가능성 | cache-first, 6-role runtime, bounded budget, ADMET-AI plan, SA/RAscore→top-5 AiZynth로 4주 MVP/확장 분리 | dependency smoke gap이 공개됨 | live API/full retrosynthesis/미검증 모델에 필수 의존 |
| 리소스 효율성 | 호출·시간·cache·candidate·synthesis budget이 측정되고 cap 초과 시 fail-closed | 예산은 있으나 측정 미완료 | 비용/호출 무제한 |
| 안전/윤리성 | 위험 합성 detail suppression, human approval, evaluator read-only, provenance 100% | 일부 control이 문서만 존재 | 안전 gate 없음 또는 고위험 자동 진행 |
| 발표/시연 완성도 | 5분 offline replay에서 TYK2 기각, API 복구, blocked transition, audit/eval을 보여줌 | 한 경로만 재현 | live API 의존/실패 숨김 |
| 보고서 추적 가능성 | manifest/tool/claim/decision/failure/approval/budget artifacts 완비 | 일부 log만 | 재현 불가 |
