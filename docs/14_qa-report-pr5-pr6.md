# PR #5 및 PR #6 통합 QA 보고서

## 1. 보고서 정보

| 항목 | 내용 |
|---|---|
| QA 수행일 | 2026-08-02 |
| 저장소 | [LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition) |
| PR #5 | [feat(agent): let the model select actions the harness executes](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition/pull/5) |
| PR #5 검사 커밋 | [`22ab25ea6bd585e891fa3f997c79e6cd6dcc803c`](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition/commit/22ab25ea6bd585e891fa3f997c79e6cd6dcc803c) |
| PR #6 | [feat(console): run the harness's rule scenarios from the console](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition/pull/6) |
| PR #6 검사 커밋 | [`032f4d5d02f5fdb6288b727cc3ed583ddfdb687f`](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition/commit/032f4d5d02f5fdb6288b727cc3ed583ddfdb687f) |
| 검사 범위 | 하네스 실행, 오류 처리, 프런트엔드 연동, 화면-응답 일치, 과학적 근거와 출처 |
| 최종 판정 | **HOLD: 핵심 규칙은 동작하지만 통합 데모 완료 상태로 보기는 어려움** |

이 보고서는 제품 코드를 수정한 결과가 아니다. 위 두 커밋을 그대로 실행하고 관찰한 결과와 코드 검토 결과를 정리한 문서다.

## 2. PR 구조와 검사 기준

PR #5와 PR #6은 서로 독립된 대안이 아니다.

- PR #5는 모델이 허용된 행동을 고르고 하네스가 실행하는 에이전트 루프를 추가한다.
- PR #6은 PR #5 브랜치를 base로 사용하는 stacked PR이며, 콘솔에서 규칙 시나리오를 실행하는 연결을 추가한다.
- 따라서 병합 순서는 **PR #5를 먼저 `main`에 병합한 뒤 PR #6의 base를 `main`으로 변경하는 순서**여야 한다.
- PR #6을 현재 상태로 `main`에 단독 병합하면 PR #5 의존 코드 때문에 정상적인 독립 변경으로 볼 수 없다.

QA에서는 다음 질문을 분리해서 검사했다.

1. 판정 규칙과 안전 게이트가 올바르게 동작하는가?
2. 모델 장애가 하네스 전체 장애로 번지지 않는가?
3. 잘못된 입력이 안정적인 오류 응답으로 처리되는가?
4. 웹의 실행 화면이 실제 백엔드 동작을 정직하게 보여주는가?
5. 실행, 취소, 검토 결과가 서버에 저장되는가?
6. 화면에 표시하는 과학적 결론에 추적 가능한 실제 출처가 있는가?

## 3. 전체 판정 요약

| 검사 영역 | 판정 | 근거 |
|---|---|---|
| 결정 규칙과 분자 게이트 | PASS | `REJECT/HOLD`에서 분자 최적화를 거부하며, 위조된 `ADVANCE`도 실제 게이트를 우회하지 못함 |
| PR #5 에이전트 행동 선택 | PASS | 허용 목록 기반 행동 선택, 잘못된 모델 출력 검증, 결정론적 정책 폴백 동작 확인 |
| 모델 장애 폴백 | PASS | 모델 미연결, 잘못된 JSON, 존재하지 않는 행동과 가설 ID에서 정책 폴백 확인 |
| 기본 테스트와 빌드 | PASS | Python 테스트, TypeScript lint/build, 브라우저 QA 통과 |
| 웹과 백엔드의 기본 연결 | PASS | 시나리오 목록 조회와 `POST /api/workspace/runs` 응답 렌더링 확인 |
| 잘못된 입력의 안정적 처리 | FAIL | 중첩 필드 타입 오류가 요청 처리 스레드 예외와 연결 종료를 유발함 |
| 실제 실행 진행 상황 표시 | FAIL | 주요 실행 API가 최종 결과를 한 번에 반환하며 중간 단계 스트리밍이나 폴링이 없음 |
| 화면과 백엔드 결과 일치 | FAIL | 보고서 화면이 실제 타깃과 판정을 사용하지 않고 TYK2/IBD/REJECTED를 고정 표시함 |
| 실행 저장, 재조회, 취소 | FAIL | 새 실행은 서버에 저장되지 않아 재조회와 취소가 불가능함 |
| 사람 검토 결과 저장 | FAIL | 검토 완료가 현재 브라우저 메모리에만 남고 재연결 시 사라짐 |
| 과학적 출처 추적성 | HOLD | 실제 임상 3건 대신 2개 fixture 레코드를 사용하며 NCT ID와 원문 스냅샷이 없음 |
| 최종 시연 준비도 | HOLD | 규칙 데모는 가능하지만 실제 에이전트 진행, 영속성, 출처 증빙이 아직 분리되어 있음 |

## 4. 통과한 항목

### 4.1 PR #5 에이전트 루프

- 모델을 끈 상태에서 6개 정책 행동이 결정론적으로 실행됐다.
- 동일한 입력을 두 번 실행했을 때 정규화된 결과가 동일했다.
- 유효한 가짜 모델 응답으로 6개 행동을 모두 선택하게 해도 최종 안전 게이트는 유지됐다.
- 존재하지 않는 행동, 존재하지 않는 가설 ID, JSON이 아닌 응답, 같은 행동 반복은 명시적인 정책 폴백으로 전환됐다.
- 모델이 `ADVANCE`를 위조하거나 프롬프트 우회 문구를 입력해도 실제 판정과 분자 게이트는 바뀌지 않았다.
- 연결할 수 없는 모델과 느린 가짜 모델에서도 제한된 시간 안에 폴백했다.
- sandbox 실행 전후 레지스트리 내용이 바뀌지 않았다.

### 4.2 결정 규칙과 게이트

- 적응증 안에서 실패 또는 부정 임상 근거가 발견되면 `REJECT`가 반환됐다.
- 다른 적응증의 긍정 근거는 현재 적응증의 지지 근거로 전이되지 않았다.
- 지지 근거가 없고 명시적 반증도 없으면 `HOLD`가 반환됐다.
- 미승인 sandbox에서 `ADVANCE`가 계산돼도 분자 최적화는 사람 승인 없이 실행되지 않았다.

### 4.3 자동 검사 결과

| 대상 | 검사 결과 |
|---|---|
| PR #5 Python, 로컬 RDKit 미설치 환경 | 232 passed, 선택적 RDKit 검사 1 skipped |
| PR #5 프런트엔드 | `npm ci`, lint, build 통과 |
| PR #5 브라우저 QA | 17개 검사 통과 |
| PR #6 Python, 로컬 RDKit 미설치 환경 | 237 passed |
| PR #6 GitHub Actions | RDKit 포함 259 passed, 2개 job 성공 |
| PR #6 프런트엔드 | lint와 build 통과 |
| PR #6 오프라인 브라우저 QA | 17개 검사 통과 |
| PR #6 온라인 브라우저 QA | 7개 검사 통과 |

PR #6의 GitHub Actions 결과는 [workflow run 30607457499](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition/actions/runs/30607457499)에서 확인했다. 로컬과 CI의 Python 테스트 수 차이는 로컬 환경에 RDKit이 없기 때문이다.

## 5. 발견한 문제

### 5.1 높음: 잘못된 중첩 입력이 안정적인 4xx 응답이 아니라 연결 종료를 유발함

`validate_packet`은 레코드 객체에서 사실상 `evidence_id`만 검사한다. `kind`, `indication_id`, `indication`, `outcome`, `stance`, `source_ref` 등의 타입과 값 범위는 검증하지 않는다. 관련 코드는 [PR #5 `src/h2l/scenarios.py`](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition/blob/22ab25ea6bd585e891fa3f997c79e6cd6dcc803c/src/h2l/scenarios.py#L158-L197)에서 확인할 수 있다.

관찰된 결과는 다음과 같다.

- `record.indication_id`에 배열을 넣으면 집합 포함 검사에서 `TypeError`가 발생한다.
- `record.outcome`에 배열을 넣으면 에이전트의 누락 근거 계산에서 `TypeError`가 발생한다.
- 클라이언트는 JSON 오류 응답 대신 연결이 끊긴 것으로 인식했다.
- 요청 처리 스레드는 실패했지만 `/api/health`는 계속 200을 반환해 서버 전체가 죽은 것은 아니었다.
- `kind`, `indication`, `stance`에 배열을 넣은 일부 비정상 입력은 200으로 수락됐다.
- `observed_at`이 `not-a-date`여도 문자열이라는 이유로 수락됐다.
- 같은 `evidence_id`를 중복해서 보내도 수락됐다.

예외가 발생하는 직접 경로는 [임상 비평의 적응증 포함 검사](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition/blob/032f4d5d02f5fdb6288b727cc3ed583ddfdb687f/src/h2l/replay.py#L116-L142)와 [에이전트 누락 근거 계산](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition/blob/032f4d5d02f5fdb6288b727cc3ed583ddfdb687f/src/h2l/agent.py#L200-L219)이다.

필요한 수정:

- 요청 스키마를 필드별 타입과 enum까지 검증한다.
- ISO 8601 날짜 형식, 중복 evidence ID, 레코드별 필수 필드를 검사한다.
- API 최상단에 예상하지 못한 예외를 구조화된 500 응답으로 바꾸는 안전망을 둔다.
- 비정상 입력 회귀 테스트를 추가한다.

### 5.2 높음: 큰 요청의 처리 결과가 일관되지 않음

- 약 900,444바이트 요청이 수락됐고 약 1,806,027바이트 응답이 생성됐다.
- 1MiB를 넘는 요청을 반복했을 때 어떤 실행은 413을 반환했지만 다른 실행은 연결 reset 또는 broken pipe로 끝났다.
- 따라서 크기 제한 자체가 있더라도 클라이언트가 항상 동일한 오류 계약을 받을 수 없다.

필요한 수정:

- body를 읽기 전에 `Content-Length`를 기준으로 일관되게 413을 반환한다.
- 제한을 넘은 본문을 안전하게 폐기하거나 연결을 명시적으로 닫는다.
- 경계값 바로 아래, 정확한 경계값, 경계값 초과 입력을 반복 검사한다.

### 5.3 높음: 메인 화면의 새 실행은 PR #5 에이전트 루프를 실행하지 않음

메인 화면의 `새 실행`은 `POST /api/workspace/runs`를 호출한다. 이 API는 preset을 가져와 `sandbox_tools(packet).decision()`으로 최종 판정만 계산한 뒤 `RunSnapshot`으로 바꾼다. `run_agent()`를 호출하지 않는다. 관련 구현은 [PR #6 `src/h2l/server.py`](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition/blob/032f4d5d02f5fdb6288b727cc3ed583ddfdb687f/src/h2l/server.py#L195-L236)에서 확인할 수 있다.

반면 별도의 Agent Harness 화면은 `/api/agent/run`을 통해 실제 `run_agent()`를 호출한다. 그러나 이 요청도 동기식이며 실행이 끝난 뒤 전체 trace를 한 번에 반환한다.

결론:

- 메인 새 실행: 규칙 시나리오 최종 판정 데모
- Agent Harness 화면: 실제 PR #5 행동 선택 루프
- 두 기능은 현재 하나의 실행 흐름으로 연결돼 있지 않다.

따라서 메인 화면에서 단계가 순서대로 실행되는 것처럼 보이면 실제 백엔드 동작보다 강한 인상을 줄 수 있다.

필요한 수정:

- 메인 실행 생성 API가 실제 에이전트 작업을 생성하도록 통합한다.
- 또는 현 단계에서는 버튼과 화면 문구를 `규칙 시나리오 재생`으로 정확히 표시한다.
- 진행률이 필요하면 서버 실행 ID와 단계 이벤트를 제공하고 SSE, WebSocket 또는 폴링으로 갱신한다.

### 5.4 높음: 실제 실행 진행 상황을 화면에서 관찰할 수 없음

- `POST /api/workspace/runs`는 로컬 검사에서 약 1ms 안에 최종 결과를 반환했다.
- Agent Harness 화면도 요청 완료 뒤 전체 trace를 한 번에 렌더링한다.
- 로딩 중 단계 카드, 진행 막대, 단계별 상태 변화, 접근성 live region은 관찰되지 않았다.
- Agent Harness의 일반 실행 버튼과 sandbox 실행 버튼은 하나의 `pending` 상태를 공유해 둘 다 `실행 중`으로 바뀐다.
- 프런트엔드 코드도 계산된 실행에 대해 `subscribe()`가 아무 작업도 하지 않는다고 명시한다. 자세한 내용은 [`httpHarness.ts`](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition/blob/032f4d5d02f5fdb6288b727cc3ed583ddfdb687f/web_dongseop/src/services/httpHarness.ts#L140-L178)에서 확인할 수 있다.

필요한 수정:

- 백엔드가 `queued`, `running`, `completed`, `failed`, `cancelled` 상태를 가진 실행을 저장한다.
- 각 단계 시작과 완료 이벤트를 서버에서 전송한다.
- 화면은 서버 이벤트를 그대로 시각화하고 임의 타이머를 실제 진행으로 표현하지 않는다.
- 두 실행 버튼의 pending 상태를 분리한다.

### 5.5 높음: 판단 보고서의 핵심 결론이 실제 응답과 다름

긍정 preset의 실제 백엔드 응답과 다운로드 TXT는 다음 상태였다.

- 타깃: `DEMO:SUPPORT`
- 판정: `ADVANCE`
- 상태: `AWAITING_APPROVAL`

하지만 화면의 판단 보고서는 모든 비-fixture 완료 실행에 대해 다음 문구를 고정 표시했다.

- 타깃: TYK2
- 적응증: IBD
- 판정: REJECTED

고정된 부분은 [PR #6 `ReportView.tsx` 87-90행](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition/blob/032f4d5d02f5fdb6288b727cc3ed583ddfdb687f/web_dongseop/src/views/ReportView.tsx#L87-L90)이다.

이는 단순한 표현 문제가 아니라 사용자가 서로 반대인 과학적 결론을 보게 만드는 데이터 무결성 문제다.

필요한 수정:

- 보고서 제목, 타깃, 적응증, 판정, 설명을 모두 현재 `RunSnapshot` 값으로 렌더링한다.
- 화면 값과 다운로드 보고서 값의 일치 여부를 온라인 E2E 검사에 추가한다.
- `ADVANCE`, `HOLD`, `REJECT` 각각의 시나리오를 검사한다.

### 5.6 높음: 생성한 실행을 서버에서 재조회하거나 취소할 수 없음

- `POST /api/workspace/runs`가 반환한 실행 ID를 `GET /api/workspace/runs/{id}`로 조회하면 404가 반환됐다.
- 같은 경로에 취소 요청을 보내면 405가 반환됐다.
- 실행 전후 서버 실행 목록은 바뀌지 않았다.
- 같은 preset을 다시 실행하면 content hash 기반의 같은 ID가 생성돼 목록에 새 이력이 쌓이지 않았다.

이 동작은 비저장 sandbox라는 현재 설계와는 일치한다. 다만 UI 용어가 `새 실행`, `취소`, `검토 완료`이므로 사용자는 지속되는 실제 작업으로 받아들일 가능성이 높다.

필요한 수정:

- 실제 실행 기능을 목표로 한다면 실행 저장소와 lifecycle API를 구현한다.
- 비저장 재생을 유지한다면 실행 이력, 취소, 검토 완료처럼 영속성을 암시하는 UI를 제거하거나 명확히 구분한다.

### 5.7 중간: 검토 완료 상태가 현재 브라우저 메모리에만 남음

`markReviewed()`는 서버에 검토 결과를 보내지 않고 프런트엔드 메모리의 snapshot만 `approved`로 바꾼다. 구현에도 브라우저 세션에만 남는다고 명시돼 있다. 관련 코드는 [`httpHarness.ts` 162-168행](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition/blob/032f4d5d02f5fdb6288b727cc3ed583ddfdb687f/web_dongseop/src/services/httpHarness.ts#L162-L168)이다.

관찰된 결과:

- 버튼은 `검토 완료`로 바뀌지만 실행 상태는 계속 `검토 대기`로 남았다.
- 재연결하면 검토 완료 표시가 사라졌다.
- 다운로드 artifact는 계속 `Human review: Required`라고 기록했다.

필요한 수정:

- reviewer, 시각, 대상 snapshot hash, 판정을 서버 감사 로그에 저장한다.
- 서버 응답을 기준으로 화면 상태와 artifact를 함께 갱신한다.

### 5.8 중간: 하네스 연결 상태와 모델 연결 상태를 혼합함

상단은 Python API에 연결됐으므로 `하네스 연결됨`이라고 표시한다. 하지만 Agent Harness 화면은 `/api/models`의 `reachable` 값을 사용해 `하네스 오프라인`이라고 표시한다.

백엔드의 `reachable`은 설치된 Ollama 모델 목록이 비어 있는지를 의미한다. 즉, 하네스 서버가 살아 있는지와 로컬 모델이 준비됐는지는 다른 상태다. 관련 구현은 [`server.py` 239-249행](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition/blob/032f4d5d02f5fdb6288b727cc3ed583ddfdb687f/src/h2l/server.py#L239-L249)이다.

필요한 수정:

- `harnessConnected`, `modelRuntimeReachable`, `modelInstalled`, `policyFallbackActive`를 별도 상태로 표현한다.
- 모델이 없어 정책 폴백 중인 상태를 `하네스 오프라인`이라고 부르지 않는다.

### 5.9 중간: 에이전트 화면이 현재 선택한 실행 문맥을 이어받지 않음

Agent Harness 화면은 처음 로드한 가설 목록의 첫 번째 값을 기본값으로 선택한다. 메인에서 TYK2 실행을 보고 있었더라도 목록 첫 값이 `IBD:DEMO-POS`이면 그 값이 선택될 수 있다. 관련 코드는 [`AgentHarnessView.tsx` 45-54행](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition/blob/032f4d5d02f5fdb6288b727cc3ed583ddfdb687f/web_dongseop/src/views/AgentHarnessView.tsx#L45-L54)이다.

필요한 수정:

- 전역 선택 실행의 `hypothesis_id`를 Agent Harness 화면으로 전달한다.
- URL 또는 공용 상태 저장소를 사용해 화면 이동 후에도 문맥을 유지한다.

### 5.10 중간: 점수 의미가 판정과 모순될 수 있음

적응증 안의 `outcome="inconclusive"` 레코드는 임상 지지로 인정되지 않아 판정은 `HOLD`가 된다. 그러나 현재 점수 계산은 적응증 불일치와 `failed/negative`만 차감하고 그 밖의 레코드는 점수를 유지한다. 그래서 `scoreBefore=0`, `scoreAfter=100`이 될 수 있다.

관련 로직은 [`workspace.py` 94-125행](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition/blob/032f4d5d02f5fdb6288b727cc3ed583ddfdb687f/src/h2l/workspace.py#L94-L125)이다.

필요한 수정:

- 이 값이 과학적 타깃 점수가 아니라 근거 coverage 점수라면 화면 명칭과 설명을 바꾼다.
- `inconclusive`, 알 수 없는 outcome, 누락 값을 지지 근거로 취급하지 않도록 계산식을 보완한다.
- 점수와 최종 판정의 허용 가능한 조합을 계약 테스트로 고정한다.

### 5.11 중간: 화면의 실행 시간과 11개 에이전트가 실제 런타임 telemetry가 아님

- 단계별 시간과 실행 시각 중 일부는 packet 시각 또는 고정 fixture 값이다.
- 화면의 11개 에이전트 목록은 제품 구조를 설명하는 정적 데이터이며 실제로 11개 프로세스나 모델이 실행됐다는 증거가 아니다.
- 현재 실제 PR #5 루프는 허용 행동과 관측 trace 중심으로 동작한다.

필요한 수정:

- 실제 시작, 종료, duration, retry, selected_by 값을 서버 이벤트에서 가져온다.
- 11개 항목은 `역할 설계` 또는 `예정 구성`으로 표시하거나 실제 실행 trace와 연결한다.

### 5.12 낮음: README 설명이 현재 구현보다 오래됨

PR #6 검사 커밋의 일부 README 문구는 Python 하네스가 웹에 연결되지 않았다고 설명하지만, 실제로는 시나리오 실행 API가 연결돼 있다. 반대로 실제 에이전트 단계 진행까지 연결된 것처럼 읽히는 표현도 피해야 한다.

필요한 수정:

- 현재 구현된 규칙 시나리오 연결과 아직 구현되지 않은 실시간 에이전트 실행을 구분해 README를 갱신한다.

## 6. 과학적 내용과 출처 QA

### 6.1 확인된 점

- 현재 규칙은 TYK2/deucravacitinib을 IBD의 긍정 타깃으로 자동 진행하지 않고 보수적으로 중단한다.
- 원 논문은 LATTICE-CD, LATTICE-UC, IM011-127의 3개 무작위배정 2상 시험에서 모두 1차 유효성 평가변수가 충족되지 않았다고 보고한다.
- 따라서 IBD 맥락에서 해당 임상 실패를 반증 근거로 사용하는 방향은 타당하다.

원 출처:

- 1차 임상 논문: [Deucravacitinib in patients with inflammatory bowel disease: 12-week efficacy and safety results from 3 randomized phase 2 studies](https://academic.oup.com/ecco-jcc/article/19/6/jjaf080/8129055), DOI `10.1093/ecco-jcc/jjaf080`
- 공개 원문: [PubMed Central PMC12137900](https://pmc.ncbi.nlm.nih.gov/articles/PMC12137900/)
- 관련 해설: [Hit the road JAK: is there still hope left for TYK2 inhibition in IBD?](https://academic.oup.com/ecco-jcc/article/19/6/jjaf088/8156999), DOI `10.1093/ecco-jcc/jjaf088`

### 6.2 보완이 필요한 점

- 현재 TYK2 fixture에는 IBD 실패 레코드가 2개뿐이다.
- 자체 평가 계획은 TYK2 실패 프로그램 3개 중 3개를 탐지하는 것을 PASS 기준으로 둔다.
- fixture에 ClinicalTrials.gov ID `NCT03599622`, `NCT03934216`, `NCT04613518`이 없다.
- source가 실제 URL이나 저장된 원문 hash가 아니라 `fixture://`로 끝난다.
- `data/raw`, `artifacts`, `reports`에는 실제 외부 출처 snapshot이 없다.
- 연구 문서의 대표 출처로 적힌 `jjaf088`은 1차 시험 결과 논문이 아니라 해설이다. 핵심 시험 결과의 대표 인용은 `jjaf080`이어야 한다.

필요한 수정:

- 3개 시험을 각각 별도 evidence record로 저장한다.
- NCT ID, DOI, 조회일, 원문 URL, snapshot hash를 함께 기록한다.
- 보고서의 각 결론에서 사용한 evidence ID를 원문 snapshot까지 추적할 수 있게 한다.
- `jjaf080`을 1차 근거로, `jjaf088`을 해석을 보조하는 2차 근거로 구분한다.

### 6.3 해석상 주의점

현재 규칙의 `해당 적응증 실패 임상 1건 이상이면 REJECT`는 안전한 데모용 운영 규칙으로는 이해할 수 있다. 그러나 이 결과를 `TYK2라는 타깃 자체가 모든 IBD 연구에서 무효`라는 일반적 과학 결론으로 확대하면 안 된다.

더 정확한 표현은 다음과 같다.

> 현재 등록된 deucravacitinib IBD 임상 근거와 보수적 운영 규칙에 따라 이 프로그램의 자동 분자 단계 진행을 중단한다.

긍정 분기인 `DEMO-POS`와 `DEMO:SUPPORT`도 합성 fixture이므로 실제 치료 후보가 검증됐다는 증거로 사용할 수 없다.

## 7. 실제 구현 범위에 대한 결론

현재 구현을 가장 정확하게 설명하면 다음과 같다.

- 구현됨: 승인 스냅샷과 sandbox packet을 이용한 결정 규칙
- 구현됨: 모델 또는 정책이 허용 행동을 고르는 제한된 PR #5 에이전트 루프
- 구현됨: 모델 오류 시 결정론적 폴백과 실행 시점 안전 게이트
- 구현됨: 웹에서 preset 규칙 시나리오를 실행하고 최종 `RunSnapshot`을 표시하는 연결
- 부분 구현: Agent Harness 화면에서 실제 에이전트 trace 요청
- 미구현: 메인 실행 화면과 실제 에이전트 trace의 통합
- 미구현: 서버 실행 lifecycle, 단계 이벤트, 실행 저장, 취소, 재개, 검토 저장
- 미구현: 외부 데이터 API를 이용한 실제 타깃 탐색, 실제 양성 타깃 분기, 완전한 ADMET와 합성 경로 실행
- 미충족: 1차 출처 snapshot과 최종 주장 provenance 100%

따라서 현 단계의 제품은 **근거 packet을 비평하고 안전 판정을 내리는 결정 지원 하네스 프로토타입**이다. 완성된 자율 신약개발 하네스 또는 실시간 다중 에이전트 실행 시스템이라고 부르기에는 구현 범위가 부족하다.

## 8. 수정 우선순위

### 병합 전 필수

1. PR #5를 먼저 병합하고 PR #6의 base를 `main`으로 변경한다.
2. `ReportView`의 TYK2/IBD/REJECTED 고정 문구를 실제 snapshot 값으로 교체한다.
3. 중첩 packet 필드의 타입과 enum을 검증하고 요청 스레드 예외를 회귀 테스트로 막는다.
4. 하네스 연결과 모델 연결 상태를 분리한다.
5. 메인 `새 실행`이 규칙 재생인지 실제 에이전트 실행인지 제품 문구와 동작을 일치시킨다.

### 최종 시연 전 필수

1. 실행 상태와 단계 이벤트를 서버에서 제공하고 화면이 실제 진행을 표시하게 한다.
2. 실행 재조회, 취소, 검토 완료를 서버에 저장한다.
3. 화면, 다운로드 보고서, API 응답의 타깃과 판정이 항상 같은지 E2E로 검사한다.
4. TYK2 임상 3건의 NCT ID와 `jjaf080` 원문 snapshot을 저장한다.
5. 큰 요청이 항상 안정적인 413을 반환하도록 한다.
6. `inconclusive` 근거에서 점수와 판정이 모순되지 않도록 점수 의미와 계산을 정리한다.

### 후속 개선

1. 현재 선택한 실행 문맥을 Agent Harness 화면에 전달한다.
2. 실제 runtime telemetry와 정적 역할 설계를 구분한다.
3. README와 데모 설명을 현재 구현 범위에 맞게 갱신한다.
4. 실제 Ollama 모델과 외부 데이터 도구를 포함한 통합 환경 검사를 별도로 수행한다.

## 9. 이번 QA에서 검증하지 못한 항목

- 로컬에 Ollama 실행 파일이 없고 11434 포트가 닫혀 있어 실제 `gemma4:latest` 추론은 재검증하지 못했다.
- 외부 Open Targets, ChEMBL, ADMET-AI, AiZynthFinder의 실제 API 실행은 현재 PR의 연결 범위에 포함되지 않아 검사하지 못했다.
- 실제 사용자 인증, 다중 사용자 동시 실행, 장시간 작업 복구는 구현이 없어 검사할 수 없었다.
- 이 보고서의 PASS는 검사한 커밋과 로컬/CI 조건에 한정되며, 두 PR에 새 커밋이 추가되면 전체 회귀 검사가 필요하다.

## 10. 최종 결론

PR #5의 핵심인 제한된 에이전트 행동 선택, 정책 폴백, 실행 시점 안전 게이트는 의도대로 동작했다. PR #6도 웹에서 하네스의 규칙 시나리오를 호출해 최종 판정을 보여주는 기본 연결은 성공했다.

그러나 현재 메인 실행은 실제 PR #5 에이전트 단계를 실행하지 않고, 진행 상황은 서버 이벤트가 아니며, 실행과 검토 결과가 저장되지 않는다. 또한 보고서 화면의 핵심 결론이 실제 백엔드 응답과 반대로 표시되는 경우가 있고, 잘못된 중첩 입력은 안정적인 오류 응답 대신 연결 종료를 일으킨다. 과학적 방향은 타당하지만 3개 임상시험의 1차 출처 provenance도 아직 완전하지 않다.

따라서 **규칙과 안전 게이트 검증은 PASS**, **통합 데모와 최종 제출 준비도는 HOLD**로 판정한다.
