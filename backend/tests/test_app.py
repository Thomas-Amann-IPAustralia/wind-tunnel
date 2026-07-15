"""Endpoint tests for the backend slice built this branch (TECH_SPEC §7):
health, run creation, the status proxy, the artefact download proxy,
submission, threshold routing, and resume-by-code. No network, no git — the
app is wired against ``FakeGitHubClient``/``FakeDispatcher`` (§15).
"""

from __future__ import annotations

import json

import statefile
from conftest import run_path, seed_run


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


# -- create_run -----------------------------------------------------------


def test_create_run_returns_a_valid_code_and_commits_the_skeleton(client, github):
    import runcode

    resp = client.post("/api/runs")
    assert resp.status_code == 201
    body = resp.json()
    assert body["run_id"] == body["run_code"]
    assert runcode.is_valid(body["run_id"])

    run_id = body["run_id"]
    assert run_path(run_id, "run.json") in github.files
    assert run_path(run_id, "status.json") in github.files
    assert run_path(run_id, "brainstorm", "outline.md") in github.files

    run = statefile.RunState.from_dict(json.loads(github.files[run_path(run_id, "run.json")]))
    assert run.run_id == run_id
    assert run.stage is statefile.Stage.BRAINSTORM

    outline = github.files[run_path(run_id, "brainstorm", "outline.md")].decode("utf-8")
    assert f'run_id: "{run_id}"' in outline
    assert 'created_at: ""' not in outline

    # One atomic commit for the whole skeleton (§7.1), not three.
    assert len(github.commits) == 1
    assert set(github.commits[0]["paths"]) == {
        run_path(run_id, "run.json"),
        run_path(run_id, "status.json"),
        run_path(run_id, "brainstorm", "outline.md"),
    }


def test_create_run_redraws_on_collision(client, github, monkeypatch):
    import runcode

    calls = {"n": 0}
    real_generate = runcode.generate

    def flaky_generate():
        calls["n"] += 1
        return "WT-AAAA-AA" if calls["n"] == 1 else real_generate()

    # Pre-seed the first code the (patched) generator will draw, forcing a redraw.
    seed_run(github, "WT-AAAA-AA")
    monkeypatch.setattr(runcode, "generate", flaky_generate)

    resp = client.post("/api/runs")
    assert resp.status_code == 201
    assert resp.json()["run_id"] != "WT-AAAA-AA"
    assert calls["n"] >= 2


# -- status proxy -----------------------------------------------------------


def test_status_proxy_returns_status_json(client, github):
    seed_run(github, "WT-BBBB-BB")
    resp = client.get("/api/runs/WT-BBBB-BB/status")
    assert resp.status_code == 200
    assert resp.json()["run_id"] == "WT-BBBB-BB"
    assert "ETag" in resp.headers


def test_status_proxy_404s_unknown_run(client):
    resp = client.get("/api/runs/WT-ZZZZ-ZZ/status")
    assert resp.status_code == 404


def test_status_proxy_conditional_get_304s_when_unchanged(client, github):
    seed_run(github, "WT-CCCC-CC")
    first = client.get("/api/runs/WT-CCCC-CC/status")
    etag = first.headers["ETag"]
    second = client.get("/api/runs/WT-CCCC-CC/status", headers={"If-None-Match": etag})
    assert second.status_code == 304


def test_status_proxy_rejects_malformed_run_id(client):
    resp = client.get("/api/runs/not-a-code/status")
    assert resp.status_code == 400


# -- artefact proxy -----------------------------------------------------------


def test_artefact_proxy_rejects_unknown_name(client, github):
    seed_run(github, "WT-DDDD-DD")
    resp = client.get("/api/runs/WT-DDDD-DD/artefact/run.json")
    assert resp.status_code == 400  # only the §7 allow-list, never an arbitrary repo path


def test_artefact_proxy_404s_when_not_yet_produced(client, github):
    seed_run(github, "WT-EEEE-EE")
    resp = client.get("/api/runs/WT-EEEE-EE/artefact/assessment.html")
    assert resp.status_code == 404


def test_artefact_proxy_streams_a_produced_artefact(client, github):
    seed_run(github, "WT-FFFF-FF")
    github.files[run_path("WT-FFFF-FF", "artefacts", "threshold.md")] = b"# Threshold\n"
    resp = client.get("/api/runs/WT-FFFF-FF/artefact/threshold.md")
    assert resp.status_code == 200
    assert resp.content == b"# Threshold\n"
    assert "markdown" in resp.headers["content-type"]


# -- submit -----------------------------------------------------------


def test_submit_dispatches_governance(client, github, dispatcher):
    seed_run(github, "WT-GGGG-GG", stage=statefile.Stage.BRAINSTORM)
    resp = client.post("/api/runs/WT-GGGG-GG/submit")
    assert resp.status_code == 200
    assert resp.json() == {"run_id": "WT-GGGG-GG", "dispatched": True}

    assert len(dispatcher.calls) == 1
    call = dispatcher.calls[0]
    assert call["workflow_file"] == "governance.yml"
    assert call["inputs"] == {"run_id": "WT-GGGG-GG", "resume_from": "THRESHOLD_DRAFTING"}

    run = statefile.RunState.from_dict(json.loads(github.files[run_path("WT-GGGG-GG", "run.json")]))
    assert run.stage is statefile.Stage.SUBMITTED

    status_doc = json.loads(github.files[run_path("WT-GGGG-GG", "status.json")])
    assert status_doc["overall_state"] == "running"


def test_submit_refuses_when_not_at_brainstorm(client, github):
    seed_run(github, "WT-HHHH-HH", stage=statefile.Stage.THRESHOLD_REVIEW)
    resp = client.post("/api/runs/WT-HHHH-HH/submit")
    assert resp.status_code == 409


def test_submit_404s_unknown_run(client):
    resp = client.post("/api/runs/WT-9999-99/submit")
    assert resp.status_code == 404


# -- threshold routing -----------------------------------------------------------


def test_threshold_route_conclude(client, github):
    seed_run(
        github,
        "WT-JJJJ-JJ",
        stage=statefile.Stage.THRESHOLD_REVIEW,
        stage_status=statefile.StageStatus.AWAITING_USER,
    )
    resp = client.post("/api/runs/WT-JJJJ-JJ/threshold/route", json={"outcome": "conclude"})
    assert resp.status_code == 200
    assert resp.json()["stage"] == "CONCLUDED"

    run = statefile.RunState.from_dict(json.loads(github.files[run_path("WT-JJJJ-JJ", "run.json")]))
    assert run.stage is statefile.Stage.CONCLUDED
    assert run.stage_status is statefile.StageStatus.COMPLETE
    status_doc = json.loads(github.files[run_path("WT-JJJJ-JJ", "status.json")])
    assert status_doc["overall_state"] == "complete"


def test_threshold_route_full_dispatches_governance(client, github, dispatcher):
    seed_run(
        github,
        "WT-KKKK-KK",
        stage=statefile.Stage.THRESHOLD_REVIEW,
        stage_status=statefile.StageStatus.AWAITING_USER,
    )
    resp = client.post("/api/runs/WT-KKKK-KK/threshold/route", json={"outcome": "full"})
    assert resp.status_code == 200
    assert resp.json()["dispatched"] is True

    assert dispatcher.calls[0]["inputs"] == {
        "run_id": "WT-KKKK-KK",
        "resume_from": "FULL_DRAFTING",
    }
    run = statefile.RunState.from_dict(json.loads(github.files[run_path("WT-KKKK-KK", "run.json")]))
    assert run.stage is statefile.Stage.FULL_DRAFTING


def test_threshold_route_refuses_when_not_paused(client, github):
    seed_run(github, "WT-RRRR-RR", stage=statefile.Stage.BRAINSTORM)
    resp = client.post("/api/runs/WT-RRRR-RR/threshold/route", json={"outcome": "conclude"})
    assert resp.status_code == 409


def test_threshold_route_rejects_bad_body(client, github):
    seed_run(
        github,
        "WT-MMMM-MM",
        stage=statefile.Stage.THRESHOLD_REVIEW,
        stage_status=statefile.StageStatus.AWAITING_USER,
    )
    resp = client.post("/api/runs/WT-MMMM-MM/threshold/route", json={"outcome": "sideways"})
    assert resp.status_code == 422


# -- resume -----------------------------------------------------------


def test_resume_returns_stage_and_status(client, github):
    seed_run(github, "WT-NNNN-NN", stage=statefile.Stage.FULL_DRAFTING)
    resp = client.post("/api/runs/WT-NNNN-NN/resume")
    assert resp.status_code == 200
    body = resp.json()
    assert body["stage"] == "FULL_DRAFTING"
    assert body["status"]["run_id"] == "WT-NNNN-NN"


def test_resume_404s_unknown_code(client):
    resp = client.post("/api/runs/WT-PPPP-PP/resume")
    assert resp.status_code == 404


def test_resume_normalises_lowercase_input(client, github):
    seed_run(github, "WT-QQQQ-QQ")
    resp = client.post("/api/runs/wt-qqqq-qq/resume")
    assert resp.status_code == 200
    assert resp.json()["run_id"] == "WT-QQQQ-QQ"


def test_resume_400s_malformed_code(client):
    resp = client.post("/api/runs/definitely-not-a-code/resume")
    assert resp.status_code == 400
