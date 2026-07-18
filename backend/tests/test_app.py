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


def test_artefact_proxy_streams_the_threshold_export(client, github):
    # The "threshold.md" name resolves to the pipeline's canonical committed file,
    # threshold/threshold_assessment.md — not a phantom artefacts/ copy (one owner, §3).
    seed_run(github, "WT-FFFF-FF")
    github.files[run_path("WT-FFFF-FF", "threshold", "threshold_assessment.md")] = b"# Threshold\n"
    resp = client.get("/api/runs/WT-FFFF-FF/artefact/threshold.md")
    assert resp.status_code == 200
    assert resp.content == b"# Threshold\n"
    assert "markdown" in resp.headers["content-type"]


def test_artefact_proxy_streams_the_outline(client, github):
    # The "outline.md" name resolves to brainstorm/outline.md, the single source of
    # the concept (§7.1), not a phantom artefacts/ copy.
    seed_run(github, "WT-GGGG-GG")
    github.files[run_path("WT-GGGG-GG", "brainstorm", "outline.md")] = b"# Outline\n"
    resp = client.get("/api/runs/WT-GGGG-GG/artefact/outline.md")
    assert resp.status_code == 200
    assert resp.content == b"# Outline\n"
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


def test_artefact_proxy_forces_download_with_query_flag(client, github):
    # ?download=1 -> Content-Disposition: attachment, so a cross-origin (Pages ->
    # Render) link saves the notebook instead of opening its raw JSON inline. The
    # anchor's `download` attribute alone is ignored across origins.
    seed_run(github, "WT-DNBA-23")
    github.files[run_path("WT-DNBA-23", "artefacts", "assessment.ipynb")] = b'{"cells": []}'
    resp = client.get("/api/runs/WT-DNBA-23/artefact/assessment.ipynb?download=1")
    assert resp.status_code == 200
    assert resp.headers["content-disposition"] == 'attachment; filename="assessment.ipynb"'


def test_artefact_proxy_serves_inline_without_download_flag(client, github):
    # Without the flag the same name is served inline (iframe src, fetchArtefactText),
    # so no attachment header is set.
    seed_run(github, "WT-DNBA-24")
    github.files[run_path("WT-DNBA-24", "artefacts", "assessment.ipynb")] = b'{"cells": []}'
    resp = client.get("/api/runs/WT-DNBA-24/artefact/assessment.ipynb")
    assert resp.status_code == 200
    assert "content-disposition" not in resp.headers


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


# -- dispatch failure is non-fatal + re-dispatch (§5.7) --------------------------


class _FailingDispatcher:
    """A dispatcher whose trigger always fails — stands in for a PAT lacking
    ``actions:write`` or a transient GitHub API error (§5.7)."""

    def dispatch(self, workflow_file, *, ref, inputs):
        from dispatch import DispatchError

        raise DispatchError("HTTP 403: Resource not accessible by personal access token")


def _failing_client(github):
    from conftest import TEST_SETTINGS
    from fastapi.testclient import TestClient

    from app import create_app

    app = create_app(github=github, dispatcher=_FailingDispatcher(), settings=TEST_SETTINGS)
    return TestClient(app)


def test_submit_dispatch_failure_keeps_run_submitted_and_reports(github):
    # A dispatch failure must NOT strand the run: the SUBMITTED transition is
    # committed, the endpoint returns 200 with dispatched=false + the reason, and
    # the SPA can move on to the Chamber (Bug: a 502 left the run un-resubmittable).
    seed_run(github, "WT-DSPA-22", stage=statefile.Stage.BRAINSTORM)
    resp = _failing_client(github).post("/api/runs/WT-DSPA-22/submit")
    assert resp.status_code == 200
    body = resp.json()
    assert body["dispatched"] is False
    assert "actions" in body["dispatch_error"] or "403" in body["dispatch_error"]

    run = statefile.RunState.from_dict(json.loads(github.files[run_path("WT-DSPA-22", "run.json")]))
    assert run.stage is statefile.Stage.SUBMITTED  # durably submitted, ready to re-kick


def test_redispatch_refires_a_submitted_run(client, github, dispatcher):
    # The §5.7 "hasn't started yet" re-dispatch: a run stuck at SUBMITTED is
    # re-fired without redoing Brainstorm, resuming from THRESHOLD_DRAFTING.
    seed_run(github, "WT-DSPB-23", stage=statefile.Stage.SUBMITTED)
    resp = client.post("/api/runs/WT-DSPB-23/redispatch")
    assert resp.status_code == 200
    assert resp.json() == {
        "run_id": "WT-DSPB-23",
        "resume_from": "THRESHOLD_DRAFTING",
        "dispatched": True,
    }
    assert dispatcher.calls[0]["inputs"] == {
        "run_id": "WT-DSPB-23",
        "resume_from": "THRESHOLD_DRAFTING",
    }


def test_redispatch_maps_full_revising_to_itself(client, github, dispatcher):
    seed_run(github, "WT-DSPC-24", stage=statefile.Stage.FULL_REVISING)
    resp = client.post("/api/runs/WT-DSPC-24/redispatch")
    assert resp.status_code == 200
    assert dispatcher.calls[0]["inputs"]["resume_from"] == "FULL_REVISING"


def test_redispatch_refuses_at_brainstorm(client, github):
    # Not yet submitted ⇒ there is no dispatch to re-fire (a plain 409).
    seed_run(github, "WT-DSPD-25", stage=statefile.Stage.BRAINSTORM)
    resp = client.post("/api/runs/WT-DSPD-25/redispatch")
    assert resp.status_code == 409


def test_redispatch_refuses_when_paused(client, github):
    # Paused at a user checkpoint is not "awaiting a dispatch" — the user acts next.
    seed_run(
        github,
        "WT-DSPE-26",
        stage=statefile.Stage.FULL_CHECKPOINT,
        stage_status=statefile.StageStatus.AWAITING_USER,
    )
    resp = client.post("/api/runs/WT-DSPE-26/redispatch")
    assert resp.status_code == 409


def test_redispatch_reports_a_dispatch_failure(github):
    seed_run(github, "WT-DSPF-27", stage=statefile.Stage.SUBMITTED)
    resp = _failing_client(github).post("/api/runs/WT-DSPF-27/redispatch")
    assert resp.status_code == 200
    body = resp.json()
    assert body["dispatched"] is False
    assert body["dispatch_error"]


def test_redispatch_resumes_a_failed_run(client, github, dispatcher):
    # §5.6 "resume from the last checkpoint" — the retry path for a failed run
    # (all three first live runs failed mid-stage and needed exactly this; the
    # old gate 409'd on stage_status=failed, leaving no retry path at all).
    seed_run(
        github,
        "WT-DSPG-28",
        stage=statefile.Stage.THRESHOLD_DRAFTING,
        stage_status=statefile.StageStatus.FAILED,
    )
    resp = client.post("/api/runs/WT-DSPG-28/redispatch")
    assert resp.status_code == 200
    assert resp.json() == {
        "run_id": "WT-DSPG-28",
        "resume_from": "THRESHOLD_DRAFTING",
        "dispatched": True,
    }
    assert dispatcher.calls[0]["inputs"] == {
        "run_id": "WT-DSPG-28",
        "resume_from": "THRESHOLD_DRAFTING",
    }


def test_redispatch_resumes_a_failed_mid_flight_stage(client, github, dispatcher):
    # ARCHITECT/REVIEW/ASSEMBLY are never dispatch targets on the happy path,
    # but a run that failed there retries from exactly that stage — an earlier
    # resume_from would fast-forward through checkpoints into a wrong re-pause.
    seed_run(
        github,
        "WT-DSPH-29",
        stage=statefile.Stage.REVIEW,
        stage_status=statefile.StageStatus.FAILED,
    )
    resp = client.post("/api/runs/WT-DSPH-29/redispatch")
    assert resp.status_code == 200
    assert resp.json()["resume_from"] == "REVIEW"
    assert dispatcher.calls[0]["inputs"]["resume_from"] == "REVIEW"


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


def test_revise_rejects_outline_artefact(client, github):
    # The outline is unbounded and has no /revise branch at all (brief §4/§7): it is refined
    # through the interview, not revised here. An "outline" value is rejected by the Literal.
    # ("threshold" IS accepted now — see the threshold-revision tests below.)
    _seed_complete(github, "WT-REDF-27")
    resp = client.post(
        "/api/runs/WT-REDF-27/revise", json={"artefact": "outline", "instructions": "x"}
    )
    assert resp.status_code == 422


# -- threshold revision (§7, brief §7) --------------------------------------------


def _seed_threshold_review(github, run_id: str, *, revisions_threshold: int = 0) -> None:
    """A run paused at THRESHOLD_REVIEW (the review screen open), optionally with some
    threshold revisions already used."""
    run = seed_run(
        github,
        run_id,
        stage=statefile.Stage.THRESHOLD_REVIEW,
        stage_status=statefile.StageStatus.AWAITING_USER,
    )
    if revisions_threshold:
        run.revisions["threshold"] = revisions_threshold
        github.files[run_path(run_id, "run.json")] = dump_json(run.to_dict())


def test_revise_threshold_commits_request_and_dispatches(client, github, dispatcher):
    _seed_threshold_review(github, "WT-THRA-35")
    resp = client.post(
        "/api/runs/WT-THRA-35/revise",
        json={"artefact": "threshold", "instructions": "Emphasise the accessibility mitigations."},
    )
    assert resp.status_code == 200
    assert resp.json() == {"run_id": "WT-THRA-35", "revision": 1, "dispatched": True}

    # rev_1/request.json committed with the instructions.
    request = json.loads(
        github.files[run_path("WT-THRA-35", "threshold", "revisions", "rev_1", "request.json")]
    )
    assert request["instructions"] == "Emphasise the accessibility mitigations."

    # run.json rewound to THRESHOLD_RECONCILING with the count incremented; governance dispatched
    # to re-run the reconciler (not FULL_DRAFTING — a revision is not a routing decision).
    run = statefile.RunState.from_dict(json.loads(github.files[run_path("WT-THRA-35", "run.json")]))
    assert run.stage is statefile.Stage.THRESHOLD_RECONCILING
    assert run.revisions["threshold"] == 1
    assert dispatcher.calls[0]["inputs"] == {
        "run_id": "WT-THRA-35",
        "resume_from": "THRESHOLD_RECONCILING",
    }
    status_doc = json.loads(github.files[run_path("WT-THRA-35", "status.json")])
    assert status_doc["overall_state"] == "running"


def test_revise_threshold_second_revision_increments_to_two(client, github):
    _seed_threshold_review(github, "WT-THRB-36", revisions_threshold=1)
    resp = client.post(
        "/api/runs/WT-THRB-36/revise", json={"artefact": "threshold", "instructions": "Once more."}
    )
    assert resp.status_code == 200
    assert resp.json()["revision"] == 2
    assert run_path("WT-THRB-36", "threshold", "revisions", "rev_2", "request.json") in github.files


def test_revise_threshold_refuses_over_the_cap(client, github, dispatcher):
    # Two revisions already used ⇒ the third is refused at the cap (brief §7), nothing dispatched.
    _seed_threshold_review(github, "WT-THRC-32", revisions_threshold=2)
    resp = client.post(
        "/api/runs/WT-THRC-32/revise", json={"artefact": "threshold", "instructions": "Again."}
    )
    assert resp.status_code == 409
    assert "cap" in resp.json()["detail"].lower() or "no further" in resp.json()["detail"].lower()
    assert dispatcher.calls == []


def test_revise_threshold_refuses_when_not_paused_at_review(client, github, dispatcher):
    # A threshold revision presupposes the review screen is open (paused at THRESHOLD_REVIEW).
    # A run still drafting, or already routed on, cannot revise the threshold artefact here.
    seed_run(github, "WT-THRD-33", stage=statefile.Stage.THRESHOLD_DRAFTING)
    resp = client.post(
        "/api/runs/WT-THRD-33/revise", json={"artefact": "threshold", "instructions": "Change it."}
    )
    assert resp.status_code == 409
    assert dispatcher.calls == []


def test_revise_threshold_rejects_empty_instructions(client, github):
    _seed_threshold_review(github, "WT-THRE-34")
    resp = client.post(
        "/api/runs/WT-THRE-34/revise", json={"artefact": "threshold", "instructions": "   "}
    )
    assert resp.status_code == 400
