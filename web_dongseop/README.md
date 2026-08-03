# H2L-Forge Web Prototype

H2L-Forge 하네스의 실행 상태, 근거 비평, 정책 중단, 출처, 감사 기록을 시각화하는 React 프로토타입입니다.

다른 프론트엔드 작업과 경로가 겹치지 않도록 동섭의 프로토타입은 `web_dongseop/`에 독립적으로 보관합니다.
화면 구성과 시각 원칙은 [DESIGN.md](DESIGN.md)에 기록합니다.

기본 실행은 TYK2를 기각한 뒤 분자 단계를 실행하지 않습니다. 분자 비교 화면은 연구 결과와 분리된 합성 UI fixture에서만 확인할 수 있습니다.

## 실행

저장소 루트에서 Python 하네스를 먼저 실행합니다. 로컬 모델 없이도 고정 정책으로
동일한 Agent 행동을 재현하도록 아래 명령은 LLM을 끕니다.

```bash
PYTHONPATH=src H2L_LLM_ENABLED=0 python3 -m h2l.server --host 127.0.0.1 --port 8765
```

다른 터미널에서 웹을 실행합니다.

```bash
cd web_dongseop
npm ci
npm run dev -- --host 127.0.0.1 --port 4173
```

브라우저 주소는 `http://127.0.0.1:4173/`입니다. Python 하네스가 꺼져 있으면
웹은 고정 픽스처만 표시하고, 켜져 있으면 실제 Agent 실행 시나리오가 추가됩니다.

로컬 규칙이 너무 빨리 끝나 단계가 보이지 않는 문제를 막기 위해 서버는 기본적으로
이벤트를 550ms 간격으로 공개합니다. 이 값은 실제 계산 시간이 아니라 화면 관찰용
간격이며 `H2L_LIVE_STEP_INTERVAL_MS`로 바꿀 수 있습니다.

## 검증

```bash
npm run lint
npm run build
npm run qa         # 하네스를 끄고 (:8765 정지 상태)
npm run qa:online  # 하네스는 게이트가 직접 켜고 끔
```

두 게이트는 서로 다른 코드 경로를 지납니다. `qa`는 `/api/*`가 전부 실패하는
경로만 밟으므로, 콘솔이 하네스에 **연결됐을 때**의 코드는 `qa:online`이 아니면
한 줄도 실행되지 않습니다. 둘 다 로컬 Google Chrome을 씁니다.

`npm run qa` — 하네스 오프라인 폴백:

- TYK2 점수 반전과 기각 결정
- 타깃 기각 후 후보물질 0개인 빈 상태
- 합성 fixture 전환과 RDKit 구조 렌더링
- 새 실행의 단계별 상태 변화와 인간 검토 처리
- 모달 Escape 동작과 탭 키보드 이동
- 390px 모바일의 결정 우선 배치와 가로 넘침
- 브라우저 콘솔 오류와 HTTP 오류

`npm run qa:online` — 하네스 연결 경로. 시작 전에 `:8765`가 비어 있어야 합니다
(게이트가 직접 띄웠다 내리며, 그 순서 자체가 검사 항목이기 때문입니다):

- 연결 표기와 계산 2건 + 픽스처 2건 병합
- 모달 시나리오가 `/api/scenarios`가 내려준 프리셋과 일치
- 프리셋 실행에서 실제 Agent 단계가 순서대로 관찰되고, 기각 실행은 분자 단계를 열지 않음
- 화면의 실행 취소가 Python 작업에 전달되고 단계가 `cancelled`로 바뀜
- 내려받은 판단 보고서(`LIVE-SANDBOX-…-report.txt`)에 `Provenance: SANDBOX`가 실림
- 임시 실행은 목록에서 재연결되지만 과학 레지스트리는 그대로 유지됨
- 서버 재시작 뒤 임시 실행과 브라우저 캐시가 함께 정리됨
- 연결 경로에서도 사이드바·기본 버튼 색과 글자 크기가 유지됨
- 하네스를 껐다 켜면 새로고침 없이 연결 상태가 다시 측정됨

## 두 가지 시나리오

### 1. IBD 근거 검토

- 데이터 분류: `source_snapshot`과 `computed`
- 핵심 결정: TYK2 기각
- 분자 단계: seed, 생성, 활성 대리평가, ADMET, 합성 가능성 모두 `skipped`
- 후보물질: 0개
- 결과: 출처와 점수 산정 내역이 연결된 판단 보고서

### 2. 분자 비교 UI 점검

- 데이터 분류: `synthetic`
- 목적: 표, 검색, 위험 라벨, 상세 패널, RDKit 렌더링 확인
- 모든 분자 판단: `demo_only`
- 합성 평가: SA proxy만 표시하며 AiZynthFinder 경로 탐색은 실행하지 않음
- 연구 결과 또는 최종 후보로 사용 불가

## 폴더 구조

```text
src/
  domain/
    contracts.ts          하네스와 웹이 공유할 데이터 계약
    validateSnapshot.ts   fixture 및 응답 일관성 검사
  services/
    harnessClient.ts      UI가 참조하는 단일 연결 지점
    httpHarness.ts        Python API 요청, polling, 취소, 캐시 정리
    mockHarness.ts        현재 프로토타입용 인메모리 어댑터
  state/
    useHarnessWorkspace.ts 실행 목록, 선택, 구독 상태
  data/
    demoScenarios.ts      출처 스냅샷 시나리오와 합성 UI fixture
  components/
    MoleculeStructure.tsx RDKit WebAssembly 구조 렌더러
    StatusBadge.tsx       실행, 단계, 판단, 데이터 분류 상태
  views/                  개요, 타깃, 분자, 중단, 감사, 보고서
```

화면 컴포넌트는 `demoScenarios.ts`를 직접 읽지 않습니다. 데이터 흐름은 아래 한 방향으로 고정되어 있습니다.

```text
HarnessClient -> RunSnapshot -> useHarnessWorkspace -> View
```

## 실제 하네스 연동

현재 `HttpHarnessClient`가 아래 API에 연결되어 있습니다.

```text
GET    /api/workspace/runs
POST   /api/workspace/runs
GET    /api/workspace/runs/{run_id}
POST   /api/workspace/runs/{run_id}/cancel
```

`POST`는 최종 결과가 아니라 HTTP 202와 `queued` 스냅샷을 반환합니다. 웹은
`HarnessClient.subscribe()` 안에서 200ms polling을 수행하고, 종료 상태가 오면
구독을 닫습니다. 이후 SSE를 도입하더라도 이 메서드 내부만 바꾸면 됩니다.

## 중요한 데이터 계약

각 단계에는 최소한 다음 값이 필요합니다.

- 안정적인 `stage.id`와 실행 순서 `ordinal`
- `status`, `startedAt`, `endedAt`, `durationMs`
- `inputArtifactIds`, `outputArtifactIds`
- `toolCall.name`, `version`, `classification`, `observedAt`
- `retryCount`, `error`, 결과 요약

각 근거에는 `sourceId`, `observedAt`, `polarity`, `classification`, 원문 링크가 필요합니다. 화면에 표시되는 집계 수치는 모두 `RunSnapshot` 배열에서 계산하며 별도 숫자로 입력하지 않습니다.

## 현재 한계

- 실행 입력은 서버가 제공하는 시드 프리셋이며 자유 입력이나 외부 논문 API 조회는 아직 없습니다.
- 진행 상태는 Python 프로세스 메모리에만 있어 서버를 재시작하면 사라집니다.
- 단계 공개 간격은 시각 확인용 pacing이며 실제 도구 처리 성능 측정값이 아닙니다.
- polling 방식이라 서버 이벤트를 즉시 push하는 SSE보다 요청 수가 많습니다.
- 자유 질병 입력은 정규화 API가 없으므로 비활성 상태입니다.
- 출처 스냅샷은 현재 시점의 실시간 조회 결과가 아닙니다.
- 인간 검토는 프로토타입의 상태 변경만 재현하며 인증과 전자서명은 없습니다.
- RDKit WASM 파일은 약 6.9MB이므로 실제 배포에서는 분자 화면 진입 시 지연 로딩과 캐시 정책을 확인해야 합니다.
