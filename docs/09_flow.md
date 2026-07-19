# 09 Flow

## Artifact Metadata

- Owner: LSB-afk / project team
- Last updated: 2026-07-19

## Core Demo Flow: Attractive Signal to Correct Rejection

1. User selects `REJECTION_DEMO` and enters inflammatory bowel disease.
2. Disease is normalized to `MONDO_0005265`; the system shows source and match.
3. Snapshot-first retrieval gathers target associations and candidate evidence.
4. TYK2 appears tractable and has an approved psoriasis drug, creating the tempting initial hypothesis.
5. Clinical Contradiction Critic checks indication match and IBD-specific trial outcomes.
6. The claim ledger records that psoriasis approval does not validate IBD and links the cited failed IBD phase-2 programs.
7. Decision Engine commits `REJECT` or reviewed `HOLD`; molecule eligibility remains false.
8. The system shows the negative decision as a successful agent outcome, including evidence, rule, uncertainty, and next research action.
9. An injected ChEMBL 5xx demonstrates bounded retry and snapshot fallback.
10. Audit report displays decision trace, failure ledger, budget, and provenance without hidden chain-of-thought.

## Positive Molecule Branch

The positive branch is disabled until a separate target completes the same contradiction review and a domain reviewer records `TargetAdvanced`. When enabled:

1. Retrieve versioned seed ligands and assay metadata.
2. Generate/retrieve a bounded candidate set.
3. RDKit-valid candidates receive measured/predicted/proxy labels.
4. Planned ADMET-AI and SA/RAscore gates run; unavailable tools are not imputed.
5. Optional AiZynthFinder runs only for the final top 5.
6. If all candidates fail, lower chemical-accessibility status and return to target review.
7. Human reviewers approve or reject bounded export.

## Flow Table

| Step | Actor | Input | System Behavior | Output | Failure Handling | Evidence Shown |
|---|---|---|---|---|---|---|
| 1 | Researcher | Disease + mode | Validate intake and budget | Run manifest | Invalid input → clarification/block | Mode, limits |
| 2 | Evidence Scout | Disease text | Normalize ID | Disease context | Ambiguity → `HOLD` | Ontology ID/source |
| 3 | Evidence Scout | Disease context | Live/cache retrieval | Evidence records | 5xx → bounded retry/cache | Cache/live/hash |
| 4 | Supervisor | Evidence | Draft target claim | Claim ledger | Missing evidence → `HOLD` | Support and unknowns |
| 5 | Clinical Critic | Claim ledger | Seek disconfirmation | Contradictions | Source conflict → review | Failed trials/indication |
| 6 | Decision Engine | Recommendation/rules | Commit state | `ADVANCE/HOLD/REJECT` | Invalid transition blocked | Rule/evidence IDs |
| 7 | Reviewer | Decision packet | Approve/reject/reopen | Approval event | No response → no progression | Reviewer state |
| 8 | Molecule roles | Eligible target/mode | Generate and verify | Top-k/rejections | All fail → target feedback | Lineage and typed metrics |
| 9 | Audit Agent | Immutable events | Render report | Audit package | Missing provenance → block | Decisions/failures/budget |
| 10 | Evaluation Plane | Audit package | Run regressions | Eval result | Failed high-risk case blocks readiness | Expected vs observed |

## Alternate / Failure Flows

| Scenario | Trigger | Expected Behavior | Audit/Event |
|---|---|---|---|
| Wrong disease ID | Multiple plausible ontology matches | Stop before target query and request review | `TargetHeld` |
| API outage | Timeout/5xx | Retry within cap, then use disclosed snapshot | `ToolFallbackUsed` |
| Missing clinical evidence | Required source class unavailable | `HOLD`; no molecule transition | `TargetHeld` |
| Indication mismatch | Approval/trial is for another disease | Mark contradiction; downgrade/reject | `ContradictionDetected` |
| Invalid SMILES | RDKit sanitization fails | Reject candidate, retry within generation cap | `CandidateRejected` |
| Predictor unavailable | Package/model smoke fails | Mark metric unavailable; do not guess | `VerificationUnavailable` |
| All candidates fail | No candidate passes hard gates | Return chemical-accessibility feedback; end/alternate target | `TargetHeld` |
| Unsafe route request | Actionable synthesis details requested | Suppress and require safety review | `SafetyBlocked` |
| Budget exceeded | Call/time/compute cap crossed | Stop branch and report partial state | `RunBudgetExceeded` |

## Five-Minute Demo Script

| Time | Screen/Action | Narration | Evidence Shown | Risk Control Shown | Backup |
|---|---|---|---|---|---|
| 0:00–0:35 | Enter IBD and start pinned replay | “We test whether an attractive target survives criticism.” | Run mode, Git SHA, snapshot date | Budget and replay mode | Pre-recorded artifact package |
| 0:35–1:20 | Target/evidence view | “TYK2 looks tractable and has an approved drug.” | Open Targets/ChEMBL IDs | Score is not confidence | Static evidence cards |
| 1:20–2:20 | Contradiction critic | “Approval is for psoriasis; the IBD trials failed.” | Trial/publication evidence | Indication-specific gate | Pinned claim ledger |
| 2:20–2:55 | Decision card | “The agent rejects the premise and blocks molecule work.” | `REJECT`, rules, uncertainty | Human review and blocked transition | Recorded decision event |
| 2:55–3:35 | Inject API 5xx | “The run recovers without fabricating data.” | Retry/fallback event | Fail closed if no snapshot | Fixture-based failure |
| 3:35–4:20 | Positive branch contract | “A different target must pass the same gate before chemistry.” | Eligibility state and molecule gates | Proxy/prediction labels; top-5 synthesis | `METHOD_ONLY` artifact |
| 4:20–5:00 | Audit/eval dashboard | “We expose evidence, decisions, failures, and resource use—not hidden reasoning.” | Golden-case result, budget, provenance | Safety case and approval log | Static report |
