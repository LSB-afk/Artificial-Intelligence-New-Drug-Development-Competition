# Compliance Rules

This is an engineering control set, not legal or clinical advice.

## Product Risk Controls

- Treat all outputs as research decision support, not clinical or experimental authorization.
- Map each high-risk transition to a reviewer, evidence packet, and audit event.
- Disclose privacy, security, copyright/license, hallucination, explainability, responsibility, and dual-use risks.
- Fail closed on missing permission, missing evidence, policy ambiguity, conflicting sources, or unavailable high-risk verification.
- Keep source terms and model/package licenses as explicit production-readiness checks.

## Approval Gate Table

| Action | Risk | Required Reviewer | Evidence Required | Auto-Execute? | Audit Event |
|---|---|---|---|---|---|
| Advance target to molecule eligibility | High | Domain reviewer | Claim ledger, indication/clinical checks, rules | No | `TargetAdvanced`, `ApprovalRecorded` |
| Reopen rejected target | High | Domain reviewer | New evidence and change rationale | No | `TargetReopened` |
| Promote/export top-k candidates | High | Domain + safety reviewer | Full provenance, gates, limitations | No | `ApprovalRecorded`, `ReportExported` |
| Show route feasibility summary | Medium | Safety policy gate | Tool/version, bounded summary | Conditional | `SynthesisSummaryReleased` |
| Show actionable synthesis detail | Critical | Safety reviewer + explicit project policy | Purpose, risk review, evidence | No by default | `SafetyApprovalRecorded` |
| Use manual/unverified source for final claim | High | Domain reviewer | Source copy/URL, reason, validation | No | `EvidenceOverrideRecorded` |
| Change eval threshold | Medium | Maintainer/project lead | Baseline, impact, rationale | No | `EvalThresholdChanged` |

## Fail-Closed Triggers

- Disease/target/indication ambiguity.
- Missing or conflicting clinical evidence.
- Unknown source permission or redistribution terms.
- External API/model/tool unavailable without an allowed fallback.
- Unvalidated predictor used for a high-risk claim.
- Missing provenance or approval.
- Unsafe synthesis/detail request.
- Budget or retry limit exceeded.

## Required Disclosures

Every exported report states:

- snapshot dates and live/cache mode,
- measured/predicted/proxy/unknown status,
- missing runtime or scientific validation,
- human reviewer state,
- that outputs are hypotheses/decision support,
- demo-vs-production differences,
- known data, license, and dual-use limitations.
