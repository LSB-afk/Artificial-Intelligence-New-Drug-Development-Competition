import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(*parts: str) -> dict:
    return json.loads((FIXTURES.joinpath(*parts)).read_text(encoding="utf-8"))


@pytest.fixture
def tyk2_packet() -> dict:
    return load_fixture("tyk2_ibd", "normalized_evidence.json")


@pytest.fixture
def tyk2_binding() -> dict:
    return load_fixture("tyk2_ibd", "chembl_500.json")


@pytest.fixture
def registry_path(tmp_path) -> Path:
    return tmp_path / "registry.json"


EVALS = Path(__file__).parent.parent / "evals"


@pytest.fixture
def decision_cases_path() -> Path:
    return EVALS / "decision_cases.json"
