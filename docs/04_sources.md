# 근거 소스

## 공식 대회 소스

| 소스 | URL | 사용 내용 |
| --- | --- | --- |
| DAKER 공식 대회 페이지 | https://daker.ai/public/hackathons/4th-jump-ai-agentic-drug-challenge | 주최/주관, 배경, 주제, 일정, 평가, 상금, 규칙 |
| DAKER hackathon API | https://daker.ai/api/hackathons/4th-jump-ai-agentic-drug-challenge | 페이지 구조화 원문, stage, 제출 설정, 평가 가중치 |
| DAKER 게시판 API | https://daker.ai/api/hackathons/ed79c1f0-1a61-4615-aa13-74cd32956a59/posts | 제출 유의사항: 제출 탭, 파일 형식, 초안 저장 주의 |
| KHIDI 공식 공고 | https://www.khidi.or.kr/board/view?linkId=48946784&menuId=MENU01108 | 공식 공고 게시, 첨부파일 |
| KHIDI 공고 PDF | https://www.khidi.or.kr/fileDownload?titleId=530053&fileId=1&fileDownType=C&paramMenuId=MENU01108 | 대회 목적, 참여기관, 주제, 평가표, 시상, 윤리 가이드 |
| KHIDI 제안서 HWPX | https://www.khidi.or.kr/fileDownload?titleId=530053&fileId=2&fileDownType=C&paramMenuId=MENU01108 | 제안서 10쪽 이내 양식과 8개 작성 항목 |

## 기술/데이터 소스

| 소스 | URL | 설계 반영 |
| --- | --- | --- |
| Open Targets GraphQL API | https://platform-docs.opentargets.org/data-access/graphql-api | target, disease, drug, target-disease association 조회 |
| Open Targets target-disease associations | https://platform-docs.opentargets.org/associations | association score와 직접/간접 근거 해석 |
| ChEMBL Data Web Services | https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services | activity, assay, molecule, target, mechanism, drug indication API |
| ChEMBL status endpoint | https://www.ebi.ac.uk/chembl/api/data/status.json | 2026-07-06 조회 기준 ChEMBL_37, 2026-05-01 release |
| RDKit QED docs | https://www.rdkit.org/docs/source/rdkit.Chem.QED.html | QED, MW, logP, TPSA, HBA/HBD, rotatable bonds, alerts |
| TDC ADMET Benchmark Group | https://tdcommons.ai/benchmark/admet_group/overview/ | ADMET categories, scaffold split, AUROC/AUPRC/MAE/Spearman 평가 |
| AiZynthFinder docs | https://molecularai.github.io/aizynthfinder/ | retrosynthesis planning, MCTS, policy model, stock collection |
| STONED/SELFIES paper | https://pubs.rsc.org/en/content/articlepdf/2021/sc/d1sc00231g | training-light molecular space traversal and optimization |
| ChemCrow paper | https://www.nature.com/articles/s42256-024-00832-8 | LLM chemistry agent and expert-designed tool integration precedent |

## 조회 메모

- DAKER 공식 페이지는 React SPA이므로 HTML 본문만으로는 대회 내용을 읽을 수 없다. 실제 내용은 `/api/hackathons/4th-jump-ai-agentic-drug-challenge`에서 구조화 JSON으로 확인했다.
- KHIDI PDF는 `pdfplumber`로 7쪽 텍스트를 추출해 DAKER 내용과 대조했다.
- HWPX 제안서 양식은 압축 해제 후 `Preview/PrvText.txt`로 주요 항목을 확인했다.
- DAKER 게시판 공지 1건은 제출 완료 상태 확인을 강조한다. 초안 저장 상태는 제출 완료가 아니다.
