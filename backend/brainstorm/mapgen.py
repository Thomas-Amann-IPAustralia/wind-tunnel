"""The information-flow map generator (TECH_SPEC §7, §12.3; PROJECT_BRIEF §4; DESIGN §3.5, §6.4).

One Flash call: given the outline (and the PoC, if one exists), produce **Mermaid flowchart
source** for the information-flow map — actors, systems, data stores, and the flows between them
in the node/flow grammar (design §3.5). Committed as ``brainstorm/flow-map.mmd``.

The map is **not** rendered to SVG here. Rendering Mermaid needs headless Chromium, a poor fit
for Render's free tier, so the SPA renders it in-browser with ``mermaid.js`` and posts the SVG
back to commit (CLAUDE.md §9). This function therefore returns the Mermaid source; the endpoint
commits it and hands it to the SPA. (This resolves the apparent §7 "SVG at generation time"
phrasing in favour of the pinned deploy decision — see STATUS.md decisions and the §7 note.)

Validation is light and structural: the output must be Mermaid ``flowchart``/``graph`` source,
not prose. A stray answer is rejected loudly (the user can regenerate), matching the "reject,
don't repair" discipline the JSON agents use.
"""

from __future__ import annotations

from dataclasses import dataclass

from agents.prompting import load_prompt, wrap_untrusted
from llm import LLMClient

from brainstorm.synthesis import strip_code_fence

# The Mermaid diagram directives we accept as a first line. The prompt asks for `flowchart`
# (the node/flow grammar, design §3.5); `graph` is the older synonym and is tolerated.
_VALID_STARTS = ("flowchart", "graph")


class MapError(RuntimeError):
    """A flow-map output that is not Mermaid flowchart source. Loud — a prose answer would
    commit an unrenderable ``flow-map.mmd``; the user regenerates instead."""


@dataclass
class MapResult:
    mermaid: str
    model: str = ""
    prompt_version: str = ""


def generate_flow_map(
    client: LLMClient,
    *,
    outline_md: str,
    poc_html: str | None = None,
    revision_instructions: str | None = None,
) -> MapResult:
    """Generate the flow map's Mermaid source from the outline, optionally informed by the PoC
    (§7, §12.3). Both inputs are user-derived and wrapped as untrusted content (§9.2). Raises
    ``MapError`` if the output is not Mermaid flowchart source.

    When ``revision_instructions`` is given (the ``/revise`` path, brief §7), the map is
    **regenerated from the amended outline** with those instructions as extra steering — a fresh
    build, not a patch (brief §4). The instructions are user-derived and wrapped as untrusted
    content too (§9.2)."""
    prompt = load_prompt("map_gen")
    parts = [wrap_untrusted(outline_md, label="## The project outline to map")]
    if poc_html and poc_html.strip():
        parts.append(
            wrap_untrusted(
                poc_html,
                label="## The proof-of-concept prototype (already produced; informs the interface)",
            )
        )
    if revision_instructions and revision_instructions.strip():
        parts.append(
            wrap_untrusted(
                revision_instructions,
                label="## Changes the user has asked for in this revision",
            )
        )
        parts.append(
            "## Your task\n\nRebuild the Mermaid flowchart source from the outline above, applying "
            "the requested changes. Regenerate it whole — do not patch a previous version. Begin "
            "with `flowchart TD` (or `flowchart LR`). No prose, no code fences."
        )
    else:
        parts.append(
            "## Your task\n\nReturn only the Mermaid flowchart source your instructions describe — "
            "beginning with `flowchart TD` (or `flowchart LR`). No prose, no code fences."
        )
    resp = client.complete_text(prompt.model_role, prompt.system, "\n\n".join(parts))
    mermaid = strip_code_fence(resp.text)
    validate_mermaid(mermaid)
    return MapResult(mermaid=mermaid, model=resp.model, prompt_version=prompt.version)


def validate_mermaid(mermaid: str) -> None:
    """Assert ``mermaid`` is Mermaid flowchart/graph source, not prose. Raises ``MapError``
    otherwise. Public because the same check gates a **user-uploaded** ``.mmd`` file (§7 file
    upload) before it is committed as the run's ``flow-map.mmd`` — a generated map and an
    uploaded one must both be renderable, so they share one validator (one owner per fact)."""
    first = _first_meaningful_line(mermaid)
    if not first.lower().startswith(_VALID_STARTS):
        raise MapError(
            "flow-map output is not Mermaid flowchart source "
            f"(first line {first[:60]!r} is not a 'flowchart'/'graph' directive)."
        )


def _first_meaningful_line(mermaid: str) -> str:
    """The first non-blank, non-comment (``%%``) line — Mermaid allows leading comments."""
    for line in mermaid.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("%%"):
            return stripped
    return ""
