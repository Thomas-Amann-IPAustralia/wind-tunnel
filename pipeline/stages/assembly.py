"""The ASSEMBLY stage (TECH_SPEC §5.1 ASSEMBLY, §12).

Gathers every committed run artefact — the threshold assessment, the six specialist
drafts, the architect appendix, and the reviewer's residual + unresolved outputs — and
builds the final deliverables: a non-executable nbformat notebook (``assessment.ipynb``)
and its self-contained nbconvert HTML render (``assessment.html``), following the §12.1
cell plan. Pure assembly of on-disk state (``pipeline/assembly/`` does the building);
this handler is the I/O boundary. On success the driver advances to ``COMPLETE``.
"""

from __future__ import annotations

import json
from pathlib import Path

from agents.prompting import (
    full_assessment_ownership,
    full_subsection_ids,
    full_subsection_title,
    specialist_friendly_name,
)
from assembly import build_document_index, build_notebook, render_html, resolve_references
from stages.context import StageContext

ASSEMBLY_NODE = "full.assembly"
NOTEBOOK_RELPATH = "artefacts/assessment.ipynb"
HTML_RELPATH = "artefacts/assessment.html"

SPECIALISTS: tuple[str, ...] = (
    "it_security",
    "privacy",
    "ethics",
    "legal",
    "data_governance",
    "solution_architect",
)


def assembly(ctx: StageContext) -> None:
    """Build ``artefacts/assessment.ipynb`` + ``assessment.html`` from the committed
    artefacts (§12.1). Advances to ``COMPLETE`` once written."""
    import nbformat

    ctx.status.start_node(ASSEMBLY_NODE)
    ctx.status.drafting(ASSEMBLY_NODE, "Assembling the notebook and the report.")

    data = gather_inputs(ctx)
    nb = build_notebook(data)
    ctx.write_text(NOTEBOOK_RELPATH, nbformat.writes(nb, version=4))
    ctx.write_text(HTML_RELPATH, render_html(nb, title=data.get("title") or "AI impact assessment"))

    ctx.status.complete_node(ASSEMBLY_NODE)


def gather_inputs(ctx: StageContext) -> dict:
    """Collect every artefact the report is built from into one bundle (§12.1). Reads
    only committed on-disk state, so ASSEMBLY re-runs identically on resume (§5.3)."""
    run = ctx.run
    outline = (
        ctx.read_text("brainstorm/outline.md") if _exists(ctx, "brainstorm/outline.md") else ""
    )
    specialists = {s: ctx.read_json(f"full/specialists/{s}.json") for s in SPECIALISTS}
    residual = ctx.read_json("full/reviewer/ratings_residual.json")

    return {
        "run_id": run.run_id,
        "title": _title_from_outline(outline),
        "created_at": run.created_at,
        "generated_at": ctx.now(),
        "attested": run.attestation.get("attested", False),
        "sensitivity_ceiling": run.attestation.get("sensitivity_ceiling", "OFFICIAL"),
        "threshold_md": _read_optional(ctx, "threshold/threshold_assessment.md"),
        "full_sections": _build_full_sections(specialists),
        "residual": residual,
        "high_risk_governance_review_required": residual.get("overall_residual") == "High",
        "architect_md": _read_optional(ctx, "full/architect.md"),
        "gaps": _aggregate_gaps(specialists),
        "skipped_questions": _skipped_questions(ctx),
        "unresolved": _read_json_optional(ctx, "full/reviewer/unresolved.json") or [],
        "references": [r.to_dict() for r in _build_references(ctx, specialists)],
        "provenance": _build_provenance(ctx, specialists),
        "poc_html": _read_optional(ctx, "brainstorm/poc.html") or None,
    }


def _build_full_sections(specialists: dict[str, dict]) -> list[dict]:
    """Sections 5–12 in tool order (§12.1), each pulled from its owning specialist with
    its inline citations, or shown as a gap. The reviewer-owned (12.3/12.4) and
    human-action (12.5) subsections are rendered elsewhere and skipped here."""
    ownership = full_assessment_ownership()
    blocks: list[dict] = []
    for sid in full_subsection_ids():
        owner = ownership.get(sid)
        if owner not in specialists:
            continue  # 12.3/12.4 (reviewer) and 12.5 (human action) are not drafted here
        draft = specialists[owner]
        sections = draft.get("sections") or {}
        gaps = {g["section"]: g["reason"] for g in (draft.get("gaps") or [])}
        block = {
            "section_id": sid,
            "title": full_subsection_title(sid),
            "friendly": specialist_friendly_name(owner),
        }
        if sid in sections:
            block["body"] = sections[sid]
            block["citations"] = (draft.get("citations") or {}).get(sid) or []
        else:
            block["gap"] = gaps.get(sid, "not drafted")
        blocks.append(block)
    return blocks


def _aggregate_gaps(specialists: dict[str, dict]) -> list[dict]:
    """The gap register (§12.1 recommended next steps): every specialist gap, with the
    friendly name of the specialist that recorded it."""
    out: list[dict] = []
    for spec in SPECIALISTS:
        friendly = specialist_friendly_name(spec)
        for gap in specialists[spec].get("gaps") or []:
            out.append({"section": gap["section"], "reason": gap["reason"], "friendly": friendly})
    out.sort(key=_section_sort_key)
    return out


def _skipped_questions(ctx: StageContext) -> list[dict]:
    """Checkpoint questions the user left unanswered (§5.1 "skipped questions → gaps"),
    surfaced in the report's recommended-next-steps appendix (§12.1). A question is skipped
    if it carries no answer — an explicit skip or one simply not addressed. Empty when the
    run had no checkpoint (``full/answers.json`` absent)."""
    answers = _read_json_optional(ctx, "full/answers.json")
    questions = _read_json_optional(ctx, "full/questions.json")
    if not answers or not questions:
        return []
    answered = {a.get("question_id") for a in (answers.get("answers") or [])}
    out: list[dict] = []
    for spec in questions.get("specialists") or []:
        for item in spec.get("items") or []:
            qid = item.get("question_id")
            if qid not in answered:
                out.append({"question_id": qid, "text": item.get("text", "")})
    return out


def _build_references(ctx: StageContext, specialists: dict[str, dict]):
    citations = {s: (specialists[s].get("citations") or {}) for s in SPECIALISTS}
    manifests = _load_manifests(ctx)
    return resolve_references(citations, build_document_index(manifests))


def _build_provenance(ctx: StageContext, specialists: dict[str, dict]) -> dict:
    """Per-role model + prompt version, from each artefact's own provenance block, plus a
    corpus-manifest summary (§12.2). Sourced from what actually ran, not config."""
    roles: dict[str, dict] = {}

    def add(role: str, artefact: dict | None) -> None:
        prov = (artefact or {}).get("provenance") or {}
        if prov:
            roles[role] = {
                "model": prov.get("model", ""),
                "prompt_version": prov.get("prompt_version", ""),
            }

    add("threshold_generalist", _read_json_optional(ctx, "threshold/generalist_a.json"))
    add("threshold_reconciler", _read_json_optional(ctx, "threshold/reconciled.json"))
    add("specialist", specialists[SPECIALISTS[0]])
    add("architect", _read_json_optional(ctx, "full/architect.json"))
    add("reviewer", _read_json_optional(ctx, "full/reviewer/cycle_1.json"))

    manifests = _load_manifests(ctx)
    corpus = [
        {
            "specialist": m.get("specialist", ""),
            "generated_at": m.get("generated_at", ""),
            "document_count": m.get("document_count", 0),
        }
        for m in manifests
    ]
    return {"roles": roles, "corpus_manifests": corpus}


def _load_manifests(ctx: StageContext) -> list[dict]:
    kb_root = ctx.kb_root or _default_kb_root()
    manifests: list[dict] = []
    for spec in SPECIALISTS:
        path = kb_root / f"{spec}.manifest.json"
        if path.is_file():
            with path.open(encoding="utf-8") as fh:
                manifests.append(json.load(fh))
    return manifests


# -- helpers -------------------------------------------------------------------


def _default_kb_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "kb").is_dir():
            return parent / "kb"
    raise FileNotFoundError(f"Could not locate kb/ above {here}.")


def _exists(ctx: StageContext, relpath: str) -> bool:
    return ctx.path(relpath).is_file()


def _read_optional(ctx: StageContext, relpath: str) -> str:
    return ctx.read_text(relpath) if _exists(ctx, relpath) else ""


def _read_json_optional(ctx: StageContext, relpath: str):
    return ctx.read_json(relpath) if _exists(ctx, relpath) else None


def _title_from_outline(outline_md: str) -> str:
    for line in outline_md.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return "AI impact assessment"


def _section_sort_key(gap: dict) -> tuple[int, int]:
    major, _, minor = str(gap["section"]).partition(".")
    return (int(major) if major.isdigit() else 0, int(minor) if minor.isdigit() else 0)
