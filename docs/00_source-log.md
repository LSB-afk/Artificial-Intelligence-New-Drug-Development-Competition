# 00 Source Log

## Artifact Metadata

- Owner: LSB-afk / project team
- Last updated: 2026-07-19
- Source status: summarized
- Confidence: high

## Source

- Type: user prompt + competition brief + repository + research
- Date: 2026-07-19
- Provided by: project owner
- Scope: preliminary proposal and final-round executable AI agent
- Locations:
  - User-provided preliminary/final judging tables in the 2026-07-19 session
  - `docs/01_competition_analysis.md`
  - `05_리서치/2026-07-16_H2L-Forge_냉정평가_및_개선안.md`
  - GitHub commit `25c622e97dc4c6c27f8a8c78f244880269bb05cb`

## Raw Intent

Verify the latest GitHub commit and repository topic, learn the competition requirements, and begin an implementation-ready AI agent harness design that can score well in both the preliminary proposal and final demonstration.

## Explicit Requirements

| ID | Requirement | Source Phrase | Priority | Confidence |
|---|---|---|---|---|
| ER-001 | Inspect the latest GitHub commit before designing | "지금 깃허브 최신 커밋 내용을 확인" | P0 | High |
| ER-002 | Confirm the actual competition/project topic | "주제도 무엇인지 확인" | P0 | High |
| ER-003 | Design an agentic service for a real drug-development problem | "에이전트 서비스 형태로 설계" | P0 | High |
| ER-004 | Go beyond a chatbot with planning, tools, collaboration, and feedback | Preliminary originality criteria | P0 | High |
| ER-005 | Define realistic open-source/API/library use | Preliminary feasibility criteria | P0 | High |
| ER-006 | Define evaluation sets and measurable metrics | Both judging tables | P0 | High |
| ER-007 | Preserve transparency, ethics, safety, and demonstrability | Ethics and final demo criteria | P0 | High |
| ER-008 | Start work immediately without a permission handoff | "바로 작업 시작" | P0 | High |

## Implied Requirements

| ID | Requirement | Why Implied | Risk if Wrong | Confidence |
|---|---|---|---|---|
| IR-001 | Preserve current uncommitted repository work | The working tree contains edited and untracked design artifacts | User work loss | High |
| IR-002 | Trace every judged claim to an artifact and observable demo event | The evaluation is proposal- and demonstration-driven | Unverifiable scoring claims | High |
| IR-003 | Treat external APIs as unreliable and support replay | ChEMBL returned HTTP 500 during the latest research verification | Demo failure | High |
| IR-004 | Prevent target-to-molecule progression when clinical evidence contradicts the indication | The TYK2/IBD premise was reversed by current evidence | Scientific invalidity | High |
| IR-005 | Separate visible decision traces from hidden model reasoning | Judges need transparency, but hidden chain-of-thought is not a product artifact | Unsafe or misleading UX | High |

## Unknowns / Ambiguities

| ID | Question | Why It Matters | Default Assumption | Owner |
|---|---|---|---|---|
| Q-001 | Positive target for the molecule branch | A positive branch is needed to demonstrate the full field 1+2 loop | Keep `TBD`; do not promote a target without the same evidence gate | Domain lead |
| Q-002 | Model/provider and credit limit | Determines tool-calling runtime and resource budget | Provider-neutral architecture with explicit budgets | Engineering lead |
| Q-003 | Measured business baseline | Required for defensible time/cost claims | No numeric savings claim until measured | Product lead |
| Q-004 | External data redistribution terms | Affects tracked fixtures and deployment | Store minimal manifests/hashes; review terms before distributing snapshots | Project lead |

## Assumptions Made

| ID | Assumption | Reason | Reversal Cost |
|---|---|---|---|
| A-001 | Public, non-personal drug-discovery data is sufficient for the MVP | Current proposal and tools use public sources | Medium |
| A-002 | Wet-lab execution and clinical decision-making are outside the MVP | Four-week final implementation window and safety constraints | Low |
| A-003 | The final UI can replay pinned evidence snapshots | Needed for reliable judging-day demonstration | Medium |

## Source-to-Artifact Trace

| Source Signal | Interpreted As | Artifact Impact | Confidence |
|---|---|---|---|
| Preliminary 20-point problem definition | CPS and problem-to-feature trace | `docs/02_cps.md`, `docs/06_prd.md` | High |
| Preliminary originality criteria | Self-falsification and failure-ledger loop | `docs/08_feature-spec.md`, `docs/09_flow.md` | High |
| Final scientific validity 30 points | Indication-aware clinical contradiction gate | `docs/05_domain-model.md`, `rules/agent-rules.md` | High |
| Final tool integration 15 points | Snapshot manifests and validated tool contracts | `docs/07_architecture.md`, `rules/data-rules.md` | High |
| Final demo 30 points | Five-minute deterministic replay | `docs/09_flow.md`, `docs/12_handoff.md` | High |

## Definition of Done

- [x] Raw source identity preserved.
- [x] Explicit and implied requirements separated.
- [x] Assumptions are labeled.
- [x] Open questions are actionable.
