# H2L-Forge Project Operating Rule

This repository uses the Harness Engineering artifacts declared in `harness.yaml`.

## Source of truth

1. Preserve raw evidence and decisions in `docs/00_source-log.md` and `docs/01_meeting-log.md`.
2. Treat `05_리서치/2026-07-16_H2L-Forge_냉정평가_및_개선안.md` as the current scientific correction source.
3. Use `docs/harness-migration-map.md` to distinguish canonical harness artifacts from preserved legacy drafts.
4. When documents disagree, prefer the latest dated, source-backed decision and record the resolution in `docs/11_change-log.md`.

## Required product sequence

`source → CPS → principles/definitions → domain states → PRD/features → architecture → agent flow → evals → handoff`

Do not implement a feature that lacks a problem trace, acceptance criteria, risk control, and eval case.

## Scientific and agent rules

- TYK2/deucravacitinib is an IBD contradiction/rejection demo unless a new, reviewed evidence package changes that decision.
- A target must be `ADVANCE` before molecule optimization. `REJECTION_DEMO` and `METHOD_ONLY` runs cannot produce therapeutic claims.
- Separate measured activity, model prediction, and similarity proxy in every output.
- Facts and calculations come from versioned tools or evidence records; the LLM selects actions and writes bounded explanations.
- Store concise decision traces, tool events, and evidence links. Do not store or present hidden chain-of-thought.
- High-risk scientific advancement, synthesis disclosure, and final candidate promotion require human approval.

## Completion report

End substantive work with:

- Files changed
- Decisions made
- Assumptions
- Validation performed
- Remaining risks
- Next action
