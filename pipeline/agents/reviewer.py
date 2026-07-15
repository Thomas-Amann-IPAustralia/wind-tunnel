"""The reviewer agent: coverage + coherence audit, amend directives, residual risk
(TECH_SPEC §5.1 REVIEW, §11, §12.3/§12.4), plus the two USER_REVISION passes (§5.8):
``run_revision_triage`` (a user revision request → amend directives + declined
instructions) and ``run_revision_verification`` (one pass confirming the amendments and
re-judging the residual). All three share the Pro model role and the same two boundaries
below.

The adjudicating reviewer (Pro) reads the assembled full draft plus the threshold
assessment and returns four things: coherence findings, amend directives targeting
individual specialists, unresolved disagreements it declined to force, and its
post-mitigation residual judgement for each of the eight §3 impact areas. It runs
once per review cycle (the ≤2 loop lives in the stage, §5.5); coverage itself is
computed deterministically in the stage (§11.1) and handed to the reviewer as
context — it is a checklist walk, not a judgement call.

Two boundaries are enforced here, the same "models argue, code computes" and
structural-write-scope discipline the other agents follow (§9.3, §10, §11.3):

  * **A directive may only target a section its specialist owns.** A directive naming
    an unknown specialist, or a section that specialist does not own, is **rejected**,
    not repaired — the reviewer cannot direct a specialist outside its write scope.
  * **The reviewer never asserts a rating.** Its residual output is consequence +
    likelihood + rationale per area; a `rating` key anywhere is rejected. The residual
    ratings are computed by the deterministic engine from these tiers (§12.4).
"""

from __future__ import annotations

from dataclasses import dataclass

from agents.prompting import (
    RISK_SECTIONS,
    load_prompt,
    wrap_untrusted,
)
from llm import LLMClient
from rating import consequence_tiers, likelihood_tiers

_SPECIALIST_PREFIX = "full.specialist."


class AgentError(RuntimeError):
    """A reviewer answer violated the output contract — a directive out of write
    scope, an asserted rating, or an incomplete residual judgement. Loud: the
    pipeline surfaces it as a calm, resumable failure (§5.6) rather than accepting an
    audit that breaks the invariants it exists to protect."""


@dataclass
class ReviewerResult:
    """One review cycle's output (§4 ``full/reviewer/cycle_N.json``). ``residual`` is
    keyed by §3 area id → ``{consequence, likelihood, rationale}`` — tiers only, never
    a rating (the engine computes those, §12.4)."""

    coherence_findings: list[dict]
    amend_directives: list[dict]
    unresolved: list[dict]
    residual: dict[str, dict]
    model: str = ""
    prompt_version: str = ""

    def to_dict(self) -> dict:
        return {
            "coherence_findings": self.coherence_findings,
            "amend_directives": self.amend_directives,
            "unresolved": self.unresolved,
            "residual": self.residual,
            "provenance": {"model": self.model, "prompt_version": self.prompt_version},
        }


def run_reviewer(
    client: LLMClient,
    *,
    instrument_context: str,
    scope_context: str,
    coverage_context: str,
    draft_context: str,
    threshold_md: str,
    outline_md: str,
    valid_targets: dict[str, tuple[str, ...]],
) -> ReviewerResult:
    """Run the reviewer once (§5.1 REVIEW, §11).

    ``instrument_context`` carries the residual consequence/likelihood tiers; ``scope_context``
    the valid directive targets; ``coverage_context`` the computed coverage checklist;
    ``draft_context`` the rendered specialist drafts. ``valid_targets`` maps each specialist
    id to the section ids it owns — the only pairs a directive may name."""
    prompt = load_prompt("reviewer")
    user = "\n\n".join(
        [
            instrument_context,
            scope_context,
            wrap_untrusted(outline_md, label="## Use-case outline (the concept under assessment)"),
            wrap_untrusted(
                threshold_md,
                label="## Threshold assessment (sections 1–4 and the computed inherent "
                "risk ratings — the residual you judge is measured against these)",
            ),
            coverage_context,
            wrap_untrusted(
                draft_context,
                label="## Assembled full assessment (sections 5–12 — the draft you audit)",
            ),
            "## Your task\n\nAudit the assembled draft now and return the single JSON "
            "object your instructions describe: coherence findings, amend directives "
            "(each within a specialist's own write scope), unresolved disagreements, and "
            "your residual consequence/likelihood judgement for every area 3.1–3.8. Never "
            "state a rating — the engine computes it.",
        ]
    )
    data, resp = client.complete_json("reviewer", prompt.system, user)
    return _parse_result(data, valid_targets, resp, prompt)


# -- USER_REVISION: triage + verification (§5.8) -------------------------------


@dataclass
class RevisionTriage:
    """The reviewer's triage of a user revision request (§5.8 step 1,
    ``full/revisions/rev_<N>/directives.json``). ``amend_directives`` are the §11.3
    directives the request translates into; ``declined`` records each instruction the
    reviewer refused to action, with a plain reason (rating-by-fiat, out of scope, or
    ungroundable) — never silently dropped."""

    amend_directives: list[dict]
    declined: list[dict]
    model: str = ""
    prompt_version: str = ""

    def to_dict(self) -> dict:
        return {
            "amend_directives": self.amend_directives,
            "declined": self.declined,
            "provenance": {"model": self.model, "prompt_version": self.prompt_version},
        }


def run_revision_triage(
    client: LLMClient,
    *,
    instructions: str,
    scope_context: str,
    draft_context: str,
    threshold_md: str,
    outline_md: str,
    valid_targets: dict[str, tuple[str, ...]],
) -> RevisionTriage:
    """Triage a user's full-assessment revision request into amend directives (§5.8 step 1).

    The instructions are wrapped as untrusted content (§9.2) — a revision request is user
    text, and a line in it that reads as a command to the model is a fact about what the
    user wants, not an instruction that overrides the rules. Directives are validated for
    write scope exactly as the review loop's are (§11.3); the reviewer asserts no rating
    and issues no directive whose effect is to set one — enforced structurally (a directive
    has no rating field) and by the prompt."""
    prompt = load_prompt("revision_triage")
    user = "\n\n".join(
        [
            scope_context,
            wrap_untrusted(outline_md, label="## Use-case outline (the concept under assessment)"),
            wrap_untrusted(
                threshold_md,
                label="## Threshold assessment (sections 1–4 — out of scope for this "
                "revision; shown for context only)",
            ),
            wrap_untrusted(
                draft_context,
                label="## The completed full assessment (sections 5–12 — what the user is "
                "asking to revise)",
            ),
            wrap_untrusted(
                instructions,
                label="## The user's revision instructions (what they want changed)",
            ),
            "## Your task\n\nTriage the request now and return the single JSON object your "
            "instructions describe: amend directives (each within a specialist's own write "
            "scope), and declined instructions with reasons. Issue no directive that sets a "
            "rating, and none touching sections 1–4.",
        ]
    )
    data, resp = client.complete_json(prompt.model_role, prompt.system, user)
    valid = {spec: set(sections) for spec, sections in valid_targets.items()}
    return RevisionTriage(
        amend_directives=_parse_directives(data.get("amend_directives"), valid),
        declined=_parse_declined(data.get("declined")),
        model=resp.model,
        prompt_version=prompt.version,
    )


def run_revision_verification(
    client: LLMClient,
    *,
    directives_context: str,
    instrument_context: str,
    draft_context: str,
    threshold_md: str,
    outline_md: str,
) -> ReviewerResult:
    """The single verification pass closing a revision (§5.8 step 3). Confirms the issued
    directives were met — anything unmet is returned as an ``unresolved`` point, not
    re-directed — and re-judges the residual consequence/likelihood per §3 area (the engine
    rates from these tiers, §12.4). Issues **no** new directives: a revision is one triage,
    one amendment, one verification (``amend_directives`` is always empty). Returns a
    :class:`ReviewerResult` so the residual flows through the same engine call the review
    loop uses."""
    prompt = load_prompt("revision_verify")
    user = "\n\n".join(
        [
            instrument_context,
            wrap_untrusted(outline_md, label="## Use-case outline (the concept under assessment)"),
            wrap_untrusted(
                threshold_md,
                label="## Threshold assessment (sections 1–4 and the computed inherent "
                "risk ratings — the residual you judge is measured against these)",
            ),
            directives_context,
            wrap_untrusted(
                draft_context,
                label="## The amended full assessment (sections 5–12 — after this revision's "
                "amendments)",
            ),
            "## Your task\n\nVerify the revision now and return the single JSON object your "
            "instructions describe: coherence findings, unresolved points for any directive "
            "not met, and your residual consequence/likelihood judgement for every area "
            "3.1–3.8. Issue no new directives. Never state a rating — the engine computes it.",
        ]
    )
    data, resp = client.complete_json(prompt.model_role, prompt.system, user)
    return ReviewerResult(
        coherence_findings=_parse_findings(data.get("coherence_findings")),
        amend_directives=[],  # verification never re-directs (§5.8)
        unresolved=_parse_unresolved(data.get("unresolved")),
        residual=_parse_residual(data.get("residual")),
        model=resp.model,
        prompt_version=prompt.version,
    )


def _parse_declined(raw: object) -> list[dict]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise AgentError("reviewer: 'declined' must be a list if present.")
    out: list[dict] = []
    for i, d in enumerate(raw, start=1):
        if not isinstance(d, dict):
            raise AgentError(f"reviewer: declined item {i} must be an object.")
        instruction = str(d.get("instruction", "")).strip()
        reason = str(d.get("reason", "")).strip()
        if not instruction or not reason:
            raise AgentError(
                f"reviewer: declined item {i} needs a non-empty 'instruction' and 'reason'."
            )
        out.append({"instruction": instruction, "reason": reason})
    return out


# -- validation (§11.3 write scope, §12.4 no asserted rating) -------------------


def _parse_result(
    data: dict, valid_targets: dict[str, tuple[str, ...]], resp, prompt
) -> ReviewerResult:
    valid = {spec: set(sections) for spec, sections in valid_targets.items()}
    return ReviewerResult(
        coherence_findings=_parse_findings(data.get("coherence_findings")),
        amend_directives=_parse_directives(data.get("amend_directives"), valid),
        unresolved=_parse_unresolved(data.get("unresolved")),
        residual=_parse_residual(data.get("residual")),
        model=resp.model,
        prompt_version=prompt.version,
    )


def _parse_findings(raw: object) -> list[dict]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise AgentError("reviewer: 'coherence_findings' must be a list if present.")
    out: list[dict] = []
    for i, f in enumerate(raw, start=1):
        if not isinstance(f, dict) or not str(f.get("summary", "")).strip():
            raise AgentError(f"reviewer: coherence finding {i} needs a non-empty 'summary'.")
        sections = f.get("sections") or []
        if not isinstance(sections, list):
            raise AgentError(f"reviewer: coherence finding {i} 'sections' must be a list.")
        out.append(
            {
                "summary": str(f["summary"]).strip(),
                "sections": [str(s) for s in sections],
                "detail": str(f.get("detail", "")).strip(),
            }
        )
    return out


def _parse_directives(raw: object, valid: dict[str, set[str]]) -> list[dict]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise AgentError("reviewer: 'amend_directives' must be a list if present.")
    out: list[dict] = []
    for i, d in enumerate(raw, start=1):
        if not isinstance(d, dict):
            raise AgentError(f"reviewer: amend directive {i} must be an object.")
        specialist = _normalise_specialist(d.get("target_specialist"), i)
        if specialist not in valid:
            raise AgentError(
                f"reviewer: directive {i} targets unknown specialist "
                f"{specialist!r} (known: {sorted(valid)})."
            )
        target_sections = d.get("target_sections")
        if not isinstance(target_sections, list) or not target_sections:
            raise AgentError(
                f"reviewer: directive {i} ({specialist}) needs a non-empty 'target_sections'."
            )
        clean_sections: list[str] = []
        for sid in target_sections:
            sid = str(sid)
            if sid not in valid[specialist]:
                raise AgentError(
                    f"reviewer: directive {i} targets section {sid!r}, which {specialist!r} "
                    f"does not own (owns: {sorted(valid[specialist])}) — a directive may only "
                    "act within a specialist's own write scope (§11.3)."
                )
            clean_sections.append(sid)
        ruling = str(d.get("ruling", "")).strip()
        if not ruling:
            raise AgentError(f"reviewer: directive {i} ({specialist}) needs a non-empty 'ruling'.")
        out.append(
            {
                "target_specialist": specialist,
                "target_sections": clean_sections,
                "conflicting_claims": _clean_claims(d.get("conflicting_claims")),
                "ruling": ruling,
                "rationale": str(d.get("rationale", "")).strip(),
            }
        )
    return out


def _normalise_specialist(raw: object, index: int) -> str:
    """Accept the §11.3 node-id form (``full.specialist.privacy``) or a bare id
    (``privacy``) and return the bare id used everywhere else in the codebase."""
    if not raw or not isinstance(raw, str):
        raise AgentError(f"reviewer: directive {index} needs a 'target_specialist'.")
    return raw[len(_SPECIALIST_PREFIX) :] if raw.startswith(_SPECIALIST_PREFIX) else raw


def _clean_claims(raw: object) -> list[dict]:
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for c in raw:
        if isinstance(c, dict):
            out.append(
                {
                    "section": str(c.get("section", "")),
                    "claim": str(c.get("claim", "")),
                    "ref": str(c.get("ref", "")),
                }
            )
    return out


def _parse_unresolved(raw: object) -> list[dict]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise AgentError("reviewer: 'unresolved' must be a list if present.")
    out: list[dict] = []
    for i, u in enumerate(raw, start=1):
        if not isinstance(u, dict):
            raise AgentError(f"reviewer: unresolved item {i} must be an object.")
        topic = str(u.get("topic", "")).strip()
        if not topic:
            raise AgentError(f"reviewer: unresolved item {i} needs a non-empty 'topic'.")
        pa, pb = u.get("position_a"), u.get("position_b")
        if not isinstance(pa, dict) or not isinstance(pb, dict):
            raise AgentError(
                f"reviewer: unresolved item {i} needs object 'position_a' and 'position_b'."
            )
        why = str(u.get("why_unresolved", "")).strip()
        if not why:
            raise AgentError(f"reviewer: unresolved item {i} needs a 'why_unresolved'.")
        out.append({"topic": topic, "position_a": pa, "position_b": pb, "why_unresolved": why})
    return out


def _parse_residual(raw: object) -> dict[str, dict]:
    if not isinstance(raw, dict):
        raise AgentError("reviewer: 'residual' must be an object covering areas 3.1–3.8.")
    cons = set(consequence_tiers())
    like = set(likelihood_tiers())
    out: dict[str, dict] = {}
    for sid in RISK_SECTIONS:
        entry = raw.get(sid)
        if not isinstance(entry, dict):
            raise AgentError(f"reviewer: residual is missing an object for area {sid!r}.")
        if "rating" in entry:
            raise AgentError(
                f"reviewer: residual[{sid!r}] contains a 'rating' — the reviewer argues "
                "consequence and likelihood; the engine computes the rating (§12.4)."
            )
        consequence = str(entry.get("consequence", ""))
        likelihood = str(entry.get("likelihood", ""))
        if consequence not in cons:
            raise AgentError(
                f"reviewer: residual[{sid!r}] consequence {consequence!r} is not a valid tier "
                f"(one of {sorted(cons)})."
            )
        if likelihood not in like:
            raise AgentError(
                f"reviewer: residual[{sid!r}] likelihood {likelihood!r} is not a valid tier "
                f"(one of {sorted(like)})."
            )
        out[sid] = {
            "consequence": consequence,
            "likelihood": likelihood,
            "rationale": str(entry.get("rationale", "")).strip(),
        }
    return out
