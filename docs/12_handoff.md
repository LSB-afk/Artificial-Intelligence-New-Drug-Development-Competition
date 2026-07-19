# 12 Handoff

## Artifact Metadata

- Owner: LSB-afk / project team
- Last updated: 2026-07-19
- Intended reader: maintainer / competition team
- Readiness: harness design started; implementation not started

## What Was Built

- Latest GitHub commit adopted locally.
- Canonical Harness Engineering scaffold and migration map.
- Source/CPS/principles/definitions/domain state machine.
- PRD, architecture, six-role runtime, separate evaluation plane.
- TYK2 rejection demo flow, molecule eligibility gate, evaluation thresholds, risk rules.
- Existing proposal/eval artifacts remain preserved for incremental correction.

## How to Run

```bash
# Runtime commands do not exist yet.
# First implementation milestone:
# 1. create a pinned evidence fixture and typed adapter tests
# 2. implement the domain event/state validator
# 3. add a machine-readable eval runner for evals/cases.jsonl
```

## Required Environment Variables

| Name | Purpose | Required? | Demo Value |
|---|---|---|---|
| `H2L_RUN_MODE` | `SCIENTIFIC`, `REJECTION_DEMO`, or `METHOD_ONLY` | Planned | `REJECTION_DEMO` |
| `H2L_OFFLINE` | Force pinned snapshot replay | Planned | `1` |
| `H2L_MAX_TOOL_CALLS` | Per-run external call cap | Planned | TODO after measurement |
| Model/provider keys | Tool-calling runtime | TBD | Never commit |

## Demo Script

Use the five-minute script in `docs/09_flow.md`. The mandatory climax is the indication-aware rejection/hold of TYK2 for IBD, followed by an API-outage fallback and the blocked molecule transition.

## Architecture Summary

Six runtime roles operate through a deterministic state/approval engine and artifact store. External calls are snapshot-first and fully audited. A separate read-only evaluation plane runs golden cases and cannot alter scientific state.

## Key Files

| Path | Purpose |
|---|---|
| `harness.yaml` | Project contract, risks, decisions, open questions |
| `docs/02_cps.md` | Problem/solution narrative |
| `docs/05_domain-model.md` | Entities, states, events, permissions |
| `docs/07_architecture.md` | Components, boundaries, fallbacks |
| `docs/08_feature-spec.md` | Agent capability contracts |
| `docs/09_flow.md` | Core and failure flows, five-minute demo |
| `docs/10_eval-plan.md` | Competition-to-evidence map and thresholds |
| `rules/` | Agent/data/UI/compliance implementation rules |
| `evals/` | Regression cases, rubric, failure modes |

## Test and Lint Status

| Check | Command | Status | Notes |
|---|---|---|---|
| Runtime unit tests | TODO | NOT RUN | No runtime code exists |
| Dependency smoke tests | TODO | NOT RUN | ADMET-AI/RAscore/AiZynthFinder unverified |
| Harness YAML/required paths | Ruby YAML/path check | PASS | 26 indexed artifact/rule/eval paths exist |
| Machine-readable eval cases | `jq -s -e ... evals/cases.jsonl` | PASS | 13 unique cases; high-risk cases present |
| Local Markdown links | Read-only Ruby link check | PASS | 35 Markdown files checked |
| Problem→feature→flow→eval trace | Targeted feature/control check | PASS | F-01 through F-07 and six core controls present |
| Git whitespace check | `git diff --check` | PASS | No tracked-diff whitespace errors |

## Known Limitations

| Limitation | Impact | Workaround | Future Fix |
|---|---|---|---|
| Positive molecule target not selected | Full positive field 1+2 branch blocked | Demonstrate TYK2 rejection and `METHOD_ONLY` tool contract | Evidence-qualify an alternative |
| ChEMBL activity count not reverified | Numeric claim cannot enter final report | Mark pending and replay only verified fields | Capture dated response |
| Planned dependencies untested | Feasibility is architectural, not runtime-proven | Keep unavailable metrics explicit | Pin and smoke-test |
| No machine-readable runner yet | Eval cases are specifications only | Manual review | Implement runner first |
| Snapshot redistribution terms not reviewed | Fixtures may not be committable | Store hashes/manifests and minimal lawful data | Source-by-source review |

## Open Risks

See `harness.yaml` R-001 through R-004. No risk is considered closed by documentation alone.

## Next Build Priorities

1. P0: Evidence-qualify a positive target; do not assume IL-23/JAK1 without the same clinical gate.
2. P0: Implement typed domain events and transition tests, including the TYK2 blocked path.
3. P0: Create lawful pinned fixtures/manifests and adapter contract tests.
4. P0: Implement `evals/cases.jsonl` runner and all high-risk cases.
5. P1: Smoke-test RDKit, ADMET-AI, SA/RAscore, then optional AiZynthFinder.
6. P1: Build the offline five-minute decision-trace UI.
7. P2: Measure manual-vs-agent time/cost three times.

## Fresh Maintainer Checklist

- [x] Can identify the current scientific correction source.
- [x] Can find demo vs production differences.
- [x] Can find known limitations and next priorities.
- [ ] Can install dependencies.
- [ ] Can run local demo.
- [ ] Can execute automated evals.
