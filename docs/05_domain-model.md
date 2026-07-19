# 05 Domain Model

## Artifact Metadata

- Owner: LSB-afk / project team
- Last updated: 2026-07-19
- Source artifacts: CPS, principles, definitions

## Entities

| Entity | Description | Key Fields | Relationships | Owner |
|---|---|---|---|---|
| RunManifest | Reproducible execution identity and budget | run_id, git_sha, mode, versions, seed, limits | Owns all run events | Supervisor |
| DiseaseContext | Normalized disease/indication | label, ontology_id, synonyms, evidence | Has target hypotheses | Evidence Scout |
| TargetHypothesis | Disease-target-mechanism proposition | target_id, claim, state, uncertainty | Has claims, decision, molecule eligibility | Hypothesis Planner |
| EvidenceRecord | Source observation | source, external_id, URL, observed_at, hash, stance, indication | Supports/contradicts claims | Evidence Scout |
| ClaimLedger | Claims and linked evidence | claim_id, status, support_ids, contradict_ids | Belongs to hypothesis | Clinical Critic |
| TargetDecision | Progression decision | decision, rule_ids, rationale, reviewer_state | Terminates target review | Supervisor |
| MoleculeCandidate | Generated/retrieved structure and lineage | candidate_id, parent_id, canonical_smiles, mode, state | Has scores and failure record | Molecule Planner |
| VerificationResult | Deterministic tool result | tool, version, metric, value, label, evidence_type | Validates candidate or ID | Deterministic Verifier |
| ToolEvent | External/local tool audit | request_hash, cache_mode, response_hash, latency, status | Belongs to run | Supervisor |
| Approval | Human high-risk decision | action, reviewer, evidence_ids, result, timestamp | Gates progression/export | Human reviewer |
| FailureRecord | Recoverable or terminal failure | category, attempt, cause, next_action, terminal | Links to object/event | Audit Agent |
| EvalResult | Case/rubric outcome | case_id, expected, observed, pass, artifacts | Links run to regression | Evaluation plane |

## States

| Object | State | Allowed Transitions | Blocked Transitions | Audit Required? |
|---|---|---|---|---|
| Run | `CREATED` | `PLANNED` | Direct to `REPORT_READY` | Yes |
| Run | `PLANNED` | `RETRIEVING`, `BLOCKED` | `OPTIMIZING` | Yes |
| Run | `RETRIEVING` | `CRITIQUING`, `RECOVERING`, `BLOCKED` | `REPORT_READY` | Yes |
| Run | `CRITIQUING` | `DECIDED`, `RECOVERING`, `BLOCKED` | Unreviewed `OPTIMIZING` | Yes |
| Run | `DECIDED` | `OPTIMIZING`, `REPORT_READY`, `AWAITING_APPROVAL` | Optimization on `HOLD/REJECT` | Yes |
| Run | `OPTIMIZING` | `VERIFYING`, `RECOVERING`, `BLOCKED` | Candidate export | Yes |
| Run | `VERIFYING` | `AWAITING_APPROVAL`, `REPORT_READY`, `BLOCKED` | Unsafe promotion | Yes |
| Run | `AWAITING_APPROVAL` | `REPORT_READY`, `BLOCKED` | Auto-approval | Yes |
| TargetHypothesis | `PROPOSED` | `EVIDENCE_COLLECTED` | `ADVANCE` | Yes |
| TargetHypothesis | `EVIDENCE_COLLECTED` | `CHALLENGED` | Molecule work | Yes |
| TargetHypothesis | `CHALLENGED` | `ADVANCE`, `HOLD`, `REJECT` | Silent default | Yes |
| TargetHypothesis | `ADVANCE` | `MOLECULE_ELIGIBLE` after approval | Eligibility without reviewer | Yes |
| TargetHypothesis | `HOLD`/`REJECT` | Reopen with new evidence | Molecule eligibility | Yes |
| MoleculeCandidate | `GENERATED` | `VALIDATED`, `REJECTED` | Scoring invalid SMILES | Yes |
| MoleculeCandidate | `VALIDATED` | `SCORED`, `REJECTED` | Top-k without gates | Yes |
| MoleculeCandidate | `SCORED` | `TOP_K`, `REJECTED` | Therapeutic claim | Yes |
| MoleculeCandidate | `TOP_K` | `APPROVED`, `REJECTED` | Export without approval | Yes |

## Events

| Event | Trigger | Minimum Payload | Consumer | Audit/Retention |
|---|---|---|---|---|
| `RunPlanned` | Supervisor sets bounded steps | run_id, mode, limits | All roles | Full run |
| `EvidenceCollected` | Source adapter validates response | source, ID, hash, observed_at | Claim ledger | Full run/report |
| `ContradictionDetected` | Evidence weakens claim | claim_id, evidence_ids, indication | Supervisor/reviewer | Full run/report |
| `TargetAdvanced` | Gate passes and reviewer approves | rule_ids, evidence_ids, approval_id | Molecule workflow | Full run |
| `TargetHeld` | Evidence incomplete/conflicting | missing evidence, next action | Report/retriever | Full run |
| `TargetRejected` | Disqualifying evidence/rule | rule_ids, evidence_ids | Report/evals | Full run/report |
| `ToolFallbackUsed` | Live call fails or budget policy selects cache | tool, failure, snapshot_hash | Audit agent | Full run |
| `CandidateRejected` | Deterministic hard gate fails | candidate_id, gate, values | Molecule planner | Full run/report |
| `ApprovalRecorded` | Human reviews high-risk action | action, result, reviewer | State machine | Full run |
| `RunBudgetExceeded` | Call/time/compute cap reached | metric, cap, observed | Supervisor | Full run |

## Permissions

| Role | Can View | Can Draft | Can Approve | Can Override | Can Export |
|---|---|---|---|---|---|
| Supervisor | All run state | Plans/decisions | No | No | No |
| Evidence Scout | Sources/claims | Evidence records | No | No | No |
| Clinical Critic | Claims/evidence | Contradictions/decision recommendation | No | No | No |
| Molecule Planner | Eligible target and molecule data | Candidates | No | No | No |
| Deterministic Verifier | Tool inputs/results | Verification results | No | No | No |
| Audit/Report Agent | Approved records | Reports | No | No | Draft only |
| Domain Reviewer | All evidence and decisions | Review notes | Target progression | With recorded rationale | Approved report |
| Safety Reviewer | Safety/dual-use fields | Redactions | Synthesis disclosure/export | With recorded rationale | Approved bounded export |
| Evaluation Plane | Read-only artifacts | Eval results/backlog | No | No | Eval report only |

## State Transition Detail

| From | To | Actor/System | Validation | Failure State | Audit Event |
|---|---|---|---|---|---|
| `EVIDENCE_COLLECTED` | `CHALLENGED` | Clinical Critic | Support and disconfirmation search completed | `HOLD` | `ContradictionDetected` if present |
| `CHALLENGED` | `ADVANCE` | Supervisor + Domain Reviewer | Indication match, evidence coverage, no disqualifying contradiction | `HOLD`/`REJECT` | `TargetAdvanced` |
| `CHALLENGED` | `REJECT` | Supervisor | Disqualifying indication-specific evidence | None; reopen only with new evidence | `TargetRejected` |
| `ADVANCE` | `MOLECULE_ELIGIBLE` | Domain Reviewer | Approval record and run mode `SCIENTIFIC` | `HOLD` | `ApprovalRecorded` |
| `GENERATED` | `VALIDATED` | Deterministic Verifier | RDKit sanitization + lineage | `REJECTED` | `CandidateRejected` |
| `TOP_K` | `APPROVED` | Domain + Safety Reviewer | Complete provenance, hard gates, bounded disclosure | `REJECTED` | `ApprovalRecorded` |

## Definition of Done

- [x] Central objects and states are defined.
- [x] Every transition has an actor and validation.
- [x] High-risk transitions require audit and approval.
- [ ] Positive target-specific fields are validated with the selected alternative target.
