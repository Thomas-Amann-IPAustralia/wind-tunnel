"""The threshold stage handlers: drafting and reconciling (TECH_SPEC §5.1, §10).

``THRESHOLD_DRAFTING`` runs two generalists independently over the outline.
``THRESHOLD_RECONCILING`` is where the integrity core lands: it resolves the two
drafts' section-3 tiers **higher-wins in code** (§10.3), the deterministic engine
computes every rating and the §3.9 overall from those resolved inputs (§10), and the
reconciler agent writes only the narrative and rationale around them. No agent — not
even the Pro reconciler — ever asserts a rating; the number is provably a code
output. Routing (full required / optional / may-conclude) is computed from the §3.9
rating per the tool's own rule (guidance §4).
"""

from __future__ import annotations

from agents.prompting import RISK_SECTIONS
from agents.threshold import (
    GeneralistDraft,
    ReconcilerResult,
    run_generalist,
    run_reconciler,
)
from rating import consequence_tiers, likelihood_tiers, overall_rating, rating
from stages.context import StageContext
from statefile import REVISION_CAP

NODE_A = "threshold.generalist_a"
NODE_B = "threshold.generalist_b"
NODE_RECONCILER = "threshold.reconciler"
NODE_RATING = "threshold.rating_engine"

REVISIONS_RELDIR = "threshold/revisions"


def revision_request_relpath(n: int) -> str:
    """Where ``POST /revise {threshold}`` stages the user's revision request (§7)."""
    return f"{REVISIONS_RELDIR}/rev_{n}/request.json"


def revision_reconciled_relpath(n: int) -> str:
    """THRESHOLD_RECONCILING's per-revision checkpoint output (§5.3): a record of the
    reconciled narrative produced for revision ``N``. It is distinct per revision so a
    revision re-dispatch is **not** idempotently skipped by the initial pass's standard
    ``reconciled.json``/``ratings.json`` outputs (the same technique USER_REVISION uses for
    its ``rev_<N>/verification.json`` checkpoint, run.py)."""
    return f"{REVISIONS_RELDIR}/rev_{n}/reconciled.json"


_CONTEXT_SECTIONS = ("1", "2", "4")
_SECTION_TITLES = {
    "1": "Basic information",
    "2": "Purpose and expected benefits",
    "3": "Inherent risk assessment",
    "4": "Threshold assessment outcome",
}
_RISK_TITLES = {
    "3.1": "Reducing service accessibility and inclusion",
    "3.2": "Unfair discrimination",
    "3.3": "Stereotyping or demeaning representations",
    "3.4": "Harm",
    "3.5": "Privacy concerns",
    "3.6": "Security concerns — data aspects",
    "3.7": "Security concerns — system aspects",
    "3.8": "Reputation or public confidence",
}


# -- THRESHOLD_DRAFTING --------------------------------------------------------


def threshold_drafting(ctx: StageContext) -> None:
    """Two generalists (Flash) draft sections 1–4 independently (§5.1). Outputs
    ``threshold/generalist_a.json`` and ``threshold/generalist_b.json``."""
    outline = ctx.outline()
    for node, label in ((NODE_A, "generalist_a"), (NODE_B, "generalist_b")):
        ctx.status.start_node(node)
        ctx.status.drafting(node, "drafting threshold sections 1–4")
        draft = run_generalist(ctx.llm, label, outline)
        ctx.write_json(f"threshold/{label}.json", draft.to_dict())
        ctx.status.complete_node(node)


# -- THRESHOLD_RECONCILING -----------------------------------------------------


def threshold_reconciling(ctx: StageContext) -> None:
    """Resolve the two drafts higher-wins, compute ratings deterministically, run the
    reconciler for narrative, and compute routing (§5.1, §10.3). Outputs
    ``reconciled.json``, ``divergence.json``, ``ratings.json``, ``routing.json`` and
    a human-readable ``threshold_assessment.md``.

    On a **user revision** (§7, ``run.json.revisions.threshold > 0``) this same stage
    re-runs with the staged instructions in context. The two generalist drafts stand
    untouched, so the higher-wins resolution — and thus the engine's ratings — are
    unchanged; the revision steers only the reconciled narrative ("models argue, code
    computes", §10). A per-revision ``rev_<N>/reconciled.json`` checkpoint is written so the
    re-dispatch is not idempotently skipped by the initial pass's outputs (run.py)."""
    draft_a = _load_draft(ctx, "generalist_a")
    draft_b = _load_draft(ctx, "generalist_b")

    resolved = resolve_inputs(draft_a, draft_b)
    divergence = build_divergence(draft_a, draft_b, resolved)

    # A threshold revision (§7): re-run with the user's instructions in context. rev is 0 on
    # the initial reconciliation (no request file, unchanged prompt).
    rev = ctx.run.revisions.get("threshold", 0)
    revision_instructions: str | None = None
    if rev > 0:
        request = ctx.read_json(revision_request_relpath(rev))
        revision_instructions = str(request.get("instructions", ""))

    # Reconciler writes narrative + rationale around the code-resolved tiers.
    ctx.status.start_node(NODE_RECONCILER)
    if rev > 0:
        ctx.status.revision(
            NODE_RECONCILER, f"user revision {rev} of {REVISION_CAP}", target="reconciler"
        )
    outline = ctx.outline()
    result = run_reconciler(
        ctx.llm, outline, draft_a, draft_b, resolved, revision_instructions=revision_instructions
    )
    ctx.status.complete_node(NODE_RECONCILER)

    # The engine computes every rating — the one place a rating comes into being.
    ctx.status.start_node(NODE_RATING)
    ratings = compute_ratings(resolved)
    routing = compute_routing(ratings)
    ctx.status.complete_node(NODE_RATING)

    reconciled = _assemble_reconciled(result, resolved, ratings)
    ctx.write_json("threshold/reconciled.json", reconciled)
    ctx.write_json("threshold/divergence.json", divergence)
    ctx.write_json("threshold/ratings.json", ratings)
    ctx.write_json("threshold/routing.json", routing)
    ctx.write_text(
        "threshold/threshold_assessment.md",
        render_markdown(ctx.run.run_id, reconciled, ratings, routing),
    )

    # Per-revision checkpoint marker (§5.3) + audit record of what this revision produced.
    if rev > 0:
        ctx.write_json(
            revision_reconciled_relpath(rev),
            {"revision": rev, "reconciled": reconciled, "routing": routing},
        )


# -- higher-wins resolution + the engine (§10.3) -------------------------------


def _tier_index(tiers: tuple[str, ...], label: str) -> int:
    return tiers.index(label)


def _higher(tiers: tuple[str, ...], a: str, b: str) -> str:
    return a if _tier_index(tiers, a) >= _tier_index(tiers, b) else b


def resolve_inputs(draft_a: GeneralistDraft, draft_b: GeneralistDraft) -> dict[str, dict]:
    """Per section-3 area, take the higher consequence tier and the higher likelihood
    tier across the two drafts (§10.3 — the tool resolves disagreement upward). The
    result is the code-resolved input the engine rates."""
    cons = consequence_tiers()
    like = likelihood_tiers()
    resolved: dict[str, dict] = {}
    for sid in RISK_SECTIONS:
        a, b = draft_a.risks[sid], draft_b.risks[sid]
        resolved[sid] = {
            "consequence": _higher(cons, a["consequence"], b["consequence"]),
            "likelihood": _higher(like, a["likelihood"], b["likelihood"]),
        }
    return resolved


def compute_ratings(resolved: dict[str, dict]) -> dict:
    """Rate every section-3 area from its resolved inputs and compute the §3.9
    overall highest-wins — all in the deterministic engine (§10)."""
    per_section: dict[str, dict] = {}
    for sid in RISK_SECTIONS:
        r = resolved[sid]
        per_section[sid] = {
            "consequence": r["consequence"],
            "likelihood": r["likelihood"],
            "rating": rating(r["consequence"], r["likelihood"]),
        }
    overall = overall_rating([per_section[sid]["rating"] for sid in RISK_SECTIONS])
    return {"sections": per_section, "overall_inherent": overall}


def build_divergence(
    draft_a: GeneralistDraft, draft_b: GeneralistDraft, resolved: dict[str, dict]
) -> dict:
    """Record, per section-3 area, both assessors' inputs, the resolved (higher)
    tiers, and whether they diverged — the audit trail for §10.3."""
    out: dict[str, dict] = {}
    for sid in RISK_SECTIONS:
        a, b = draft_a.risks[sid], draft_b.risks[sid]
        diverged = a["consequence"] != b["consequence"] or a["likelihood"] != b["likelihood"]
        out[sid] = {
            "a": {"consequence": a["consequence"], "likelihood": a["likelihood"]},
            "b": {"consequence": b["consequence"], "likelihood": b["likelihood"]},
            "resolved": resolved[sid],
            "diverged": diverged,
        }
    return {"sections": out}


# -- routing (guidance §4) -----------------------------------------------------


def compute_routing(ratings: dict) -> dict:
    """Compute the threshold outcome routing from the §3.9 overall (guidance §4):
    Low → full assessment optional, the officer may conclude at section 4;
    Medium/High → full assessment required; High additionally flags an internal
    governance body review (§12.5). This is computed, never agent-asserted."""
    overall = ratings["overall_inherent"]
    medium_or_high = [
        sid for sid in RISK_SECTIONS if ratings["sections"][sid]["rating"] in ("Medium", "High")
    ]
    required = overall in ("Medium", "High")
    return {
        "overall_inherent_rating": overall,
        "full_assessment": "required" if required else "optional",
        "may_conclude": overall == "Low",
        "high_risk_governance_review_required": overall == "High",
        "medium_or_high_sections": medium_or_high,
        "basis": (
            "DTA AI impact assessment tool §3.9/§4: all-low ⇒ officer may conclude at "
            "section 4 (full assessment optional); any medium or high ⇒ full assessment "
            "required; overall high ⇒ also refer to an internal governance body (§12.5)."
        ),
    }


# -- assembly ------------------------------------------------------------------


def _assemble_reconciled(result: ReconcilerResult, resolved: dict, ratings: dict) -> dict:
    """The final threshold assessment record: reconciled narrative + per-area
    consequence/likelihood/rating/rationale (rating from the engine)."""
    risks: dict[str, dict] = {}
    for sid in RISK_SECTIONS:
        risks[sid] = {
            "consequence": resolved[sid]["consequence"],
            "likelihood": resolved[sid]["likelihood"],
            "rating": ratings["sections"][sid]["rating"],
            "rationale": result.risk_rationale[sid],
            "divergence_note": result.divergence_notes.get(sid, ""),
        }
    return {
        "sections": result.sections,
        "risks": risks,
        "overall_inherent": ratings["overall_inherent"],
        "provenance": {"model": result.model, "prompt_version": result.prompt_version},
    }


def _load_draft(ctx: StageContext, label: str) -> GeneralistDraft:
    data = ctx.read_json(f"threshold/{label}.json")
    return GeneralistDraft(
        label=data["label"],
        sections=data["sections"],
        risks=data["risks"],
        model=data.get("provenance", {}).get("model", ""),
        prompt_version=data.get("provenance", {}).get("prompt_version", ""),
    )


def render_markdown(run_id: str, reconciled: dict, ratings: dict, routing: dict) -> str:
    """A readable threshold assessment for export (Stage 2 markdown export). Faithful
    to the reconciled record; the ratings shown are the engine's, not an agent's."""
    lines = [f"# Threshold AI impact assessment — {run_id}", ""]
    for sid in _CONTEXT_SECTIONS:
        if sid == "4":
            continue
        lines += [f"## {sid}. {_SECTION_TITLES[sid]}", "", reconciled["sections"][sid], ""]

    lines += ["## 3. Inherent risk assessment", ""]
    lines += ["| Area | Consequence | Likelihood | Risk rating |", "| --- | --- | --- | --- |"]
    for sid in RISK_SECTIONS:
        r = reconciled["risks"][sid]
        lines.append(
            f"| {sid} {_RISK_TITLES[sid]} | {r['consequence']} | {r['likelihood']} | {r['rating']} |"
        )
    lines += [
        "",
        f"**3.9 Overall inherent risk rating (highest-wins): {reconciled['overall_inherent']}**",
        "",
    ]
    for sid in RISK_SECTIONS:
        r = reconciled["risks"][sid]
        lines += [f"### {sid} {_RISK_TITLES[sid]}", "", r["rationale"]]
        if r["divergence_note"]:
            lines += ["", f"*Divergence: {r['divergence_note']}*"]
        lines.append("")

    lines += ["## 4. Threshold assessment outcome", "", reconciled["sections"]["4"], ""]
    outcome = (
        "A full assessment is **required**."
        if routing["full_assessment"] == "required"
        else "A full assessment is **optional**; the officer may conclude at section 4."
    )
    lines.append(outcome)
    if routing["high_risk_governance_review_required"]:
        lines.append(
            "\nOverall inherent risk is **High** — refer to an internal governance body (§12.5)."
        )
    lines.append("")
    return "\n".join(lines)
