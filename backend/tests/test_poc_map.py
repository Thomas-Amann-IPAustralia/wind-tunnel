"""Tests for the PoC / flow-map / feasibility slice (TECH_SPEC §7, §12.3/§12.4).

LLM-free (§15): a scripted transport plays the feasibility gate (Flash-Lite) and the PoC / map
generators (Flash), keyed by resolved model id. Covers the three agents in isolation and the
three endpoints end-to-end against the in-memory GitHub fake.
"""

from __future__ import annotations

import json

import pytest
import statefile
from conftest import TEST_SETTINGS, run_path, seed_run
from fastapi.testclient import TestClient
from llm import LLMClient, ScriptedTransport, resolve_model

from app import create_app
from brainstorm import assess_feasibility, generate_flow_map, generate_poc
from brainstorm.feasibility import FeasibilityError
from brainstorm.mapgen import MapError
from brainstorm.poc import PocError
from dispatch import FakeDispatcher
from outline import Outline, render_initial_outline

NOW = statefile.utc_now_iso()

_LITE = resolve_model("feasibility_gate")  # interviewer/sufficiency/feasibility_gate share this
_FLASH = resolve_model("poc_gen")  # poc_gen and map_gen share the flash tier


# -- fixtures / helpers ---------------------------------------------------------


def _poc_html() -> str:
    return (
        '<!doctype html>\n<html><head><meta charset="utf-8"><style>body{font-family:serif}</style>'
        "</head><body>"
        '<section class="poc-limitations"><h2>What this mock does not do</h2>'
        "<p>No real case data — every record shown is invented. No connection to the real "
        "case-management system. The risk scores are illustrative, not computed.</p></section>"
        "<main><h1>Enquiry triage</h1><button>Show result</button></main>"
        "</body></html>"
    )


def _mermaid() -> str:
    return "flowchart TD\n  Citizen -->|enquiry text| AI[AI triage]\n  AI -->|risk score| Officer"


def _handler_client(fn) -> LLMClient:
    return LLMClient(transport=ScriptedTransport(handler=fn))


def _make_llm(*, lite: list[str] | None = None, flash: list[str] | None = None):
    """Factory returning a fresh scripted client per call, responses keyed by model id (the
    feasibility gate resolves to the lite tier; the PoC/map generators to the flash tier)."""

    def factory() -> LLMClient:
        responses: dict[str, object] = {}
        if lite is not None:
            responses[_LITE] = list(lite)
        if flash is not None:
            responses[_FLASH] = list(flash)
        return LLMClient(transport=ScriptedTransport(responses=responses))

    return factory


def _app_client(github, make_llm) -> TestClient:
    return TestClient(
        create_app(
            github=github, dispatcher=FakeDispatcher(), settings=TEST_SETTINGS, make_llm=make_llm
        )
    )


def _seed_brainstorm(github, run_id: str, *, resolved: dict[str, str] | None = None) -> None:
    seed_run(github, run_id)  # default stage is BRAINSTORM
    outline = Outline.parse(render_initial_outline(run_id, NOW))
    if resolved:
        outline.apply_updates(resolved, now=NOW)
    github.files[run_path(run_id, "brainstorm", "outline.md")] = outline.render().encode("utf-8")


# -- the feasibility gate -------------------------------------------------------


def test_feasibility_parses_verdict():
    client = _handler_client(
        lambda **_: json.dumps({"feasible": True, "reason": "It has a triage screen to mock."})
    )
    res = assess_feasibility(client, ux_ui="A triage screen.", happy_path="Officer reviews it.")
    assert res.feasible is True
    assert res.reason == "It has a triage screen to mock."


def test_feasibility_rejects_missing_boolean():
    client = _handler_client(lambda **_: json.dumps({"reason": "no verdict"}))
    with pytest.raises(FeasibilityError):
        assess_feasibility(client, ux_ui="x", happy_path="y")


def test_feasibility_rejects_missing_reason():
    client = _handler_client(lambda **_: json.dumps({"feasible": False}))
    with pytest.raises(FeasibilityError):
        assess_feasibility(client, ux_ui="x", happy_path="y")


def test_feasibility_reads_ux_and_happy_path():
    seen: list[str] = []

    def handler(**kw):
        seen.append(kw["user"])
        return json.dumps({"feasible": False, "reason": "Headless — a flow map suits it better."})

    res = assess_feasibility(
        _handler_client(handler),
        ux_ui="No interface — this runs headless.",
        happy_path="A nightly batch classifies records.",
    )
    assert res.feasible is False
    assert any("headless" in u.lower() and "nightly batch" in u.lower() for u in seen)


def test_feasibility_empty_sections_are_passed_as_not_yet_described():
    seen: list[str] = []

    def handler(**kw):
        seen.append(kw["user"])
        return json.dumps({"feasible": True, "reason": "ok"})

    assess_feasibility(_handler_client(handler), ux_ui="   ", happy_path="")
    assert any("(not yet described)" in u for u in seen)


# -- the PoC generator ----------------------------------------------------------


def test_generate_poc_ok_and_records_provenance():
    client = _handler_client(lambda **_: _poc_html())
    res = generate_poc(client, outline_md="the outline")
    assert res.html.startswith("<!doctype html>")
    assert "poc-limitations" in res.html
    assert res.model == _FLASH
    assert res.prompt_version == "v1"


def test_generate_poc_strips_code_fence():
    fenced = "```html\n" + _poc_html() + "\n```"
    res = generate_poc(_handler_client(lambda **_: fenced), outline_md="o")
    assert res.html.startswith("<!doctype html>")
    assert res.html.endswith("</html>")


def test_generate_poc_rejects_non_html():
    with pytest.raises(PocError):
        generate_poc(_handler_client(lambda **_: "I cannot build that."), outline_md="o")


def test_generate_poc_rejects_missing_banner():
    no_banner = "<!doctype html><html><body><h1>Triage</h1></body></html>"
    with pytest.raises(PocError, match="limitations banner"):
        generate_poc(_handler_client(lambda **_: no_banner), outline_md="o")


def test_generate_poc_rejects_empty():
    with pytest.raises(PocError):
        generate_poc(_handler_client(lambda **_: "   "), outline_md="o")


# -- the flow-map generator -----------------------------------------------------


def test_generate_flow_map_ok():
    res = generate_flow_map(_handler_client(lambda **_: _mermaid()), outline_md="o")
    assert res.mermaid.startswith("flowchart TD")
    assert res.model == _FLASH


def test_generate_flow_map_strips_fence():
    fenced = "```mermaid\n" + _mermaid() + "\n```"
    res = generate_flow_map(_handler_client(lambda **_: fenced), outline_md="o")
    assert res.mermaid.startswith("flowchart TD")
    assert not res.mermaid.endswith("`")


def test_generate_flow_map_tolerates_leading_comment():
    src = "%% information flow\nflowchart LR\n  A --> B"
    res = generate_flow_map(_handler_client(lambda **_: src), outline_md="o")
    assert "flowchart LR" in res.mermaid


def test_generate_flow_map_rejects_prose():
    with pytest.raises(MapError):
        generate_flow_map(
            _handler_client(lambda **_: "Here is a diagram of the flow."), outline_md="o"
        )


def test_generate_flow_map_includes_poc_when_present():
    seen: list[str] = []

    def handler(**kw):
        seen.append(kw["user"])
        return _mermaid()

    generate_flow_map(_handler_client(handler), outline_md="o", poc_html="<html>MOCK-UI</html>")
    assert any("MOCK-UI" in u for u in seen)


# -- POST /poc ------------------------------------------------------------------


def test_poc_feasible_commits_poc_and_feasibility(github):
    _seed_brainstorm(github, "WT-PCAF-22")
    make_llm = _make_llm(
        lite=[json.dumps({"feasible": True, "reason": "Has a triage screen to mock."})],
        flash=[_poc_html()],
    )
    resp = _app_client(github, make_llm).post("/api/runs/WT-PCAF-22/poc")
    assert resp.status_code == 200
    assert resp.json() == {"produced": "poc", "reason": "Has a triage screen to mock."}

    poc = github.files[run_path("WT-PCAF-22", "brainstorm", "poc.html")].decode()
    assert "poc-limitations" in poc
    feasibility = json.loads(github.files[run_path("WT-PCAF-22", "brainstorm", "feasibility.json")])
    assert feasibility["feasible"] is True
    assert feasibility["reason"] == "Has a triage screen to mock."
    # No map was produced on the feasible branch.
    assert run_path("WT-PCAF-22", "brainstorm", "flow-map.mmd") not in github.files


def test_poc_not_feasible_produces_map(github):
    _seed_brainstorm(github, "WT-PCAM-23")
    make_llm = _make_llm(
        lite=[json.dumps({"feasible": False, "reason": "Headless — a flow map fits better."})],
        flash=[_mermaid()],
    )
    resp = _app_client(github, make_llm).post("/api/runs/WT-PCAM-23/poc")
    assert resp.status_code == 200
    body = resp.json()
    assert body["produced"] == "map"
    assert body["reason"] == "Headless — a flow map fits better."
    assert body["mermaid"].startswith("flowchart TD")

    assert run_path("WT-PCAM-23", "brainstorm", "flow-map.mmd") in github.files
    assert run_path("WT-PCAM-23", "brainstorm", "poc.html") not in github.files
    feasibility = json.loads(github.files[run_path("WT-PCAM-23", "brainstorm", "feasibility.json")])
    assert feasibility["feasible"] is False


def test_poc_missing_banner_is_502(github):
    _seed_brainstorm(github, "WT-PCAB-24")
    make_llm = _make_llm(
        lite=[json.dumps({"feasible": True, "reason": "ok"})],
        flash=["<!doctype html><html><body>no banner</body></html>"],
    )
    resp = _app_client(github, make_llm).post("/api/runs/WT-PCAB-24/poc")
    assert resp.status_code == 502
    # Nothing was committed — the feasibility.json only lands with a valid artefact.
    assert run_path("WT-PCAB-24", "brainstorm", "poc.html") not in github.files


def test_poc_409_after_brainstorm(github):
    seed_run(github, "WT-PCAX-25", stage=statefile.Stage.SUBMITTED)
    resp = _app_client(github, _make_llm()).post("/api/runs/WT-PCAX-25/poc")
    assert resp.status_code == 409


# -- POST /flow-map -------------------------------------------------------------


def test_flow_map_commits_mmd_and_returns_source(github):
    _seed_brainstorm(github, "WT-MAPG-26")
    resp = _app_client(github, _make_llm(flash=[_mermaid()])).post("/api/runs/WT-MAPG-26/flow-map")
    assert resp.status_code == 200
    body = resp.json()
    assert body["produced"] == "map"
    assert body["mermaid"].startswith("flowchart TD")
    assert (
        github.files[run_path("WT-MAPG-26", "brainstorm", "flow-map.mmd")]
        .decode()
        .startswith("flowchart TD")
    )


def test_flow_map_includes_existing_poc(github):
    _seed_brainstorm(github, "WT-MAPP-27")
    github.files[run_path("WT-MAPP-27", "brainstorm", "poc.html")] = b"<html>MOCK-UI</html>"
    seen: list[str] = []

    def make_llm():
        def handler(**kw):
            seen.append(kw["user"])
            return _mermaid()

        return LLMClient(transport=ScriptedTransport(handler=handler))

    resp = _app_client(github, make_llm).post("/api/runs/WT-MAPP-27/flow-map")
    assert resp.status_code == 200
    assert any("MOCK-UI" in u for u in seen)  # the PoC reached the map prompt


def test_flow_map_409_after_brainstorm(github):
    seed_run(github, "WT-MAPX-28", stage=statefile.Stage.THRESHOLD_REVIEW)
    resp = _app_client(github, _make_llm()).post("/api/runs/WT-MAPX-28/flow-map")
    assert resp.status_code == 409


# -- POST /flow-map/svg ---------------------------------------------------------


def test_flow_map_svg_commits(github):
    _seed_brainstorm(github, "WT-SWGC-29")
    github.files[run_path("WT-SWGC-29", "brainstorm", "flow-map.mmd")] = _mermaid().encode()
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><g></g></svg>'
    resp = _app_client(github, _make_llm()).post(
        "/api/runs/WT-SWGC-29/flow-map/svg", json={"svg": svg}
    )
    assert resp.status_code == 200
    assert resp.json()["committed"] is True
    assert github.files[run_path("WT-SWGC-29", "brainstorm", "flow-map.svg")].decode() == svg


def test_flow_map_svg_requires_mmd_first(github):
    _seed_brainstorm(github, "WT-SWGM-34")  # no flow-map.mmd committed
    resp = _app_client(github, _make_llm()).post(
        "/api/runs/WT-SWGM-34/flow-map/svg", json={"svg": "<svg></svg>"}
    )
    assert resp.status_code == 409


def test_flow_map_svg_rejects_non_svg(github):
    _seed_brainstorm(github, "WT-SWGN-35")
    github.files[run_path("WT-SWGN-35", "brainstorm", "flow-map.mmd")] = _mermaid().encode()
    resp = _app_client(github, _make_llm()).post(
        "/api/runs/WT-SWGN-35/flow-map/svg", json={"svg": "not an svg"}
    )
    assert resp.status_code == 400


def test_flow_map_svg_rejects_script(github):
    _seed_brainstorm(github, "WT-SWGS-32")
    github.files[run_path("WT-SWGS-32", "brainstorm", "flow-map.mmd")] = _mermaid().encode()
    resp = _app_client(github, _make_llm()).post(
        "/api/runs/WT-SWGS-32/flow-map/svg",
        json={"svg": "<svg><script>alert(1)</script></svg>"},
    )
    assert resp.status_code == 400


def test_flow_map_svg_409_after_brainstorm(github):
    seed_run(github, "WT-SWGX-33", stage=statefile.Stage.FULL_DRAFTING)
    resp = _app_client(github, _make_llm()).post(
        "/api/runs/WT-SWGX-33/flow-map/svg", json={"svg": "<svg></svg>"}
    )
    assert resp.status_code == 409
