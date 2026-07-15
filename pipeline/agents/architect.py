"""The architect agent: the Implementation Plan appendix (TECH_SPEC §5.1 ARCHITECT,
§12.1; PROJECT_BRIEF §5.5).

Structurally the simplest of the drafting agents — a single Pro call, no retrieval
tool loop. It reads what the specialists have already drafted (their sections 5–12,
citations and gaps), the completed threshold assessment, and the outline, and writes
a concrete implementation plan whose every step traces back to a mitigation a
specialist actually recorded.

Two boundaries are enforced here, mirroring the "models argue, code computes" and
structural-write-scope discipline the other agents follow (§9.3, §10):

  * **The architect writes only the appendix.** Its output is ``overview`` + ``steps``
    — there is no section-content field, so it cannot restate or re-draft any
    specialist's owned section (§5.1 "cannot modify other content").
  * **Every step must trace to a real drafted mitigation.** A ``traces_to`` entry
    naming a ``(specialist, section)`` pair the specialist did not actually draft is
    **rejected**, not ignored — the plan cannot fabricate a control the assessment
    never made or attribute one to the wrong specialist. This is the machine-checkable
    half of PROJECT_BRIEF §5.5's "the plan demonstrably answers the assessment rather
    than existing beside it."
"""

from __future__ import annotations

from dataclasses import dataclass

from agents.prompting import load_prompt, specialist_friendly_name, wrap_untrusted
from llm import LLMClient


class AgentError(RuntimeError):
    """The architect's answer violated the output contract — a missing overview or
    steps, a step without a traceable mitigation, or a trace to a section a
    specialist did not draft. Loud: the pipeline surfaces it as a calm, resumable
    failure (§5.6) rather than assembling a plan that does not answer the
    assessment."""


@dataclass
class ArchitectPlan:
    """The Implementation Plan appendix (§4 ``full/architect.json`` → rendered to
    ``full/architect.md``). ``steps`` each carry a non-empty ``traces_to`` list of
    ``{specialist, section, mitigation}`` naming a section the specialist drafted."""

    overview: str
    steps: list[dict]
    model: str = ""
    prompt_version: str = ""

    def to_dict(self) -> dict:
        return {
            "overview": self.overview,
            "steps": self.steps,
            "provenance": {"model": self.model, "prompt_version": self.prompt_version},
        }


def run_architect(
    client: LLMClient,
    outline_md: str,
    threshold_md: str,
    specialist_context: str,
    valid_targets: dict[str, tuple[str, ...]],
) -> ArchitectPlan:
    """Run the architect once (§5.1 ARCHITECT). ``specialist_context`` is the rendered
    drafted sections + gaps of all six specialists; ``valid_targets`` maps each
    specialist id to the section ids it actually drafted — the only ``(specialist,
    section)`` pairs a step may trace to."""
    prompt = load_prompt("architect")
    user = "\n\n".join(
        [
            wrap_untrusted(outline_md, label="## Use-case outline (the concept under assessment)"),
            wrap_untrusted(
                threshold_md,
                label="## Threshold assessment (sections 1–4 and the computed inherent "
                "risk ratings)",
            ),
            wrap_untrusted(
                specialist_context,
                label="## Completed specialist assessment (sections 5–12 — the drafts "
                "your plan must answer)",
            ),
            _targets_note(valid_targets),
            "## Your task\n\nWrite the Implementation Plan appendix now, as the single "
            "JSON object your instructions describe. Every step must trace to a "
            "mitigation a specialist actually drafted above.",
        ]
    )
    data, resp = client.complete_json("architect", prompt.system, user)
    return _parse_plan(data, valid_targets, resp, prompt)


def _targets_note(valid_targets: dict[str, tuple[str, ...]]) -> str:
    """The exhaustive list of (specialist, section) pairs a step may trace to — the
    drafted sections only. Stated in the prompt so the model traces to real
    mitigations rather than guessing at ownership."""
    lines = [
        "## Traceable sections\n",
        "Each step's `traces_to` may reference only these `(specialist, section)` "
        "pairs — the sections that were actually drafted:",
    ]
    for specialist, sections in valid_targets.items():
        if sections:
            joined = ", ".join(sections)
            lines.append(f"- **{specialist}** ({specialist_friendly_name(specialist)}): {joined}")
    return "\n".join(lines)


# -- validation (§5.1 write scope, §5.5 traceability) --------------------------


def _parse_plan(
    data: dict, valid_targets: dict[str, tuple[str, ...]], resp, prompt
) -> ArchitectPlan:
    overview = data.get("overview")
    if not isinstance(overview, str) or not overview.strip():
        raise AgentError("architect: 'overview' must be a non-empty string.")

    steps_in = data.get("steps")
    if not isinstance(steps_in, list) or not steps_in:
        raise AgentError("architect: 'steps' must be a non-empty list.")

    valid = {spec: set(sections) for spec, sections in valid_targets.items()}
    steps_out: list[dict] = []
    for i, step in enumerate(steps_in, start=1):
        if not isinstance(step, dict):
            raise AgentError(f"architect: step {i} must be an object.")
        title = step.get("title")
        detail = step.get("detail")
        if not isinstance(title, str) or not title.strip():
            raise AgentError(f"architect: step {i} needs a non-empty 'title'.")
        if not isinstance(detail, str) or not detail.strip():
            raise AgentError(f"architect: step {i} ({title!r}) needs a non-empty 'detail'.")
        traces = _require_traces(step.get("traces_to"), i, title, valid)
        steps_out.append({"title": title.strip(), "detail": detail.strip(), "traces_to": traces})

    return ArchitectPlan(
        overview=overview.strip(),
        steps=steps_out,
        model=resp.model,
        prompt_version=prompt.version,
    )


def _require_traces(
    raw: object, step_no: int, title: str, valid: dict[str, set[str]]
) -> list[dict]:
    if not isinstance(raw, list) or not raw:
        raise AgentError(
            f"architect: step {step_no} ({title!r}) needs a non-empty 'traces_to' — "
            "every step must implement a mitigation the assessment made (§5.5)."
        )
    out: list[dict] = []
    for t in raw:
        if not isinstance(t, dict) or not t.get("specialist") or not t.get("section"):
            raise AgentError(
                f"architect: step {step_no} ({title!r}) has a trace without a "
                "'specialist' and 'section'."
            )
        specialist = str(t["specialist"])
        section = str(t["section"])
        if specialist not in valid:
            raise AgentError(
                f"architect: step {step_no} ({title!r}) traces to unknown specialist "
                f"{specialist!r}."
            )
        if section not in valid[specialist]:
            raise AgentError(
                f"architect: step {step_no} ({title!r}) traces to section {section!r}, "
                f"which {specialist!r} did not draft (drafted: {sorted(valid[specialist])}) "
                "— a step may only implement a real drafted mitigation (§5.5)."
            )
        out.append(
            {
                "specialist": specialist,
                "section": section,
                "mitigation": str(t.get("mitigation", "")).strip(),
            }
        )
    return out
