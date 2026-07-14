"""Shared fixtures/paths for pipeline tests."""

import json
from pathlib import Path

import pytest
import yaml


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "instrument" / "risk_matrix.json").is_file():
            return parent
    raise RuntimeError("repo root (with instrument/) not found above tests")


REPO_ROOT = _repo_root()
INSTRUMENT = REPO_ROOT / "instrument"
CONFIG = REPO_ROOT / "config"
CORPUS = REPO_ROOT / "corpus"


def load_json(name: str) -> dict:
    with (INSTRUMENT / name).open(encoding="utf-8") as fh:
        return json.load(fh)


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def sections() -> dict:
    return load_json("sections.json")


@pytest.fixture(scope="session")
def questions() -> dict:
    return load_json("questions.json")


@pytest.fixture(scope="session")
def risk_matrix() -> dict:
    return load_json("risk_matrix.json")


@pytest.fixture(scope="session")
def likelihood_table() -> dict:
    return load_json("likelihood_table.json")


@pytest.fixture(scope="session")
def consequence_table() -> dict:
    return load_json("consequence_table.json")
