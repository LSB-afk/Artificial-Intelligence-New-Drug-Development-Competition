# 01 Meeting Log

## Artifact Metadata

- Meeting/session: GitHub latest-state review and harness kickoff
- Date: 2026-07-19
- Participants: project owner, Codex agent team
- Owner: LSB-afk / project team
- Last updated: 2026-07-19

## Summary

The repository proposes a field 1+2 fusion service, H2L-Forge. The latest commit does not add runtime code; it corrects the scientific narrative and tool feasibility. The harness therefore centers on indication-aware self-falsification, explicit rejection states, provenance, bounded tool use, and deterministic replay.

## Decisions

| ID | Decision | Rationale | Owner | Status | Downstream Artifact |
|---|---|---|---|---|---|
| D-001 | TYK2 is the IBD rejection demo | Deucravacitinib failed the cited IBD phase-2 programs | Domain lead | Accepted | Domain model, flow, evals |
| D-002 | Positive optimization target remains unselected | Candidate alternatives have not passed the same evidence gate | Domain lead | Accepted | PRD, handoff |
| D-003 | Originality is evidence criticism, not the generic closed loop | Close prior art exists | Product lead | Accepted | CPS, proposal, rubric |
| D-004 | Use ADMET-AI; use SA/RAscore for bulk and AiZynthFinder only for top 5 | More implementable in four weeks | Engineering lead | Accepted, runtime unverified | Architecture, evals |
| D-005 | Use snapshot-first external retrieval | API outages must not break the demo | Engineering lead | Accepted | Data rules, architecture |
| D-006 | Keep evaluation-plane scoring separate from scientific authority | Rubric optimization must not bias evidence decisions | Project lead | Accepted | Architecture |

## Requirements Mentioned

| ID | Requirement | Source Phrase | Priority | Confidence | Trace |
|---|---|---|---|---|---|
| RM-001 | Autonomous decomposition and correction | "오류·잘못된 결과 발생 시 스스로 인지하고 수정" | P0 | High | F-04, GC-004, GC-009 |
| RM-002 | Accurate API/DB/tool use | "생성된 정보가 실제 데이터와 일치" | P0 | High | F-03, GC-003, GC-010 |
| RM-003 | Efficient use of credits | "제공된 크레딧 대비 결과물의 질적 완성도" | P0 | High | Budget Governor, cache metrics |
| RM-004 | Transparent demonstration | "에이전트의 사고 과정을 투명하게" | P0 | High | Decision trace UI, not hidden reasoning |

## Rejected / Deferred Options

| Option | Reason | Revisit Trigger |
|---|---|---|
| Use TYK2/deucravacitinib as positive IBD validation | Contradicted by indication-specific clinical results | New peer-reviewed evidence and domain approval |
| Claim the target-to-lead loop itself as novel | Close prior art exists | Never without a precise comparative claim |
| Use TDC as a ready ADMET predictor | TDC supplies datasets/benchmarks, not the planned ready inference path | A trained, versioned local model is added |
| Run AiZynthFinder over every generated candidate | Too slow and fragile for the MVP loop | Validated compute budget and benchmark |
| Show raw chain-of-thought | Not necessary for auditability and creates misleading disclosure | Never; show evidence, rules, actions, and concise reasons |

## Open Questions

| ID | Question | Why It Matters | Suggested Resolution | Owner |
|---|---|---|---|---|
| Q-001 | Which target powers the positive molecule branch? | Needed for end-to-end scientific demo | Compare candidate targets with the same clinical contradiction gate | Domain lead |
| Q-002 | What is the exact tool/runtime budget? | Needed for retry and call caps | Measure during week-1 smoke tests | Engineering lead |
| Q-003 | Which snapshots can be committed or redistributed? | Needed for reproducible fixtures | Review source terms and commit minimal lawful fixtures/manifests | Project lead |

## Build Implications

| Signal | Product Impact | Architecture Impact | Risk Impact |
|---|---|---|---|
| TYK2 clinical contradiction | Rejection is a first-class success outcome | Add `REJECT`/`HOLD`; block molecule transition | Prevents false therapeutic claims |
| API outage | Demo must replay offline | Snapshot manifest and cache adapter | Reduces demo and reproducibility risk |
| Prior art | Comparison must be honest | Evaluation ablation for contradiction critic | Reduces originality overclaim |
| Four-week final | Small, bounded scope | Six runtime roles; two-stage synthesis checks | Reduces scope and credit risk |

## Next Actions

| Action | Owner | Due | Artifact |
|---|---|---|---|
| Evidence-qualify a positive target | Domain lead | Before molecule implementation | `docs/12_handoff.md` Q-001 |
| Smoke-test planned dependencies | Engineering lead | Final week 1 | Validation report |
| Build machine-readable golden case runner | Engineering lead | Before feature implementation | `evals/cases.jsonl` |
