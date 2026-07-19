# 07 Architecture

## Artifact Metadata

- Owner: LSB-afk / project team
- Last updated: 2026-07-19
- Stack: Python; provider-neutral tool-calling model; local deterministic chemistry; snapshot-first public APIs
- Status: discovery architecture; runtime dependencies not yet smoke-tested

## Architecture Summary

H2L-Forge separates the scientific runtime plane from the evaluation plane. Six runtime roles execute a bounded state machine; deterministic tools validate identifiers and chemistry; every external result becomes a versioned evidence record. A read-only evaluation plane scores artifacts after the scientific decision and cannot change target or molecule state.

```text
UI / CLI
  -> Supervisor & Budget Governor
      -> Evidence Scout -> Source Adapters -> Snapshot Store
      -> Clinical Contradiction Critic -> Claim Ledger
      -> Molecule Planner (ADVANCE or METHOD_ONLY only)
      -> Deterministic Verifier
      -> Audit / Report Agent
  -> Decision + Approval Engine
  -> Event / Artifact Store

Read-only Evaluation Plane
  -> golden cases + rubric + failure injection
  -> eval results and improvement backlog
```

## Components

| Component | Responsibility | Inputs | Outputs | Owner | Runtime |
|---|---|---|---|---|---|
| Supervisor/Budget Governor | Plan, route roles, enforce state/retry/call/time caps | User goal, run manifest, events | Next bounded action, terminal state | Agent runtime | LLM + rules |
| Evidence Scout | Normalize disease/targets and collect source records | Disease/target queries | Validated evidence records | Agent runtime | LLM tool selection + adapters |
| Clinical Contradiction Critic | Seek indication mismatch, failed trials, conflicting mechanisms | Claims + evidence | Contradictions, `ADVANCE/HOLD/REJECT` recommendation | Agent runtime | LLM judgment constrained by rules |
| Molecule Planner | Retrieve seed set and propose constrained candidates | Eligible target or `METHOD_ONLY` input | Candidate lineage | Agent runtime | LLM planning + local generator |
| Deterministic Verifier | Validate IDs/SMILES and calculate typed metrics/gates | Evidence/candidates | Verification results and hard failures | Engineering | Local code/models |
| Audit/Report Agent | Render decision, failure, resource, approval, and limitations | Approved event stream | Decision card and report | Agent runtime | Template-constrained LLM |
| Decision/Approval Engine | Enforce transition and reviewer gates | Recommended transition, evidence, approval | Committed state/event | Engineering | Deterministic |
| Source Adapters | Call APIs or load pinned snapshots | Typed query, cache policy | Normalized response + hash | Engineering | Python |
| Artifact Store | Retain manifests, snapshots, ledgers, events, reports | Run outputs | Replayable artifact package | Engineering | Local files/object store |
| Evaluation Plane | Run cases, inject failures, score rubric, propose backlog | Versioned artifacts | Eval results | Test engineering | Read-only to runtime state |

## Data Flow

1. Intake validates run mode (`SCIENTIFIC`, `REJECTION_DEMO`, or `METHOD_ONLY`), disease text, and budget.
2. The Supervisor writes `run_manifest.json` with Git SHA, model/tool versions, seed, and limits.
3. Evidence Scout normalizes the disease and calls source adapters.
4. Each adapter tries an allowed live call or a pinned snapshot according to policy, validates schema/ID, hashes the response, and appends `tool_events.jsonl`.
5. Evidence becomes `EvidenceRecord` rows and is attached to claims in `claim_ledger.jsonl`.
6. Clinical Critic performs a required disconfirmation pass and emits a typed recommendation.
7. The Decision Engine commits `ADVANCE`, `HOLD`, or `REJECT`; high-risk progression waits for human approval.
8. Only `ADVANCE` or explicit `METHOD_ONLY` enters the molecule path.
9. Deterministic Verifier records validity, measured/predicted/proxy labels, ADMET, alerts, and synthesis tiers. Failed candidates enter the failure ledger.
10. Audit/Report Agent renders only committed events and verified records.
11. Evaluation Plane reads the immutable package, executes cases, and writes results without changing scientific state.

## Agent Execution Contract

| Step | Component/Agent | Input | Action | Output | Verification |
|---|---|---|---|---|---|
| 1 | Supervisor | Goal + limits | Produce bounded plan | `RunPlanned` | Step/call/time caps exist |
| 2 | Evidence Scout | Disease context | Retrieve support and clinical context | Evidence records | ID/schema/hash checks |
| 3 | Clinical Critic | Claim ledger | Search for disconfirmation and indication mismatch | Recommendation | Required source classes attempted |
| 4 | Decision Engine | Recommendation + rules | Commit state or request review | Decision event | Transition contract |
| 5 | Molecule Planner | Eligible target/mode | Retrieve seeds and generate lineage | Candidates | Eligibility and mode |
| 6 | Deterministic Verifier | Candidates | Calculate/gate | Scores/rejections | Versioned tool output |
| 7 | Audit/Report | Immutable events | Render decision trace | Report | Provenance and language lint |

## Security and Trust Boundaries

| Boundary | Data Crossing | Control | Audit |
|---|---|---|---|
| User → runtime | Disease text, constraints, optional SMILES | Input schema, mode, safety classification | `RunCreated` |
| Runtime → external public API | Public identifiers and queries | Allowlist, timeout, no secrets/PII, terms review | `ToolCalled` |
| Runtime → external model | Bounded structured context; no raw private reasoning | Data minimization, provider policy, prompt/version log | `ModelCalled` |
| Agent → deterministic tools | SMILES, IDs, parameters | Typed schemas, version pinning, sandbox/resource caps | `VerificationCompleted` |
| Agent recommendation → state | Decision + evidence IDs | Deterministic transition and approval gate | `TargetAdvanced/Held/Rejected` |
| Report → user/export | Evidence, metrics, concise rationale | Claim lint, redaction, safety approval | `ReportExported` |
| Evaluation → runtime | None | Read-only artifacts; no mutation token | `EvalCompleted` |

## External Services / APIs

| Service | Purpose | Data Sent | Data Received | License / Constraint | Fallback | Audit Event |
|---|---|---|---|---|---|---|
| Open Targets | Disease-target evidence/tractability | Ontology/target IDs | Associations and evidence | Terms/schema/freshness review; score is not confidence | Pinned snapshot | `EvidenceCollected` |
| ChEMBL | Indications, assays, activities, structures | Target/molecule/query filters | Curated records | Assay heterogeneity and outages; terms review | Pinned normalized subset | `EvidenceCollected` |
| ClinicalTrials.gov | Indication-specific study status/results | Disease/drug/target query | Trial metadata/results links | Entity matching and update lag | Cited publication/manual packet | `EvidenceCollected` |
| PubMed/Europe PMC | Literature verification | Search terms/IDs | Metadata/abstract links | Copyright and retrieval limits | Citation-only manual packet | `EvidenceCollected` |
| Tool-calling LLM | Planning, criticism, bounded report drafting | Structured evidence summaries | Typed actions/text | Provider, price, privacy TBD | Deterministic stop/manual flow | `ModelCalled` |
| ADMET-AI, planned | Pretrained ADMET prediction | Candidate SMILES | Typed predictions | Version/license/domain shift unverified | Limited RDKit-only report | `VerificationCompleted` |
| RAscore, planned | Fast synthesis feasibility proxy | Candidate SMILES | Proxy score | Runtime/model version unverified | SA score | `VerificationCompleted` |
| AiZynthFinder, optional | Final top-5 route feasibility | Top-5 SMILES | Route-found/score summary | Heavy setup/runtime; no actionable route by default | Proxy only | `VerificationCompleted` |

## Storage, Retention, and Deletion

| Data | Store | Retention | Delete/Redact | Owner |
|---|---|---|---|---|
| Run manifest | `artifacts/<run_id>/run_manifest.json` | Through submission + reproducibility window | Remove secrets/local paths | Engineering |
| Minimal evidence fixtures/manifests | `tests/fixtures/` or lawful artifact package | Versioned | Respect source terms; avoid prohibited redistribution | Project lead |
| Tool events/claim/decision/failure logs | `artifacts/<run_id>/` | Through audit/review | Redact tokens and provider request bodies | Engineering |
| Molecule lineage | `artifacts/<run_id>/molecule_lineage.parquet` | Through review | Suppress unsafe route details | Safety reviewer |
| Hidden model reasoning | Not stored | None | Always exclude | Project lead |
| Final reports/eval results | `reports/`, `evals/results/` | Versioned submission evidence | Remove secrets | Project lead |

The repository currently ignores broad artifact/data paths. Implementation must track lawful small fixtures or manifests in a dedicated allowlisted location rather than assuming ignored runtime data proves reproducibility.

## Logging and Audit

| Event | Trigger | Required Fields | Reviewer |
|---|---|---|---|
| `RunPlanned` | Plan accepted | run_id, mode, limits, versions | Maintainer |
| `ToolCalled`/`ToolFallbackUsed` | Tool request/fallback | query hash, cache/live, status, response hash, latency | Maintainer |
| `EvidenceCollected` | Evidence validated | source, ID/URL, observed_at, hash, indication | Domain reviewer |
| `ContradictionDetected` | Claim weakened | claim ID, evidence IDs, rule | Domain reviewer |
| `TargetAdvanced/Held/Rejected` | State committed | previous/new state, rules, evidence, approval | Domain reviewer |
| `CandidateRejected` | Hard gate fails | candidate, metric/gate, value, tool version | Chemist |
| `ApprovalRecorded` | Human decision | reviewer, action, result, evidence | Project lead |
| `RunBudgetExceeded` | Cap crossed | metric, limit, observed, terminal state | Engineering |

## Failure Handling

| Failure | Detection | User/System Response | Fallback | Severity |
|---|---|---|---|---|
| API timeout/5xx | Adapter status/timeout | Retry with backoff up to configured cap | Pinned snapshot | Medium; High if no snapshot |
| Schema/ID mismatch | Typed validation | Reject record and request alternate query | Manual evidence packet | High |
| Conflicting clinical evidence | Claim ledger contradiction | `HOLD` or `REJECT`; reviewer packet | None | High |
| Missing positive target | No hypothesis reaches `ADVANCE` | End scientific branch honestly | `REJECTION_DEMO`; no molecule claim | Medium |
| Invalid SMILES | RDKit sanitization | Reject and bounded regeneration | Stop after cap | Medium |
| Predictor unavailable | Import/smoke failure | Mark metric unavailable | Limited report; do not impute | High |
| All molecules fail | Hard-gate summary | Lower chemical-accessibility status; return to target review | Choose another approved target after review | Medium |
| Budget exceeded | Event metrics | Stop current branch and report partial evidence | Cached replay | Medium |
| Unsafe synthesis request | Policy classifier/rule | Suppress detail and escalate | Feasibility-only output | Critical |

## Demo vs Production Differences

| Area | Demo Mode | Production Requirement | Risk |
|---|---|---|---|
| Evidence | Pinned public snapshots + optional refresh | Source governance, freshness SLA, signed provenance | Stale data |
| Identity | Local reviewer label | Authentication, RBAC, signed approvals | Unauthorized override |
| Storage | Local artifact package | Encrypted, access-controlled, retention/deletion | Leakage |
| Models/tools | Version-pinned MVP | Validated deployment, monitoring, calibration | Drift |
| Safety | Bounded output and manual reviewer | Formal dual-use policy and incident response | Misuse |
| Reliability | Five deterministic replays | Availability/error budget and disaster recovery | Demo-only robustness |
