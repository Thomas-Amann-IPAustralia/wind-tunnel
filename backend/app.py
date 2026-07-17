"""FastAPI endpoints (TECH_SPEC §7) — the slice this build covers.

Run creation, the Brainstorm interview (``/brainstorm/message`` →
interviewer + sufficiency; ``/brainstorm/edit-outline`` → canvas edit), the PoC and
flow-map synthesis (``/poc`` → feasibility gate then PoC or map; ``/flow-map`` →
Mermaid; ``/flow-map/svg`` → the SPA posts back the client-rendered SVG, CLAUDE.md §9),
the status proxy, the artefact download proxy, submission into Governance, threshold
routing, checkpoint answers (``/answers`` → ``FULL_REVISING``), and revision
(``/revise``: ``poc``/``flow_map`` regenerate from the amended outline while at
``BRAINSTORM`` with the ≤2 cap; ``threshold`` re-runs ``THRESHOLD_RECONCILING`` while
paused at ``THRESHOLD_REVIEW``; ``full`` dispatches ``USER_REVISION`` post-``COMPLETE``),
re-dispatch (``/redispatch`` re-kicks a run whose ``workflow_dispatch`` never took, §5.7),
and resume-by-code. The outline is unbounded and has no ``/revise`` branch (brief §4/§7).

A dispatch that fails after its state transition is committed is **not** fatal
(§5.7 — ``workflow_dispatch`` is fire-and-forget, the SPA watches ``status.json``):
the dispatching endpoints return ``dispatched: false`` + ``dispatch_error`` rather
than a 502, so a run is never stranded, and ``/redispatch`` re-fires it.

**Statelessness (§14).** Render's disk is ephemeral and a cold instance has no
memory of any run, so every endpoint re-reads ``run.json``/``status.json``
from the repo on every call rather than trusting in-process state — the repo
is the only durable store (CLAUDE.md §3).

**Shared run-state code (packaging note, STATUS.md handoff step 1).** Rather
than vendor ``pipeline/statefile.py``/``status.py``/``runcode.py`` into the
backend — forking the one owner of the run-code/run.json/status.json facts
(CLAUDE.md §3 "one owner per fact") — this module adds ``pipeline/`` to
``sys.path`` and imports them directly. Both deployables share the one repo at
runtime (TECH_SPEC §1), so this is a real import, not a copy.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable, Literal

_PIPELINE_DIR = Path(__file__).resolve().parent.parent / "pipeline"
if str(_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_DIR))

import runcode  # noqa: E402 — after the sys.path shim, see module docstring
import statefile  # noqa: E402
import status as status_module  # noqa: E402  (avoid shadowing fastapi.status below)
from fastapi import Depends, FastAPI, Header, HTTPException  # noqa: E402
from fastapi import status as http_status  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import Response  # noqa: E402
from llm import GeminiTransport, LLMClient, LLMError  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from brainstorm import (  # noqa: E402
    Transcript,
    assess_feasibility,
    assess_sufficiency,
    generate_flow_map,
    generate_poc,
    run_interviewer,
)
from brainstorm.feasibility import FeasibilityError  # noqa: E402
from brainstorm.interviewer import BrainstormError  # noqa: E402
from brainstorm.mapgen import MapError  # noqa: E402
from brainstorm.poc import PocError  # noqa: E402
from config import Settings, load_settings  # noqa: E402
from dispatch import Dispatcher, DispatchError, WorkflowDispatcher  # noqa: E402
from github_io import GitHubClient, GitHubError, RestGitHubClient  # noqa: E402
from outline import Outline, OutlineError, render_initial_outline  # noqa: E402

# name -> path within runs/<id>/, and its download media type (§7 artefact proxy;
# "name is allow-listed; arbitrary repo paths are refused").
_ARTEFACTS: dict[str, tuple[str, str]] = {
    "outline.md": ("artefacts/outline.md", "text/markdown; charset=utf-8"),
    "threshold.md": ("artefacts/threshold.md", "text/markdown; charset=utf-8"),
    "assessment.ipynb": ("artefacts/assessment.ipynb", "application/x-ipynb+json"),
    "assessment.html": ("artefacts/assessment.html", "text/html; charset=utf-8"),
    # Brainstorm optional artefacts (§6.3/§6.4). The SPA displays the PoC in a
    # sandboxed iframe and re-renders the flow map from its Mermaid source on
    # resume; both are served here so the canvas can restore them (CLAUDE.md §9).
    "poc.html": ("brainstorm/poc.html", "text/html; charset=utf-8"),
    "flow-map.mmd": ("brainstorm/flow-map.mmd", "text/plain; charset=utf-8"),
}

# The dispatched stages a run can be re-kicked from (§5.7), mapped to the
# ``resume_from`` the original dispatch used. SUBMITTED is a gate whose pipeline
# entry is THRESHOLD_DRAFTING; every other stage here is entered by resuming from
# itself. Paused (AWAITING_USER) and terminal stages are absent — they are not
# waiting on a dispatch. (See ``/redispatch``.)
_REDISPATCH_RESUME_FROM: dict[statefile.Stage, str] = {
    statefile.Stage.SUBMITTED: "THRESHOLD_DRAFTING",
    statefile.Stage.THRESHOLD_DRAFTING: "THRESHOLD_DRAFTING",
    statefile.Stage.THRESHOLD_RECONCILING: "THRESHOLD_RECONCILING",
    statefile.Stage.FULL_DRAFTING: "FULL_DRAFTING",
    statefile.Stage.FULL_REVISING: "FULL_REVISING",
    statefile.Stage.USER_REVISION: "USER_REVISION",
}


class RouteBody(BaseModel):
    outcome: Literal["conclude", "full"]


class AnswerItem(BaseModel):
    question_id: str
    value: str


class AnswersBody(BaseModel):
    answers: list[AnswerItem] = []
    skips: list[str] = []


class ReviseBody(BaseModel):
    # The brainstorm artefacts ("poc"/"flow_map") regenerate from the amended outline on the
    # backend while at BRAINSTORM; "threshold" re-runs THRESHOLD_RECONCILING while paused at
    # THRESHOLD_REVIEW; "full" dispatches USER_REVISION post-COMPLETE (§5.8, §7). The outline is
    # unbounded and has no /revise branch (brief §4, §7 — an "outline" value is a 422; see
    # statefile.REVISION_ARTEFACTS).
    artefact: Literal["poc", "flow_map", "threshold", "full"]
    instructions: str


class MessageBody(BaseModel):
    message: str


class EditOutlineBody(BaseModel):
    # A canvas edit is a per-section patch (§7.1 "replaces whole section bodies between
    # anchors"), never raw markdown — so a user can never break the anchors or front-matter.
    sections: dict[str, str] = {}
    title: str | None = None
    summary: str | None = None


class FlowMapSvgBody(BaseModel):
    # The SPA renders the committed flow-map.mmd to SVG in-browser (mermaid.js) and posts it
    # back here to commit (CLAUDE.md §9 — Render's free tier can't run headless Chromium).
    svg: str


def create_app(
    *,
    github: GitHubClient | None = None,
    dispatcher: Dispatcher | None = None,
    settings: Settings | None = None,
    make_llm: Callable[[], LLMClient] | None = None,
) -> FastAPI:
    """The FastAPI app factory. Real clients are constructed only when no fake
    is injected, so tests never touch the network (TECH_SPEC §15). ``make_llm`` is a
    factory called once per Brainstorm request so each interview turn gets a fresh call
    budget (§13); tests inject one that returns a scripted client."""
    settings = settings or load_settings()
    github = github or RestGitHubClient(
        owner=settings.github_owner, repo=settings.github_repo, branch=settings.github_branch
    )
    dispatcher = dispatcher or WorkflowDispatcher(
        owner=settings.github_owner, repo=settings.github_repo
    )
    make_llm = make_llm or (lambda: LLMClient(transport=GeminiTransport()))

    app = FastAPI(title="Windtunnel backend")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def _run_path(run_id: str, *parts: str) -> str:
        return "/".join(("runs", run_id, *parts))

    def _valid_run_id(run_id: str) -> str:
        """Path-param guard for every ``{run_id}`` route. Rejects anything that
        is not a well-formed run code *before* it is used to build a repo path
        — the format check (§3) doubles as the arbitrary-path-traversal guard
        the artefact proxy text calls for (§7)."""
        try:
            return runcode.validate(run_id)
        except runcode.RunCodeError as exc:
            raise HTTPException(http_status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    def _load_run(run_id: str) -> statefile.RunState:
        result = github.get_file(_run_path(run_id, "run.json"))
        if result.status == "missing":
            raise HTTPException(http_status.HTTP_404_NOT_FOUND, f"No run found for code {run_id}.")
        try:
            return statefile.RunState.from_dict(json.loads(result.content))
        except statefile.StateError as exc:
            raise HTTPException(http_status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc

    def _load_status(run_id: str, run: statefile.RunState) -> status_module.StatusModel:
        result = github.get_file(_run_path(run_id, "status.json"))
        if result.status == "missing":
            return status_module.StatusModel.initial(run)
        data = json.loads(result.content)
        events = [status_module.Event.from_dict(e) for e in data.get("log", [])]
        return status_module.rebuild(run, events)

    def _load_outline(run_id: str) -> Outline:
        result = github.get_file(_run_path(run_id, "brainstorm", "outline.md"))
        if result.status == "missing":
            # The outline is written at run creation (§7.1); its absence is a corrupt run,
            # not a normal 404 the client can act on.
            raise HTTPException(
                http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                f"Run {run_id} has no brainstorm/outline.md on record.",
            )
        try:
            return Outline.parse(result.content.decode("utf-8"))
        except OutlineError as exc:
            raise HTTPException(http_status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc

    def _get_bytes_optional(run_id: str, *parts: str) -> bytes | None:
        result = github.get_file(_run_path(run_id, *parts))
        return result.content if result.status == "ok" else None

    def _commit_run_and_status(
        run_id: str, run: statefile.RunState, st: status_module.StatusModel, message: str
    ) -> str:
        files = {
            _run_path(run_id, "run.json"): _dump_json(run.to_dict()),
            _run_path(run_id, "status.json"): _dump_json(st.to_dict()),
        }
        try:
            return github.commit_files(files, f"run {run_id}: {message}")
        except GitHubError as exc:
            raise HTTPException(http_status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    def _commit_brainstorm(run_id: str, files: dict[str, bytes], message: str) -> str:
        """Commit brainstorm artefacts (outline/poc/map/svg). Brainstorm runs on Render, not
        Actions, and does not touch run.json/status.json — it only writes ``brainstorm/*`` files
        (a GitHubError becomes a 502)."""
        try:
            return github.commit_files(files, f"run {run_id}: {message}")
        except GitHubError as exc:
            raise HTTPException(http_status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    def _dispatch(workflow: str, run_id: str, resume_from: str) -> str | None:
        """Fire the governance workflow (§5.7). ``workflow_dispatch`` is
        fire-and-forget: the SPA learns the run *actually* started by watching
        ``status.json`` advance, not by this call's result (§5.7). So a dispatch
        failure is **not** fatal to the state transition the caller already
        committed — the run is durably at its new stage and can be re-kicked via
        ``/redispatch`` (or by simply retrying once the cause is fixed). Returns
        the error string on failure, ``None`` on success; the caller surfaces it as
        ``dispatched: false`` + ``dispatch_error`` rather than a 502 that would
        strand the run with no Action behind it (the bug behind a submitted run
        that never starts)."""
        try:
            dispatcher.dispatch(
                workflow,
                ref=settings.github_branch,
                inputs={"run_id": run_id, "resume_from": resume_from},
            )
            return None
        except DispatchError as exc:
            return str(exc)

    def _dispatch_result(err: str | None) -> dict:
        """The shared ``{dispatched, dispatch_error?}`` tail every dispatching
        endpoint returns. On success it is just ``{"dispatched": True}`` (no error
        key), so existing success-path contracts are unchanged."""
        return {"dispatched": err is None} | ({"dispatch_error": err} if err else {})

    # -- endpoints ------------------------------------------------------------

    @app.get("/api/health")
    def health() -> dict:
        """Wake + liveness (§7) — cheap, used to trigger the Render cold-start
        wake the instant the user passes the usage-warning gate."""
        return {"ok": True}

    @app.post("/api/runs", status_code=http_status.HTTP_201_CREATED)
    def create_run() -> dict:
        """Generates + collision-checks the run code, commits the initial
        ``runs/<id>/`` skeleton (§3, §7.1), returns ``{run_id, run_code}``."""

        def exists(code: str) -> bool:
            return github.get_file(_run_path(code, "run.json")).status != "missing"

        try:
            run_id = runcode.generate_unique(exists)
        except runcode.RunCodeError as exc:
            raise HTTPException(http_status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

        now = statefile.utc_now_iso()
        run = statefile.RunState.new(run_id, now=now)
        st = status_module.StatusModel.initial(run, now=now)
        files = {
            _run_path(run_id, "run.json"): _dump_json(run.to_dict()),
            _run_path(run_id, "status.json"): _dump_json(st.to_dict()),
            _run_path(run_id, "brainstorm", "outline.md"): render_initial_outline(
                run_id, now
            ).encode("utf-8"),
        }
        try:
            github.commit_files(files, f"run {run_id}: create run skeleton")
        except GitHubError as exc:
            raise HTTPException(http_status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
        return {"run_id": run_id, "run_code": run_id}

    def _require_brainstorm(run_id: str) -> statefile.RunState:
        """The Brainstorm endpoints are valid only before submission — once a run leaves
        ``BRAINSTORM`` the outline is frozen and later changes go through the revision paths
        (§5.8, §7). Returns the loaded run or raises 409/404."""
        run = _load_run(run_id)
        if run.stage is not statefile.Stage.BRAINSTORM:
            raise HTTPException(
                http_status.HTTP_409_CONFLICT,
                f"Run {run_id} has left Brainstorm (currently {run.stage}); the outline is "
                "no longer editable here.",
            )
        return run

    def _brainstorm_artefacts(run_id: str) -> dict:
        """Which optional Brainstorm artefacts (§6.3/§6.4) already exist, so the SPA can
        restore the focus track and re-display them on load/resume (§7.5). Read-only
        existence checks plus the feasibility verdict (feasible + the honest reason the
        conditional-stage note shows). A malformed feasibility.json is reported as absent
        rather than raised — this is a display hint, not an integrity-critical read."""
        feasibility = None
        raw = _get_bytes_optional(run_id, "brainstorm", "feasibility.json")
        if raw is not None:
            try:
                doc = json.loads(raw)
                feasibility = {
                    "feasible": bool(doc["feasible"]),
                    "reason": str(doc["reason"]),
                }
            except (ValueError, KeyError, TypeError):
                feasibility = None
        return {
            "poc": _get_bytes_optional(run_id, "brainstorm", "poc.html") is not None,
            "flow_map": _get_bytes_optional(run_id, "brainstorm", "flow-map.mmd") is not None,
            "flow_map_svg": _get_bytes_optional(run_id, "brainstorm", "flow-map.svg") is not None,
            "feasibility": feasibility,
        }

    def _brainstorm_response(run_id: str, outline: Outline, client: LLMClient) -> dict:
        """The shared tail of both Brainstorm endpoints: render the outline and run the
        sufficiency check (§7.1) for the banner. Never raises for a healthy outline."""
        outline_md = outline.render()
        try:
            sufficiency = assess_sufficiency(outline, outline_md, client)
        except LLMError as exc:
            raise HTTPException(http_status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
        return {"outline_md": outline_md, "sufficiency": sufficiency, "stage": "BRAINSTORM"}

    @app.post("/api/runs/{run_id}/brainstorm/message")
    def brainstorm_message(body: MessageBody, run_id: str = Depends(_valid_run_id)) -> dict:
        """One interview turn (§7, §7.1): runs the interviewer, writes any resolved outline
        sections, appends both messages to the transcript, runs the sufficiency check, and
        commits the outline (when it changed) + transcript as one commit. Returns
        ``{assistant_message, outline_md, outline_delta, sufficiency, stage}``."""
        message = body.message.strip()
        if not message:
            raise HTTPException(http_status.HTTP_400_BAD_REQUEST, "Message must not be empty.")
        _require_brainstorm(run_id)
        outline = _load_outline(run_id)
        transcript = Transcript.parse(_get_bytes_optional(run_id, "brainstorm", "transcript.jsonl"))
        dialogue = transcript.as_dialogue()  # the conversation *before* this turn

        now = statefile.utc_now_iso()
        client = make_llm()
        try:
            result = run_interviewer(
                client, outline_md=outline.render(), dialogue=dialogue, user_message=message
            )
        except (LLMError, BrainstormError) as exc:
            raise HTTPException(http_status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

        update = outline.apply_updates(
            result.section_updates, title=result.title, summary=result.summary, now=now
        )
        transcript.append("user", message, now)
        transcript.append("assistant", result.assistant_message, now)

        files = {_run_path(run_id, "brainstorm", "transcript.jsonl"): transcript.render()}
        if update.changed:
            files[_run_path(run_id, "brainstorm", "outline.md")] = outline.render().encode("utf-8")
        try:
            github.commit_files(files, f"run {run_id}: brainstorm turn")
        except GitHubError as exc:
            raise HTTPException(http_status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

        return {
            "assistant_message": result.assistant_message,
            "outline_delta": update.delta,
            **_brainstorm_response(run_id, outline, client),
        }

    @app.post("/api/runs/{run_id}/brainstorm/edit-outline")
    def brainstorm_edit_outline(
        body: EditOutlineBody, run_id: str = Depends(_valid_run_id)
    ) -> dict:
        """A user canvas edit (§7, §7.1): applies a per-section patch (plus optional
        title/summary) to the outline — the outline stays the single source of truth (brief
        §4). Returns ``{outline_md, outline_delta, sufficiency, stage}``."""
        if not body.sections and body.title is None and body.summary is None:
            raise HTTPException(http_status.HTTP_400_BAD_REQUEST, "No outline edits supplied.")
        _require_brainstorm(run_id)
        outline = _load_outline(run_id)
        now = statefile.utc_now_iso()
        try:
            update = outline.apply_updates(
                body.sections, title=body.title, summary=body.summary, now=now
            )
        except OutlineError as exc:
            raise HTTPException(http_status.HTTP_400_BAD_REQUEST, str(exc)) from exc

        if update.changed:
            files = {
                _run_path(run_id, "brainstorm", "outline.md"): outline.render().encode("utf-8")
            }
            try:
                github.commit_files(files, f"run {run_id}: brainstorm canvas edit")
            except GitHubError as exc:
                raise HTTPException(http_status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

        return {
            "outline_delta": update.delta,
            **_brainstorm_response(run_id, outline, make_llm()),
        }

    @app.get("/api/runs/{run_id}/brainstorm")
    def get_brainstorm(run_id: str = Depends(_valid_run_id)) -> dict:
        """Load the co-design state for the SPA (§7, §7.1) — the outline, the conversation
        transcript, and the sufficiency banner. This is how a fresh page load or a resume
        (§7.5) restores the Brainstorm canvas: the stateless backend re-reads the committed
        outline + transcript (CLAUDE.md §3), so the SPA never has to hold them. Read-only;
        it makes no commit. ``sufficiency`` is computed only while the run is still at
        ``BRAINSTORM`` (a submitted run's outline is frozen); the ``stage`` lets the SPA
        redirect a stale link on to the Chamber."""
        run = _load_run(run_id)
        outline = _load_outline(run_id)
        transcript = Transcript.parse(_get_bytes_optional(run_id, "brainstorm", "transcript.jsonl"))
        turns = [t.to_dict() for t in transcript.turns]
        if run.stage is not statefile.Stage.BRAINSTORM:
            return {
                "outline_md": outline.render(),
                "transcript": turns,
                "sufficiency": None,
                "stage": str(run.stage),
            }
        return {
            "transcript": turns,
            "artefacts": _brainstorm_artefacts(run_id),
            **_brainstorm_response(run_id, outline, make_llm()),
        }

    @app.post("/api/runs/{run_id}/poc")
    def generate_poc_endpoint(run_id: str = Depends(_valid_run_id)) -> dict:
        """Generate the PoC (§7, §12.3/§12.4). Runs the feasibility gate first; if a static HTML
        PoC would help, generates and commits ``brainstorm/poc.html``; if not, generates the flow
        map instead (``brainstorm/flow-map.mmd``) and says why. Either way writes
        ``brainstorm/feasibility.json`` and returns ``{produced: "poc"|"map", reason}`` (plus the
        Mermaid source on the map branch, for the SPA to render). Valid only at ``BRAINSTORM``."""
        _require_brainstorm(run_id)
        outline = _load_outline(run_id)
        now = statefile.utc_now_iso()
        client = make_llm()  # one fresh call budget for the gate + the synthesis (§13)
        try:
            feasibility = assess_feasibility(
                client,
                ux_ui=outline.section_body("ux_ui"),
                happy_path=outline.section_body("happy_path"),
            )
        except (LLMError, FeasibilityError) as exc:
            raise HTTPException(http_status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

        feasibility_doc = {
            "feasible": feasibility.feasible,
            "reason": feasibility.reason,
            "model": feasibility.model,
            "prompt_version": feasibility.prompt_version,
            "assessed_at": now,
        }
        feasibility_path = _run_path(run_id, "brainstorm", "feasibility.json")

        if feasibility.feasible:
            try:
                poc = generate_poc(client, outline_md=outline.render())
            except (LLMError, PocError) as exc:
                raise HTTPException(http_status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
            _commit_brainstorm(
                run_id,
                {
                    _run_path(run_id, "brainstorm", "poc.html"): poc.html.encode("utf-8"),
                    feasibility_path: _dump_json(feasibility_doc),
                },
                "proof of concept generated",
            )
            return {"produced": "poc", "reason": feasibility.reason}

        # Not a fit for a PoC → produce the flow map instead (§7), and say why.
        try:
            flow_map = generate_flow_map(client, outline_md=outline.render())
        except (LLMError, MapError) as exc:
            raise HTTPException(http_status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
        _commit_brainstorm(
            run_id,
            {
                _run_path(run_id, "brainstorm", "flow-map.mmd"): flow_map.mermaid.encode("utf-8"),
                feasibility_path: _dump_json(feasibility_doc),
            },
            "PoC not a fit — flow map generated instead",
        )
        return {"produced": "map", "reason": feasibility.reason, "mermaid": flow_map.mermaid}

    @app.post("/api/runs/{run_id}/flow-map")
    def flow_map_endpoint(run_id: str = Depends(_valid_run_id)) -> dict:
        """Generate the information-flow map (§7, §12.3). Produces Mermaid source from the whole
        outline (informed by the PoC if one exists), commits ``brainstorm/flow-map.mmd``, and
        returns the source for the SPA to render to SVG (posted back via ``/flow-map/svg``,
        CLAUDE.md §9). Valid only at ``BRAINSTORM``."""
        _require_brainstorm(run_id)
        outline = _load_outline(run_id)
        poc_bytes = _get_bytes_optional(run_id, "brainstorm", "poc.html")
        poc_html = poc_bytes.decode("utf-8") if poc_bytes else None
        try:
            flow_map = generate_flow_map(make_llm(), outline_md=outline.render(), poc_html=poc_html)
        except (LLMError, MapError) as exc:
            raise HTTPException(http_status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
        _commit_brainstorm(
            run_id,
            {_run_path(run_id, "brainstorm", "flow-map.mmd"): flow_map.mermaid.encode("utf-8")},
            "flow map generated",
        )
        return {"produced": "map", "mermaid": flow_map.mermaid}

    @app.post("/api/runs/{run_id}/flow-map/svg")
    def flow_map_svg_endpoint(body: FlowMapSvgBody, run_id: str = Depends(_valid_run_id)) -> dict:
        """Accept the SPA's client-rendered SVG and commit ``brainstorm/flow-map.svg`` (CLAUDE.md
        §9 — Render's free tier can't render Mermaid). The map must already have been generated
        (``flow-map.mmd`` present), the payload must be an SVG, and it must carry no ``<script>``
        (defence-in-depth, though it is later embedded sandboxed). Valid only at ``BRAINSTORM``."""
        _require_brainstorm(run_id)
        svg = body.svg.strip()
        low = svg.lower()
        if "<svg" not in low:
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST, "Body 'svg' is not an SVG document."
            )
        if "<script" in low:
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST, "SVG must not contain a <script> element."
            )
        if _get_bytes_optional(run_id, "brainstorm", "flow-map.mmd") is None:
            raise HTTPException(
                http_status.HTTP_409_CONFLICT,
                f"Run {run_id} has no flow-map.mmd on record; generate the map before posting "
                "its SVG.",
            )
        _commit_brainstorm(
            run_id,
            {_run_path(run_id, "brainstorm", "flow-map.svg"): svg.encode("utf-8")},
            "flow map SVG rendered",
        )
        return {"run_id": run_id, "committed": True}

    @app.get("/api/runs/{run_id}/status")
    def get_run_status(
        run_id: str = Depends(_valid_run_id),
        if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    ) -> Response:
        """The primary poll (§7): proxies ``status.json`` via the Contents API
        with conditional ``If-None-Match``, so steady-state polling is cheap."""
        result = github.get_file(_run_path(run_id, "status.json"), if_none_match=if_none_match)
        if result.status == "missing":
            raise HTTPException(http_status.HTTP_404_NOT_FOUND, f"No run found for code {run_id}.")
        if result.status == "not_modified":
            headers = {"ETag": if_none_match} if if_none_match else {}
            return Response(status_code=http_status.HTTP_304_NOT_MODIFIED, headers=headers)
        headers = {"ETag": result.etag} if result.etag else {}
        return Response(content=result.content, media_type="application/json", headers=headers)

    @app.get("/api/runs/{run_id}/artefact/{name}")
    def get_artefact(name: str, run_id: str = Depends(_valid_run_id)) -> Response:
        """Download proxy. ``name`` is allow-listed against ``_ARTEFACTS``;
        anything else is refused rather than resolved as a repo path (§7)."""
        entry = _ARTEFACTS.get(name)
        if entry is None:
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST,
                f"Unknown artefact name: {name!r}. Allowed: {sorted(_ARTEFACTS)}.",
            )
        rel, media_type = entry
        result = github.get_file(_run_path(run_id, rel))
        if result.status == "missing":
            raise HTTPException(
                http_status.HTTP_404_NOT_FOUND, f"{name} not yet produced for run {run_id}."
            )
        return Response(content=result.content, media_type=media_type)

    @app.post("/api/runs/{run_id}/submit")
    def submit_run(run_id: str = Depends(_valid_run_id)) -> dict:
        """Submission gate (§7, §5.1 SUBMITTED): dispatches Governance with
        ``resume_from=THRESHOLD_DRAFTING``."""
        run = _load_run(run_id)
        if run.stage is not statefile.Stage.BRAINSTORM:
            raise HTTPException(
                http_status.HTTP_409_CONFLICT,
                f"Run {run_id} is not at BRAINSTORM (currently {run.stage}); cannot submit.",
            )
        st = _load_status(run_id, run)
        now = statefile.utc_now_iso()
        run.advance_to(statefile.Stage.SUBMITTED, now=now)
        st.set_running(now=now)
        st.heartbeat(agent="backend", now=now)
        _commit_run_and_status(run_id, run, st, "submitted — dispatching governance")
        err = _dispatch(settings.governance_workflow, run_id, "THRESHOLD_DRAFTING")
        return {"run_id": run_id, **_dispatch_result(err)}

    @app.post("/api/runs/{run_id}/redispatch")
    def redispatch_run(run_id: str = Depends(_valid_run_id)) -> dict:
        """Re-fire Governance for a run whose dispatch never took (§5.7 "hasn't
        started yet" re-dispatch). ``workflow_dispatch`` is fire-and-forget and can
        fail *after* the state transition is already committed — a transient GitHub
        API error, or a PAT lacking ``actions:write`` — leaving the run sitting at a
        running stage with no Action behind it. This re-kicks it without redoing any
        prior work: the pipeline resumes idempotently from its last checkpoint (§5.3)
        and the governance workflow's per-run ``concurrency`` group serialises repeat
        dispatches (a second queues, never races), so this is safe to call more than
        once. Valid only for a non-paused, non-terminal dispatched stage — the
        ``resume_from`` is the one the original dispatch used."""
        run = _load_run(run_id)
        resume_from = _REDISPATCH_RESUME_FROM.get(run.stage)
        if resume_from is None or run.stage_status is not statefile.StageStatus.IN_PROGRESS:
            raise HTTPException(
                http_status.HTTP_409_CONFLICT,
                f"Run {run_id} is not awaiting a governance dispatch "
                f"(stage={run.stage}, status={run.stage_status}).",
            )
        err = _dispatch(settings.governance_workflow, run_id, resume_from)
        return {"run_id": run_id, "resume_from": resume_from, **_dispatch_result(err)}

    @app.post("/api/runs/{run_id}/threshold/route")
    def threshold_route(body: RouteBody, run_id: str = Depends(_valid_run_id)) -> dict:
        """Threshold routing (§7, §5.1 THRESHOLD_REVIEW): ``conclude`` finalises
        the run; ``full`` dispatches Governance with ``resume_from=FULL_DRAFTING``."""
        run = _load_run(run_id)
        if (
            run.stage is not statefile.Stage.THRESHOLD_REVIEW
            or run.stage_status is not statefile.StageStatus.AWAITING_USER
        ):
            raise HTTPException(
                http_status.HTTP_409_CONFLICT,
                f"Run {run_id} is not paused at THRESHOLD_REVIEW (stage={run.stage}, "
                f"status={run.stage_status}).",
            )
        st = _load_status(run_id, run)
        now = statefile.utc_now_iso()

        if body.outcome == "conclude":
            run.advance_to(statefile.Stage.CONCLUDED, statefile.StageStatus.COMPLETE, now=now)
            st.set_complete(now=now)
            _commit_run_and_status(run_id, run, st, "threshold routing: concluded")
            return {"run_id": run_id, "outcome": "conclude", "stage": str(run.stage)}

        run.advance_to(statefile.Stage.FULL_DRAFTING, now=now)
        st.set_running(now=now)
        st.heartbeat(agent="backend", now=now)
        _commit_run_and_status(run_id, run, st, "threshold routing: full assessment")
        err = _dispatch(settings.governance_workflow, run_id, "FULL_DRAFTING")
        return {
            "run_id": run_id,
            "outcome": "full",
            "stage": str(run.stage),
            **_dispatch_result(err),
        }

    @app.post("/api/runs/{run_id}/answers")
    def submit_answers(body: AnswersBody, run_id: str = Depends(_valid_run_id)) -> dict:
        """Checkpoint answers (§7, §5.1 FULL_CHECKPOINT → FULL_REVISING). Validates each
        submitted id against ``full/questions.json``, commits ``full/answers.json``
        alongside the advanced ``run.json``/``status.json``, and dispatches Governance with
        ``resume_from=FULL_REVISING``. Only valid while paused at ``FULL_CHECKPOINT``."""
        run = _load_run(run_id)
        if (
            run.stage is not statefile.Stage.FULL_CHECKPOINT
            or run.stage_status is not statefile.StageStatus.AWAITING_USER
        ):
            raise HTTPException(
                http_status.HTTP_409_CONFLICT,
                f"Run {run_id} is not paused at FULL_CHECKPOINT (stage={run.stage}, "
                f"status={run.stage_status}); no checkpoint questions to answer.",
            )

        valid_ids = _question_ids(run_id)
        answered_ids = [a.question_id for a in body.answers]
        skip_ids = list(body.skips)
        _validate_answer_ids(answered_ids, skip_ids, valid_ids)

        now = statefile.utc_now_iso()
        answers_doc = {
            "answers": [{"question_id": a.question_id, "value": a.value} for a in body.answers],
            "skips": skip_ids,
            "submitted_at": now,
        }
        st = _load_status(run_id, run)
        run.advance_to(statefile.Stage.FULL_REVISING, now=now)
        st.set_running(now=now)
        st.heartbeat(agent="backend", now=now)
        files = {
            _run_path(run_id, "full", "answers.json"): _dump_json(answers_doc),
            _run_path(run_id, "run.json"): _dump_json(run.to_dict()),
            _run_path(run_id, "status.json"): _dump_json(st.to_dict()),
        }
        try:
            github.commit_files(files, f"run {run_id}: checkpoint answers — revising")
        except GitHubError as exc:
            raise HTTPException(http_status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
        err = _dispatch(settings.governance_workflow, run_id, "FULL_REVISING")
        return {
            "run_id": run_id,
            "answered": len(answered_ids),
            "skipped": len(skip_ids),
            **_dispatch_result(err),
        }

    def _question_ids(run_id: str) -> set[str]:
        result = github.get_file(_run_path(run_id, "full", "questions.json"))
        if result.status == "missing":
            raise HTTPException(
                http_status.HTTP_409_CONFLICT,
                f"Run {run_id} has no checkpoint questions on record.",
            )
        payload = json.loads(result.content)
        return {
            item["question_id"]
            for spec in payload.get("specialists", [])
            for item in spec.get("items", [])
        }

    def _revise_brainstorm_artefact(run_id: str, artefact: str, instructions: str) -> dict:
        """Revise a brainstorm artefact (``poc``/``flow_map``, §7, brief §4/§7). Valid only at
        ``BRAINSTORM`` — the outline must still be live to regenerate from. Enforces the ≤2 cap
        (``run.json.revisions[artefact]``) and requires the artefact to already exist (a revision
        presupposes an initial generation, brief §7). Regenerates the artefact **whole from the
        amended outline** with the instructions in context — never a patch (brief §4) — and
        commits it alongside the advanced ``run.json`` (the cap counter's one owner, §7.1).
        No dispatch: brainstorm runs on Render, not Actions."""
        run = _require_brainstorm(run_id)
        source = "poc.html" if artefact == "poc" else "flow-map.mmd"
        if _get_bytes_optional(run_id, "brainstorm", source) is None:
            raise HTTPException(
                http_status.HTTP_409_CONFLICT,
                f"Run {run_id} has no {artefact.replace('_', ' ')} to revise yet — generate it "
                "first.",
            )
        now = statefile.utc_now_iso()
        try:
            revision = run.record_revision(artefact, now=now)  # raises at the cap (brief §7)
        except statefile.StateError as exc:
            raise HTTPException(http_status.HTTP_409_CONFLICT, str(exc)) from exc

        outline = _load_outline(run_id)
        client = make_llm()
        if artefact == "poc":
            try:
                poc = generate_poc(
                    client, outline_md=outline.render(), revision_instructions=instructions
                )
            except (LLMError, PocError) as exc:
                raise HTTPException(http_status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
            artefact_file = {_run_path(run_id, "brainstorm", "poc.html"): poc.html.encode("utf-8")}
            extra: dict = {}
        else:  # flow_map
            poc_bytes = _get_bytes_optional(run_id, "brainstorm", "poc.html")
            poc_html = poc_bytes.decode("utf-8") if poc_bytes else None
            try:
                flow_map = generate_flow_map(
                    client,
                    outline_md=outline.render(),
                    poc_html=poc_html,
                    revision_instructions=instructions,
                )
            except (LLMError, MapError) as exc:
                raise HTTPException(http_status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
            # The committed flow-map.svg is now stale; the SPA re-renders the returned source and
            # re-posts it via /flow-map/svg, the same round-trip as the initial /flow-map.
            artefact_file = {
                _run_path(run_id, "brainstorm", "flow-map.mmd"): flow_map.mermaid.encode("utf-8")
            }
            extra = {"mermaid": flow_map.mermaid}

        _commit_brainstorm(
            run_id,
            {
                **artefact_file,
                _run_path(run_id, "run.json"): _dump_json(run.to_dict()),
            },
            f"{artefact.replace('_', ' ')} revision {revision}",
        )
        return {"run_id": run_id, "artefact": artefact, "revision": revision, **extra}

    def _revise_threshold(run_id: str, instructions: str) -> dict:
        """Revise the threshold assessment (§7, brief §7). Valid only while paused at
        ``THRESHOLD_REVIEW`` — the review screen is where the user asks for a change. Enforces
        the ≤2 cap (``run.json.revisions.threshold``), commits the request alongside the run
        advanced back to ``THRESHOLD_RECONCILING``, and dispatches Governance with
        ``resume_from=THRESHOLD_RECONCILING`` so the reconciler re-runs with the instructions in
        context. The two generalist drafts stand untouched (their independence is preserved) and
        the engine recomputes the ratings — a revision steers the reconciled narrative, never a
        rating ("models argue, code computes", §10). Mirrors ``/answers`` and ``/revise full``:
        one atomic commit, then the dispatch."""
        run = _load_run(run_id)
        if (
            run.stage is not statefile.Stage.THRESHOLD_REVIEW
            or run.stage_status is not statefile.StageStatus.AWAITING_USER
        ):
            raise HTTPException(
                http_status.HTTP_409_CONFLICT,
                f"Run {run_id} is not paused at THRESHOLD_REVIEW (stage={run.stage}, "
                f"status={run.stage_status}); a threshold revision is only possible while the "
                "threshold review is open.",
            )
        now = statefile.utc_now_iso()
        try:
            revision = run.record_revision("threshold", now=now)  # raises at the cap (brief §7)
        except statefile.StateError as exc:
            raise HTTPException(http_status.HTTP_409_CONFLICT, str(exc)) from exc

        run.advance_to(statefile.Stage.THRESHOLD_RECONCILING, now=now)
        st = _load_status(run_id, run)
        st.set_running(now=now)
        st.heartbeat(agent="backend", now=now)
        request_doc = {"instructions": instructions, "requested_at": now}
        files = {
            _run_path(
                run_id, "threshold", "revisions", f"rev_{revision}", "request.json"
            ): _dump_json(request_doc),
            _run_path(run_id, "run.json"): _dump_json(run.to_dict()),
            _run_path(run_id, "status.json"): _dump_json(st.to_dict()),
        }
        try:
            github.commit_files(files, f"run {run_id}: threshold revision {revision} requested")
        except GitHubError as exc:
            raise HTTPException(http_status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
        err = _dispatch(settings.governance_workflow, run_id, "THRESHOLD_RECONCILING")
        return {"run_id": run_id, "revision": revision, **_dispatch_result(err)}

    @app.post("/api/runs/{run_id}/revise")
    def revise_run(body: ReviseBody, run_id: str = Depends(_valid_run_id)) -> dict:
        """Revise an artefact (§7). ``poc``/``flow_map`` regenerate from the amended outline
        while at ``BRAINSTORM`` (brief §4/§7). ``threshold`` re-runs ``THRESHOLD_RECONCILING``
        while paused at ``THRESHOLD_REVIEW`` with the instructions in context (the generalist
        drafts stand; the engine recomputes). ``full`` is the full-assessment revision (§5.1
        USER_REVISION, §5.8): valid only at ``COMPLETE``, it enforces the ≤2 cap
        (``run.json.revisions.full``), commits ``full/revisions/rev_<N>/request.json`` alongside
        the advanced ``run.json``/``status.json``, and dispatches Governance with
        ``resume_from=USER_REVISION``. All branches share the ≤2 per-artefact cap."""
        instructions = body.instructions.strip()
        if not instructions:
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST, "Revision instructions must not be empty."
            )
        if body.artefact in ("poc", "flow_map"):
            return _revise_brainstorm_artefact(run_id, body.artefact, instructions)
        if body.artefact == "threshold":
            return _revise_threshold(run_id, instructions)

        run = _load_run(run_id)
        if run.stage is not statefile.Stage.COMPLETE:
            raise HTTPException(
                http_status.HTTP_409_CONFLICT,
                f"Run {run_id} is not COMPLETE (currently {run.stage}); a full-assessment "
                "revision is only possible on a completed assessment.",
            )
        now = statefile.utc_now_iso()
        try:
            revision = run.record_revision("full", now=now)  # raises at the cap (§5.8)
        except statefile.StateError as exc:
            raise HTTPException(http_status.HTTP_409_CONFLICT, str(exc)) from exc

        run.advance_to(statefile.Stage.USER_REVISION, now=now)
        st = _load_status(run_id, run)
        st.set_running(now=now)
        st.heartbeat(agent="backend", now=now)
        request_doc = {"instructions": instructions, "requested_at": now}
        files = {
            _run_path(run_id, "full", "revisions", f"rev_{revision}", "request.json"): _dump_json(
                request_doc
            ),
            _run_path(run_id, "run.json"): _dump_json(run.to_dict()),
            _run_path(run_id, "status.json"): _dump_json(st.to_dict()),
        }
        try:
            github.commit_files(
                files, f"run {run_id}: full-assessment revision {revision} requested"
            )
        except GitHubError as exc:
            raise HTTPException(http_status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
        err = _dispatch(settings.governance_workflow, run_id, "USER_REVISION")
        return {"run_id": run_id, "revision": revision, **_dispatch_result(err)}

    @app.post("/api/runs/{run_id}/resume")
    def resume_run(run_id: str = Depends(_valid_run_id)) -> dict:
        """Resume by code (§7): validated already by ``_valid_run_id``; a code
        that is well-formed but unknown still surfaces a plain 404, never a raw
        failure (design §7.5)."""
        run = _load_run(run_id)
        st = _load_status(run_id, run)
        return {
            "run_id": run_id,
            "stage": str(run.stage),
            "stage_status": str(run.stage_status),
            "phase": str(run.phase),
            "status": st.to_dict(),
        }

    return app


def _validate_answer_ids(answered_ids: list[str], skip_ids: list[str], valid_ids: set[str]) -> None:
    """Every submitted id must be a real checkpoint question, and no id may be both
    answered and skipped (a UI contradiction). Unaddressed questions are permitted — the
    pipeline treats a question with neither an answer nor an explicit skip as skipped (§5.1
    "skipped questions → gaps"). Raises HTTP 400 on any violation."""
    submitted = answered_ids + skip_ids
    unknown = sorted(set(submitted) - valid_ids)
    if unknown:
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            f"Unknown question id(s): {unknown}. Answers must reference the run's own "
            "checkpoint questions.",
        )
    both = sorted(set(answered_ids) & set(skip_ids))
    if both:
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            f"Question id(s) both answered and skipped: {both}. Choose one.",
        )
    for kind, ids in (("answered", answered_ids), ("skipped", skip_ids)):
        dupes = sorted({q for q in ids if ids.count(q) > 1})
        if dupes:
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST,
                f"Duplicate {kind} question id(s): {dupes}.",
            )


def _dump_json(obj: object) -> bytes:
    return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


app = create_app()
