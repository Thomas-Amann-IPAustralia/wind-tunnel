"""Threshold agents: the two generalists and the reconciler (TECH_SPEC §5.1, §9, §10).

Each agent builds its prompt, calls the model through the LLM seam, and validates
the structured answer. The validation is where the "models argue, code computes"
invariant (§10) is enforced at the agent boundary: a generalist selects a
consequence tier and a likelihood tier — exact members of the instrument tables —
and an answer that carries a ``rating`` (or an off-vocabulary tier) is **rejected**,
not repaired. No agent here ever returns a risk rating; the engine computes those in
the reconciling stage.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agents.prompting import (
    RISK_SECTIONS,
    load_prompt,
    threshold_instrument_context,
    wrap_untrusted,
)
from llm import LLMClient
from rating import consequence_tiers, likelihood_tiers

# Keys an agent is forbidden to emit inside a risk entry — asserting a rating is the
# one thing the integrity model does not permit (§10, §9.4).
_FORBIDDEN_RISK_KEYS = frozenset({"rating", "risk", "risk_rating", "level", "score"})
_CONTEXT_SECTIONS: tuple[str, ...] = ("1", "2", "4")


class AgentError(RuntimeError):
    """A threshold agent's answer violated the output contract — a missing section,
    an off-vocabulary tier, or a forbidden rating key. Loud: the pipeline surfaces it
    as a calm, resumable failure (§5.6) rather than proceeding on a bad draft."""


@dataclass
class GeneralistDraft:
    """One generalist's threshold draft (§5.1 THRESHOLD_DRAFTING output). ``risks``
    maps each of 3.1–3.8 to ``{consequence, likelihood, rationale}`` — no rating."""

    label: str  # "generalist_a" | "generalist_b"
    sections: dict[str, str]  # "1" | "2" | "4" -> markdown
    risks: dict[str, dict]  # "3.x" -> {consequence, likelihood, rationale}
    model: str = ""
    prompt_version: str = ""

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "sections": self.sections,
            "risks": self.risks,
            "provenance": {"model": self.model, "prompt_version": self.prompt_version},
        }


@dataclass
class ReconcilerResult:
    """The reconciler's synthesised narrative + per-area rationale + divergence notes
    (§5.1 THRESHOLD_RECONCILING). It carries no tiers or ratings — those are resolved
    and computed by code (§10.3)."""

    sections: dict[str, str]
    risk_rationale: dict[str, str]
    divergence_notes: dict[str, str] = field(default_factory=dict)
    model: str = ""
    prompt_version: str = ""


def run_generalist(client: LLMClient, label: str, outline_md: str) -> GeneralistDraft:
    """Run one threshold generalist over the outline (§5.1, §9.3). ``label`` is
    ``generalist_a``/``generalist_b`` — the two run independently on the same input,
    and any divergence is the reconciler's signal."""
    prompt = load_prompt("threshold_generalist")
    user = (
        f"{threshold_instrument_context()}\n\n"
        f"{wrap_untrusted(outline_md, label='## Use-case outline (the concept under assessment)')}"
    )
    data, resp = client.complete_json(prompt.model_role, prompt.system, user)
    sections = _require_sections(data, label)
    risks = _require_risks(data, label)
    return GeneralistDraft(
        label=label,
        sections=sections,
        risks=risks,
        model=resp.model,
        prompt_version=prompt.version,
    )


def run_reconciler(
    client: LLMClient,
    outline_md: str,
    draft_a: GeneralistDraft,
    draft_b: GeneralistDraft,
    resolved: dict[str, dict],
    *,
    revision_instructions: str | None = None,
) -> ReconcilerResult:
    """Run the reconciler (§5.1, §10.3). ``resolved`` is the code-resolved
    higher-wins ``{3.x: {consequence, likelihood}}`` map the stage computed; the
    reconciler writes the narrative and rationale that explain it but never sets a
    tier or rating.

    ``revision_instructions`` (a threshold revision, §7) — when present — carries the
    user's requested changes as **untrusted data** (§9.2): they steer the reconciled
    narrative and rationale but never license changing a resolved tier or a rating (those
    are computed by code from the two generalists' unchanged inputs — "models argue, code
    computes", §10). On the initial reconciliation it is ``None`` and the prompt is
    unchanged."""
    prompt = load_prompt("threshold_reconciler")
    parts = [
        threshold_instrument_context(),
        wrap_untrusted(outline_md, label="## Use-case outline"),
        _render_draft("Assessor A", draft_a),
        _render_draft("Assessor B", draft_b),
        _render_resolved(resolved),
    ]
    if revision_instructions and revision_instructions.strip():
        parts.append(
            wrap_untrusted(
                revision_instructions,
                label=(
                    "## Requested revision to the threshold assessment\n"
                    "The user has asked for the following changes. Apply them to the reconciled "
                    "narrative and rationale where faithful to the resolved position. You may "
                    "**not** change any consequence tier, likelihood tier, or rating — those are "
                    "computed by code from the two assessors' unchanged inputs (§10)."
                ),
            )
        )
    user = "\n\n".join(parts)
    data, resp = client.complete_json(prompt.model_role, prompt.system, user)
    sections = _require_sections(data, "reconciler")
    rationale = _require_rationale(data)
    notes = data.get("divergence_notes") or {}
    if not isinstance(notes, dict):
        raise AgentError("reconciler: 'divergence_notes' must be an object if present.")
    return ReconcilerResult(
        sections=sections,
        risk_rationale=rationale,
        divergence_notes={str(k): str(v) for k, v in notes.items()},
        model=resp.model,
        prompt_version=prompt.version,
    )


# -- validation ----------------------------------------------------------------


def _require_sections(data: dict, who: str) -> dict[str, str]:
    sections = data.get("sections")
    if not isinstance(sections, dict):
        raise AgentError(f"{who}: 'sections' must be an object with keys 1, 2, 4.")
    out: dict[str, str] = {}
    for sid in _CONTEXT_SECTIONS:
        value = sections.get(sid)
        if not isinstance(value, str) or not value.strip():
            raise AgentError(f"{who}: section {sid!r} is missing or empty.")
        out[sid] = value.strip()
    return out


def _require_risks(data: dict, who: str) -> dict[str, dict]:
    risks = data.get("risks")
    if not isinstance(risks, dict):
        raise AgentError(f"{who}: 'risks' must be an object with keys 3.1–3.8.")
    valid_consequence = set(consequence_tiers())
    valid_likelihood = set(likelihood_tiers())
    out: dict[str, dict] = {}
    for sid in RISK_SECTIONS:
        entry = risks.get(sid)
        if not isinstance(entry, dict):
            raise AgentError(f"{who}: risk {sid!r} is missing.")
        forbidden = _FORBIDDEN_RISK_KEYS & set(entry)
        if forbidden:
            raise AgentError(
                f"{who}: risk {sid!r} asserts a rating via {sorted(forbidden)} — agents "
                "select consequence + likelihood only; the engine computes the rating (§10)."
            )
        consequence = entry.get("consequence")
        likelihood = entry.get("likelihood")
        rationale = entry.get("rationale")
        if consequence not in valid_consequence:
            raise AgentError(
                f"{who}: risk {sid!r} consequence {consequence!r} is not a valid tier "
                f"{sorted(valid_consequence)}."
            )
        if likelihood not in valid_likelihood:
            raise AgentError(
                f"{who}: risk {sid!r} likelihood {likelihood!r} is not a valid tier "
                f"{sorted(valid_likelihood)}."
            )
        if not isinstance(rationale, str) or not rationale.strip():
            raise AgentError(f"{who}: risk {sid!r} has no rationale.")
        out[sid] = {
            "consequence": consequence,
            "likelihood": likelihood,
            "rationale": rationale.strip(),
        }
    return out


def _require_rationale(data: dict) -> dict[str, str]:
    rationale = data.get("risk_rationale")
    if not isinstance(rationale, dict):
        raise AgentError("reconciler: 'risk_rationale' must be an object with keys 3.1–3.8.")
    out: dict[str, str] = {}
    for sid in RISK_SECTIONS:
        value = rationale.get(sid)
        if not isinstance(value, str) or not value.strip():
            raise AgentError(f"reconciler: risk_rationale {sid!r} is missing or empty.")
        if _FORBIDDEN_RISK_KEYS & {value.lower().strip()}:
            raise AgentError(f"reconciler: risk_rationale {sid!r} looks like a bare rating.")
        out[sid] = value.strip()
    return out


# -- prompt rendering helpers --------------------------------------------------


def _render_draft(name: str, draft: GeneralistDraft) -> str:
    lines = [f"## {name}'s draft"]
    for sid in _CONTEXT_SECTIONS:
        lines.append(f"### Section {sid}\n{draft.sections[sid]}")
    lines.append("### Section 3 judgements")
    for sid in RISK_SECTIONS:
        r = draft.risks[sid]
        lines.append(
            f"- {sid}: consequence={r['consequence']}, likelihood={r['likelihood']} — "
            f"{r['rationale']}"
        )
    return "\n".join(lines)


def _render_resolved(resolved: dict[str, dict]) -> str:
    lines = ["## Resolved section-3 tiers (higher-wins, computed by code — do not change)"]
    for sid in RISK_SECTIONS:
        r = resolved[sid]
        lines.append(f"- {sid}: consequence={r['consequence']}, likelihood={r['likelihood']}")
    return "\n".join(lines)
