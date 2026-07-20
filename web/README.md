# H2L-Forge Web Prototype

H2L-Forge 하네스의 실행 상태, 근거 비평, 정책 중단, 출처, 감사 기록을 시각화하는 React 프로토타입입니다.

기본 실행은 TYK2를 기각한 뒤 분자 단계를 실행하지 않습니다. 분자 비교 화면은 연구 결과와 분리된 합성 UI fixture에서만 확인할 수 있습니다.

## 실행

```bash
cd web
npm install
npm run dev -- --host 127.0.0.1 --port 4173
```

브라우저 주소는 `http://127.0.0.1:4173/`입니다.

## 검증

```bash
npm run lint
npm run build
npm run qa
```

`npm run qa`는 로컬 Google Chrome을 사용하며 다음 항목을 자동 검사합니다.

- TYK2 점수 반전과 기각 결정
- 타깃 기각 후 후보물질 0개인 빈 상태
- 합성 fixture 전환과 RDKit 구조 렌더링
- 새 실행의 단계별 상태 변화와 인간 검토 처리
- 모달 Escape 동작과 탭 키보드 이동
- 390px 모바일의 결정 우선 배치와 가로 넘침
- 브라우저 콘솔 오류와 HTTP 오류

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

실제 백엔드가 준비되면 `src/services/harnessClient.ts`의 구현체를 HTTP 또는 SSE 어댑터로 교체합니다. 화면과 `RunSnapshot` 계약은 유지합니다.

최소 API 범위는 다음과 같습니다.

```text
GET    /api/runs
POST   /api/runs
GET    /api/runs/{run_id}
GET    /api/runs/{run_id}/events
POST   /api/runs/{run_id}/cancel
POST   /api/runs/{run_id}/review
```

첫 연동에서는 `events`를 polling으로 구현해도 됩니다. 이후 SSE를 도입하더라도 `HarnessClient.subscribe()` 내부만 변경하면 됩니다.

## 중요한 데이터 계약

각 단계에는 최소한 다음 값이 필요합니다.

- 안정적인 `stage.id`와 실행 순서 `ordinal`
- `status`, `startedAt`, `endedAt`, `durationMs`
- `inputArtifactIds`, `outputArtifactIds`
- `toolCall.name`, `version`, `classification`, `observedAt`
- `retryCount`, `error`, 결과 요약

각 근거에는 `sourceId`, `observedAt`, `polarity`, `classification`, 원문 링크가 필요합니다. 화면에 표시되는 집계 수치는 모두 `RunSnapshot` 배열에서 계산하며 별도 숫자로 입력하지 않습니다.

## 현재 한계

- 외부 API와 Python 하네스는 아직 연결되지 않았습니다.
- 자유 질병 입력은 정규화 API가 없으므로 비활성 상태입니다.
- 출처 스냅샷은 현재 시점의 실시간 조회 결과가 아닙니다.
- 인간 검토는 프로토타입의 상태 변경만 재현하며 인증과 전자서명은 없습니다.
- RDKit WASM 파일은 약 6.9MB이므로 실제 배포에서는 분자 화면 진입 시 지연 로딩과 캐시 정책을 확인해야 합니다.
