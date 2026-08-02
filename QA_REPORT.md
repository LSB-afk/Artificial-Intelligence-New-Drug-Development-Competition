# PR #5·#6 QA 문제 보고서

- 검사한 PR: [PR #5](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition/pull/5), [PR #6](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition/pull/6)
- 검사한 커밋: PR #5 `22ab25e`, PR #6 `032f4d5`
- 결론: **현재 상태로는 최종 데모에 사용하기 어렵다.**

## 1. 화면에 잘못된 판정이 표시됨

백엔드의 실제 결과는 다음과 같았다.

- 타깃: `DEMO:SUPPORT`
- 판정: `ADVANCE`
- 상태: `승인 대기`

하지만 화면에는 `TYK2`, `IBD`, `REJECTED`가 표시됐다. 화면 문구가 코드에 고정되어 있기 때문이다.

수정 방법: 화면의 타깃, 질병, 판정을 백엔드가 보낸 값으로 표시해야 한다.

[문제가 있는 코드](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition/blob/032f4d5d02f5fdb6288b727cc3ed583ddfdb687f/web_dongseop/src/views/ReportView.tsx#L87-L90)

## 2. 메인 화면의 새 실행이 실제 에이전트를 실행하지 않음

메인 화면의 `새 실행`은 정해진 예제 데이터로 최종 판정만 계산한다. PR #5에서 만든 에이전트 행동 선택 과정은 실행하지 않는다.

실제 에이전트 실행은 별도의 Agent Harness 화면에서만 호출된다. 두 기능이 아직 연결되지 않았다.

수정 방법: 메인 화면의 새 실행이 실제 에이전트 실행 API를 호출하도록 연결해야 한다. 연결 전에는 버튼 이름을 `예제 판정 실행`처럼 정확하게 바꿔야 한다.

[현재 새 실행 코드](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition/blob/032f4d5d02f5fdb6288b727cc3ed583ddfdb687f/src/h2l/server.py#L195-L236)

## 3. 실행 과정이 실시간으로 보이지 않음

실행 버튼을 누르면 백엔드가 최종 결과를 한 번에 보낸다. 실행 중인 단계가 서버에서 차례대로 전달되지 않는다.

따라서 화면의 단계 진행 효과는 실제 에이전트 진행 상황이라고 볼 수 없다.

수정 방법: 서버가 `대기`, `실행 중`, `완료`, `실패`, `취소` 상태와 각 단계 결과를 차례대로 보내야 한다. 화면은 그 값을 받아 표시해야 한다.

## 4. 실행 결과가 서버에 저장되지 않음

새 실행 뒤에 다음 문제가 발생했다.

- 생성된 실행 ID를 다시 조회하면 404가 나온다.
- 실행 취소 요청은 405가 나온다.
- 실행 전후 서버의 실행 목록이 바뀌지 않는다.
- 같은 예제를 다시 실행하면 같은 ID가 나온다.

수정 방법: 실행 ID, 상태, 단계 기록, 최종 결과를 서버에 저장해야 한다. 저장하지 않을 계획이라면 `새 실행`, `취소`, `실행 이력`이라는 표현을 사용하면 안 된다.

## 5. 검토 완료가 저장되지 않음

`검토 완료` 버튼을 눌러도 결과가 서버에 저장되지 않는다. 현재 브라우저 안에서만 완료로 바뀐다.

- 다시 연결하면 검토 완료가 사라진다.
- 실행 상태는 계속 `검토 대기`로 남는다.
- 다운로드 보고서도 계속 `검토 필요`라고 표시한다.

수정 방법: 검토자, 검토 시간, 검토한 결과 ID를 서버에 저장하고 화면과 다운로드 보고서에 같은 상태를 표시해야 한다.

[현재 검토 처리 코드](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition/blob/032f4d5d02f5fdb6288b727cc3ed583ddfdb687f/web_dongseop/src/services/httpHarness.ts#L162-L168)

## 6. 잘못된 입력 때문에 연결이 끊김

입력 데이터 안의 `indication_id` 또는 `outcome`에 배열을 넣으면 정상적인 오류 안내 대신 요청 연결이 끊겼다.

그 밖에 다음 잘못된 입력도 그대로 받아들였다.

- 날짜가 아닌 `observed_at`
- 중복된 `evidence_id`
- 배열로 입력한 `kind`, `indication`, `stance`

수정 방법: 입력 항목마다 허용하는 자료형과 값을 검사해야 한다. 잘못된 입력은 연결을 끊지 말고 400 오류와 이유를 반환해야 한다.

[현재 입력 검사 코드](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition/blob/22ab25ea6bd585e891fa3f997c79e6cd6dcc803c/src/h2l/scenarios.py#L158-L197)

## 7. 큰 입력의 오류 처리가 일정하지 않음

약 0.9MB 입력은 받아들였고 약 1.8MB 응답을 만들었다. 1MB가 넘는 입력을 반복했을 때는 413 오류가 나오기도 했고, 연결이 갑자기 끊기기도 했다.

수정 방법: 최대 입력 크기를 하나로 정하고, 제한을 넘으면 항상 같은 413 오류를 반환해야 한다.

## 8. 하네스 연결과 AI 모델 연결을 혼동함

같은 화면에서 상단은 `하네스 연결됨`, Agent Harness 영역은 `하네스 오프라인`이라고 표시될 수 있다.

실제로는 Python 서버는 연결됐지만 Ollama 모델이 없는 상태다. 서버 연결과 모델 연결은 서로 다른 상태다.

수정 방법: `하네스 서버 연결`, `AI 모델 연결`, `규칙 방식으로 실행 중`을 따로 표시해야 한다.

[현재 모델 상태 코드](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition/blob/032f4d5d02f5fdb6288b727cc3ed583ddfdb687f/src/h2l/server.py#L239-L249)

## 9. 현재 보고 있는 실행과 Agent Harness의 선택값이 다를 수 있음

메인 화면에서 TYK2 실행을 보고 있어도 Agent Harness로 이동하면 목록의 첫 번째 가설이 자동 선택된다. 이 때문에 사용자가 다른 실행을 실행할 수 있다.

수정 방법: 메인 화면에서 선택한 실행의 가설 ID를 Agent Harness에도 그대로 전달해야 한다.

[현재 자동 선택 코드](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition/blob/032f4d5d02f5fdb6288b727cc3ed583ddfdb687f/web_dongseop/src/views/AgentHarnessView.tsx#L45-L54)

## 10. 점수와 최종 판정이 반대로 보일 수 있음

결론이 불확실한 근거만 넣으면 최종 판정은 `HOLD`인데 점수는 0점에서 100점으로 오를 수 있다.

수정 방법: 불확실한 근거를 긍정 근거처럼 계산하지 않아야 한다. 이 점수가 과학적 타깃 점수가 아니라 단순한 근거 정리 점수라면 화면 이름도 바꿔야 한다.

[현재 점수 계산 코드](https://github.com/LSB-afk/Artificial-Intelligence-New-Drug-Development-Competition/blob/032f4d5d02f5fdb6288b727cc3ed583ddfdb687f/src/h2l/workspace.py#L94-L125)

## 11. 과학적 근거 자료가 부족함

실제 논문에는 deucravacitinib의 IBD 2상 시험이 3개 있지만 현재 예제 데이터에는 실패 기록이 2개만 있다.

빠진 정보:

- `NCT03599622`
- `NCT03934216`
- `NCT04613518`
- 논문 원문 주소
- 자료를 저장한 날짜
- 저장한 파일이 바뀌지 않았는지 확인할 hash 값

또한 현재 자료의 `fixture://` 주소는 실제 출처가 아니다.

수정 방법: 시험 3개를 각각 실제 출처와 함께 저장하고, 화면의 근거에서 원문까지 확인할 수 있게 해야 한다.

1차 논문: [Deucravacitinib in patients with inflammatory bowel disease](https://academic.oup.com/ecco-jcc/article/19/6/jjaf080/8129055)

## 12. 실제로 실행한 값처럼 보이는 고정 데이터가 있음

화면의 11개 에이전트와 일부 실행 시간은 실제 서버 실행 기록이 아니라 미리 작성된 화면 데이터다.

수정 방법: 실제로 실행한 단계와 역할 설명용 항목을 분리해야 한다. 실행 시간도 서버에서 측정한 값만 표시해야 한다.

## 13. PR 병합 순서를 지켜야 함

PR #6은 PR #5 위에서 만들어졌다. PR #6만 먼저 합치면 필요한 코드가 빠질 수 있다.

수정 방법: PR #5를 먼저 `main`에 합친 뒤 PR #6의 기준 브랜치를 `main`으로 바꾸고 다시 검사해야 한다.

## 14. 실제 AI 모델과 외부 도구는 확인하지 못함

검사한 컴퓨터에는 Ollama가 실행되지 않았고 11434 포트도 닫혀 있었다. 따라서 실제 `gemma4:latest` 모델 실행은 확인하지 못했다.

Open Targets, ChEMBL, ADMET-AI, AiZynthFinder도 현재 웹 실행 과정에 연결되지 않았다.

수정 방법: 팀의 실제 실행 환경에서 모델과 외부 도구를 연결한 뒤 처음부터 끝까지 다시 검사해야 한다.
