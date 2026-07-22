---
name: manage-evidence-snapshots
description: 외부 데이터베이스 응답을 스키마 검증하고 출처, 관측일, 쿼리, 해시, live/cache 모드가 포함된 재생 가능한 스냅샷으로 관리한다. API 장애 fallback과 감사 추적을 구성할 때 사용한다.
---

# 근거 스냅샷 관리

## 절차

1. 요청 URL 또는 query, source ID, 관측 시각, 응답 상태를 기록한다.
2. 원본 응답과 정규화 결과를 분리 저장한다.
3. 스키마와 핵심 ID를 검증한 뒤 SHA-256을 계산한다.
4. manifest에 source, version, observed_at, query_hash, content_hash, classification을 기록한다.
5. live 호출은 제한된 재시도 후 승인된 pinned snapshot으로 fallback한다.
6. fallback 사용 사실과 snapshot 날짜를 사용자에게 노출한다.

## 불변식

- 승인 전 pending snapshot이 현재 판단을 바꾸지 못하게 한다.
- 해시 또는 스키마가 다르면 실행을 중단한다.
- live 실패를 성공으로 위장하거나 cache를 live라고 표시하지 않는다.
- live와 snapshot adapter는 동일한 정규화 스키마를 반환한다.

이 저장소에서는 `docs/07_architecture.md`, `docs/12_handoff.md`, `rules/data-rules.md`를 따른다.
