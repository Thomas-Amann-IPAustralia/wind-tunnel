"""The full-assessment stages (TECH_SPEC §5.1): FULL_DRAFTING, FULL_REVISING,
ARCHITECT, REVIEW.

``full_drafting`` — six specialists each draft their own owned §5–12 sections
independently, driving their own KB through the bounded fetch/search tool loop
(``agents/specialist.py``). They run **concurrently** (§5.4), fanned out over a
thread pool bounded by ``config/budgets.yml`` ``specialist_concurrency``; workers
compute and narrate only, while all file writes and commits stay on the
coordinating thread (see ``stages/fanout.py``). Each may raise up to three
checkpoint questions; if any does, ``full/questions.json`` is written and the next
stage is the ``FULL_CHECKPOINT`` user pause (§6.4). If none do, the checkpoint
(and ``FULL_REVISING``) is skipped — the §5.1 happy path straight to ``architect``.

``full_revising`` — after a ``FULL_CHECKPOINT`` pause, each specialist that raised a
question revises its own sections once in light of the user's answers (§5.1, §5.8), a
thin orchestration over ``run_specialist_amendment`` with the same §5.4 fan-out.
Skipped questions become gaps.

``architect`` — a single Pro call writes the Implementation Plan appendix, every step
traceable to a mitigation a specialist actually drafted (§5.5, §12.1).

``review`` — the bounded reviewer loop (§5.5, §11): coverage checklist (computed here,
§11.1) + coherence audit + amend directives to individual specialists (each acting only
on its own sections, §11.3), capped at two cycles with unresolved conflicts recorded
rather than forced (§11.4). The deterministic engine — never the reviewer — computes the
residual §12.3/§12.4 ratings from the reviewer's post-mitigation tiers. The stage after
this, ``ASSEMBLY``, is not built yet.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from agents.architect import ArchitectPlan, run_architect
from agents.prompting import (
    RISK_SECTIONS,
    full_assessment_ownership,
    full_subsection_ids,
    full_subsection_title,
    reviewer_scope_context,
    specialist_friendly_name,
    specialist_owned_sections,
    threshold_instrument_context,
)
from agents.reviewer import (
    ReviewerResult,
    run_reviewer,
    run_revision_triage,
    run_revision_verification,
)
from agents.specialist import SpecialistDraft, run_specialist, run_specialist_amendment
from rating import overall_rating, rating
from retrieval.retrieve import KB
from stages.assembly import archive_superseded
from stages.context import StageContext
from stages.fanout import AgentTask, run_agent_tasks
from statefile import REVISION_CAP
from status import friendly_name

# The six drafting specialists, in `instrument/sections.json` `specialists` order
# (the one owner of that fact — this tuple must stay in step with it; asserted by
# `pipeline/tests/test_instrument.py`).
SPECIALISTS: tuple[str, ...] = (
    "it_security",
    "privacy",
    "ethics",
    "legal",
    "data_governance",
    "solution_architect",
)

QUESTIONS_RELPATH = "full/questions.json"
ANSWERS_RELPATH = "full/answers.json"
REVISED_RELPATH = "full/revised.json"
_SPECIALIST_NODE_PREFIX = "full.specialist."
ARCHITECT_NODE = "full.architect"
ARCHITECT_MD_RELPATH = "full/architect.md"
REVIEWER_NODE = "full.reviewer"
RESIDUAL_RELPATH = "full/reviewer/ratings_residual.json"
UNRESOLVED_RELPATH = "full/reviewer/unresolved.json"
REVISIONS_RELDIR = "full/revisions"


def revision_request_relpath(n: int) -> str:
    """Where ``POST /revise`` commits the user's revision request (§5.8 entry)."""
    return f"{REVISIONS_RELDIR}/rev_{n}/request.json"


def revision_directives_relpath(n: int) -> str:
    """The reviewer's triage of revision N (§5.8 step 1)."""
    return f"{REVISIONS_RELDIR}/rev_{n}/directives.json"


def revision_verification_relpath(n: int) -> str:
    """The reviewer's verification of revision N — USER_REVISION's checkpoint output (§5.8 step 3)."""
    return f"{REVISIONS_RELDIR}/rev_{n}/verification.json"


def _section_sort_key(section_id: str) -> tuple[int, int]:
    major, _, minor = section_id.partition(".")
    return (int(major), int(minor) if minor else 0)


def _default_kb_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "kb").is_dir():
            return parent / "kb"
    raise FileNotFoundError(f"Could not locate kb/ above {here}.")


def _load_index_text(kb_root: Path, specialist: str) -> str:
    path = kb_root / f"{specialist}.index.json"
    with path.open(encoding="utf-8") as fh:
        index = json.load(fh)
    return json.dumps(index, ensure_ascii=False)


def full_drafting(ctx: StageContext) -> None:
    """Every specialist drafts its owned sections independently — and concurrently,
    fanned out over the bounded §5.4 pool (§5.1, §9.3). Outputs
    ``full/specialists/<id>.json`` + ``.md`` for each, and ``full/questions.json``
    — always, with an empty ``specialists`` list when no question was raised. The
    questions file is part of the stage checkpoint (run.py): drafts are
    pulse-committed one by one as they finish, so "all six drafts exist" alone no
    longer proves the stage ran to its end — without the questions file in the
    checkpoint, a death between the last draft and the questions write would let
    resume skip the stage and silently drop raised questions.

    Each specialist is individually idempotent (§5.3): a retry skips any draft
    already committed — its questions are reloaded from the committed file so the
    batched payload still carries them."""
    kb_root = ctx.kb_root or _default_kb_root()
    outline = ctx.outline()
    threshold_md = ctx.read_text("threshold/threshold_assessment.md")

    drafts: dict[str, SpecialistDraft] = {}
    tasks: list[AgentTask] = []
    for specialist in SPECIALISTS:
        relpath = f"full/specialists/{specialist}.json"
        if ctx.path(relpath).is_file():
            drafts[specialist] = SpecialistDraft.from_dict(ctx.read_json(relpath))
            continue
        tasks.append(_draft_task(ctx, specialist, kb_root, outline, threshold_md, drafts))
    run_agent_tasks(ctx, tasks)

    # Collected in SPECIALISTS order — not completion order — so the questions
    # payload (and its committed JSON) is deterministic across re-runs.
    raised = [
        (f"{_SPECIALIST_NODE_PREFIX}{s}", drafts[s]) for s in SPECIALISTS if drafts[s].questions
    ]
    ctx.write_json(QUESTIONS_RELPATH, _build_questions_payload(raised))
    for node, draft in raised:
        for item in draft.questions:
            ctx.status.question_raised(node, item["question_id"], item["text"])


def _draft_task(
    ctx: StageContext,
    specialist: str,
    kb_root: Path,
    outline: str,
    threshold_md: str,
    drafts: dict[str, SpecialistDraft],
) -> AgentTask:
    """One specialist's FULL_DRAFTING task (§5.4): the worker narrates its own
    start and drives its own KB through the tool loop; the coordinator writes the
    finished draft and completes the node."""
    node = f"{_SPECIALIST_NODE_PREFIX}{specialist}"

    def work() -> SpecialistDraft:
        ctx.status.start_node(node)
        ctx.status.drafting(node, f"drafting {specialist}'s owned sections")
        index_text = _load_index_text(kb_root, specialist)
        with KB(kb_root / f"{specialist}.sqlite") as kb:
            return run_specialist(
                ctx.llm,
                specialist,
                outline,
                threshold_md,
                kb,
                index_text,
                status=ctx.status,
                node_id=node,
            )

    def finish(draft: SpecialistDraft) -> None:
        ctx.write_json(f"full/specialists/{specialist}.json", draft.to_dict())
        ctx.write_text(f"full/specialists/{specialist}.md", render_specialist_markdown(draft))
        ctx.status.complete_node(node)
        drafts[specialist] = draft

    return AgentTask(name=specialist, work=work, finish=finish)


# -- FULL_REVISING -------------------------------------------------------------

_REVISION_HEADING = "Your checkpoint questions — now answered"
_REVISION_INTRO = (
    "The person running this assessment has answered the checkpoint questions you raised. "
    "Revise your own sections ({targets}) in light of their answers. Where a question was "
    "left unanswered, treat that fact as unavailable — re-affirm any section that still "
    "holds, and record any section you cannot ground from the evidence as a gap rather "
    "than inventing detail. Raise no new questions."
)


def full_revising(ctx: StageContext) -> None:
    """Each specialist that raised a checkpoint question revises its own sections once in
    light of the user's answers (§5.1 FULL_REVISING, §5.8), the questioners fanned out
    concurrently (§5.4). This is a thin orchestration over ``run_specialist_amendment``
    (§11.3): the answers are the directive, and the specialist's whole owned set is the
    target (a question is not tied to one section, so the specialist re-drafts its slice
    with the new facts in hand). A skipped question is presented as an unavailable fact,
    so a section it still cannot ground becomes a gap (§5.1 "skipped questions → gaps").
    Specialists that raised no question are untouched. Writes updated
    ``full/specialists/*`` and ``full/revised.json`` (the checkpoint marker + a record
    of what was revised)."""
    questions = ctx.read_json(QUESTIONS_RELPATH)
    answers = ctx.read_json(ANSWERS_RELPATH)
    outline = ctx.outline()
    threshold_md = ctx.read_text("threshold/threshold_assessment.md")
    kb_root = ctx.kb_root or _default_kb_root()

    answer_by_id = {a["question_id"]: a.get("value", "") for a in (answers.get("answers") or [])}
    skipped_ids = set(answers.get("skips") or [])

    answered_count = 0
    skipped_count = 0
    tasks: list[AgentTask] = []
    for entry in questions.get("specialists") or []:
        specialist = _specialist_from_node(entry["node_id"])
        items = entry.get("items") or []
        directive_context, n_ans, n_skip = _render_answers_directive(
            items, answer_by_id, skipped_ids
        )
        answered_count += n_ans
        skipped_count += n_skip
        tasks.append(
            _revise_task(
                ctx,
                specialist,
                kb_root,
                outline,
                threshold_md,
                directive_context,
                _revision_seed_terms(items, answer_by_id),
            )
        )
    run_agent_tasks(ctx, tasks)

    # Task order (the questions-payload order), not completion order — deterministic.
    revised = [t.name for t in tasks]
    ctx.write_json(
        REVISED_RELPATH,
        {"revised": revised, "counts": {"answered": answered_count, "skipped": skipped_count}},
    )


def _revise_task(
    ctx: StageContext,
    specialist: str,
    kb_root: Path,
    outline: str,
    threshold_md: str,
    directive_context: str,
    seed_terms: str,
) -> AgentTask:
    """One questioning specialist's FULL_REVISING task (§5.4): re-draft its whole
    owned set with the user's answers in hand (§5.1, §11.3 machinery)."""
    node = f"{_SPECIALIST_NODE_PREFIX}{specialist}"
    targets = specialist_owned_sections(specialist)
    prior = SpecialistDraft.from_dict(ctx.read_json(f"full/specialists/{specialist}.json"))

    def work() -> SpecialistDraft:
        ctx.status.start_node(node)
        ctx.status.revision(
            node, f"revising {specialist}'s sections in light of your answers", target=specialist
        )
        index_text = _load_index_text(kb_root, specialist)
        with KB(kb_root / f"{specialist}.sqlite") as kb:
            return run_specialist_amendment(
                ctx.llm,
                specialist,
                prior,
                targets,
                directive_context,
                seed_terms,
                outline,
                threshold_md,
                kb,
                index_text,
                directive_heading=_REVISION_HEADING,
                directive_intro=_REVISION_INTRO,
                status=ctx.status,
                node_id=node,
            )

    def finish(new_draft: SpecialistDraft) -> None:
        ctx.write_json(f"full/specialists/{specialist}.json", new_draft.to_dict())
        ctx.write_text(f"full/specialists/{specialist}.md", render_specialist_markdown(new_draft))
        ctx.status.complete_node(node)

    return AgentTask(name=specialist, work=work, finish=finish)


def _specialist_from_node(node_id: str) -> str:
    """The specialist id inside a ``full.specialist.<id>`` node id (§6.2)."""
    if not node_id.startswith(_SPECIALIST_NODE_PREFIX):
        raise ValueError(f"Not a specialist node id: {node_id!r}.")
    specialist = node_id[len(_SPECIALIST_NODE_PREFIX) :]
    if specialist not in SPECIALISTS:
        raise ValueError(f"Unknown specialist {specialist!r} in node id {node_id!r}.")
    return specialist


def _render_answers_directive(
    items: list[dict], answer_by_id: dict[str, str], skipped_ids: set[str]
) -> tuple[str, int, int]:
    """Render one specialist's checkpoint questions with the user's answers, marking any it
    left unanswered. Returns the block plus (answered, skipped) counts. A question with no
    answer and no explicit skip is treated as skipped — the honest default (§5.1)."""
    lines: list[str] = []
    answered = 0
    skipped = 0
    for item in items:
        qid = item["question_id"]
        lines.append(f"### {qid}: {item['text']}")
        value = answer_by_id.get(qid)
        if qid in skipped_ids or value is None or not str(value).strip():
            lines.append(
                "**The user chose not to answer this question.** Treat the fact it asked "
                "about as unavailable."
            )
            skipped += 1
        else:
            lines.append(f"**Answer:** {value}")
            answered += 1
        lines.append("")
    return "\n".join(lines), answered, skipped


def _revision_seed_terms(items: list[dict], answer_by_id: dict[str, str]) -> str:
    """Seed the amendment's pre-fetch search with the question text and the user's answers,
    so re-grounding starts from the newly supplied facts rather than an empty query."""
    terms: list[str] = []
    for item in items:
        terms.append(str(item.get("text", "")))
        value = answer_by_id.get(item["question_id"])
        if value:
            terms.append(str(value))
    return " ".join(t for t in terms if t.strip())


# -- ARCHITECT -----------------------------------------------------------------


def architect(ctx: StageContext) -> None:
    """The architect reads the finalised specialist drafts + threshold + outline and
    writes the Implementation Plan appendix (§5.1 ARCHITECT, §12.1). A single Pro
    call, no retrieval — it answers what has already been drafted. Outputs
    ``full/architect.json`` (structured + provenance) and ``full/architect.md`` (the
    rendered appendix); every step traces to a section a specialist actually drafted
    (§5.5, enforced in ``agents/architect.py``)."""
    outline = ctx.outline()
    threshold_md = ctx.read_text("threshold/threshold_assessment.md")

    drafts = {s: ctx.read_json(f"full/specialists/{s}.json") for s in SPECIALISTS}
    specialist_context = _render_specialist_context(drafts)
    valid_targets = {
        s: tuple(sorted((drafts[s].get("sections") or {}).keys())) for s in SPECIALISTS
    }

    ctx.status.start_node(ARCHITECT_NODE)
    ctx.status.drafting(
        ARCHITECT_NODE,
        "Writing an implementation plan that answers the risks the specialists raised.",
    )
    plan = run_architect(ctx.llm, outline, threshold_md, specialist_context, valid_targets)
    ctx.status.complete_node(ARCHITECT_NODE)

    ctx.write_json("full/architect.json", plan.to_dict())
    ctx.write_text(ARCHITECT_MD_RELPATH, render_architect_markdown(plan))


def _render_specialist_context(drafts: dict[str, dict]) -> str:
    """Render every specialist's drafted sections, citations and gaps into the single
    block the architect reads (§5.5 "reads the complete draft")."""
    lines: list[str] = []
    for specialist in SPECIALISTS:
        draft = drafts[specialist]
        lines.append(f"### {specialist_friendly_name(specialist)} ({specialist})")
        sections = draft.get("sections") or {}
        citations = draft.get("citations") or {}
        for sid in sorted(sections):
            lines += [f"#### {sid}", sections[sid]]
            cites = citations.get(sid) or []
            if cites:
                rendered = ", ".join(f"[{c['short_name']}, {c['locator']}]" for c in cites)
                lines.append(f"*Citations: {rendered}*")
        gaps = draft.get("gaps") or []
        if gaps:
            lines.append("**Gaps (not drafted):**")
            for g in gaps:
                lines.append(f"- {g['section']}: {g['reason']}")
        lines.append("")
    return "\n".join(lines)


def render_architect_markdown(plan: ArchitectPlan) -> str:
    """The Implementation Plan appendix as markdown (assembled into the notebook,
    §12.1 appendices). Each step names the mitigations it answers so the plan's
    traceability is visible in the report, not only in the JSON."""
    lines = [
        "# Appendix — Implementation Plan",
        "",
        plan.overview,
        "",
        "## Implementation steps",
        "",
    ]
    for i, step in enumerate(plan.steps, start=1):
        lines += [f"### {i}. {step['title']}", "", step["detail"], ""]
        traced = []
        for t in step["traces_to"]:
            friendly = specialist_friendly_name(t["specialist"])
            mitigation = f" — {t['mitigation']}" if t.get("mitigation") else ""
            traced.append(f"[{friendly}, §{t['section']}]{mitigation}")
        lines += [f"*Answers: {'; '.join(traced)}*", ""]
    return "\n".join(lines)


# -- REVIEW --------------------------------------------------------------------


def review(ctx: StageContext) -> None:
    """The reviewer loop (§5.1 REVIEW, §5.5, §11). One pipeline stage, internally
    iterative: the reviewer audits coverage (computed here, §11.1) + coherence, issues
    amend directives to individual specialists (each acting only on its own sections,
    §11.3), and judges residual risk. The loop is capped at two cycles; conflicts still
    live after cycle 2 are recorded, not forced (§11.4). The engine — never the
    reviewer — computes the residual ratings (§12.4). Outputs
    ``full/reviewer/cycle_N.json``, ``coverage.json``, ``ratings_residual.json`` and,
    if any, ``unresolved.json`` (plus a readable ``review.md``)."""
    outline = ctx.outline()
    threshold_md = ctx.read_text("threshold/threshold_assessment.md")
    drafts = {s: ctx.read_json(f"full/specialists/{s}.json") for s in SPECIALISTS}
    valid_targets = {s: specialist_owned_sections(s) for s in SPECIALISTS}

    coverage = _build_coverage(drafts)
    ctx.write_json("full/reviewer/coverage.json", coverage)

    # REVIEW is one checkpoint that re-runs its whole bounded loop on resume (§5.3);
    # reset the cycle counter so it reflects THIS execution, not a failed prior attempt.
    ctx.run.reset_review_cycles(now=ctx.now())

    instrument_context = threshold_instrument_context()
    scope_context = reviewer_scope_context()

    result: ReviewerResult | None = None
    directives_unapplied = False
    while True:
        cycle = ctx.run.record_review_cycle(now=ctx.now())
        ctx.status.start_node(REVIEWER_NODE)
        ctx.status.review_finding(
            REVIEWER_NODE,
            f"Reviewing cycle {cycle}: auditing coverage, coherence and residual risk.",
        )
        result = run_reviewer(
            ctx.llm,
            instrument_context=instrument_context,
            scope_context=scope_context,
            coverage_context=_render_coverage(coverage),
            draft_context=_render_specialist_context(drafts),
            threshold_md=threshold_md,
            outline_md=outline,
            valid_targets=valid_targets,
        )
        ctx.write_json(f"full/reviewer/cycle_{cycle}.json", result.to_dict())
        for finding in result.coherence_findings:
            ctx.status.review_finding(REVIEWER_NODE, finding["summary"])
        ctx.status.complete_node(REVIEWER_NODE)

        if not result.amend_directives:
            break
        if not ctx.run.can_review_again():
            directives_unapplied = True  # cap reached with directives still live (§11.4)
            break
        drafts = _apply_amendments(
            ctx, drafts, result.amend_directives, outline, threshold_md, cycle=cycle
        )

    # Residual 12.3/12.4 — the engine computes from the last cycle's post-mitigation tiers.
    residual = _compute_residual(result.residual)
    ctx.write_json(RESIDUAL_RELPATH, residual)
    ctx.status.review_finding(
        REVIEWER_NODE,
        f"Residual overall risk after mitigation (highest-wins): {residual['overall_residual']}.",
    )

    unresolved = list(result.unresolved)
    if directives_unapplied:
        unresolved += _directives_as_unresolved(result.amend_directives)
    if unresolved:
        ctx.write_json("full/reviewer/unresolved.json", unresolved)

    ctx.write_text(
        "full/reviewer/review.md", render_review_markdown(coverage, result, residual, unresolved)
    )


def _build_coverage(drafts: dict[str, dict]) -> dict:
    """The mechanical coverage checklist (§11.1): every §5–12 subsection is addressed,
    gapped, missing (a deterministic finding), produced by this stage (12.3/12.4), or a
    flagged human action (12.5). Not a judgement call — a checklist walk over the
    instrument inventory against what the specialists drafted."""
    ownership = full_assessment_ownership()
    drafted = {s: set((drafts[s].get("sections") or {}).keys()) for s in SPECIALISTS}
    gapped = {s: {g["section"] for g in (drafts[s].get("gaps") or [])} for s in SPECIALISTS}

    items: list[dict] = []
    counts = {"addressed": 0, "gapped": 0, "missing": 0, "human_action": 0}
    for sid in full_subsection_ids():
        owner = ownership.get(sid)
        if owner in SPECIALISTS:
            if sid in drafted[owner]:
                state = "addressed"
            elif sid in gapped[owner]:
                state = "gapped"
            else:
                state = "missing"
        elif owner == "reviewer":
            state = "addressed"  # 12.3/12.4 produced by this stage (residual)
        elif owner == "human_action":
            state = "human_action"  # 12.5 — flagged for a human, not drafted
        else:
            state = "missing"
        counts[state] += 1
        items.append(
            {"section": sid, "title": full_subsection_title(sid), "owner": owner, "state": state}
        )
    return {
        "items": items,
        "counts": counts,
        "missing": [i["section"] for i in items if i["state"] == "missing"],
        "gaps": [i["section"] for i in items if i["state"] == "gapped"],
    }


def _render_coverage(coverage: dict) -> str:
    """The coverage checklist as context for the reviewer (§11.1) — so it knows what
    the draft actually addresses and does not paper over a gap or a missing section."""
    c = coverage["counts"]
    lines = [
        "# Coverage checklist (computed — do not recompute)\n",
        f"Addressed: {c['addressed']} · Gapped: {c['gapped']} · Missing: {c['missing']} · "
        f"Human action: {c['human_action']}\n",
    ]
    if coverage["missing"]:
        lines.append(f"**Missing (a deterministic finding): {', '.join(coverage['missing'])}**")
    if coverage["gaps"]:
        lines.append(
            f"Gapped (recorded, with reasons in the drafts): {', '.join(coverage['gaps'])}"
        )
    return "\n".join(lines)


def _apply_amendments(
    ctx: StageContext,
    drafts: dict[str, dict],
    directives: list[dict],
    outline: str,
    threshold_md: str,
    *,
    cycle: int | None = None,
    detail: Callable[[tuple[str, ...]], str] | None = None,
) -> dict[str, dict]:
    """Apply a set of amend directives: each targeted specialist amends its own directed
    sections (§11.3), re-driving its KB — targeted specialists fanned out concurrently
    (§5.4). Directives are grouped per specialist so a specialist amends all its directed
    sections in one pass. Shared by the REVIEW loop (``cycle`` set, default narration) and
    USER_REVISION (``detail`` set, no cycle) — the machinery is identical; only the
    ``revision``-event wording and the loop-counter differ."""
    kb_root = ctx.kb_root or _default_kb_root()
    by_spec: dict[str, list[dict]] = {}
    for d in directives:
        by_spec.setdefault(d["target_specialist"], []).append(d)

    tasks = [
        _amend_task(ctx, spec, dirs, kb_root, outline, threshold_md, drafts, cycle, detail)
        for spec, dirs in by_spec.items()
    ]
    run_agent_tasks(ctx, tasks)
    return drafts


def _amend_task(
    ctx: StageContext,
    spec: str,
    dirs: list[dict],
    kb_root: Path,
    outline: str,
    threshold_md: str,
    drafts: dict[str, dict],
    cycle: int | None,
    detail: Callable[[tuple[str, ...]], str] | None,
) -> AgentTask:
    """One targeted specialist's amendment task (§5.4, §11.3)."""
    node = f"{_SPECIALIST_NODE_PREFIX}{spec}"
    target_sections = tuple(
        sorted({s for d in dirs for s in d["target_sections"]}, key=_section_sort_key)
    )
    detail_text = (
        detail(target_sections)
        if detail is not None
        else f"amending {', '.join(target_sections)} per reviewer cycle {cycle}"
    )
    prior = SpecialistDraft.from_dict(drafts[spec])

    def work() -> SpecialistDraft:
        ctx.status.start_node(node)
        ctx.status.revision(node, detail_text, cycle=cycle, target=spec)
        index_text = _load_index_text(kb_root, spec)
        with KB(kb_root / f"{spec}.sqlite") as kb:
            return run_specialist_amendment(
                ctx.llm,
                spec,
                prior,
                target_sections,
                _render_directives(dirs),
                _amendment_seed_terms(dirs, target_sections),
                outline,
                threshold_md,
                kb,
                index_text,
                status=ctx.status,
                node_id=node,
            )

    def finish(new_draft: SpecialistDraft) -> None:
        ctx.write_json(f"full/specialists/{spec}.json", new_draft.to_dict())
        ctx.write_text(f"full/specialists/{spec}.md", render_specialist_markdown(new_draft))
        ctx.status.complete_node(node)
        drafts[spec] = new_draft.to_dict()

    return AgentTask(name=spec, work=work, finish=finish)


def _render_directives(dirs: list[dict]) -> str:
    """The directives for one specialist, rendered for its amendment prompt (§11.3)."""
    lines: list[str] = []
    for i, d in enumerate(dirs, start=1):
        lines.append(f"### Directive {i}: amend {', '.join(d['target_sections'])}")
        lines.append(f"**Ruling:** {d['ruling']}")
        if d.get("rationale"):
            lines.append(f"**Rationale:** {d['rationale']}")
        for claim in d.get("conflicting_claims") or []:
            ref = f" {claim['ref']}" if claim.get("ref") else ""
            lines.append(f"- §{claim.get('section', '?')}: {claim.get('claim', '')}{ref}")
        lines.append("")
    return "\n".join(lines)


def _amendment_seed_terms(dirs: list[dict], target_sections: tuple[str, ...]) -> str:
    """Seed the amendment's pre-fetch search with the directed section titles and the
    reviewer's rulings, so re-grounding starts from the conflict, not an empty query."""
    terms = [full_subsection_title(sid) for sid in target_sections]
    terms += [d["ruling"] for d in dirs]
    return " ".join(terms)


def _directives_as_unresolved(directives: list[dict]) -> list[dict]:
    """Directives still live when the cycle cap is reached become unresolved
    disagreements (§11.4) — recorded honestly rather than forced past the cap."""
    out: list[dict] = []
    for d in directives:
        claims = d.get("conflicting_claims") or []
        pa = claims[0] if len(claims) > 0 else {"claim": d["ruling"]}
        pb = claims[1] if len(claims) > 1 else {"claim": d.get("rationale", "")}
        out.append(
            {
                "topic": d["ruling"],
                "position_a": {
                    "specialist": f"full.specialist.{d['target_specialist']}",
                    "claim": pa.get("claim", ""),
                    "support": [pa["ref"]] if pa.get("ref") else [],
                },
                "position_b": {
                    "specialist": "reviewer",
                    "claim": pb.get("claim", ""),
                    "support": [pb["ref"]] if pb.get("ref") else [],
                },
                "why_unresolved": (
                    "The reviewer directed an amendment, but the review-cycle cap (2, §11) "
                    "was reached before it could be applied and re-verified."
                ),
            }
        )
    return out


def _compute_residual(residual_inputs: dict[str, dict]) -> dict:
    """Rate the reviewer's post-mitigation consequence/likelihood per §3 area and the
    §12.4 overall residual — highest-wins, in the deterministic engine (§10, §12.4).
    The one place a residual rating comes into being; the reviewer supplied only tiers."""
    per_section: dict[str, dict] = {}
    for sid in RISK_SECTIONS:
        r = residual_inputs[sid]
        per_section[sid] = {
            "consequence": r["consequence"],
            "likelihood": r["likelihood"],
            "rating": rating(r["consequence"], r["likelihood"]),
            "rationale": r.get("rationale", ""),
        }
    overall = overall_rating([per_section[sid]["rating"] for sid in RISK_SECTIONS])
    return {"sections": per_section, "overall_residual": overall}


def render_review_markdown(
    coverage: dict, result: ReviewerResult, residual: dict, unresolved: list[dict]
) -> str:
    """The reviewer's outputs as markdown (assembled into the notebook — §12.1's residual
    summary table, points of unresolved disagreement, and the coverage note)."""
    lines = ["# Review — coverage, coherence and residual risk", ""]

    lines += ["## 12.3 Residual risk summary", ""]
    lines += ["| Area | Consequence | Likelihood | Residual rating |", "| --- | --- | --- | --- |"]
    for sid in RISK_SECTIONS:
        r = residual["sections"][sid]
        lines.append(f"| {sid} | {r['consequence']} | {r['likelihood']} | {r['rating']} |")
    lines += [
        "",
        f"**12.4 Overall residual risk rating (highest-wins): {residual['overall_residual']}**",
        "",
    ]

    c = coverage["counts"]
    lines += [
        "## Coverage",
        "",
        f"Addressed: {c['addressed']} · Gapped: {c['gapped']} · Missing: {c['missing']} · "
        f"Human action: {c['human_action']}",
        "",
    ]
    if coverage["missing"]:
        lines += [f"Missing sections (deterministic finding): {', '.join(coverage['missing'])}", ""]

    if result.coherence_findings:
        lines += ["## Coherence findings", ""]
        for f in result.coherence_findings:
            secs = ", ".join(f["sections"]) if f["sections"] else ""
            lines.append(f"- **{f['summary']}**" + (f" ({secs})" if secs else ""))
            if f["detail"]:
                lines.append(f"  {f['detail']}")
        lines.append("")

    if unresolved:
        lines += ["## Points of unresolved disagreement", ""]
        for u in unresolved:
            lines += [
                f"### {u['topic']}",
                f"- **{u['position_a'].get('specialist', 'A')}**: {u['position_a'].get('claim', '')}",
                f"- **{u['position_b'].get('specialist', 'B')}**: {u['position_b'].get('claim', '')}",
                f"*Why unresolved: {u['why_unresolved']}*",
                "",
            ]
    return "\n".join(lines)


# -- USER_REVISION -------------------------------------------------------------


def user_revision(ctx: StageContext) -> None:
    """A post-COMPLETE user revision of the full assessment (§5.1 USER_REVISION, §5.8).

    Three steps, in order: (1) the reviewer **triages** the user's instructions into amend
    directives + declined instructions; (2) the targeted specialists **amend** their own
    directed sections (the same ``run_specialist_amendment`` machinery REVIEW uses, no new
    questions raised); (3) the reviewer **verifies** in a single pass and the engine —
    never the reviewer — recomputes the residual §12.3/§12.4 ratings. Unmet directives are
    recorded as unresolved rather than looped.

    The whole stage re-runs from step 1 on resume: its only committed output is the
    revision's ``verification.json`` (the checkpoint), and every input it reads
    (``request.json``, the specialist drafts) is the last committed state — on a fresh
    Actions disk an uncommitted partial run left nothing behind, so re-running is clean
    (the same whole-stage-idempotence REVIEW relies on). The revision number ``N`` is
    ``run.json``'s ``revisions.full``, already incremented by ``POST /revise`` before the
    dispatch."""
    n = ctx.run.revisions.get("full", 0)
    request = ctx.read_json(revision_request_relpath(n))
    instructions = str(request.get("instructions", ""))
    outline = ctx.outline()
    threshold_md = ctx.read_text("threshold/threshold_assessment.md")
    drafts = {s: ctx.read_json(f"full/specialists/{s}.json") for s in SPECIALISTS}
    valid_targets = {s: specialist_owned_sections(s) for s in SPECIALISTS}

    # Archive the outgoing report before it is superseded (§5.8). Doing the move here — at
    # the revision boundary, not inside ASSEMBLY — keeps ASSEMBLY's idempotent-skip honest:
    # once the prior assessment.ipynb/.html are moved to superseded/rev_<N>/, ASSEMBLY's
    # checkpoint files are absent, so the driver rebuilds them rather than mistaking the
    # superseded report for a completed one. Idempotent (a no-op if already moved).
    archive_superseded(ctx, n)

    # Step 1 — triage (reviewer, Pro): instructions → amend directives + declines.
    ctx.status.start_node(REVIEWER_NODE)
    ctx.status.revision(REVIEWER_NODE, f"user revision {n} of {REVISION_CAP}", target="reviewer")
    ctx.status.review_finding(
        REVIEWER_NODE, "Triaging your revision request into amend directives."
    )
    triage = run_revision_triage(
        ctx.llm,
        instructions=instructions,
        scope_context=reviewer_scope_context(),
        draft_context=_render_specialist_context(drafts),
        threshold_md=threshold_md,
        outline_md=outline,
        valid_targets=valid_targets,
    )
    ctx.write_json(revision_directives_relpath(n), triage.to_dict())
    for d in triage.declined:
        ctx.status.review_finding(REVIEWER_NODE, f"Declined: {d['instruction']} — {d['reason']}")
    ctx.status.complete_node(REVIEWER_NODE)

    # Step 2 — amendment (targeted specialists amend their own directed sections, §11.3).
    if triage.amend_directives:
        drafts = _apply_amendments(
            ctx,
            drafts,
            triage.amend_directives,
            outline,
            threshold_md,
            detail=lambda secs: f"amending {', '.join(secs)} for your revision request",
        )

    # Step 3 — verification (reviewer, one pass) + deterministic residual recompute (§12.4).
    ctx.status.start_node(REVIEWER_NODE)
    ctx.status.review_finding(
        REVIEWER_NODE, "Verifying the revision and re-judging the residual risk."
    )
    verification = run_revision_verification(
        ctx.llm,
        directives_context=_render_revision_directives(triage.amend_directives),
        instrument_context=threshold_instrument_context(),
        draft_context=_render_specialist_context(drafts),
        threshold_md=threshold_md,
        outline_md=outline,
    )
    residual = _compute_residual(verification.residual)
    ctx.write_json(RESIDUAL_RELPATH, residual)
    ctx.status.review_finding(
        REVIEWER_NODE,
        f"Residual overall risk after your revision (highest-wins): {residual['overall_residual']}.",
    )
    ctx.status.complete_node(REVIEWER_NODE)

    # The verification's unresolved set is authoritative for the revised report: it re-reads
    # the whole amended draft, so it — not a stale pre-revision list — is what the report
    # should show. Replace unresolved.json (removing it when the revision left nothing open).
    unresolved = list(verification.unresolved)
    if unresolved:
        ctx.write_json(UNRESOLVED_RELPATH, unresolved)
    else:
        ctx.path(UNRESOLVED_RELPATH).unlink(missing_ok=True)

    ctx.write_json(
        revision_verification_relpath(n),
        {
            "revision": n,
            "coherence_findings": verification.coherence_findings,
            "unresolved": unresolved,
            "declined": triage.declined,
            "residual": residual,
            "provenance": {
                "model": verification.model,
                "prompt_version": verification.prompt_version,
            },
        },
    )


def _render_revision_directives(directives: list[dict]) -> str:
    """Render the triage directives for the verification pass — so the reviewer can confirm
    each was addressed (§5.8 step 3). A revision that translated into no directives (every
    instruction declined) says so plainly."""
    heading = "## Directives issued in this revision (confirm each was addressed)"
    if not directives:
        return heading + "\n\nNo amend directives were issued — no actionable change was found."
    return heading + "\n\n" + _render_directives(directives)


def _build_questions_payload(raised: list[tuple[str, SpecialistDraft]]) -> dict:
    """The §6.4 batched-questions payload, grouped by specialist."""
    total = sum(len(d.questions) for _, d in raised)
    return {
        "batch_id": "q-1",
        "specialists": [
            {
                "node_id": node,
                "friendly": friendly_name(node),
                "why": d.questions_why,
                "items": d.questions,
            }
            for node, d in raised
        ],
        "counts": {"total": total, "answered": 0, "skipped": 0},
    }


def render_specialist_markdown(draft: SpecialistDraft) -> str:
    """A readable per-specialist section (assembled into the notebook, §12.1)."""
    lines = [f"# {draft.specialist} — owned sections", ""]
    for sid, text in draft.sections.items():
        lines += [f"## {sid}", "", text, ""]
        cites = draft.citations.get(sid) or []
        if cites:
            rendered = ", ".join(f"[{c['short_name']}, {c['locator']}]" for c in cites)
            lines += [f"*Citations: {rendered}*", ""]
    if draft.gaps:
        lines += ["## Gaps", ""]
        for g in draft.gaps:
            lines.append(f"- **{g['section']}**: {g['reason']}")
        lines.append("")
    return "\n".join(lines)
