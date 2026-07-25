# 13 Competition Readiness Assessment

## Artifact Metadata

- Owner: LSB-afk / project team
- Date: 2026-07-24
- Purpose: Map H2L-Forge to the AI 신약개발 경진대회 domains and both rubrics (예선/본선), grounded in the actual repository and eval reports.
- Evidence: `artifacts/eval_report.json`, `artifacts/molopt_eval_report.json`, `src/h2l/molopt.py`, `src/h2l/tools.py`, `docs/02_field1_field2_fusion_design.md`, `docs/01_business-model.md`, `web_dongseop/`.

## Verdict

H2L-Forge has competition-grade **design, harness discipline, and evaluation structure**, but the thing the competition centers on — a **추론 기반 자율(agentic) LLM** — is not yet actually running. The current system is a rigorous, byte-reproducible **deterministic** harness. Inserting a local-LLM orchestration/explanation layer (Ollama) is the single highest-leverage move for the score, and it raises autonomy/demo/originality — not scientific accuracy, which is (correctly) tool-driven.

## Domain Coverage

We are a **분야 4 (융합)** entry.

| 대회 분야 | 상태 | 근거 |
|---|---|---|
| 분야 1: 자율형 가설 생성·검증 | ✅ 강함 | Evidence Critic, 적응증별 반증, `ADVANCE/HOLD/REJECT`, TYK2/IBD 기각 데모 |
| 분야 2: 도구 기반 분자 최적화 루프 | 🟡 부분 | tool-adapter 랭킹 + hard gate + Pareto + over-opt 제어. 단 "생성"이 아니라 pool 랭킹이고 도구가 reference 휴리스틱 |
| 융합 | ✅ | target `ADVANCE` → molecule eligibility 게이트로 두 평면 연결 |

## Rubric Coverage

| 항목 (배점) | 상태 | 비고 |
|---|---|---|
| 문제정의·도메인 반영 (예선 20) | ✅ | 반증-우선 thesis, 근거 계보 |
| 설계 독창성 (예선 20) | ✅ | 반증 loop·감사·승인. 로컬 LLM은 행동 선택과 해설 작성에만 권한을 갖고 가동 중 |
| 기술 실현가능성 (예선 20) | ✅ | 오픈소스·RDKit 계획 구체 |
| 성능평가 체계 (예선 10) | 🟡 | ablation·seed 42·bootstrap 있으나 평가셋 4·14건으로 작음 |
| 비즈니스/사회 가치 (예선 20) | 🔴 | 시간·비용 절감이 전부 TODO |
| 연구윤리·완성도 (예선 10) | ✅ | guardrail·no-CoT·human approval·audit |
| 과학적 타당성·혁신성 (본선 30) | ✅/🟡 | 설계 강함 / 수치는 fixture 대상 |
| 에이전트 자율성·지능 (본선 10) | ✅/🟡 | 행동 선택 루프 가동 (2026-07-25). 모델이 7개 허용 목록에서 다음 행동을 고르고 하네스가 실행하며, `gemma4:latest` 기준 6/6 단계를 모델이 주도하고 거절된 타깃에 분자 최적화를 스스로 제안해 거부당한다. 실패 시 고정 정책으로 폴백하고 단계별로 `selected_by`를 남긴다. 다중 가설 계획·목표 재설정은 여전히 미구현 |
| 도구 활용·통합 (본선 15) | 🟡 | RDKit 실호출 가동 (descriptor·QED·ECFP4·SA·PAINS). ADMET-AI·RAscore·외부 API는 여전히 미검증 |
| 리소스 효율 (본선 15) | 🔴 | 크레딧/시간 수치 미측정 |
| 시연·완성도 (본선 30) | 🟡 | 콘솔이 하네스 계산 결과를 렌더링 (2026-07-25). 서버를 끄면 계산된 실행이 사라지는 것으로 연동 확인 가능. 판정관이 직접 쓴 근거 패킷을 같은 루프에 넣을 수 있고 규칙별 프리셋 4종이 서로 다른 판정으로 갈린다 — 기각을 우리 픽스처가 아니라 심사자 입력에서 재현 가능. 분자 비교 화면은 아직 픽스처 |

## Current Status and Measured Results (seed 42)

**분야 1 결정 코어** (`artifacts/eval_report.json`, contradiction-aware vs support-only):
- 결정 정확도 0.25 → **1.0**, 모순 재현율 0.0 → **1.0**, 위험한 ADVANCE 3 → **0건**, 스냅샷 폴백 성공 **1.0**, paired bootstrap 평균 Δ **0.75**.
- 케이스 **4개** (illustrative fixture).

**분야 2 분자 랭킹** (`artifacts/molopt_eval_report.json`, METHOD_ONLY, therapeutic_claim=false):
- 선정 정확도 0.43 → **1.0**, top-k 정밀도/재현율 0.2 → **1.0**, 평균 Δ **0.571**, CI [0.357, 0.857].
- 분자 **14개(good 5)**, "생성=제공 pool 랭킹", 도구는 reference 휴리스틱.

정직한 해석: 의도적으로 약한 baseline 대비 데모 fixture 위에서 설계가 작동함을 보이는 수치이며, 실제 세계 효율(크레딧/시간)은 미측정. byte-재현성(seed 42)은 확실한 강점.

## Reviewer-Testable Surface (2026-07-25, D-014)

기각 데모의 약점은 "우리가 고른 2건에서만 기각된다"였다. `POST /api/agent/sandbox`로 판정관이 직접 쓴 근거 패킷을 같은 루프에 넣을 수 있고, 콘솔의 "시나리오 직접 입력" 카드에 프리셋 4종이 붙는다.

| 프리셋 | 판정 | 규칙 |
|---|---|---|
| 양성 근거 | ADVANCE | (없음) |
| 실패 임상 | REJECT | `FAILED_TRIAL_BLOCKS_ADVANCE` |
| 적응증 불일치 | HOLD | `INDICATION_MATCH_REQUIRED` + `REQUIRED_EVIDENCE_MISSING` |
| 맥락 근거만 | HOLD | `REQUIRED_EVIDENCE_MISSING` |

제출 패킷은 저장되지도 승인되지도 않는다. 승인 기록이 없으므로 ADVANCE가 나와도 `molecule_eligible`은 false로 남고, 이것이 미검토 근거를 승인 집합에 넣지 않고도 임의 입력을 받을 수 있는 이유다. "맥락 근거만"은 측정·예측값이 임상 검증이 아니라는 규칙의 첫 데모다.

## Originality

강한 차별점: "매력적이지만 적응증 불일치 타깃을 스스로 기각하고 실패를 결과물로 남기는 **감사 가능한 근거 비평가**"(`01_business-model.md`) — 분자 생성기 하나 더가 아님. 반증-우선 loop, failure-as-output, 같은 근거 그래프로 "왜 이 타깃/왜 이 분자" 설명, 버전 도구·승인 게이트·읽기전용 eval·provenance, 선행연구(PharmAgents·OriGene·AI co-scientist) 명시. 약점: 독창성이 아직 "작동하는 에이전트"가 아니라 아키텍처에 있음.

## LLM (Ollama) Leverage

- **구현 가능**: 낮은 위험. 오케스트레이션·설명 계층에 삽입, 사실은 도구에 유지.
- **올리는 것**: 자율성(10) — 계획·질병 정규화·자기 수정 데모; 시연·완성도(30) — 사고 과정 투명화; 독창성.
- **못 올리는 것**: 과학 정확도 수치(30/15). 도구가 담당. LLM을 판단에 넣으면 hallucination 위험.
- **로컬 모델 천장**: llama3.1 8B/qwen2.5급은 오케스트레이션·요약·설명엔 충분, 도메인 판단엔 약함 → 도구 위 계획·설명 계층으로 한정(아키텍처 규정과 일치).

## Prioritized Gaps and Direction

**P0 — 대회 코어 공백:**
1. ~~Ollama를 오케스트레이션+설명 계층으로 삽입~~ → **완료 (2026-07-25, D-009).** `src/h2l/llm.py` + `GET /api/explain` + 콘솔 "판단 해설". 모델은 사실 권한 없이 설명만 쓰고, 가드레일(숫자·근거 ID·인용·판정 뒤집기·치료 주장·추론 노출)이 위반 출력을 폐기하고 결정론적 템플릿으로 대체. 기본 OFF, 오프라인 유지. 자기 수정 시나리오는 "하네스 다운 → 폴백"과 "미승인 가설 → fail-closed HOLD"로 관측됨.
2. ~~도구 최소 1개 실호출~~ → **완료 (2026-07-25, D-010).** `src/h2l/chem.py`가 descriptor·QED·ECFP4·SA·PAINS/Brenk를 SMILES에서 실제 계산. 구조 기반 풀에서 selection accuracy 0.571 → 1.000, precision 0.40 → 1.00, bootstrap Δ 0.429 CI [0.214, 0.714]. 유사도만 쓰는 baseline이 반응성 액체 3개를 top-5에 올리는 것을 실측으로 보임. **ADMET-AI·RAscore는 여전히 미검증(R-003)이며 정확도 주장 없음.**
3. ~~web_dongseop 단일 콘솔화 + **백엔드 연동**~~ → **완료 (2026-07-25, D-011).** `src/h2l/workspace.py`가 결정 결과를 콘솔 `RunSnapshot`으로 투영하고 읽기 전용 `GET /api/workspace/runs`가 내려준다. 하네스가 살아 있으면 **계산된 실행**이 목록 맨 위에 오고, 끄면 그 실행이 사라지며 고정 픽스처로 폴백한다. TYK2 점수 반전(100 → 0)은 규칙과 근거 ID를 각각 붙인 차감 3건이고, 미승인 스냅샷은 화면에 도달하지 않으며, REJECT는 게이트가 ADVANCE는 사람 승인이 분자 단계를 막는다. 패킷에 없는 값(association·tractability)은 자리표시 숫자 대신 "미수집"으로 표시한다. → 시연 30.

**P0 잔여 없음.** 다음은 P1이다.

**P1 — 정량 근거:**
4. 평가셋 확장(decision 4 → 10~15, molopt pool 확대, ChEMBL holdout 일부). → 성능평가 10.
5. 리소스 효율 측정(cold vs replay 외부 호출 수, wall time, 크레딧). → 효율 15.
6. 비즈니스 가치 정량화(고정 수동 워크플로 1건 reviewer minutes before/after). → 비즈니스 20.

**P2 — 다듬기:**
7. 실제 생성(SELFIES/STONED) 최소 1경로로 pool-ranking → 생성+ranking 승격.
8. 콘솔 정보구조 정리: 범위 밖(임상시험 설계·안전성 시그널) 정리, "적응증 반증 검토"를 1급 항목화.

## Console Decision (2026-07-24)

- 단일 콘솔을 **web_dongseop(React)** 로 정리. 별도 파이썬 R&D 콘솔(`/rnd`, `rnd_console_store.py`, `static/rnd/`)은 제거.
- 파이썬 `/rnd`의 운영 정보구조("AI·자동화 관리": AI 분석 요청·신약개발 Agent 하네스·근거/논문 검색·실험 추천 큐·담당자/권한)를 web_dongseop 사이드바로 이관.
