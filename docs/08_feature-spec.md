# 08 Feature Specification

## Artifact Metadata

- Owner: LSB-afk / project team
- Last updated: 2026-07-19

## Feature Index

| Feature | Status | User | Trace to Problem | Demoable | Eval Case | Risk Control |
|---|---|---|---|---|---|---|
| F-01 Snapshot evidence intake | Designed | Researcher | Fragmented/unreliable evidence | Yes | GC-001, GC-003, GC-010 | ID/schema/hash/freshness rules |
| F-02 Clinical contradiction critic | Designed | Researcher/reviewer | Positive-signal bias | Yes | GC-002, GC-009 | Required disconfirmation pass |
| F-03 Target decision gate | Designed | Reviewer | Bad premise enters molecule work | Yes | GC-009 | State machine + approval |
| F-04 Resilient tool executor | Designed | Judge/engineer | API/demo failure | Yes | GC-010 | Bounded retry + snapshot |
| F-05 Molecule qualification | Blocked on positive target | Chemist | Unvalidated/overclaimed candidates | Conditional | GC-004, GC-005, GC-011 | Deterministic hard gates |
| F-06 Audit report | Designed | Judge/reviewer | Opaque agent output | Yes | GC-007, GC-012 | Immutable event rendering |
| F-07 Evaluation plane | Designed | Maintainer | Quality/score drift | Yes | All | Read-only authority |

## Agent Capability Cards

### Agent Capability: Supervise a Bounded Run

| Field | Content |
|---|---|
| Trigger | Validated intake creates a run |
| Inputs | Goal, mode, constraints, tool/time/call budget |
| Context Sources | Harness rules, state machine, prior events |
| Judgment | Next valid step or terminal state, with rule IDs |
| Possible Actions | Route role, retry, use fallback, hold, stop, request approval |
| Forbidden Actions | Skip state gates, exceed limits silently, alter evidence |
| Verification | Decision Engine validates transition and budget |
| Approval Needed? | Target advancement, final candidate export, synthesis disclosure |
| Audit Events | `RunPlanned`, `RunBudgetExceeded`, transition events |
| Failure Modes | Infinite loop, invalid transition, evaluator influence |
| Eval Cases | GC-008, GC-010 |

### Agent Capability: Collect Snapshot-First Evidence

| Field | Content |
|---|---|
| Trigger | Disease/target query is planned |
| Inputs | Normalized query, source allowlist, freshness/cache policy |
| Context Sources | Open Targets, ChEMBL, ClinicalTrials.gov, PubMed/Europe PMC |
| Judgment | Evidence is valid, conflicting, missing, or stale |
| Possible Actions | Call live, load snapshot, refine query, mark unavailable |
| Forbidden Actions | Invent IDs/counts, hide cache use, treat score as confidence |
| Verification | Schema, ID, timestamp, query/response hash |
| Approval Needed? | Manual source substitution for a final claim |
| Audit Events | `ToolCalled`, `ToolFallbackUsed`, `EvidenceCollected` |
| Failure Modes | API 5xx, schema change, indication mismatch |
| Eval Cases | GC-001, GC-003, GC-010 |

### Agent Capability: Challenge a Target Hypothesis

| Field | Content |
|---|---|
| Trigger | Initial claim ledger is complete |
| Inputs | Disease context, target hypothesis, supporting evidence |
| Context Sources | Indication records, failed/successful trials, mechanisms, assay coverage |
| Judgment | `ADVANCE`, `HOLD`, or `REJECT`; uncertainty; missing evidence |
| Possible Actions | Seek contradiction, downgrade, reject, request evidence, recommend review |
| Forbidden Actions | Search only for support, transfer approval across indications, call association score confidence |
| Verification | Required indication and clinical checks recorded |
| Approval Needed? | `ADVANCE` always; reopening `REJECT` requires new evidence |
| Audit Events | `ContradictionDetected`, `TargetHeld`, `TargetRejected` |
| Failure Modes | Cherry-picking, source conflict, trial/entity mismatch |
| Eval Cases | GC-002, GC-009 |

### Agent Capability: Plan Molecule Exploration

| Field | Content |
|---|---|
| Trigger | Target is `MOLECULE_ELIGIBLE` or run is `METHOD_ONLY` |
| Inputs | Eligible target, seed records, objective, hard gates, budget |
| Context Sources | ChEMBL records and verified molecule lineage |
| Judgment | Candidate generation/retrieval action; never efficacy |
| Possible Actions | Retrieve seeds, generate constrained variants, stop, return target feedback |
| Forbidden Actions | Run on `HOLD/REJECT`, label proxy as activity, generate unbounded candidates |
| Verification | Eligibility, canonical parent/child lineage, generation cap |
| Approval Needed? | Final top-k promotion/export |
| Audit Events | `CandidateGenerated`, `CandidateRejected` |
| Failure Modes | Invalid rate, no active data, mode confusion |
| Eval Cases | GC-004, GC-011 |

### Agent Capability: Verify Chemistry and Feasibility

| Field | Content |
|---|---|
| Trigger | Evidence ID or candidate requires deterministic validation |
| Inputs | IDs, SMILES, tool parameters, model/proxy policy |
| Context Sources | RDKit; planned ADMET-AI; SA/RAscore; optional AiZynthFinder |
| Judgment | Typed pass/warn/fail per gate |
| Possible Actions | Reject, score, label unavailable, escalate |
| Forbidden Actions | Guess missing metric, run AiZynthFinder beyond top 5, hide model/proxy type |
| Verification | Tool version, inputs, values, response hash |
| Approval Needed? | Overrides and synthesis detail |
| Audit Events | `VerificationCompleted`, `CandidateRejected` |
| Failure Modes | Dependency unavailable, domain shift, timeout |
| Eval Cases | GC-004, GC-005, GC-006, GC-011 |

### Agent Capability: Render an Auditable Report

| Field | Content |
|---|---|
| Trigger | Run reaches a terminal/review state |
| Inputs | Immutable manifests, evidence, decisions, failures, approvals, budgets |
| Context Sources | Local artifact store only |
| Judgment | Report complete or blocked for missing provenance/safety |
| Possible Actions | Render decision card, block, request citation repair, redact |
| Forbidden Actions | Add new scientific claims, expose hidden chain-of-thought, omit failures |
| Verification | Claim-to-evidence coverage and language lint |
| Approval Needed? | External export |
| Audit Events | `ReportRendered`, `ReportBlocked`, `ReportExported` |
| Failure Modes | Missing citation, unsafe detail, stale snapshot disclosure |
| Eval Cases | GC-006, GC-007, GC-012 |

## Acceptance Criteria

### F-02 Clinical contradiction critic

- [ ] TYK2/IBD case retrieves or replays the three cited failed phase-2 programs.
- [ ] The decision explicitly separates psoriasis approval from IBD evidence.
- [ ] The target cannot auto-advance.
- [ ] Evidence IDs, URLs, dates, and hashes are present.
- [ ] Removing the critic worsens contradiction detection in a documented ablation.

### F-04 Resilient tool executor

- [ ] Timeout/5xx retries are bounded by the run manifest.
- [ ] A valid pinned snapshot produces the same normalized scientific payload.
- [ ] Cache/live mode and response hash are visible.
- [ ] Missing live and snapshot evidence fails closed.

### F-05 Molecule qualification

- [ ] Entry requires `MOLECULE_ELIGIBLE` or `METHOD_ONLY`.
- [ ] Top-k RDKit validity and provenance are 100%.
- [ ] Activity is labeled measured, predicted, proxy, or unknown.
- [ ] ADMET-AI is used only after version-pinned smoke validation.
- [ ] SA/RAscore is applied before optional top-5 AiZynthFinder.
- [ ] Unsafe/failed candidates are retained in the failure ledger.

### F-06 Audit report

- [ ] Shows plan steps, tool calls, evidence, rules, decision, uncertainty, approval, and failures.
- [ ] Does not display hidden chain-of-thought.
- [ ] Contains no unsupported final claim.
- [ ] Discloses snapshot dates, missing validations, and demo-vs-production limits.

## Evaluation-Plane Authority

The Score Improvement/Evaluation Agent may read artifacts, score rubrics, and propose backlog items. It cannot alter evidence, target decisions, molecule ranks, approval state, or report content without a separately reviewed change.
