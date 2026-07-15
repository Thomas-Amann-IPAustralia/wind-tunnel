"""The full-assessment drafting stage (TECH_SPEC §5.1 FULL_DRAFTING, §8.1, §9.3).

Six specialists each draft their own owned §5–12 sections independently, driving
their own KB through the bounded fetch/search tool loop (``agents/specialist.py``).
Each may raise up to three checkpoint questions; if any specialist raises one,
``full/questions.json`` is written and the driver's next stage is the
``FULL_CHECKPOINT`` user pause (§6.4). If none do, the checkpoint (and, since it
exists only to act on answers, ``FULL_REVISING``) is skipped entirely — the §5.1
happy path — and the driver proceeds straight to ``ARCHITECT`` (not yet built).
"""

from __future__ import annotations

import json
from pathlib import Path

from agents.architect import ArchitectPlan, run_architect
from agents.prompting import specialist_friendly_name
from agents.specialist import SpecialistDraft, run_specialist
from retrieval.retrieve import KB
from stages.context import StageContext
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
ARCHITECT_NODE = "full.architect"
ARCHITECT_MD_RELPATH = "full/architect.md"


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
    """Every specialist drafts its owned sections independently (§5.1, §9.3).
    Outputs ``full/specialists/<id>.json`` + ``.md`` for each, and
    ``full/questions.json`` iff at least one specialist raised a question."""
    kb_root = ctx.kb_root or _default_kb_root()
    outline = ctx.outline()
    threshold_md = ctx.read_text("threshold/threshold_assessment.md")

    raised: list[tuple[str, SpecialistDraft]] = []
    for specialist in SPECIALISTS:
        node = f"full.specialist.{specialist}"
        ctx.status.start_node(node)
        ctx.status.drafting(node, f"drafting {specialist}'s owned sections")
        index_text = _load_index_text(kb_root, specialist)
        with KB(kb_root / f"{specialist}.sqlite") as kb:
            draft = run_specialist(
                ctx.llm,
                specialist,
                outline,
                threshold_md,
                kb,
                index_text,
                status=ctx.status,
                node_id=node,
            )
        ctx.write_json(f"full/specialists/{specialist}.json", draft.to_dict())
        ctx.write_text(f"full/specialists/{specialist}.md", render_specialist_markdown(draft))
        ctx.status.complete_node(node)
        if draft.questions:
            raised.append((node, draft))

    if raised:
        ctx.write_json(QUESTIONS_RELPATH, _build_questions_payload(raised))
        for node, draft in raised:
            for item in draft.questions:
                ctx.status.question_raised(node, item["question_id"], item["text"])


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
