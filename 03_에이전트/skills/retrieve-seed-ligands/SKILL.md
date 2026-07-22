---
name: retrieve-seed-ligands
description: 인간 승인까지 받은 적격 타깃에서 품질 기준을 만족하는 측정 활성 리간드와 reference molecule을 선별한다. ChEMBL assay와 activity를 필터링해 재현 가능한 seed set을 만들 때 사용한다.
---

# 시드 리간드 검색

## 진입 게이트

`molecule_eligible=true`가 아니면 실행하지 않는다. `REJECTION_DEMO`의 TYK2/deucravacitinib은 치료적 seed로 진행하지 않고 method/reference 문맥으로만 사용한다.

## 절차

1. ChEMBL target ID를 검증한다.
2. assay confidence, target type, standard type, relation, value, unit 조건을 명시한다.
3. 단백질 결합·기능 assay를 구분하고 비교 불가능한 endpoint를 섞지 않는다.
4. canonical SMILES와 molecule ID를 보존하고 중복·염·혼합물을 정리한다.
5. 측정 활성과 승인 reference의 적응증을 별도 필드로 유지한다.
6. 필터 전후 개수와 제외 사유를 기록한다.

## 출력

seed table, assay metadata, measured activity type, source snapshot, 제외 ledger를 반환한다.

현재 응답 스냅샷 없이 ChEMBL activity count를 확정 수치로 보고하지 않는다.
