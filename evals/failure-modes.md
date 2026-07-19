# H2L-Forge Failure Modes

| Failure mode | Detection | Impact | Mitigation | Owner |
| --- | --- | --- | --- | --- |
| Disease ID mismatch | selected ID not in Open Targets search top candidates | wrong target graph | exact/synonym verification, human review | Disease Normalizer |
| Association score overclaim | report calls score "confidence" | scientific validity loss | wording lint: heuristic only | Evidence Critic |
| Indication transfer error | approval/trial indication differs from disease context | false target progression | mandatory indication-aware clinical check; `HOLD/REJECT` | Clinical Contradiction Critic |
| Failed clinical program ignored | expected contradictory trials absent from ledger | false-positive hypothesis | required disconfirmation source classes and GC-002 | Clinical Contradiction Critic |
| ChEMBL assay heterogeneity | mixed units/types/relations | noisy seed selection | standard_type/unit/relation filters | Seed Ligand Agent |
| Unverified ChEMBL count | numeric claim lacks current response snapshot | false precision | mark pending; block final claim | Evidence Scout |
| Cache presented as live | tool event mode and report disagree | ethics/reproducibility loss | manifest/report lint | Audit/Report Agent |
| Citation hallucination | claim has no URL/DOI/DB ID | ethics/completeness fail | report block | Report Agent |
| Prior-art overclaim | proposal says closed loop is first/unique | originality/credibility loss | cited comparison + prohibited-claim lint | Evaluation Agent |
| TDC predictor mischaracterization | implementation plan calls TDC a ready inference API | feasibility loss | ADMET-AI plan or versioned trained model | Deterministic Verifier |
| Invalid molecule | RDKit parse fail | invalid candidate | reject/retry | Molecule Optimizer |
| Rejected target enters optimization | molecule event exists while target `HOLD/REJECT` | scientific control failure | deterministic transition validator | Supervisor |
| Activity proxy overclaim | Tanimoto similarity labeled activity/prediction | scientific validity loss | schema-level evidence type | Deterministic Verifier |
| Over-optimization | high QED but low similarity or high ADMET risk | unrealistic lead | hard gates + Pareto | Score Improvement Agent |
| PAINS/reactive alert | filter match | false positive biology/safety | reject/warn | ADMET/Safety Agent |
| AiZynth scope/runtime failure | >5 candidates or route search exceeds budget | demo/resource failure | SA/RAscore bulk gate; top-5 cap; proxy fallback | Deterministic Verifier |
| Dangerous synthesis detail | route output too actionable | dual-use risk | suppress details, human approval | Report Agent |
| Hidden reasoning disclosure | UI/report contains private chain-of-thought | unsafe/misleading transparency | render decision trace only | Audit/Report Agent |
| Evaluator authority leakage | score agent changes target/rank/approval | scientific score gaming | read-only evaluation plane and boundary test | Evaluation Agent |
| Scope creep | roadmap exceeds 4 weeks | 본선 구현 실패 | MVP/stretch split | Score Improvement Agent |
