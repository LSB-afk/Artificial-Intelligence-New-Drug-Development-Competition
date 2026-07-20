# Design

## Source of truth
- Status: Active
- Last refreshed: 2026-07-20
- Primary product surfaces: H2L-Forge run list, run monitor, target evidence, molecule comparison, failure log, audit trail, report
- Evidence reviewed: `README.md`, `docs/01_competition_analysis.md`, `docs/02_field1_field2_fusion_design.md`, `docs/05_work_plan.md`, `05_리서치/2026-07-16_H2L-Forge_냉정평가_및_개선안.md`

## Brand
- Personality: calm, rigorous, skeptical, traceable
- Trust signals: source IDs, observation dates, score breakdowns, failure reasons, data-mode labels, human-review gates
- Avoid: AI chat-first layouts, purple gradients, glass effects, decorative science imagery, oversized marketing copy, unsupported certainty

## Product goals
- Goals: make harness progress observable; explain target and molecule decisions; preserve failures as first-class results; support a stable competition demo
- Non-goals: replace expert judgment; expose private model reasoning; provide executable synthesis instructions; support every disease in the prototype
- Success signals: a reviewer understands the TYK2 reversal in under one minute; every visible decision has a source; a rejected target cannot produce downstream molecules; synthetic UI fixtures cannot be mistaken for research results

## Personas and jobs
- Primary personas: competition reviewer, drug-discovery researcher, H2L-Forge developer
- User jobs: start an analysis, inspect progress, compare targets, understand a rejection, compare molecules, review failures, download a report
- Key contexts of use: laptop-based live demo, recorded demo, technical review, local development

## Information architecture
- Primary navigation: Runs, Overview, Targets, Molecules, Failures, Audit, Report
- Core routes/screens: prototype uses a single run workspace with tabbed views; production should map tabs to run-scoped routes
- Content hierarchy: run state first, decision second, evidence third, raw logs last

## Design principles
- Evidence before assertion: every conclusion exposes its supporting and conflicting sources.
- Failure is output: rejected targets and molecules remain inspectable.
- Dense but calm: tables and split panes support comparison without decorative card grids.
- Honest state: progress, skipped stages, uncertainty, source snapshots, and synthetic proxy metrics are explicitly labeled.
- Tradeoffs: desktop demo quality is prioritized over full mobile authoring; mobile remains readable for review.

## Visual language
- Color: neutral canvas and white work surfaces; teal action color; blue information; amber warning; red rejection; green completion
- Typography: Pretendard/system sans for interface; system monospace for identifiers and SMILES
- Spacing/layout rhythm: 4px base with 8, 12, 16, 24, and 32px increments
- Shape/radius/elevation: 6px panel radius, 1px borders, shadows only for overlays
- Motion: restrained status and panel transitions; reduced-motion preference respected
- Imagery/iconography: Lucide interface icons and molecule structure diagrams; no decorative AI imagery

## Components
- Existing components to reuse: none
- New/changed components: app shell, run switcher, stage navigator, evidence comparison, source list, target table, molecule fixture table, failure ledger, audit timeline, report view, start-run modal, RDKit renderer
- Variants and states: queued, running, completed, warning, failed, skipped, blocked, cancelled; review, rejected, insufficient-data, reference-only, demo-only
- Token/component ownership: `web_dongseop/src/styles.css` owns prototype tokens and component styling

## Accessibility
- Target standard: WCAG 2.2 AA where practical for the prototype
- Keyboard/focus behavior: visible focus rings, semantic buttons, labeled controls, Escape closes modal
- Contrast/readability: status never relies on color alone; dense tables use readable sizes and row labels
- Screen-reader semantics: tab roles, progress labels, table headers, modal dialog semantics
- Reduced motion and sensory considerations: animations disabled under `prefers-reduced-motion`

## Responsive behavior
- Supported breakpoints/devices: primary at 1280px and above; reviewable at 768px and 390px
- Layout adaptations: sidebar becomes a drawer; the decision panel appears before the pipeline; molecule records use a compact mobile list; wide tables scroll inside their own region
- Touch/hover differences: all primary actions remain labeled and tap targets remain at least 40px

## Interaction states
- Loading: stage-specific spinner and textual state
- Empty: explain which upstream stage has not produced data
- Error: name the failed tool and expose retry or cached fallback
- Success: show completed stage, duration, and produced artifact count
- Disabled: explain unavailable actions through nearby status text
- Offline/slow network: preserve the last snapshot and clearly label cached mode

## Content voice
- Tone: concise, clinical, and explicit about uncertainty
- Terminology: use `근거 비평`, `활성 대리지표`, `후보 가설`, and `데이터 스냅샷`; avoid claiming prediction certainty
- Microcopy rules: state what happened, why it matters, and what the harness does next

## Implementation constraints
- Framework/styling system: React, TypeScript, Vite, plain CSS tokens, Lucide icons
- Design-token constraints: no gradient, no glass effect, radius at or below 8px
- Performance constraints: prototype uses local fixture data; RDKit WASM is loaded only when a molecule structure is rendered; production must measure and cache the 6.9MB WASM asset
- Compatibility constraints: current desktop browsers; no requirement for server-side rendering
- Test/screenshot expectations: production build plus desktop and mobile screenshots with no overlap or blank states

## Open questions
- [ ] Confirm the harness stage names and stable IDs with the harness owner.
- [ ] Confirm whether progress is event-based or derived from completed stages.
- [ ] Confirm the exact target-score components and their direction.
- [x] Prototype molecule depictions are generated from SMILES with official RDKit WebAssembly.
- [ ] Confirm the final report formats and artifact download paths.
