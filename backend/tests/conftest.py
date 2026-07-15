"""Shared fixtures for backend tests — no network, no git (TECH_SPEC §15)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_PIPELINE_DIR = Path(__file__).resolve().parent.parent.parent / "pipeline"
if str(_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_DIR))

import statefile  # noqa: E402
import status as status_module  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import create_app  # noqa: E402
from config import Settings  # noqa: E402
from dispatch import FakeDispatcher  # noqa: E402
from github_io import FakeGitHubClient  # noqa: E402

TEST_SETTINGS = Settings(github_owner="test-owner", github_repo="test-repo", github_branch="main")


def run_path(run_id: str, *parts: str) -> str:
    return "/".join(("runs", run_id, *parts))


def dump_json(obj: object) -> bytes:
    return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def seed_run(
    github: FakeGitHubClient,
    run_id: str,
    *,
    stage: statefile.Stage = statefile.Stage.BRAINSTORM,
    stage_status: statefile.StageStatus = statefile.StageStatus.IN_PROGRESS,
) -> statefile.RunState:
    """Write a run.json + status.json straight into the fake store, bypassing
    the create-run endpoint, so route/submit/status tests can start from any
    stage without driving the whole state machine."""
    now = statefile.utc_now_iso()
    run = statefile.RunState.new(run_id, now=now)
    run.advance_to(stage, stage_status, now=now)
    st = status_module.StatusModel.initial(run, now=now)
    github.files[run_path(run_id, "run.json")] = dump_json(run.to_dict())
    github.files[run_path(run_id, "status.json")] = dump_json(st.to_dict())
    return run


@pytest.fixture
def github() -> FakeGitHubClient:
    return FakeGitHubClient()


@pytest.fixture
def dispatcher() -> FakeDispatcher:
    return FakeDispatcher()


@pytest.fixture
def client(github: FakeGitHubClient, dispatcher: FakeDispatcher) -> TestClient:
    app = create_app(github=github, dispatcher=dispatcher, settings=TEST_SETTINGS)
    return TestClient(app)
