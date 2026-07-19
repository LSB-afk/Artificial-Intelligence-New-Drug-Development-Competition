# Harness Adoption and Migration Map

Last updated: 2026-07-19

This repository adopted the canonical Harness Engineering artifact names without deleting or overwriting existing proposal work. Number prefixes overlap by design; `harness.yaml` is the canonical index.

| Existing Artifact | Canonical Harness Role | Status / Rule |
|---|---|---|
| `docs/01_competition_analysis.md` | Source context for CPS/evals | Reuse official requirements; verify changes before submission |
| `docs/02_field1_field2_fusion_design.md` | Legacy concept/agent inventory | Preserve; canonical state, tools, and gates live in `docs/05_domain-model.md` through `docs/10_eval-plan.md` |
| `docs/03_proposal_outline.md` | Submission narrative | Active; must stay synchronized with D-001 through D-005 |
| `docs/04_sources.md` | Bibliography/source registry | Active; evidence records need timestamps and IDs beyond this list |
| `docs/05_work_plan.md` | Schedule/backlog | Active; positive target remains a P0 open decision |
| `docs/06_score_improvement_research.md` | Historical 2026-07-06 score analysis | Superseded where it conflicts with the 2026-07-16 cold assessment |
| `docs/07_agent_loop_architecture.md` | Detailed legacy capability inventory | Reuse retry/log schemas; canonical role authority and boundaries live in `docs/07_architecture.md` |
| `docs/08_molecular_optimization_loop.md` | Molecular method draft | May run only after target `ADVANCE`, or explicitly in `METHOD_ONLY` mode |
| `05_리서치/2026-07-06_H2L-Forge_deep_research_report.md` | Historical research source | Preserve; later correction wins on conflicts |
| `05_리서치/2026-07-16_H2L-Forge_냉정평가_및_개선안.md` | Current scientific/design correction source | Authoritative as of 2026-07-19 |
| `prompts/agent_system_prompt.md` | Runtime prompt seed | Subordinate to `rules/agent-rules.md` and feature contracts |
| `evals/*.md` | Human-readable regression assets | Active and incrementally updated |

## Conflict Resolution

1. Prefer the most recent source-backed evidence.
2. Record semantic corrections in `docs/11_change-log.md`.
3. Do not silently delete historical claims; mark them superseded or update active proposal artifacts.
4. Do not implement from a legacy artifact when it conflicts with `harness.yaml`, rules, or canonical flow/evals.
