"""Tests for the Brainstorm interview slice (TECH_SPEC §7, §7.1).

LLM-free (§15): a scripted transport plays the interviewer and sufficiency judge (both
Flash-Lite, so they share one model queue, consumed in call order). Covers the two agents in
isolation and the two endpoints end-to-end against the in-memory GitHub fake.
"""

from __future__ import annotations

import json

import pytest
import statefile
from conftest import TEST_SETTINGS, run_path, seed_run
from fastapi.testclient import TestClient
from llm import LLMClient, ScriptedTransport, resolve_model

from app import create_app
from brainstorm import Transcript, assess_sufficiency, run_interviewer
from brainstorm.interviewer import BrainstormError
from dispatch import FakeDispatcher
from outline import SECTION_IDS, Outline, render_initial_outline

NOW = statefile.utc_now_iso()


# -- helpers --------------------------------------------------------------------


def _handler_client(payload: dict) -> LLMClient:
    return LLMClient(transport=ScriptedTransport(handler=lambda **_: json.dumps(payload)))


def _boom(**_):
    raise AssertionError("the sufficiency judge should not have been called")


def _fresh_outline() -> Outline:
    return Outline.parse(render_initial_outline("WT-ABCD-EF", NOW))


def _complete_outline() -> Outline:
    doc = _fresh_outline()
    doc.apply_updates({sid: f"body for {sid}" for sid in SECTION_IDS}, now=NOW)
    return doc


def _make_llm(*payloads: dict):
    """A factory returning a fresh scripted client per call. The interviewer and the
    sufficiency judge resolve to the same Flash-Lite model, so ``payloads`` are consumed in
    call order (interviewer first, judge second) from one model queue."""
    model = resolve_model("interviewer")

    def factory() -> LLMClient:
        return LLMClient(
            transport=ScriptedTransport(responses={model: [json.dumps(p) for p in payloads]})
        )

    return factory


def _app_client(github, make_llm) -> TestClient:
    return TestClient(
        create_app(
            github=github, dispatcher=FakeDispatcher(), settings=TEST_SETTINGS, make_llm=make_llm
        )
    )


def _seed_brainstorm(github, run_id: str, *, outline_md: str | None = None) -> None:
    seed_run(github, run_id)  # default stage is BRAINSTORM
    github.files[run_path(run_id, "brainstorm", "outline.md")] = (
        outline_md or render_initial_outline(run_id, NOW)
    ).encode("utf-8")


# -- the interviewer agent ------------------------------------------------------


def test_interviewer_parses_and_filters_unknown_ids():
    client = _handler_client(
        {
            "assistant_message": "What data does it use?",
            "section_updates": {"problem": "Long waits.", "bogus": "drop me"},
            "title": "Triage",
            "summary": "An assistant.",
        }
    )
    result = run_interviewer(client, outline_md="o", dialogue="", user_message="hi")
    assert result.assistant_message == "What data does it use?"
    assert result.section_updates == {"problem": "Long waits."}  # unknown id dropped (§7.1)
    assert result.title == "Triage"
    assert result.summary == "An assistant."


def test_interviewer_requires_assistant_message():
    client = _handler_client({"assistant_message": "   ", "section_updates": {}})
    with pytest.raises(BrainstormError):
        run_interviewer(client, outline_md="o", dialogue="", user_message="hi")


def test_interviewer_title_summary_optional():
    client = _handler_client({"assistant_message": "Tell me about the problem?"})
    result = run_interviewer(client, outline_md="o", dialogue="", user_message="hi")
    assert result.title is None
    assert result.summary is None
    assert result.section_updates == {}


# -- the sufficiency judge ------------------------------------------------------


def test_interviewer_and_sufficiency_share_the_lite_model():
    # The shared model id is what lets the endpoints script both calls on one queue.
    assert resolve_model("interviewer") == resolve_model("sufficiency")


def test_sufficiency_lists_unresolved_and_skips_judge_when_nothing_resolved():
    doc = _fresh_outline()
    res = assess_sufficiency(
        doc, doc.render(), LLMClient(transport=ScriptedTransport(handler=_boom))
    )
    assert res["ready"] is False
    assert {m["section_id"] for m in res["missing"]} == set(SECTION_IDS)
    assert all(m["reason"] == "unresolved" for m in res["missing"])


def test_sufficiency_ready_when_complete_and_no_issues():
    doc = _complete_outline()
    client = _handler_client({"issues": []})
    assert assess_sufficiency(doc, doc.render(), client) == {"ready": True, "missing": []}


def test_sufficiency_appends_judged_issue():
    doc = _complete_outline()
    client = _handler_client(
        {"issues": [{"section_id": "happy_path", "reason": "contradicts the data section"}]}
    )
    res = assess_sufficiency(doc, doc.render(), client)
    assert res["ready"] is False
    assert res["missing"] == [
        {"section_id": "happy_path", "reason": "contradicts the data section"}
    ]


def test_sufficiency_ignores_judged_issue_for_unresolved_section():
    # A judge that (wrongly) flags an unresolved section adds nothing — it is already covered
    # deterministically as "unresolved", and the judged half only speaks to resolved sections.
    doc = _fresh_outline()
    doc.apply_updates({"problem": "p"}, now=NOW)
    client = _handler_client({"issues": [{"section_id": "data", "reason": "made up"}]})
    reasons = {
        (m["section_id"], m["reason"])
        for m in assess_sufficiency(doc, doc.render(), client)["missing"]
    }
    assert ("data", "unresolved") in reasons
    assert ("data", "made up") not in reasons


# -- POST /brainstorm/message ---------------------------------------------------


def test_message_turn_resolves_section_and_commits(github):
    _seed_brainstorm(github, "WT-MSGR-22")
    interviewer = {
        "assistant_message": "What data does it touch?",
        "section_updates": {"problem": "Citizens wait too long for replies."},
        "title": "Enquiry Triage",
        "summary": "An AI assistant that triages enquiries.",
    }
    client = _app_client(github, _make_llm(interviewer, {"issues": []}))
    resp = client.post(
        "/api/runs/WT-MSGR-22/brainstorm/message", json={"message": "We have long waits."}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["assistant_message"] == "What data does it touch?"
    assert body["outline_delta"]["newly_resolved"] == ["problem"]
    assert body["outline_delta"]["title_changed"] is True
    assert body["sufficiency"]["ready"] is False  # eight sections still unresolved
    assert body["stage"] == "BRAINSTORM"

    outline = Outline.parse(
        github.files[run_path("WT-MSGR-22", "brainstorm", "outline.md")].decode()
    )
    assert outline.resolved == ["problem"]
    assert outline.frontmatter["title"] == "Enquiry Triage"

    transcript = Transcript.parse(
        github.files[run_path("WT-MSGR-22", "brainstorm", "transcript.jsonl")]
    )
    assert [t.role for t in transcript.turns] == ["user", "assistant"]
    assert transcript.turns[0].text == "We have long waits."
    assert transcript.turns[1].text == "What data does it touch?"


def test_message_pure_question_turn_leaves_outline_unchanged(github):
    _seed_brainstorm(github, "WT-MSGQ-23")
    # No section updates and nothing resolved yet ⇒ the sufficiency judge is not called, so a
    # single interviewer response is the whole script.
    client = _app_client(
        github, _make_llm({"assistant_message": "Tell me the problem?", "section_updates": {}})
    )
    resp = client.post("/api/runs/WT-MSGQ-23/brainstorm/message", json={"message": "hi"})
    assert resp.status_code == 200
    assert resp.json()["outline_delta"] is None
    assert resp.json()["sufficiency"]["ready"] is False

    # The transcript is still committed (the turn happened); the outline is untouched.
    assert run_path("WT-MSGQ-23", "brainstorm", "transcript.jsonl") in github.files
    outline = Outline.parse(
        github.files[run_path("WT-MSGQ-23", "brainstorm", "outline.md")].decode()
    )
    assert outline.resolved == []


def test_message_carries_prior_dialogue_to_the_interviewer(github):
    prior = (
        b'{"role": "user", "text": "first message", "ts": "t"}\n'
        b'{"role": "assistant", "text": "a reply", "ts": "t"}\n'
    )
    _seed_brainstorm(github, "WT-MSGD-24")
    github.files[run_path("WT-MSGD-24", "brainstorm", "transcript.jsonl")] = prior
    seen: list[str] = []

    def make_llm():
        def handler(**kw):
            seen.append(kw["user"])
            return json.dumps({"assistant_message": "next?", "section_updates": {}})

        return LLMClient(transport=ScriptedTransport(handler=handler))

    client = _app_client(github, make_llm)
    resp = client.post(
        "/api/runs/WT-MSGD-24/brainstorm/message", json={"message": "second message"}
    )
    assert resp.status_code == 200
    # The prior turns reached the interviewer prompt, and the new message is present too.
    assert any("first message" in u and "a reply" in u for u in seen)
    assert any("second message" in u for u in seen)
    transcript = Transcript.parse(
        github.files[run_path("WT-MSGD-24", "brainstorm", "transcript.jsonl")]
    )
    assert len(transcript.turns) == 4  # two prior + this turn's two


def test_message_empty_400(github):
    _seed_brainstorm(github, "WT-MSGE-25")
    client = _app_client(github, _make_llm())
    assert (
        client.post("/api/runs/WT-MSGE-25/brainstorm/message", json={"message": "   "}).status_code
        == 400
    )


def test_message_409_after_brainstorm(github):
    seed_run(github, "WT-MSGX-26", stage=statefile.Stage.SUBMITTED)
    client = _app_client(github, _make_llm())
    assert (
        client.post("/api/runs/WT-MSGX-26/brainstorm/message", json={"message": "hi"}).status_code
        == 409
    )


# -- POST /brainstorm/edit-outline ----------------------------------------------


def test_edit_outline_sets_section_and_runs_sufficiency(github):
    _seed_brainstorm(github, "WT-EDTS-27")
    client = _app_client(github, _make_llm({"issues": []}))  # only the judge runs
    resp = client.post(
        "/api/runs/WT-EDTS-27/brainstorm/edit-outline",
        json={"sections": {"problem": "Edited problem statement."}, "title": "Edited"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["outline_delta"]["newly_resolved"] == ["problem"]
    assert body["sufficiency"]["ready"] is False

    outline = Outline.parse(
        github.files[run_path("WT-EDTS-27", "brainstorm", "outline.md")].decode()
    )
    assert outline.section_body("problem") == "Edited problem statement."
    assert outline.frontmatter["title"] == "Edited"


def test_edit_outline_unknown_section_400(github):
    _seed_brainstorm(github, "WT-EDTU-28")
    client = _app_client(github, _make_llm())
    resp = client.post(
        "/api/runs/WT-EDTU-28/brainstorm/edit-outline", json={"sections": {"bogus": "x"}}
    )
    assert resp.status_code == 400


def test_edit_outline_empty_body_400(github):
    _seed_brainstorm(github, "WT-EDTE-29")
    client = _app_client(github, _make_llm())
    assert client.post("/api/runs/WT-EDTE-29/brainstorm/edit-outline", json={}).status_code == 400


def test_edit_outline_409_after_brainstorm(github):
    seed_run(github, "WT-EDTX-32", stage=statefile.Stage.THRESHOLD_REVIEW)
    client = _app_client(github, _make_llm())
    resp = client.post(
        "/api/runs/WT-EDTX-32/brainstorm/edit-outline", json={"sections": {"problem": "x"}}
    )
    assert resp.status_code == 409
