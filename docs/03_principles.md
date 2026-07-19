# 03 Principles

## Artifact Metadata

- Owner: LSB-afk / project team
- Last updated: 2026-07-19

## Non-Negotiable Principles

| ID | Principle | Meaning | Enforced By | Reject If |
|---|---|---|---|---|
| P1 | Evidence before progression | Every scientific claim and state transition shows source, observation date, and uncertainty | Claim ledger, report gate, evals | A target or molecule advances on unsupported prose |
| P2 | Indication specificity | Approval or activity in one indication is not evidence for another | Clinical contradiction critic | Drug approval is reused without indication match |
| P3 | Seek disconfirmation | The agent actively searches for conflicting clinical, mechanistic, and assay evidence | Critic capability and TYK2 golden case | Only supporting evidence is retrieved |
| P4 | Fail closed | Missing, conflicting, stale, or unlicensed evidence yields `HOLD`, `REJECT`, or escalation | State machine, compliance rules | Uncertainty silently becomes confidence |
| P5 | Deterministic verification | IDs, chemistry validity, descriptors, gates, and hashes are checked by versioned tools | Tool adapters and verifier | LLM text substitutes for a calculation |
| P6 | Calibrated claim language | Outputs distinguish measured, predicted, proxy, and unknown | Definitions, UI rules, report lint | Similarity is called activity or a generated structure is called a drug |
| P7 | Bounded autonomy | Retries, tool calls, compute, and optimization iterations have declared limits | Budget Governor | Agent loops indefinitely or exceeds budget silently |
| P8 | Human authority for high risk | Target promotion, final candidate export, and synthesis disclosure require review | Approval log and compliance rules | High-risk output auto-executes |
| P9 | Reproducible by default | A run records Git SHA, tool/model versions, seeds, query/response hashes, and cache/live mode | Run manifest and tool events | Results cannot be replayed or attributed |
| P10 | Decision trace, not hidden reasoning | Show inputs, rules, evidence, action, and concise rationale; do not expose hidden chain-of-thought | UI and logging rules | “Transparency” is implemented as raw private reasoning |

## Tradeoffs

| Tradeoff | Preferred Direction | Reason | Exception |
|---|---|---|---|
| Recall vs scientific precision | Precision at progression gates | False advancement is costlier than a hold | Exploratory shortlist may keep low-confidence items labeled `HOLD` |
| Live freshness vs demo reliability | Pinned snapshot + optional live refresh | Reproducible judging-day replay | Final report must disclose snapshot date |
| Agent count vs clarity | Six runtime roles with explicit ownership | Coordination evidence without agent theater | A role may split after measured bottlenecks |
| Generative novelty vs validation | Constrained exploration and deterministic gates | Four-week feasibility and scientific honesty | Broader generation only after validated activity evaluation |

## Principle-to-Artifact Map

| Principle | Docs | Rules | Evals | Code/UX Implication |
|---|---|---|---|---|
| P1–P4 | Domain model, flow | Agent/compliance | GC-002, GC-007, GC-009 | `ADVANCE/HOLD/REJECT` card |
| P5–P6 | Architecture, feature spec | Data/UI | GC-004, GC-011 | Typed tool results and claim labels |
| P7 | Architecture | Agent | GC-010 | Budget panel and bounded retry |
| P8 | Flow | Compliance | GC-006 | Approval state cannot be bypassed |
| P9–P10 | Eval plan, handoff | Data/UI | Rubric provenance rows | Replay manifest and decision trace |
