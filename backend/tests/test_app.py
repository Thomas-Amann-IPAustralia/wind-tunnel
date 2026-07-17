"""Endpoint tests for the backend slice built this branch (TECH_SPEC §7):
health, run creation, the status proxy, the artefact download proxy,
submission, threshold routing, and resume-by-code. No network, no git — the
app is wired against ``FakeGitHubClient``/``FakeDispatcher`` (§15).
"""

from __future__ import annotations

import json

import statefile
from conftest import dump_json, run_path, seed_run


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


def test_artefact_proxy_serves_the_poc(client, github):
    # The SPA previews the generated PoC in a sandboxed iframe pointed at this URL (§6.3).
    seed_run(github, "WT-PQCF-FF")
    github.files[run_path("WT-PQCF-FF", "brainstorm", "poc.html")] = b"<!doctype html><p>PoC</p>"
    resp = client.get("/api/runs/WT-PQCF-FF/artefact/poc.html")
    assert resp.status_code == 200
    assert resp.content == b"<!doctype html><p>PoC</p>"
    assert "text/html" in resp.headers["content-type"]


def test_artefact_proxy_serves_the_flow_map_source(client, github):
    # The SPA re-renders the flow map from its Mermaid source on resume (CLAUDE.md §9).
    seed_run(github, "WT-MMDF-FF")
    github.files[run_path("WT-MMDF-FF", "brainstorm", "flow-map.mmd")] = b"flowchart TD\n  A-->B\n"
    resp = client.get("/api/runs/WT-MMDF-FF/artefact/flow-map.mmd")
    assert resp.status_code == 200
    assert resp.content == b"flowchart TD\n  A-->B\n"


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


# -- checkpoint answers -----------------------------------------------------------


def _seed_checkpoint(github, run_id: str, *, question_ids=("privacy-1", "it_security-1")) -> None:
    """Seed a run paused at FULL_CHECKPOINT with a questions.json carrying ``question_ids``,
    grouped one per specialist by the id's prefix."""
    seed_run(
        github,
        run_id,
        stage=statefile.Stage.FULL_CHECKPOINT,
        stage_status=statefile.StageStatus.AWAITING_USER,
    )
    specialists: dict[str, list[dict]] = {}
    for qid in question_ids:
        spec = qid.rsplit("-", 1)[0]
        specialists.setdefault(spec, []).append(
            {
                "question_id": qid,
                "text": f"fact for {qid}?",
                "options": None,
                "allow_free_text": True,
            }
        )
    payload = {
        "batch_id": "q-1",
        "specialists": [
            {"node_id": f"full.specialist.{s}", "friendly": s, "why": "w", "items": items}
            for s, items in specialists.items()
        ],
        "counts": {"total": len(question_ids), "answered": 0, "skipped": 0},
    }
    github.files[run_path(run_id, "full", "questions.json")] = dump_json(payload)


def test_answers_commits_and_dispatches_revising(client, github, dispatcher):
    _seed_checkpoint(github, "WT-ANSW-23")
    resp = client.post(
        "/api/runs/WT-ANSW-23/answers",
        json={
            "answers": [{"question_id": "privacy-1", "value": "AWS Sydney"}],
            "skips": ["it_security-1"],
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"run_id": "WT-ANSW-23", "answered": 1, "skipped": 1, "dispatched": True}

    # answers.json committed with both the answer and the skip (§5.1 "skips → gaps").
    answers = json.loads(github.files[run_path("WT-ANSW-23", "full", "answers.json")])
    assert answers["answers"] == [{"question_id": "privacy-1", "value": "AWS Sydney"}]
    assert answers["skips"] == ["it_security-1"]

    # run.json advanced to FULL_REVISING and governance dispatched to resume there.
    run = statefile.RunState.from_dict(json.loads(github.files[run_path("WT-ANSW-23", "run.json")]))
    assert run.stage is statefile.Stage.FULL_REVISING
    assert dispatcher.calls[0]["inputs"] == {"run_id": "WT-ANSW-23", "resume_from": "FULL_REVISING"}


def test_answers_refuses_when_not_at_checkpoint(client, github):
    seed_run(github, "WT-ANSW-24", stage=statefile.Stage.FULL_DRAFTING)
    resp = client.post("/api/runs/WT-ANSW-24/answers", json={"answers": [], "skips": []})
    assert resp.status_code == 409


def test_answers_rejects_unknown_question_id(client, github):
    _seed_checkpoint(github, "WT-ANSW-25")
    resp = client.post(
        "/api/runs/WT-ANSW-25/answers",
        json={"answers": [{"question_id": "ethics-9", "value": "x"}], "skips": []},
    )
    assert resp.status_code == 400
    assert "Unknown question id" in resp.json()["detail"]


def test_answers_rejects_answer_and_skip_of_same_id(client, github):
    _seed_checkpoint(github, "WT-ANSW-26")
    resp = client.post(
        "/api/runs/WT-ANSW-26/answers",
        json={"answers": [{"question_id": "privacy-1", "value": "x"}], "skips": ["privacy-1"]},
    )
    assert resp.status_code == 400
    assert "both answered and skipped" in resp.json()["detail"]


def test_answers_allows_partial_coverage(client, github, dispatcher):
    # Answering one of two questions is fine — the unaddressed one is treated as skipped
    # downstream (§5.1). The endpoint must not require full coverage.
    _seed_checkpoint(github, "WT-ANSW-27")
    resp = client.post(
        "/api/runs/WT-ANSW-27/answers",
        json={"answers": [{"question_id": "privacy-1", "value": "AWS Sydney"}], "skips": []},
    )
    assert resp.status_code == 200
    assert dispatcher.calls[0]["inputs"]["resume_from"] == "FULL_REVISING"


def test_answers_409s_when_no_questions_on_record(client, github):
    # Paused at the checkpoint but questions.json is missing — a corrupt state, refused.
    seed_run(
        github,
        "WT-ANSW-28",
        stage=statefile.Stage.FULL_CHECKPOINT,
        stage_status=statefile.StageStatus.AWAITING_USER,
    )
    resp = client.post("/api/runs/WT-ANSW-28/answers", json={"answers": [], "skips": []})
    assert resp.status_code == 409


# -- full-assessment revision (§5.8) ----------------------------------------------


def _seed_complete(github, run_id: str, *, revisions_full: int = 0) -> None:
    """A run at COMPLETE, optionally with some full-assessment revisions already used."""
    run = seed_run(
        github, run_id, stage=statefile.Stage.COMPLETE, stage_status=statefile.StageStatus.COMPLETE
    )
    if revisions_full:
        run.revisions["full"] = revisions_full
        github.files[run_path(run_id, "run.json")] = dump_json(run.to_dict())


def test_revise_commits_request_and_dispatches(client, github, dispatcher):
    _seed_complete(github, "WT-REDA-22")
    resp = client.post(
        "/api/runs/WT-REDA-22/revise",
        json={"artefact": "full", "instructions": "Tighten the privacy retention analysis."},
    )
    assert resp.status_code == 200
    assert resp.json() == {"run_id": "WT-REDA-22", "revision": 1, "dispatched": True}

    # rev_1/request.json committed with the instructions.
    request = json.loads(
        github.files[run_path("WT-REDA-22", "full", "revisions", "rev_1", "request.json")]
    )
    assert request["instructions"] == "Tighten the privacy retention analysis."

    # run.json advanced to USER_REVISION with the count incremented, and governance dispatched.
    run = statefile.RunState.from_dict(json.loads(github.files[run_path("WT-REDA-22", "run.json")]))
    assert run.stage is statefile.Stage.USER_REVISION
    assert run.revisions["full"] == 1
    assert dispatcher.calls[0]["inputs"] == {"run_id": "WT-REDA-22", "resume_from": "USER_REVISION"}


def test_revise_second_revision_increments_to_two(client, github):
    _seed_complete(github, "WT-REDB-23", revisions_full=1)
    resp = client.post(
        "/api/runs/WT-REDB-23/revise", json={"artefact": "full", "instructions": "One more change."}
    )
    assert resp.status_code == 200
    assert resp.json()["revision"] == 2
    assert run_path("WT-REDB-23", "full", "revisions", "rev_2", "request.json") in github.files


def test_revise_refuses_over_the_cap(client, github, dispatcher):
    # Two revisions already used ⇒ the third is refused at the cap (§5.8), nothing dispatched.
    _seed_complete(github, "WT-REDC-24", revisions_full=2)
    resp = client.post(
        "/api/runs/WT-REDC-24/revise", json={"artefact": "full", "instructions": "Again."}
    )
    assert resp.status_code == 409
    assert "cap" in resp.json()["detail"].lower()
    assert dispatcher.calls == []


def test_revise_refuses_when_not_complete(client, github):
    seed_run(github, "WT-REDD-25", stage=statefile.Stage.FULL_DRAFTING)
    resp = client.post(
        "/api/runs/WT-REDD-25/revise", json={"artefact": "full", "instructions": "Change it."}
    )
    assert resp.status_code == 409


def test_revise_rejects_empty_instructions(client, github):
    _seed_complete(github, "WT-REDE-26")
    resp = client.post(
        "/api/runs/WT-REDE-26/revise", json={"artefact": "full", "instructions": "   "}
    )
    assert resp.status_code == 400


def test_revise_rejects_threshold_artefact(client, github):
    # "threshold" revises on its own THRESHOLD_REVIEW path, not this endpoint; the outline is
    # unbounded and has no /revise branch at all (brief §4/§7). Both are rejected by the Literal.
    _seed_complete(github, "WT-REDF-27")
    resp = client.post(
        "/api/runs/WT-REDF-27/revise", json={"artefact": "threshold", "instructions": "x"}
    )
    assert resp.status_code == 422
    resp = client.post(
        "/api/runs/WT-REDF-27/revise", json={"artefact": "outline", "instructions": "x"}
    )
    assert resp.status_code == 422
