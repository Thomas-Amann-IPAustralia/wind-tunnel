"""FastAPI endpoints (TECH_SPEC §7) — the slice this build covers.

Run creation, the status proxy, the artefact download proxy, submission into
Governance, threshold routing, checkpoint answers (``/answers`` →
``FULL_REVISING``), full-assessment revision (``/revise {artefact:"full"}`` →
``USER_REVISION``), and resume-by-code. **Not** in this slice: the Brainstorm
interview endpoints (``/brainstorm/message``, ``/edit-outline``, ``/poc``,
``/flow-map``) and the non-``full`` branches of ``/revise`` (outline/poc/flow_map
regenerate from the amended outline; ``threshold`` revises at ``THRESHOLD_REVIEW``) —
those belong to the interviewer/PoC build (STATUS.md "Brainstorm interview + outline
canvas"), which this backend does not implement yet.

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
from typing import Literal

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
from pydantic import BaseModel  # noqa: E402

from config import Settings, load_settings  # noqa: E402
from dispatch import Dispatcher, DispatchError, WorkflowDispatcher  # noqa: E402
from github_io import GitHubClient, GitHubError, RestGitHubClient  # noqa: E402
from outline import render_initial_outline  # noqa: E402

# name -> path within runs/<id>/, and its download media type (§7 artefact proxy;
# "name is allow-listed; arbitrary repo paths are refused").
_ARTEFACTS: dict[str, tuple[str, str]] = {
    "outline.md": ("artefacts/outline.md", "text/markdown; charset=utf-8"),
    "threshold.md": ("artefacts/threshold.md", "text/markdown; charset=utf-8"),
    "assessment.ipynb": ("artefacts/assessment.ipynb", "application/x-ipynb+json"),
    "assessment.html": ("artefacts/assessment.html", "text/html; charset=utf-8"),
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
    # Only "full" is served here — the other revisable artefacts (§7) revise through the
    # Brainstorm/threshold paths, not this endpoint. A non-"full" value is a 422.
    artefact: Literal["full"]
    instructions: str


def create_app(
    *,
    github: GitHubClient | None = None,
    dispatcher: Dispatcher | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    """The FastAPI app factory. Real clients are constructed only when no fake
    is injected, so tests never touch the network (TECH_SPEC §15)."""
    settings = settings or load_settings()
    github = github or RestGitHubClient(
        owner=settings.github_owner, repo=settings.github_repo, branch=settings.github_branch
    )
    dispatcher = dispatcher or WorkflowDispatcher(
        owner=settings.github_owner, repo=settings.github_repo
    )

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

    def _dispatch(workflow: str, run_id: str, resume_from: str) -> None:
        try:
            dispatcher.dispatch(
                workflow,
                ref=settings.github_branch,
                inputs={"run_id": run_id, "resume_from": resume_from},
            )
        except DispatchError as exc:
            raise HTTPException(http_status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

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
        _dispatch(settings.governance_workflow, run_id, "THRESHOLD_DRAFTING")
        return {"run_id": run_id, "dispatched": True}

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
        _dispatch(settings.governance_workflow, run_id, "FULL_DRAFTING")
        return {"run_id": run_id, "outcome": "full", "stage": str(run.stage), "dispatched": True}

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
        _dispatch(settings.governance_workflow, run_id, "FULL_REVISING")
        return {
            "run_id": run_id,
            "answered": len(answered_ids),
            "skipped": len(skip_ids),
            "dispatched": True,
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

    @app.post("/api/runs/{run_id}/revise")
    def revise_run(body: ReviseBody, run_id: str = Depends(_valid_run_id)) -> dict:
        """Full-assessment revision (§7, §5.1 USER_REVISION, §5.8). Valid only at
        ``COMPLETE``; enforces the ≤2 per-artefact cap (``run.json.revisions.full``).
        Increments the count, commits ``full/revisions/rev_<N>/request.json`` alongside the
        advanced ``run.json``/``status.json``, and dispatches Governance with
        ``resume_from=USER_REVISION``."""
        instructions = body.instructions.strip()
        if not instructions:
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST, "Revision instructions must not be empty."
            )
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
        _dispatch(settings.governance_workflow, run_id, "USER_REVISION")
        return {"run_id": run_id, "revision": revision, "dispatched": True}

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
