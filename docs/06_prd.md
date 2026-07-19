# 06 PRD

## Artifact Metadata

- Owner: LSB-afk / project team
- Last updated: 2026-07-19
- Stage: discovery

## 1. Product Summary

H2L-Forge is an evidence-critical research decision-support agent. It normalizes a disease, retrieves and versions target/clinical/molecular evidence, searches for contradictions, emits an auditable `ADVANCE/HOLD/REJECT` decision, and only then permits a bounded molecule workflow. The preliminary MVP proves the design; the final MVP must replay the TYK2/IBD rejection and one separately qualified positive molecule branch.

## 2. Users and Jobs

| User | Job | Current Pain | Desired Outcome | Surface |
|---|---|---|---|---|
| Translational researcher | Review disease-target hypotheses | Evidence is fragmented and positive signals dominate | Defensible go/hold/reject packet | Evidence/decision workspace |
| Medicinal chemist | Qualify a target and candidate set | Target premise and molecule metrics are disconnected | Eligible target, bounded candidates, rejection reasons | Molecule workspace |
| Domain reviewer | Approve scientific progression | Hard to audit how an AI reached a recommendation | Evidence, rule, uncertainty, and override log | Approval queue |
| Judge/maintainer | Verify autonomy, tools, safety, and reproducibility | Demos hide failures and depend on live APIs | Deterministic replay with visible decision trace | Demo/audit dashboard |

## 3. Goals

| Goal | Metric or Demo Proof | Priority |
|---|---|---|
| Catch indication-specific false premises | TYK2/IBD case yields `REJECT` or reviewed `HOLD`, never auto-advance | P0 |
| Show bounded autonomous recovery | Injected API/SMILES/evidence conflicts produce correct next action | P0 |
| Keep every final claim traceable | 100% final claims/top-k rows have evidence and tool/version metadata | P0 |
| Demonstrate offline reliability | Five replay runs complete without live external APIs | P0 |
| Make resource use visible | Calls, cache hits, latency, retries, and synthesis tier recorded | P1 |
| Prove value honestly | One manual-vs-agent workflow measured three times | P1 |

## 4. Non-Goals

| Non-Goal | Reason | Revisit Trigger |
|---|---|---|
| Clinical recommendation | Not validated or authorized | Production governance and validation |
| Wet-lab proof | Outside MVP | Confirmed partner |
| Universal disease coverage | Four-week scope | Targeted MVP passes |
| Full autonomous synthesis | Safety and infrastructure | Approved controlled environment |
| New molecule therapeutic efficacy claim | No wet-lab and positive target not yet selected | Validated assay/model and reviewer approval |

## 5. User Scenarios

| Scenario | Actor | Trigger | Happy Path | Failure/Escalation |
|---|---|---|---|---|
| TYK2 contradiction demo | Researcher | Enters IBD | Agent finds attractive signals, then indication-specific failures and rejects/holds | Missing clinical source → `HOLD` and evidence request |
| Positive target review | Researcher/reviewer | Selects candidate target | Evidence gate passes, reviewer approves molecule eligibility | Contradiction → `REJECT`; insufficient assay data → `HOLD` |
| Molecule method run | Engineer | Runs `METHOD_ONLY` | Toolchain produces labeled non-therapeutic metrics | Any claim of efficacy is blocked |
| API outage | Judge | Live source returns 5xx | Pinned snapshot used and fallback is shown | Missing snapshot → fail closed with report |
| Unsafe synthesis request | User | Requests actionable route | Feasibility signal only; disclosure gate | Safety reviewer escalation |

## 6. Product Surfaces

| Surface | Primary User | Job | Core Screens | Data Access | Actions | Risks | MVP? |
|---|---|---|---|---|---|---|---|
| Intake/Plan | Researcher | Define disease and constraints | Disease ID, run mode, budget | Public identifiers | Start bounded run | Wrong disease ID | Yes |
| Evidence/Claims | Researcher | Inspect support and contradiction | Claim ledger, source cards | Public API/snapshots | Mark missing/conflict | Citation drift | Yes |
| Decision | Reviewer | Approve target state | `ADVANCE/HOLD/REJECT` card | All evidence | Approve/reject/reopen | Automation bias | Yes |
| Molecule | Chemist | Review eligible candidates | Lineage, metrics, gate reasons | Chemical structures/tools | Re-rank/reject | Overclaim/dual use | Yes, after positive target |
| Audit/Replay | Judge | Verify run | Timeline, tool events, budget, failures | Run artifacts | Replay/export report | Hidden state | Yes |
| Eval | Maintainer | Run regression | Case results, rubric gaps | Fixtures/artifacts | Compare versions | Score gaming | Yes |

## 7. Core Features

| Feature | User | Trigger | Input | Output | Success Criteria | Problem Trace | Demoable |
|---|---|---|---|---|---|---|---|
| F-01 Snapshot evidence intake | Researcher | Disease accepted | Disease ID, source policy | Validated evidence records | IDs/hashes/timestamps complete | Fragmented evidence | Yes |
| F-02 Clinical contradiction critic | Researcher/reviewer | Claims ready | Claim ledger | Contradictions and recommendation | TYK2 case correct | Positive-signal bias | Yes |
| F-03 Target decision gate | Reviewer | Critic complete | Evidence + rules | State + approval | No invalid molecule transition | Bad premise propagation | Yes |
| F-04 Resilient tool executor | Judge/engineer | Tool request | Budget + cache policy | Tool event/result/fallback | Bounded retries and replay | API fragility | Yes |
| F-05 Molecule qualification | Chemist | Target eligible or `METHOD_ONLY` | Seed/candidates | Lineage, metrics, rejects | Top-k valid/provenanced; claims calibrated | Disconnected chemistry | Conditional |
| F-06 Audit report | Judge/reviewer | Terminal state | Run artifacts | Decision/failure/resource report | Complete trace, no hidden CoT | Opaque agent output | Yes |
| F-07 Evaluation plane | Maintainer | Artifact change | Golden cases/rubric | Pass/warn/fail + backlog | High-risk cases all pass | Unmeasured quality | Yes |

## 8. Data and System Dependencies

| Dependency | Purpose | Constraint | Fallback |
|---|---|---|---|
| Open Targets | Disease-target evidence | Score is not confidence | Pinned response + source disclosure |
| ChEMBL | Indications, assays, molecules | Heterogeneous data/API outage | Pinned normalized subset |
| ClinicalTrials.gov/publications | Indication-specific outcomes | Entity/trial matching | Manual evidence packet |
| RDKit | Structure validation/descriptors | Version/config drift | Version-pinned deterministic replay |
| ADMET-AI, planned | Pretrained ADMET inference | Runtime/license/domain shift unverified | Explicitly limited RDKit-only report |
| SA score/RAscore, planned | Fast synthesis screen | RAscore runtime unverified | SA score |
| AiZynthFinder, optional | Top-5 route feasibility | Expensive setup/runtime | Omit route; retain proxy |

## 9. Risks and Controls

| Risk | Scenario | Control | Residual Risk |
|---|---|---|---|
| Scientific overclaim | Proxy called activity | Typed claim labels and report lint | Model calibration remains limited |
| Wrong target progression | Strong association hides failed trials | Disconfirmation search + approval | New/conflicting evidence |
| Stale evidence | Cached demo snapshot | Visible date/hash and refresh warning | Source changes after snapshot |
| API outage | Live request fails | Bounded retry then cache | Missing fixture |
| Unsafe chemistry detail | Route requested | Feasibility-only default + safety approval | Dual-use interpretation |
| Evaluation gaming | Score agent biases decisions | Separate read-only evaluation plane | Rubric design bias |

## 10. MVP Scope

- IBD disease normalization and evidence snapshot.
- TYK2/deucravacitinib indication mismatch and failed-trial rejection demo.
- `ADVANCE/HOLD/REJECT` state machine, bounded retry, audit logs, and five-minute offline replay.
- Positive molecule branch only after a separate target passes the same evidence gate.
- Molecule gates: RDKit validity; measured/predicted/proxy labeling; planned ADMET-AI; SA/RAscore bulk; optional AiZynthFinder top 5.
- Human approval and bounded report export.

## 11. Future Scope

- Additional diseases and calibrated target ranking.
- Validated scaffold-split QSAR and uncertainty calibration.
- Production identity/access, signed audit logs, source-license automation.
- Wet-lab or partner validation.

## Definition of Done

- [x] Every feature traces to the CPS.
- [x] MVP and future scope are separated.
- [x] Risks have controls.
- [ ] Positive target is evidence-qualified.
- [ ] Runtime dependencies and replay are implemented.
