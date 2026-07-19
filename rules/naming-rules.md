# Naming Rules

## Canonical Source

Use terms from `docs/04_definitions.md` in code, schemas, UI, reports, and evals.

## Domain Names

- Use `TargetHypothesis`, `TargetDecision`, `EvidenceRecord`, `MoleculeCandidate`, `VerificationResult`, and `RunManifest`.
- Decision enum values are `ADVANCE`, `HOLD`, and `REJECT`.
- Run modes are `SCIENTIFIC`, `REJECTION_DEMO`, and `METHOD_ONLY`.
- Evidence stance values are `SUPPORTS`, `CONTRADICTS`, `NEUTRAL`, and `UNKNOWN`.
- Activity evidence types are `MEASURED`, `PREDICTED`, `PROXY`, and `UNKNOWN`.

## Event Names

Use past-tense domain events:

- `RunPlanned`
- `EvidenceCollected`
- `ContradictionDetected`
- `TargetAdvanced`
- `TargetHeld`
- `TargetRejected`
- `ToolFallbackUsed`
- `CandidateRejected`
- `ApprovalRecorded`
- `RunBudgetExceeded`

## AI/Agent Names

- Runtime roles: `Supervisor`, `EvidenceScout`, `ClinicalContradictionCritic`, `MoleculePlanner`, `DeterministicVerifier`, `AuditReportAgent`.
- The evaluation role is `EvaluationAgent`; it is not a runtime scientific actor.
- Capabilities use verb-object names such as `collectEvidence`, `challengeHypothesis`, `validateCandidate`, and `renderAuditReport`.

## Forbidden or Misleading Names

- Do not name an Open Targets association value `confidence`.
- Do not name a Tanimoto value `activity` or `prediction`.
- Do not call an unvalidated molecule `drug`, `lead`, or `effective_candidate`.
- Do not call a decision trace `chain_of_thought`.
- Avoid generic `Manager`, `Utils`, `Thing`, or `Agent1` names.

## Eval Names

Use scenario-based names such as `indicationMismatchRejectsTarget`, `apiOutageUsesPinnedSnapshot`, and `proxyNeverBecomesActivityClaim`.
