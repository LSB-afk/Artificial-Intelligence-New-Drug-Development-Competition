"""CLI smoke tests: the harness must be runnable end to end from a shell."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _run(*args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    return subprocess.run(
        [sys.executable, "-m", "h2l.cli", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def test_run_rejects_tyk2_ibd_fixture():
    proc = _run("run", "--evidence", "tests/fixtures/tyk2_ibd/normalized_evidence.json")
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["decision"] == "REJECT"
    assert result["molecule_eligible"] is False


def test_eval_reports_candidate_ready():
    proc = _run("eval", "--cases", "evals/decision_cases.json")
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["candidate"]["readiness"] is True
    assert report["baseline"]["readiness"] is False


def test_eval_output_is_byte_equivalent_across_runs():
    first = _run("eval", "--cases", "evals/decision_cases.json")
    second = _run("eval", "--cases", "evals/decision_cases.json")
    assert first.stdout == second.stdout
