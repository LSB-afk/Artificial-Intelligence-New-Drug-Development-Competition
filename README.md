# 제4회 AI 신약개발 경진대회 워크스페이스

이 저장소는 제4회 인공지능(AI) 신약개발 경진대회 예선 제안서와 본선 구현을 준비하기 위한 작업 공간이다.

현재 방향은 **분야 1: 자율형 가설 생성 및 검증**과 **분야 2: 도구 활용 기반의 분자 최적화 루프**를 융합한 `Hypothesis-to-Lead Agent`다. 핵심 차별점은 일반적인 폐루프 자체가 아니라, 적응증별 임상 근거를 먼저 반증하고 `ADVANCE/HOLD/REJECT`를 결정하며 실패 사유를 1급 산출물로 남기는 evidence-critical agent harness다.

## 핵심 산출물

- [대회 분석](docs/01_competition_analysis.md): 공식 홈페이지, KHIDI 공고, 제출 게시판, 제안서 양식 기준 분석
- [분야 1+2 융합 설계](docs/02_field1_field2_fusion_design.md): 에이전트 프로세스, 데이터/도구, 평가 체계, 안전 설계
- [제안서 작성 골격](docs/03_proposal_outline.md): 10쪽 이내 HWPX 제안서에 바로 옮길 목차와 메시지
- [근거 소스](docs/04_sources.md): 공식 대회/기술/논문/도구 출처
- [실행 계획](docs/05_work_plan.md): 예선 제출 전 작업과 본선 4주 구현 계획
- [최신 냉정 평가](05_리서치/2026-07-16_H2L-Forge_냉정평가_및_개선안.md): TYK2/IBD 전제, 선행연구, 도구 실현성을 바로잡은 현재 기준
- [점수 개선 리서치](docs/06_score_improvement_research.md): 2026-07-06 역사 자료이며 최신 평가와 충돌하는 부분은 superseded
- [Agent loop architecture](docs/07_agent_loop_architecture.md): 기존 capability/log/retry 초안
- [Molecular optimization loop](docs/08_molecular_optimization_loop.md): target `ADVANCE` 또는 `METHOD_ONLY`에서만 사용하는 분자 평가 초안
- [Eval rubric](evals/rubric.md): 본선 MVP와 제안서 품질을 반복 평가하기 위한 pass/warn/fail 기준
- [Harness contract](harness.yaml): canonical artifacts, quality gates, risks, decisions, open questions
- [Canonical architecture](docs/07_architecture.md): 6-role runtime, deterministic state/approval engine, snapshot-first dataflow
- [Demo flow and eval plan](docs/09_flow.md): TYK2 rejection demo, API fallback, five-minute replay, measurable thresholds

## 저장소 구조

```text
.
├── data/
│   ├── raw/          # 원천 데이터, API 응답, 다운로드 자료
│   └── processed/    # 정제된 타깃/활성/분자 테이블
├── docs/             # 대회 분석, 설계, 제안서 문서
├── experiments/      # 실험 로그와 결과 요약
├── notebooks/        # 탐색/분석 노트북
├── prompts/          # 에이전트 역할 프롬프트
├── reports/          # 제안서/본선 보고서 산출물
├── static/           # 하데스 콘솔 정적 셸(index.html, app.js, styles.css)
├── src/h2l/          # 의사결정 코어와 관리 콘솔 서버/스토어
│   ├── console_store.py  # 하데스 콘솔 JSON 관리 상태 저장소
│   ├── server.py         # stdlib HTTP 서버와 /api/* 라우팅
│   └── ...
└── tests/            # 평가/회귀 테스트
```

## 실행 방법

JB(`Search-for-AI-based-internal-regulations`)의 운영 불변조건을 이식한 결정론적 오프라인 코어다. 외부 API·RDKit 없이 동작한다.
`pyproject.toml` 기준 Python `>=3.10` 환경에서 실행한다.

```bash
# 전체 테스트 (현재 수집 105 케이스)
python3 -m pytest

# TYK2/IBD 고정 사례 한 건 실행 -> REJECT, molecule_eligible=false
PYTHONPATH=src python3 -m h2l.cli run --evidence tests/fixtures/tyk2_ibd/normalized_evidence.json

# 근거-지지 전용 baseline vs 반증 인지 candidate ablation 평가 (seed 42, 재현 가능)
PYTHONPATH=src python3 -m h2l.cli eval --cases evals/decision_cases.json --out artifacts/eval_report.json

# 하데스 콘솔 (기본 상태: artifacts/hades-console.json)
PYTHONPATH=src python3 -m h2l.server --host 127.0.0.1 --port 8765
```

`python3 -m pytest`는 현재 105개 테스트를 수집한다. 이 중 4개 real-socket HTTP 테스트는 실행 환경이 `127.0.0.1` 바인드를 허용해야 통과한다.

코어가 보장하는 4가지 이식 불변조건:

1. 승인되지 않은 새 근거 스냅샷은 현재 판단을 바꾸지 않는다(`registry`).
2. 타깃 판단과 분자 단계 사이에 결정론적 상태 전이와 사람 승인을 둔다(`state_machine`).
3. 도구가 실패해도 고정 스냅샷으로 동일한 판단을 재생한다(`replay`, snapshot-first fallback).
4. 평가 plane은 과학 상태를 변경하지 못하며, 같은 seed로 두 번 실행하면 byte-equivalent하다(`eval_runner`).

## 하데스 콘솔

Hades Console은 프로젝트 운영을 위한 dependency-free 관리 콘솔이다. Python 표준 라이브러리 HTTP 서버와 정적 HTML/CSS/JavaScript만 사용하며, 과학 의사결정 코어와 같은 프로세스에서 실행되지만 mutable state는 `src/h2l/console_store.py`의 별도 JSON 저장소에 둔다.

기본 상태 파일은 `artifacts/hades-console.json`이다. 다른 위치를 쓰려면 실행 전에 `H2L_CONSOLE_STATE_PATH`를 지정한다.

```bash
H2L_CONSOLE_STATE_PATH=/tmp/hades-console.json \
PYTHONPATH=src python3 -m h2l.server --host 127.0.0.1 --port 8765
```

콘솔은 8개 뷰를 제공한다.

- Dashboard: 운영 요약, 주의 큐, 최근 실행, 활동
- Projects: 프로젝트 목표, 상태, 리드 에이전트
- Tasks: 작업 큐, 우선순위, 담당자, 체크아웃/릴리스
- Agents: 역할, 상태, heartbeat, 월 예산 사용률, pause/resume
- Runs: 실행 상태, 로그 요약, 비용, 실패 실행 retry
- Costs: 총 사용량, agent/project별 비용, 비용 이벤트
- Approvals: 운영 승인 요청의 approve/reject/request-revision
- Activity: append-only 활동 타임라인

관리 API는 `/api/console`, `/api/projects`, `/api/tasks`, `/api/agents`, `/api/runs`, `/api/costs`, `/api/approvals`, `/api/activity`를 제공한다. 생성/수정/체크아웃/릴리스/일시정지/재개/retry/승인 결정은 입력을 검증하고, 불법 상태 전이는 구조화된 JSON 오류와 409 conflict로 거부하며, 성공한 mutation마다 활동 이벤트를 추가한다. 승인은 `pending` 상태에서만 결정할 수 있고 결정 후 terminal 상태가 된다.

초기 콘솔 데이터는 `source: "demo"`로 표시되는 저장소 운영 데모 데이터다. 프로젝트, 태스크, 에이전트, 실행, 비용, 승인 예시는 콘솔 동작 확인용이며 생물학적 근거, 약효, 분자 설계, 합성 가능성을 주장하지 않는다.

안전 경계: Hades Console은 소프트웨어 운영 관리 plane이다. 콘솔 action은 evidence snapshot, target decision, molecule eligibility, replay/eval 결과를 변경하지 못한다. 신약개발 판단, 임상 판단, 분자 최적화, 합성 경로, 실험 프로토콜 생성은 콘솔 권한 밖이다.

문서/통합 검증에 사용한 명령:

```bash
rg -n "Hades|하데스|console_store|hades-console" README.md harness.yaml docs/superpowers
python -m py_compile src/h2l/server.py src/h2l/console_store.py
python -m pytest tests/test_console_store.py tests/test_server.py -q -k "not real"
python -m pytest --collect-only -q
git diff --check
```

## 제안 시스템 한 줄

`H2L-Forge`는 질병-타깃 근거를 스스로 반증해 잘못된 가설을 먼저 멈추고, 통과한 타깃에만 분자 도구를 연결하는 감사 가능한 신약개발 의사결정 에이전트다.

## 현재 상태

- 공식 대회 요건 분석 완료
- 분야 1+2 융합 프로세스 초안 완료
- 대표 negative demo: inflammatory bowel disease / TYK2 / deucravacitinib의 적응증 불일치와 IBD 임상 실패를 에이전트가 탐지해 `REJECT/HOLD`
- positive molecule demo target: 미정이며 동일한 임상 근거 gate 통과 전까지 molecule eligibility 차단
- AI agent harness의 CPS, 상태모델, PRD, 아키텍처, flow, eval, risk rule 초안 생성
- JB 이식 코어 구현 완료: `src/h2l`(registry/state_machine/replay/eval_runner/cli), 결정론적 오프라인 평가 재현 확인
- Hades Console 통합 완료: `server.py`, `console_store.py`, `static/` 관리 UI, JSON 단일 프로세스 persistence, 승인/활동 audit
- 다음 작업: positive target evidence qualification, live Open Targets/ChEMBL/ClinicalTrials.gov adapter + snapshot fallback, `MOLECULE_ELIGIBLE` 이후 RDKit/ADMET 분자 검증
