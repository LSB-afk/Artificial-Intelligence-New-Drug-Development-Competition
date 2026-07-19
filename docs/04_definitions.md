# 04 Definitions

## Artifact Metadata

- Owner: LSB-afk / project team
- Last updated: 2026-07-19

## Canonical Terms

| Term | Definition | Examples | Not This | Owner | Used In |
|---|---|---|---|---|---|
| Run | One bounded execution with a manifest, budget, inputs, events, and terminal status | IBD replay run | A free-form chat session | Supervisor | Architecture, flow |
| Evidence Record | Versioned observation with source, ID/URL, query, retrieval time, hash, and stance | Trial result contradicts a claim | An uncited summary | Evidence Scout | Claim ledger |
| Claim | A testable proposition linked to supporting, contradicting, or missing evidence | “TYK2 is suitable for IBD progression” | Generic narrative | Clinical Critic | Report |
| Indication Match | Explicit relationship between disease context and the indication of a drug/trial/evidence item | Psoriasis ≠ IBD | Same target name | Clinical Critic | Target gate |
| Target Hypothesis | Disease-target-mechanism proposition under review | IBD–TYK2 hypothesis | Final clinical truth | Hypothesis Planner | Domain model |
| Target Decision | `ADVANCE`, `HOLD`, or `REJECT` plus rule, evidence, uncertainty, and reviewer state | TYK2 → `REJECT` for IBD demo | Numeric association score | Supervisor | Flow |
| Contradiction | Evidence that materially weakens or invalidates a claim in the current indication | Failed IBD trials | A merely low association rank | Clinical Critic | Evals |
| Molecule Eligibility | Permission to enter molecule work after target `ADVANCE` and review | Alternative target approved | TYK2 rejection demo | Human reviewer | State machine |
| METHOD_ONLY | Chemistry tool qualification without a therapeutic/indication claim | Pipeline smoke test on a reference ligand | Positive lead proposal | Engineering lead | Demo/handoff |
| Measured Activity | Curated experimental assay observation with assay metadata | pChEMBL value with assay ID | Similarity or model score | Evidence Scout | Reports |
| Predicted Activity | Output of a versioned model with validation metadata | QSAR prediction | Experimental fact | Deterministic Verifier | Molecule table |
| Activity Proxy | Heuristic correlated signal explicitly labeled as non-activity | Tanimoto similarity | Binding claim | Molecule Planner | Molecule table |
| Failure Ledger | First-class record of rejected hypotheses/candidates and causes | Indication mismatch, invalid SMILES | Deleted errors | Audit Agent | Report/evals |
| Decision Trace | Observable evidence, rules, actions, and outcome for a transition | Evidence IDs + applied gate | Hidden chain-of-thought | Audit Agent | UI |

## Concept Hierarchy

```text
H2L-Forge Run
  ├── Disease Context
  ├── Target Hypothesis
  │    ├── Claim/Evidence Ledger
  │    ├── Contradiction Review
  │    └── Target Decision (ADVANCE | HOLD | REJECT)
  ├── Molecule Workflow (ADVANCE or METHOD_ONLY only)
  │    ├── Seed Set
  │    ├── Candidate Lineage
  │    └── Deterministic Verification
  └── Audit Package
       ├── Decision Trace
       ├── Failure Ledger
       ├── Approval Log
       └── Budget Metrics
```

## Anti-Synonyms

| Canonical Term | Do Not Use | Reason |
|---|---|---|
| Target Decision | “AI confidence score” | Decision is evidence/rule based, not calibrated probability by default |
| Activity Proxy | “Predicted activity” | A similarity heuristic is not a model prediction |
| Candidate Molecule | “Drug” or “lead” | No experimental validation |
| Decision Trace | “Chain-of-thought” | Product auditability does not require private reasoning disclosure |
| REJECT | “Failure of the agent” | Correct rejection is a successful scientific outcome |

## Naming Propagation

| Term | UI Label | API/Type Name | Stored Object | Eval Name |
|---|---|---|---|---|
| Target Decision | Target decision | `TargetDecision` | `decision_events.jsonl` | `targetDecision` |
| Evidence Record | Evidence | `EvidenceRecord` | `claim_ledger.jsonl` | `evidenceGrounding` |
| Molecule Candidate | Candidate | `MoleculeCandidate` | `molecule_lineage.parquet` | `moleculeGate` |
| Run | Run | `RunManifest` | `run_manifest.json` | `replayRun` |
