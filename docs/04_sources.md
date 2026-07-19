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
| Deucravacitinib IBD phase-2 results | https://academic.oup.com/ecco-jcc/article/19/6/jjaf088/8156999 | LATTICE-CD/UC와 IM011-127의 1차 지표 실패; TYK2/IBD negative demo 근거 |
| Deucravacitinib IBD review/full text | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12137900/ | IBD 프로그램 실패와 조기 종료 교차 확인 |
| ChEMBL status endpoint | https://www.ebi.ac.uk/chembl/api/data/status.json | 2026-07-06 조회 기준 ChEMBL_37, 2026-05-01 release |
| RDKit QED docs | https://www.rdkit.org/docs/source/rdkit.Chem.QED.html | QED, MW, logP, TPSA, HBA/HBD, rotatable bonds, alerts |
| TDC ADMET Benchmark Group | https://tdcommons.ai/benchmark/admet_group/overview/ | ADMET 데이터셋·benchmark와 scaffold split; ready predictor로 사용하지 않음 |
| ADMET-AI paper | https://academic.oup.com/bioinformatics/article/40/7/btae416/7698030 | planned pretrained ADMET inference path |
| ADMET-AI repository | https://github.com/swansonk14/admet_ai | 설치/API/version smoke-test 대상 |
| RAscore paper | https://pubs.rsc.org/en/content/articlehtml/2021/sc/d0sc05401a | bulk synthesis feasibility proxy와 AiZynthFinder 대비 속도 근거 |
| AiZynthFinder docs | https://molecularai.github.io/aizynthfinder/ | optional top-5 retrosynthesis feasibility; 전체 loop 도구가 아님 |
| STONED/SELFIES paper | https://pubs.rsc.org/en/content/articlepdf/2021/sc/d1sc00231g | training-light molecular space traversal and optimization |
| ChemCrow paper | https://www.nature.com/articles/s42256-024-00832-8 | LLM chemistry agent and expert-designed tool integration precedent |
| Coscientist paper | https://www.nature.com/articles/s41586-023-06792-0 | autonomous chemical research loop, document/code/tool integration |
| PharmAgents | https://arxiv.org/abs/2503.22164 | target discovery부터 preclinical까지의 close prior art; generic closed-loop novelty claim 제한 |
| OriGene | https://www.biorxiv.org/content/10.1101/2025.06.03.657658v1 | self-evolving disease biology multi-agent prior art |
| Google AI co-scientist | https://www.nature.com/articles/s41586-026-10644-y | multi-agent hypothesis generation/critique prior art |
| DrugAgent DTI | https://arxiv.org/html/2408.13378v4 | coordinator-based multi-agent drug-target reasoning |
| DrugAgent programming | https://arxiv.org/abs/2411.15692 | LLM planner/instructor for drug discovery ML programming |
| AgentD modular drug agent | https://arxiv.org/html/2507.02925v3 | modular drug discovery agent with RAG, ADMET, binding, SMILES generation |
| GuacaMol GitHub | https://github.com/BenevolentAI/guacamol | distribution-learning and goal-directed molecular generation evaluation |
| MOSES paper | https://www.frontiersin.org/journals/pharmacology/articles/10.3389/fphar.2020.565644/full | validity, uniqueness, novelty, filters, scaffold metrics |
| 제2회 AI 신약개발 경진대회 우수상 후기 | https://hyperlab.hits.ai/blog/2nd-JUMP-AI-KR | 데이터 부족 극복 전략: MolCLR, LDS/FDS, binding affinity signal |
| 제3회 공개 솔루션 예시 | https://github.com/Samdo3/MAP3K5_JumpAI2025_Competition | 실험노트, 실패 실험, CV/LB gap 기록 방식 |

## 조회 메모

- DAKER 공식 페이지는 React SPA이므로 HTML 본문만으로는 대회 내용을 읽을 수 없다. 실제 내용은 `/api/hackathons/4th-jump-ai-agentic-drug-challenge`에서 구조화 JSON으로 확인했다.
- KHIDI PDF는 `pdfplumber`로 7쪽 텍스트를 추출해 DAKER 내용과 대조했다.
- HWPX 제안서 양식은 압축 해제 후 `Preview/PrvText.txt`로 주요 항목을 확인했다.
- DAKER 게시판 공지 1건은 제출 완료 상태 확인을 강조한다. 초안 저장 상태는 제출 완료가 아니다.
- 2026-07-16 최신 냉정 평가가 TYK2/IBD 임상 전제, 선행연구, ADMET/합성 도구 계획을 교정했다. 기존 2026-07-06 문서와 충돌하면 최신 근거와 `docs/11_change-log.md`를 우선한다.
- ChEMBL TYK2 activity 44,880건 수치는 2026-07-16 서버 500 오류로 재검증하지 못했으므로 response snapshot이 생기기 전에는 최종 주장에 사용하지 않는다.
