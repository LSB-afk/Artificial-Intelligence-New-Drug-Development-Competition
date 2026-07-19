# 02 CPS

## Artifact Metadata

- Owner: LSB-afk / project team
- Last updated: 2026-07-19
- Source artifacts: `docs/00_source-log.md`, `docs/01_meeting-log.md`

## Context

- The competition requires an agentic drug-development service in the preliminary proposal and a working, transparent demonstration in the final.
- The repository joins autonomous target hypothesis generation with tool-based molecule optimization.
- A current repository audit found a representative failure: an approved psoriasis drug was incorrectly treated as positive evidence for the same target in IBD, despite negative IBD phase-2 results.
- Close systems already automate target discovery and target-to-lead workflows, so a generic multi-agent loop is not a defensible originality claim.
- Public APIs can be unavailable during evaluation; ChEMBL returned HTTP 500 during the latest verification attempt.

## Problem

Early-discovery researchers reviewing a disease-target hypothesis must reconcile association evidence, tractability, indication-specific clinical outcomes, assay availability, and molecule properties across separate tools. Attractive signals can be carried into expensive molecule work before contradictory evidence is noticed, while existing automation often presents positive candidates without a first-class, reproducible record of why a target or molecule should be rejected.

## Solution

H2L-Forge runs a bounded evidence-to-decision loop:

1. Normalize the disease and retrieve dated, hashed evidence snapshots.
2. Build a claim/evidence ledger that separates support, contradiction, and unknowns.
3. Let an indication-aware critic actively search for disconfirming clinical and mechanistic evidence.
4. Decide `ADVANCE`, `HOLD`, or `REJECT` under explicit rules and human approval.
5. Only for `ADVANCE`, retrieve seed ligands and run deterministic validity, activity-proxy/model, ADMET, and two-stage synthesis gates.
6. Feed molecule failure back to target chemical-accessibility status.
7. Produce a decision card, failure ledger, resource log, and reproducible report.

The IBD/TYK2 demo succeeds when the agent rejects or holds the initially attractive premise for the correct indication-specific reason. A separate target may enter the positive molecule branch only after passing the same gate.

## Non-Solutions

| Non-Solution | Why Excluded | Revisit Trigger |
|---|---|---|
| Autonomous clinical or experimental decision-maker | Outputs are research hypotheses and decision support | Validated production governance and domain approval |
| Wet-lab validation | Outside the four-week MVP and available infrastructure | Confirmed partner and protocol |
| Unbounded de novo molecule generation | Weak scientific control and high evaluation cost | Validated activity model and safety program |
| Full retrosynthesis for every candidate | Too slow for the MVP | Measured compute budget supports it |
| Claiming TYK2 is an effective IBD target | Current cited clinical evidence contradicts it | New reviewed evidence |

## Success Evidence

| Evidence | How Observed | Target or Demo Proof |
|---|---|---|
| Scientific self-correction | TYK2 decision event and claim ledger | Correctly identifies indication mismatch and cited IBD failures; no auto-advance |
| Agent autonomy | Failure injection and next-action log | Recovers from API 5xx/invalid SMILES; stops after bounded retries |
| Tool accuracy | ID/schema/hash validation | Core IDs and top-k provenance complete |
| Feasibility | Offline replay and dependency smoke tests | Five deterministic replay runs; planned tools version-pinned |
| Resource efficiency | Tool/cache/budget metrics | Warm replay uses pinned snapshots; AiZynthFinder restricted to top 5 |
| Ethics and transparency | Approval and report gates | No unsupported final claim or actionable hazardous synthesis detail |

## Traceability

| Context | Problem | Solution Mechanism | Evidence |
|---|---|---|---|
| TYK2/IBD premise reversal | Positive-looking evidence can hide indication conflict | Clinical Contradiction Critic + `REJECT` state | GC-002, GC-009 |
| API outage | Live-only demos are fragile | Snapshot-first tool adapter | GC-010 |
| Close prior art | Generic closed loop is not novel | Failure-first ledger and critic ablation | Evaluation rubric |
| Four-week MVP | Unbounded chemistry is infeasible | Budget governor and two-stage gates | Architecture and budget metrics |

## Definition of Done

- [x] Context is repository- and competition-specific.
- [x] Problem names actor, situation, and cost/risk.
- [x] Solution is an observable mechanism.
- [x] Non-solutions prevent scope creep.
