# JB 기반 신약개발 하네스 설계

## 상태

- 기준 저장소: `LSB-afk/Search-for-AI-based-internal-regulations`
- 기준 커밋: `ab9900a26a55a2bce2a66b6c263bf221d39764f7`
- 적용 대상: H2L-Forge
- 범위: 실행 가능한 첫 하네스 코어와 결정론적 오프라인 평가
- 비범위: 실제 후보물질 효능 주장, 양성 타깃 선정, 외부 API 실시간 연동, 합성 경로 생성

## 목표

JB 저장소에서 검증된 운영 불변조건을 신약개발 의사결정에 맞게 이식한다.

1. 새 근거가 감지되어도 검토 전에는 현재 승인된 과학 판단을 바꾸지 않는다.
2. 외부 도구가 실패해도 허용된 고정 스냅샷으로 동일한 판단을 재생한다.
3. 타깃 판단과 분자 단계 사이에 결정론적 상태 전이와 사람 승인을 둔다.
4. 골드 케이스와 ablation으로 Clinical Contradiction Critic의 효과를 오프라인에서 측정한다.
5. 모든 관찰, 판단, 행동, 검증 결과를 숨은 사고과정이 아닌 구조화된 이벤트로 남긴다.

## 검토한 접근

### A. JB 애플리케이션 전체 복제

`dev/server.py`, 레지스트리, 자동 수집, 정적 UI를 그대로 복제하고 규정 용어를 신약 용어로 바꾼다.

- 장점: 화면과 서버를 가장 빠르게 확보한다.
- 단점: 문서 검색·시행일·규정 권한 모델이 과학 근거·가설·분자 상태와 맞지 않는다.
- 판단: 거부. 코드 양은 늘지만 과학적 상태 전이가 왜곡된다.

### B. 문서 하네스만 보강

현재 `harness.yaml`, `docs/`, `rules/`, `evals/`에 JB 패턴을 설명으로만 추가한다.

- 장점: 가장 작고 안전한 변경이다.
- 단점: 본선 평가의 실제 동작, 오류 복구, 도구 통합, 자율성 증거가 생기지 않는다.
- 판단: 거부. 현재 저장소가 이미 이 수준에 도달해 있다.

### C. 운영 불변조건 중심의 도메인 코어 이식

JB의 레지스트리, 승인 게이트, 오프라인 fallback, 결정론적 평가 방식을 신약 도메인 객체로 다시 구현한다. UI와 실시간 API는 코어가 증명된 뒤 얹는다.

- 장점: 작은 코드로 대회 평가에 직접 연결되는 증거를 만든다.
- 단점: 첫 단계에는 화려한 UI나 실제 RDKit/외부 API 통합이 없다.
- 판단: 채택. 현재 하네스와 충돌이 가장 적고 테스트 가능한 경계를 만든다.

## 아키텍처

```text
CLI / 향후 HTTP API
  -> DrugDiscoveryHarness
       -> SnapshotRegistry
       -> EvidenceAdapter (snapshot-first)
       -> ClinicalContradictionCritic
       -> DecisionGate
       -> AuditEventStore

Read-only Evaluation Plane
  -> gold cases
  -> baseline (support-only)
  -> candidate (contradiction-aware)
  -> paired metrics / deterministic bootstrap
```

### `SnapshotRegistry`

JB의 `RegulationRegistry`가 “검토 대기 버전은 현재 검색 결과를 바꾸지 않는다”를 보장한 방식을 과학 근거 패킷에 적용한다.

- `detect`: 내용 해시가 다른 근거 패킷을 `pending` 버전으로 등록한다.
- `approve`: 검토자가 버전을 승인하면 해당 가설의 `current` 스냅샷이 된다.
- `reject`: 근거 부족, 출처 문제, 스키마 오류 사유를 기록하고 활성화하지 않는다.
- `current`: 승인된 최신 버전만 과학 판단에 제공한다.
- 기존 승인본은 새 `pending`이 생겨도 유지한다.
- 모든 mutation은 원자적 JSON 교체와 이벤트 추가를 사용한다.

### `DrugDiscoveryHarness`

하나의 실행은 다음 순서를 지킨다.

1. 입력과 예산을 검증한다.
2. 승인된 근거 스냅샷을 읽는다.
3. 지지 근거와 적응증별 반증 근거를 분리한다.
4. Critic이 `ADVANCE`, `HOLD`, `REJECT` 중 하나를 추천한다.
5. DecisionGate가 상태 전이를 검증한다.
6. `ADVANCE`는 자동으로 분자 단계에 들어가지 않고 `AWAITING_APPROVAL`이 된다.
7. `HOLD`와 `REJECT`는 분자 적격성을 `false`로 고정한다.
8. 입력·스냅샷 해시·규칙·결정·다음 행동을 이벤트로 반환한다.

첫 고정 사례는 TYK2/deucravacitinib의 IBD 적응증 불일치와 실패 임상 근거다. 이 사례의 성공 조건은 후보 생성이 아니라 잘못된 전제를 기각하는 것이다.

### `EvidenceAdapter`

- 기본 실행은 네트워크를 사용하지 않는다.
- 승인된 스냅샷을 읽고 스키마와 SHA-256을 검증한다.
- 향후 live adapter가 실패하면 정해진 재시도 한도 후 동일 스냅샷을 사용한다.
- live와 snapshot은 동일한 정규화 레코드 스키마를 반환한다.
- 둘 다 없으면 `HOLD`로 닫는다.

### `ClinicalContradictionCritic`

Critic은 자유 텍스트 추론 대신 정규화 레코드와 규칙 ID를 사용한다.

- 다른 적응증의 승인을 현재 질환의 검증으로 이전하지 않는다.
- 실패한 적응증별 임상 근거가 있으면 이를 지지 근거보다 먼저 평가한다.
- 필수 근거 클래스가 비어 있으면 `HOLD`한다.
- 치명적 반증이 있으면 `REJECT`한다.
- `ADVANCE`는 충분한 근거와 반증 부재를 뜻할 뿐, 효능이나 임상 성공을 뜻하지 않는다.

### `DecisionGate`

| 현재 상태 | 요청 | 결과 |
|---|---|---|
| `EVIDENCE_COLLECTED` | critic 실행 | `CHALLENGED` |
| `CHALLENGED` | `REJECT` | `REJECTED` |
| `CHALLENGED` | `HOLD` | `HELD` |
| `CHALLENGED` | `ADVANCE` | `AWAITING_APPROVAL` |
| `AWAITING_APPROVAL` | reviewer 승인 | `MOLECULE_ELIGIBLE` |
| `HELD`/`REJECTED` | 분자 최적화 | 차단 |

Evaluation plane은 어떠한 전이도 요청할 수 없다.

## 데이터 계약

### Evidence packet

```json
{
  "hypothesis_id": "IBD:TYK2",
  "disease_id": "MONDO_0005265",
  "target": "TYK2",
  "observed_at": "2026-07-16T00:00:00Z",
  "records": [
    {
      "evidence_id": "EV-TYK2-PSO-APPROVAL",
      "kind": "approval",
      "indication": "plaque psoriasis",
      "outcome": "positive",
      "stance": "context"
    }
  ]
}
```

필수 필드는 `hypothesis_id`, `disease_id`, `target`, `observed_at`, `records`다. 각 레코드는 `evidence_id`, `kind`, `indication`, `outcome`, `stance`, `source_ref`를 가진다.

### Decision result

```json
{
  "run_id": "stable-id",
  "hypothesis_id": "IBD:TYK2",
  "decision": "REJECT",
  "state": "REJECTED",
  "molecule_eligible": false,
  "evidence_ids": ["EV-..."],
  "rule_ids": ["INDICATION_MATCH_REQUIRED", "FAILED_TRIAL_BLOCKS_ADVANCE"],
  "snapshot": {"version_id": "...", "content_hash": "..."},
  "events": []
}
```

## 오류 처리

- 승인 스냅샷 없음: `HOLD`, `SNAPSHOT_REQUIRED`.
- 스냅샷 해시/스키마 불일치: 실행 중단, 기존 승인본은 보존.
- 필수 임상 근거 없음: `HOLD`, 근거 수집 작업 제안.
- 적응증 불일치 또는 실패 임상: `REJECT`, 분자 단계 차단.
- 잘못된 상태 전이: 예외와 `InvalidTransitionBlocked` 이벤트.
- 평가 도구의 mutation 요청: 거부하고 과학 상태를 그대로 유지.

## 평가 설계

JB의 검색 골드셋 ablation을 다음처럼 바꾼다.

- baseline: 지지 근거만 보는 `support-only` 판단기.
- candidate: 적응증별 반증을 필수로 보는 `contradiction-aware` 판단기.
- 고정 케이스: TYK2/IBD, 근거 누락, 승인 대기 스냅샷, 평가-plane mutation, API 실패 후 snapshot.
- 지표: decision accuracy, contradiction recall, unsafe advance count, snapshot fallback success.
- 비교: 케이스 단위 paired bootstrap, 10,000회, seed 42.
- 안전 중요 케이스가 하나라도 실패하면 전체 readiness는 실패한다.

## 첫 구현 파일

```text
src/h2l/
  __init__.py
  registry.py
  state_machine.py
  replay.py
  eval_runner.py
  cli.py
tests/
  fixtures/tyk2_ibd/
    manifest.json
    normalized_evidence.json
    chembl_500.json
  test_registry.py
  test_state_machine.py
  test_offline_replay.py
  test_eval_runner.py
```

`src/`와 `tests/`의 기존 placeholder를 실제 패키지와 검증 코드로 채운다. JB의 `dev/` 디렉터리명은 복사하지 않고, 레지스트리·평가의 행동 계약만 이식한다.

## 수용 기준

1. 새 pending 스냅샷은 승인 전 현재 판단을 바꾸지 않는다.
2. TYK2/IBD 고정 사례는 `REJECT`, `molecule_eligible=false`를 반환한다.
3. Critic 제거 ablation은 최소 한 안전 중요 사례에서 성능이 악화된다.
4. 오프라인 평가를 같은 seed로 두 번 실행하면 결과가 byte-equivalent하다.
5. 평가 plane은 과학 상태를 변경하지 못한다.
6. 전체 단위 테스트와 Python 문법 검사가 통과한다.
7. 기존 문서와 dirty 작업을 삭제하거나 덮어쓰지 않는다.

## 후속 범위

코어가 통과한 뒤에만 다음을 추가한다.

1. HTTP API와 의사결정 trace UI.
2. Open Targets/ChEMBL/ClinicalTrials.gov live adapter와 snapshot fallback.
3. 승인된 양성 타깃 선정 후 RDKit 분자 검증.
4. ADMET-AI, SA/RAscore, top-5 AiZynthFinder 통합.
