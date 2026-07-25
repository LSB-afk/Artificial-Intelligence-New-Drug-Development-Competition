# 11 Change Log

## Artifact Metadata

- Owner: LSB-afk / project team
- Last updated: 2026-07-25

| Date | Artifact | Change | Reason | Impact | Approved By |
|---|---|---|---|---|---|
| 2026-07-19 | Repository HEAD | Fast-forwarded to `25c622e` | Inspect and adopt latest GitHub evidence | Adds current cold assessment | Project request |
| 2026-07-19 | Harness scaffold | Added canonical docs/rules/evals index and migration map | Existing repo lacked a project harness | Traceable future work | Project request |
| 2026-07-19 | Scientific demo | Reframed TYK2 as IBD contradiction/rejection case | Current clinical evidence reverses old premise | Prevents invalid positive demo | Source-backed decision |
| 2026-07-19 | Originality thesis | Moved from generic closed loop to indication-aware self-falsification/failure ledger | Close prior art exists | More defensible proposal | Source-backed decision |
| 2026-07-19 | Tool plan | TDC predictor → ADMET-AI plan; bulk SA/RAscore → top-5 AiZynth | Four-week feasibility | Smaller runtime/cost risk | Source-backed decision |
| 2026-07-19 | Agent authority | Moved score improvement to read-only evaluation plane | Avoid scientific score gaming | Cleaner responsibility boundary | Architecture decision |
| 2026-07-19 | Harness validation | Checked YAML paths, JSONL cases, links, feature/control trace, and diff whitespace | Verify before handoff | Design scaffold passes; runtime remains unimplemented | Automated read-only checks |
| 2026-07-19 | Decision core | Implemented JB-derived `src/h2l` (registry, state_machine, replay, eval_runner, cli) test-first | README next-work item "state/eval runner 구현"; ports JB operating invariants | 38 tests pass; runtime now executable and reproducible | D-006 |
| 2026-07-20 | Field-2 loop | Added `tools`, `molopt`, `molopt_eval`, labeled pool fixture, and `molopt`/`molopt-eval` CLI | Raise inference accuracy via versioned tools + eval loop, not LLM weight training | 135 tests pass; ablation candidate 1.00 vs baseline 0.43 selection accuracy, byte-reproducible; offline/dependency-free | D-008 |
| 2026-07-24 | Console surface | Migrated the operator console to `web_dongseop` and added the AI·자동화 관리 section; removed the local-only `/rnd` console | Consolidate on one console; `/rnd` was never on origin and duplicated the surface | 5 views render from real run data; console QA suite green | Project request |
| 2026-07-25 | Explanation layer | Added `src/h2l/llm.py` (Ollama + output guardrail + template fallback), read-only `GET /api/explain`, and the 판단 해설 console view | Answer Q-002 and let the harness explain decisions without granting the model authority over facts | 145 tests pass (26 new); model path verified on `qwen2.5:7b-instruct`; harness-down and unmapped-hypothesis paths both fall back without breaking the console | D-009 |
| 2026-07-25 | Chemistry backend | Added optional `src/h2l/chem.py` (RDKit descriptors/QED/ECFP4/SA/PAINS+Brenk) behind `H2L_CHEM_BACKEND`, a structure-backed pool fixture, and `--backend` on the molopt CLI | Reference adapters read authored descriptors and a 16-bit fingerprint, so no molecular result rested on real chemistry | 167 tests pass with RDKit, 145 pass + 1 skip without it; selection accuracy 0.571→1.000, precision 0.40→1.00, bootstrap Δ 0.429 CI [0.214, 0.714]; reference ablation unchanged and still byte-reproducible | D-010 |

## Scope Change Summary

| Feature | Baseline | Current | Risk | Demo Impact |
|---|---|---|---|---|
| TYK2 story | Positive lead-loop target | Negative self-falsification case | Positive target remains TBD | Stronger autonomy/scientific demo |
| Molecule optimization | TYK2/deucravacitinib direct optimization | Gate-controlled branch after target `ADVANCE`; `METHOD_ONLY` allowed | End-to-end positive branch incomplete | Honest blocked state |
| ADMET | TDC as immediate predictor | Planned ADMET-AI, runtime validation required | Dependency unverified | Disclosed |
| Synthesis | AiZynth throughout loop | SA/RAscore bulk, AiZynth top 5 | RAscore runtime unverified | Faster/replayable |
| Transparency | Generic logs/“thinking” | Decision trace + evidence/rules/actions/failures | UI not built | Better final-demo contract |
| LLM role | Undecided runtime, unclear authority | Local Ollama writes explanations only, gated by an output guardrail; OFF by default | Model text is rejected, not corrected, on violation | Reviewer sees model vs template provenance per claim |
| Chemistry | Authored descriptors, 16-bit hand-written fingerprint, alert strings | Optional RDKit backend computes every property from SMILES; reference stays default | RDKit is optional, so two lineages must stay in step | Each rejection cites a real substructure, not a label |
