"""Tests for the Brainstorm file-upload slice (TECH_SPEC §7, §9.2, §12.3/§12.4).

A public servant may upload a file instead of chatting, in three formats: plain text (seed
material fed through the interviewer to populate the outline — the primary path), Mermaid
(committed as the run's ``flow-map.mmd`` starting material), and HTML (committed as
``poc.html``). Two acknowledgements gate the upload.

LLM-free (§15): the Mermaid/HTML commit paths make no model call at all, and the plain-text
ingest is driven with a scripted transport (like the interviewer tests), so the whole slice is
exercised without the network. The acknowledgement gating and format validation are pure
boundary checks.
"""

from __future__ import annotations

import json

import pytest
import statefile
from conftest import TEST_SETTINGS, run_path, seed_run
from fastapi.testclient import TestClient
from llm import LLMClient, ScriptedTransport, resolve_model

from app import create_app
from brainstorm import Transcript, validate_mermaid, validate_poc_html
from brainstorm.mapgen import MapError
from brainstorm.poc import PocError
from dispatch import FakeDispatcher
from outline import Outline, render_initial_outline

NOW = statefile.utc_now_iso()


# -- helpers --------------------------------------------------------------------


def _make_llm(*payloads: dict):
    """A factory returning a fresh scripted client per call (interviewer + sufficiency judge
    share the Flash-Lite model, consumed in call order)."""
    model = resolve_model("interviewer")

    def factory() -> LLMClient:
        return LLMClient(
            transport=ScriptedTransport(responses={model: [json.dumps(p) for p in payloads]})
        )

    return factory


def _boom_llm():
    """A factory whose client must never be called (the Mermaid/HTML paths are LLM-free)."""

    def factory() -> LLMClient:
        def handler(**_):
            raise AssertionError("upload path made an unexpected LLM call")

        return LLMClient(transport=ScriptedTransport(handler=handler))

    return factory


def _app_client(github, make_llm) -> TestClient:
    return TestClient(
        create_app(
            github=github, dispatcher=FakeDispatcher(), settings=TEST_SETTINGS, make_llm=make_llm
        )
    )


def _seed_brainstorm(github, run_id: str) -> None:
    seed_run(github, run_id)  # default stage is BRAINSTORM
    github.files[run_path(run_id, "brainstorm", "outline.md")] = render_initial_outline(
        run_id, NOW
    ).encode("utf-8")


_MERMAID = "flowchart TD\n  Citizen -->|enquiry| AI[AI triage]\n  AI --> Officer"
_HTML = "<!doctype html><html><body><h1>My mock</h1><button>Go</button></body></html>"
_ACK = {"acknowledge_no_sensitive": True}


def _upload(client, run_id: str, **body):
    return client.post(f"/api/runs/{run_id}/brainstorm/upload", json=body)


# -- the shared validators (banner relaxation for user uploads) -----------------


def test_validate_poc_html_relaxes_banner_for_uploads():
    no_banner = "<!doctype html><html><body><h1>Mock</h1></body></html>"
    # A generated PoC still requires the §12.4 banner…
    with pytest.raises(PocError, match="limitations banner"):
        validate_poc_html(no_banner, require_banner=True)
    # …but a user upload is exempt (returns without raising).
    validate_poc_html(no_banner, require_banner=False)


def test_validate_poc_html_still_requires_a_document():
    with pytest.raises(PocError):
        validate_poc_html("just some words", require_banner=False)


def test_validate_mermaid_accepts_flowchart_and_rejects_prose():
    validate_mermaid(_MERMAID)  # no raise
    with pytest.raises(MapError):
        validate_mermaid("not a diagram")


# -- plain text → seed material (the primary path) ------------------------------


def test_upload_text_populates_outline_and_records_turn(github):
    _seed_brainstorm(github, "WT-SEED-22")
    interviewer = {
        "assistant_message": "I've drafted the problem and solution — who are the users?",
        "section_updates": {
            "problem": "Citizens wait weeks for enquiry replies.",
            "solution": "An AI assistant drafts replies for officer review.",
        },
        "title": "Enquiry Triage",
        "summary": "An AI assistant that triages enquiries.",
    }
    make_llm = _make_llm(interviewer, {"issues": []})
    resp = _upload(
        _app_client(github, make_llm),
        "WT-SEED-22",
        format="text",
        content="We run an enquiries team. Replies take weeks. We want AI to help draft them.",
        **_ACK,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["produced"] == "outline"
    assert body["assistant_message"].startswith("I've drafted")
    assert set(body["outline_delta"]["newly_resolved"]) == {"problem", "solution"}
    assert body["stage"] == "BRAINSTORM"

    outline = Outline.parse(
        github.files[run_path("WT-SEED-22", "brainstorm", "outline.md")].decode()
    )
    assert set(outline.resolved) == {"problem", "solution"}
    assert outline.frontmatter["title"] == "Enquiry Triage"

    # The upload is recorded as a user turn (verbatim), the interviewer's summary as the reply.
    transcript = Transcript.parse(
        github.files[run_path("WT-SEED-22", "brainstorm", "transcript.jsonl")]
    )
    assert [t.role for t in transcript.turns] == ["user", "assistant"]
    assert "enquiries team" in transcript.turns[0].text


def test_upload_text_reaches_interviewer_wrapped_as_untrusted(github):
    # §9.2: the uploaded document is delimited as untrusted content in the prompt.
    _seed_brainstorm(github, "WT-SEDW-23")
    seen: list[str] = []

    def make_llm():
        def handler(**kw):
            seen.append(kw["user"])
            return json.dumps({"assistant_message": "Noted.", "section_updates": {}})

        return LLMClient(transport=ScriptedTransport(handler=handler))

    resp = _upload(
        _app_client(github, make_llm),
        "WT-SEDW-23",
        format="text",
        content="SENTINEL-DOCUMENT-BODY",
        **_ACK,
    )
    assert resp.status_code == 200
    prompt = next(u for u in seen)
    assert "SENTINEL-DOCUMENT-BODY" in prompt
    assert "<untrusted_user_content>" in prompt  # wrapped as data, never instructions (§9.2)


# -- Mermaid → flow-map.mmd (LLM-free) ------------------------------------------


def test_upload_mermaid_commits_flow_map_and_returns_source(github):
    _seed_brainstorm(github, "WT-MMAP-24")
    resp = _upload(
        _app_client(github, _boom_llm()),
        "WT-MMAP-24",
        format="mermaid",
        content=_MERMAID,
        acknowledge_no_sensitive=True,
        acknowledge_starting_material=True,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["produced"] == "map"
    assert body["mermaid"] == _MERMAID  # returned for the SPA to render + post the SVG
    assert github.files[run_path("WT-MMAP-24", "brainstorm", "flow-map.mmd")].decode() == _MERMAID


def test_upload_mermaid_requires_starting_material_ack(github):
    _seed_brainstorm(github, "WT-MMAK-25")
    resp = _upload(
        _app_client(github, _boom_llm()),
        "WT-MMAK-25",
        format="mermaid",
        content=_MERMAID,
        acknowledge_no_sensitive=True,  # missing the starting-material ack
    )
    assert resp.status_code == 400
    assert "starting material" in resp.json()["detail"].lower()
    assert run_path("WT-MMAK-25", "brainstorm", "flow-map.mmd") not in github.files


def test_upload_mermaid_rejects_non_mermaid(github):
    _seed_brainstorm(github, "WT-MMRJ-26")
    resp = _upload(
        _app_client(github, _boom_llm()),
        "WT-MMRJ-26",
        format="mermaid",
        content="This is just prose, not a diagram.",
        acknowledge_no_sensitive=True,
        acknowledge_starting_material=True,
    )
    assert resp.status_code == 400
    assert run_path("WT-MMRJ-26", "brainstorm", "flow-map.mmd") not in github.files


# -- HTML → poc.html (LLM-free, banner requirement relaxed) ---------------------


def test_upload_html_commits_poc_without_requiring_banner(github):
    # A user-supplied PoC is exempt from the §12.4 limitations-banner requirement.
    _seed_brainstorm(github, "WT-HTMK-27")
    resp = _upload(
        _app_client(github, _boom_llm()),
        "WT-HTMK-27",
        format="html",
        content=_HTML,  # no poc-limitations banner
        **_ACK,
    )
    assert resp.status_code == 200
    assert resp.json() == {"produced": "poc"}
    assert github.files[run_path("WT-HTMK-27", "brainstorm", "poc.html")].decode() == _HTML


def test_upload_html_rejects_non_html(github):
    _seed_brainstorm(github, "WT-HTRJ-28")
    resp = _upload(
        _app_client(github, _boom_llm()),
        "WT-HTRJ-28",
        format="html",
        content="not html at all",
        **_ACK,
    )
    assert resp.status_code == 400
    assert run_path("WT-HTRJ-28", "brainstorm", "poc.html") not in github.files


# -- shared acknowledgement gating + stage guard --------------------------------


def test_upload_requires_no_sensitive_ack(github):
    _seed_brainstorm(github, "WT-NACK-29")
    resp = _upload(
        _app_client(github, _boom_llm()),
        "WT-NACK-29",
        format="html",
        content=_HTML,
        acknowledge_no_sensitive=False,
    )
    assert resp.status_code == 400
    assert "sensitive" in resp.json()["detail"].lower()
    assert run_path("WT-NACK-29", "brainstorm", "poc.html") not in github.files


def test_upload_rejects_empty_content(github):
    _seed_brainstorm(github, "WT-MTYX-32")
    resp = _upload(
        _app_client(github, _boom_llm()),
        "WT-MTYX-32",
        format="text",
        content="   ",
        **_ACK,
    )
    assert resp.status_code == 400


def test_upload_409_after_brainstorm(github):
    seed_run(github, "WT-GATE-33", stage=statefile.Stage.SUBMITTED)
    resp = _upload(
        _app_client(github, _boom_llm()),
        "WT-GATE-33",
        format="text",
        content="anything",
        **_ACK,
    )
    assert resp.status_code == 409
