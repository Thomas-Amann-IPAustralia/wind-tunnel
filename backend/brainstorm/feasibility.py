"""The PoC feasibility gate (TECH_SPEC §7; PROJECT_BRIEF §4, §6.1).

One Flash-Lite call, run by ``POST /api/runs/{id}/poc`` before a PoC is offered: given the
outline's UX/interface and happy-path sections, would a static single-file HTML PoC meaningfully
visualise this solution? Interfaces / dashboards / form-driven tools → yes; headless pipelines,
integrations and back-office automations → no, in which case the caller produces the flow map
instead and says why (§7).

Returns ``{feasible, reason}`` — the ``reason`` is shown to the user verbatim (the honest "not a
fit for this idea; you'll get a flow map instead" message, design §5 conditional-stage rule). A
malformed answer (no boolean ``feasible`` or no ``reason``) is a loud ``FeasibilityError`` so the
endpoint returns a clean error rather than guessing.
"""

from __future__ import annotations

from dataclasses import dataclass

from agents.prompting import load_prompt, wrap_untrusted
from llm import LLMClient


class FeasibilityError(RuntimeError):
    """A feasibility answer with no usable verdict (no boolean ``feasible`` / no ``reason``).
    Loud so the endpoint surfaces a clean error rather than proceeding on a guess."""


@dataclass
class FeasibilityResult:
    feasible: bool
    reason: str
    model: str = ""
    prompt_version: str = ""


def assess_feasibility(client: LLMClient, *, ux_ui: str, happy_path: str) -> FeasibilityResult:
    """Judge whether a static HTML PoC would help (§7). ``ux_ui`` and ``happy_path`` are the two
    outline section bodies the gate reads; both are user-derived and wrapped as untrusted content
    (§9.2). An empty section body is passed as a plain "(not yet described)" so the gate can still
    lean on the happy path."""
    prompt = load_prompt("feasibility_gate")
    parts = [
        wrap_untrusted(
            ux_ui.strip() or "(not yet described)", label="## UX and interface (from the outline)"
        ),
        wrap_untrusted(
            happy_path.strip() or "(not yet described)", label="## Happy path (from the outline)"
        ),
        "## Your task\n\nReturn the single JSON object your instructions describe: `feasible` "
        "(true/false — would a static single-file HTML PoC meaningfully visualise this?) and a "
        "one-sentence `reason` the person will read.",
    ]
    data, resp = client.complete_json(prompt.model_role, prompt.system, "\n\n".join(parts))
    return _parse(data, resp, prompt)


def _parse(data: dict, resp, prompt) -> FeasibilityResult:
    feasible = data.get("feasible")
    if not isinstance(feasible, bool):
        raise FeasibilityError("feasibility gate returned no boolean 'feasible'.")
    reason = str(data.get("reason", "")).strip()
    if not reason:
        raise FeasibilityError("feasibility gate returned no 'reason'.")
    return FeasibilityResult(
        feasible=feasible, reason=reason, model=resp.model, prompt_version=prompt.version
    )
