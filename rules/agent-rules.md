# Agent Rules

## Required Agent Loop

Every capability must declare:

1. trigger and run state,
2. typed inputs,
3. allowed context sources,
4. judgment output and uncertainty,
5. possible actions,
6. forbidden actions,
7. deterministic verification,
8. approval/escalation,
9. audit event,
10. retry/budget limits,
11. linked eval cases.

## Runtime Authority

| Role | May Decide | May Not Do |
|---|---|---|
| Supervisor/Budget Governor | Next valid step, retry/fallback/stop | Alter evidence or bypass state/approval |
| Evidence Scout | Evidence validity/missing status | Make final target decision or invent records |
| Clinical Contradiction Critic | Recommendation and contradiction status | Approve progression |
| Molecule Planner | Bounded candidate plan | Run on `HOLD/REJECT` or claim efficacy |
| Deterministic Verifier | Typed metric/gate result | Guess unavailable outputs |
| Audit/Report Agent | Completeness/block/export draft | Add new scientific claims |
| Evaluation Agent | Score artifacts and propose backlog | Change scientific state, ranks, or approvals |

## Target Progression

- The critic must attempt indication-specific disconfirmation before any target decision.
- `ADVANCE` requires evidence coverage, no disqualifying contradiction, and domain approval.
- `HOLD` and `REJECT` cannot transition to molecule eligibility.
- TYK2/deucravacitinib in IBD defaults to `REJECTION_DEMO` based on current evidence.
- Reopening a rejected target requires new evidence and a recorded reviewer decision.

## Molecule Progression

- Molecule work requires `MOLECULE_ELIGIBLE` or explicit `METHOD_ONLY`.
- `METHOD_ONLY` outputs cannot make disease efficacy or lead claims.
- Invalid SMILES are rejected before scoring.
- Similarity is an activity proxy unless a validated model/assay supports a stronger type.
- ADMET-AI and RAscore cannot be described as implemented until smoke-tested and versioned.
- Apply SA/RAscore to the bulk set; optional AiZynthFinder is restricted to final top 5.
- All rejected candidates and causes remain in the failure ledger.

## Retry and Budget

- Retry only recoverable errors and use bounded exponential backoff.
- The run manifest declares maximum tool calls, attempts, wall time, candidate count, and optional synthesis calls.
- After the cap, stop or use an allowed pinned fallback; never continue silently.
- Identical failed queries must not be retried without a changed condition.

## Forbidden Claims and Actions

- Do not call a generic target-to-lead loop novel or unique.
- Do not transfer a drug’s approval evidence across indications.
- Do not call association score confidence.
- Do not call a generated candidate a drug/lead or similarity predicted activity.
- Do not fabricate source IDs, counts, tool success, or unavailable metrics.
- Do not provide actionable hazardous synthesis instructions.
- Do not expose hidden chain-of-thought; provide a concise evidence/rule/action trace.

## Default Safety Posture

Missing evidence, conflicting evidence, unclear permission, unavailable verifier, unsafe detail, or invalid transition produces `HOLD`, `REJECT`, or escalation. It never produces silent advancement.
