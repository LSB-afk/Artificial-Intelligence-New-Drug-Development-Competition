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
| 설계 독창성 (예선 20) | ✅ | 반증 loop·감사·승인. 단 LLM 미가동 |
| 기술 실현가능성 (예선 20) | ✅ | 오픈소스·RDKit 계획 구체 |
| 성능평가 체계 (예선 10) | 🟡 | ablation·seed 42·bootstrap 있으나 평가셋 4·14건으로 작음 |
| 비즈니스/사회 가치 (예선 20) | 🔴 | 시간·비용 절감이 전부 TODO |
| 연구윤리·완성도 (예선 10) | ✅ | guardrail·no-CoT·human approval·audit |
| 과학적 타당성·혁신성 (본선 30) | ✅/🟡 | 설계 강함 / 수치는 fixture 대상 |
| 에이전트 자율성·지능 (본선 10) | 🔴 | 자기 인지·수정 LLM 루프 부재 |
| 도구 활용·통합 (본선 15) | 🔴 | RDKit/외부 API가 실호출 아닌 fixture·휴리스틱 |
| 리소스 효율 (본선 15) | 🔴 | 크레딧/시간 수치 미측정 |
| 시연·완성도 (본선 30) | 🟡 | 콘솔 작동. web_dongseop 단일 콘솔로 정리 중, 백엔드 미연동 |

## Current Status and Measured Results (seed 42)

**분야 1 결정 코어** (`artifacts/eval_report.json`, contradiction-aware vs support-only):
- 결정 정확도 0.25 → **1.0**, 모순 재현율 0.0 → **1.0**, 위험한 ADVANCE 3 → **0건**, 스냅샷 폴백 성공 **1.0**, paired bootstrap 평균 Δ **0.75**.
- 케이스 **4개** (illustrative fixture).

**분야 2 분자 랭킹** (`artifacts/molopt_eval_report.json`, METHOD_ONLY, therapeutic_claim=false):
- 선정 정확도 0.43 → **1.0**, top-k 정밀도/재현율 0.2 → **1.0**, 평균 Δ **0.571**, CI [0.357, 0.857].
- 분자 **14개(good 5)**, "생성=제공 pool 랭킹", 도구는 reference 휴리스틱.

정직한 해석: 의도적으로 약한 baseline 대비 데모 fixture 위에서 설계가 작동함을 보이는 수치이며, 실제 세계 효율(크레딧/시간)은 미측정. byte-재현성(seed 42)은 확실한 강점.

## Originality

강한 차별점: "매력적이지만 적응증 불일치 타깃을 스스로 기각하고 실패를 결과물로 남기는 **감사 가능한 근거 비평가**"(`01_business-model.md`) — 분자 생성기 하나 더가 아님. 반증-우선 loop, failure-as-output, 같은 근거 그래프로 "왜 이 타깃/왜 이 분자" 설명, 버전 도구·승인 게이트·읽기전용 eval·provenance, 선행연구(PharmAgents·OriGene·AI co-scientist) 명시. 약점: 독창성이 아직 "작동하는 에이전트"가 아니라 아키텍처에 있음.

## LLM (Ollama) Leverage

- **구현 가능**: 낮은 위험. 오케스트레이션·설명 계층에 삽입, 사실은 도구에 유지.
- **올리는 것**: 자율성(10) — 계획·질병 정규화·자기 수정 데모; 시연·완성도(30) — 사고 과정 투명화; 독창성.
- **못 올리는 것**: 과학 정확도 수치(30/15). 도구가 담당. LLM을 판단에 넣으면 hallucination 위험.
- **로컬 모델 천장**: llama3.1 8B/qwen2.5급은 오케스트레이션·요약·설명엔 충분, 도메인 판단엔 약함 → 도구 위 계획·설명 계층으로 한정(아키텍처 규정과 일치).

## Prioritized Gaps and Direction

**P0 — 대회 코어 공백 (지금):**
1. Ollama를 오케스트레이션+설명 계층으로 삽입. 자기 수정 시나리오 1개(잘못된 입력 → 인지 → 폴백/재시도)를 데모 하이라이트로. → 자율성 10 + 시연 30 + 독창성.
2. 도구 최소 1개 실호출: `similarity_proxy`/`druglikeness`를 실제 RDKit(Morgan·QED)로 교체, ADMET-AI smoke test 또는 명시적 limited fallback. → 도구활용 15.
3. web_dongseop 단일 콘솔화 + 백엔드 연동: README의 최소 API(`/api/runs…`)로 mockHarness를 HTTP 어댑터로 교체. → 시연 30.

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
