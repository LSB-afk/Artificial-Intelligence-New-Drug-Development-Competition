# 01 Business Model

## Artifact Metadata

- Owner: LSB-afk / project team
- Last updated: 2026-07-19
- Business stage: idea
- Confidence: medium

## Judge-Facing Thesis

H2L-Forge is a research decision-support service for early discovery teams that need to connect disease-target evidence with molecule work without silently carrying a bad premise forward. Its value is not another molecule generator; it is an auditable evidence critic that can stop an attractive but indication-inconsistent target, record why it failed, and only then authorize a bounded molecule workflow. The economic claim will be measured against a fixed manual workflow rather than inferred from generic industry timelines.

## DDBM 11 Blocks

| Block | Product-Specific Answer | Evidence | Confidence |
|---|---|---|---|
| Mission | Reduce avoidable early-discovery work caused by weak or contradictory target premises | TYK2/IBD correction in the 2026-07-16 report | High |
| Key Partners | Public DB providers, open-source chemistry tools, domain reviewers | Open Targets, ChEMBL, ClinicalTrials.gov, PubMed/Europe PMC, RDKit | High |
| Key Activities | Evidence retrieval, contradiction review, molecule qualification, audit/report generation | Canonical flow and eval plan | High |
| Key Data | Dated target, clinical, assay, molecule, and tool-output evidence records | Architecture/data rules | High |
| Key Enablers | Tool-calling LLM, deterministic chemistry code, cache/replay, evaluation harness | Planned architecture | Medium |
| Key Barriers | Scientific calibration, source terms, reproducibility, reviewer trust | Open risks R-001–R-004 | High |
| Value Proposition | Faster, more defensible go/hold/reject preparation for early target review | To be measured on one fixed case | Medium |
| Benefits | Less duplicated search, clearer negative decisions, reproducible handoff, safer demo | Flow and audit artifacts | Medium |
| Negative Impacts | Automation bias, false confidence, unsafe chemistry detail, stale evidence | Compliance rules | High |
| Costs | Model/tool calls, compute, engineering, domain review, deployment | TODO: measure during MVP | Low |
| Revenues | Possible team SaaS/API/report workflow; not assumed for competition MVP | TODO: customer discovery | Low |

## Key Data Inventory

| Data-ID | Data Asset | Source | Permission / Consent Basis | Freshness | Quality Risk | Fallback |
|---|---|---|---|---|---|---|
| DATA-001 | Disease-target evidence | Open Targets | Public API; terms review required | Snapshot timestamp | Score misinterpretation | Cached response + source URL |
| DATA-002 | Drug indication and activity | ChEMBL | Public service; terms review required | Release + query timestamp | Heterogeneous assays/API outage | Cached normalized subset |
| DATA-003 | Clinical study evidence | ClinicalTrials.gov + publications | Public records; citation required | Retrieved date | Indication/trial mismatch | Manual review packet |
| DATA-004 | Molecule descriptors | RDKit | Local deterministic calculation | Tool version | Sanitization/config drift | Version-pinned replay |
| DATA-005 | ADMET predictions | ADMET-AI, planned | Package/model license review required | Model version | Domain shift/calibration | Warn + RDKit-only limited report |

## Barrier and Risk Linkage

| Risk-ID | Risk / Negative Impact | Mitigation | Owner | Review Gate |
|---|---|---|---|---|
| R-001 | Wrong target advances | Indication-specific contradiction gate | Domain lead | Target approval |
| R-002 | Stale/unverified numeric claims | Evidence status and snapshot hash | Evidence Scout | Report gate |
| R-003 | Planned tool cannot run | Version-pinned smoke test and fallback | Engineering lead | Build gate |
| R-004 | Unsafe or overclaimed molecule output | Deterministic gates + human approval + bounded disclosure | Safety reviewer | Export gate |

## Cost and Revenue Units

| Unit | Assumption | Value | Evidence | Sensitivity |
|---|---|---|---|---|
| External calls per cold run | Measured from tool events | TODO | `budget_metrics.json` | API/cache design |
| External calls per replay | Snapshot-first | Target: 0 | Demo design | Missing fixture |
| Median wall time | Three repeated runs | TODO | Benchmark log | Network/model latency |
| Reviewer minutes per case | Fixed review checklist | TODO | User test | Evidence density |
| Revenue per customer/case | Not part of MVP | TODO | Customer discovery | Segment |

## Definition of Done

- [x] All 11 DDBM blocks have an explicit answer or TODO.
- [x] Key data includes permission, freshness, and fallback.
- [x] Negative impacts map to risk controls.
- [ ] Costs and benefits have measured values.
