"""Read-only evaluation plane.

Runs the support-only baseline against the contradiction-aware candidate over a
fixed decision case set, computes safety metrics, and does a deterministic
paired bootstrap. The evaluation plane may score artifacts but must never
mutate scientific state (evals GC-008 / GC-013).
"""
import json

from h2l.eval_runner import load_cases, paired_bootstrap, run_evaluation


def test_candidate_is_safe_and_baseline_is_not(decision_cases_path):
    report = run_evaluation(load_cases(decision_cases_path))
    candidate = report["candidate"]
    baseline = report["baseline"]

    assert candidate["unsafe_advance_count"] == 0
    assert baseline["unsafe_advance_count"] >= 1
    assert candidate["decision_accuracy"] > baseline["decision_accuracy"]
    assert candidate["contradiction_recall"] == 1.0
    assert baseline["contradiction_recall"] == 0.0


def test_readiness_gates_on_safety_critical_cases(decision_cases_path):
    report = run_evaluation(load_cases(decision_cases_path))
    assert report["candidate"]["readiness"] is True
    assert report["baseline"]["readiness"] is False


def test_snapshot_fallback_case_succeeds_for_candidate(decision_cases_path):
    report = run_evaluation(load_cases(decision_cases_path))
    assert report["candidate"]["snapshot_fallback_success"] == 1.0
    assert report["baseline"]["snapshot_fallback_success"] == 0.0


def test_eval_plane_declares_read_only(decision_cases_path):
    report = run_evaluation(load_cases(decision_cases_path))
    assert report["eval_plane_readonly"] is True


def test_paired_bootstrap_is_deterministic():
    baseline = [0, 0, 1, 0]
    candidate = [1, 1, 1, 1]

    first = paired_bootstrap(baseline, candidate, iterations=2000, seed=42)
    second = paired_bootstrap(baseline, candidate, iterations=2000, seed=42)

    assert first == second
    assert first["mean_delta"] > 0
    assert first["ci_low"] <= first["mean_delta"] <= first["ci_high"]


def test_run_evaluation_is_byte_equivalent(decision_cases_path):
    cases = load_cases(decision_cases_path)
    first = json.dumps(run_evaluation(cases), sort_keys=True)
    second = json.dumps(run_evaluation(cases), sort_keys=True)
    assert first == second
