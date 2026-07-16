"""The proof-of-concept generator (TECH_SPEC §7, §12.3/§12.4; PROJECT_BRIEF §4; DESIGN §6.3).

One Flash call: given the outline, produce a single **self-contained** HTML document that mocks
the interface the finished system would have — no real data, no real integrations, simulated
logic. The file is committed as ``brainstorm/poc.html`` and later embedded into the governance
report as a sandboxed ``<iframe srcdoc>`` (§12.3), so it must stand alone.

The §12.4 limitations banner is authored **into** the file (design §6.3: a first-class element,
not chrome the app wraps around it). We do not add it ourselves; we *require* the model to, and
validate its presence via the ``poc-limitations`` marker class — a PoC without that banner is
rejected loudly rather than shipped, because the banner is a hard design requirement and the
downstream report has no other way to know it is there.
"""

from __future__ import annotations

from dataclasses import dataclass

from agents.prompting import load_prompt, wrap_untrusted
from llm import LLMClient

from brainstorm.synthesis import strip_code_fence

# The marker class the prompt instructs the model to put on the banner's outer element. It is
# the machine-checkable half of the §12.4 "authored into the file" contract.
LIMITATIONS_MARKER = "poc-limitations"


class PocError(RuntimeError):
    """A PoC output that is not a usable self-contained HTML document with its limitations
    banner. Loud — a PoC missing the banner violates a first-class design requirement
    (design §6.3, §12.4), so it is rejected, not silently committed."""


@dataclass
class PocResult:
    html: str
    model: str = ""
    prompt_version: str = ""


def generate_poc(
    client: LLMClient, *, outline_md: str, revision_instructions: str | None = None
) -> PocResult:
    """Generate the single-file HTML PoC from the whole outline (§7). ``outline_md`` is
    user-derived and wrapped as untrusted content (§9.2). Raises ``PocError`` if the output is
    not an HTML document carrying the limitations banner.

    When ``revision_instructions`` is given (the ``/revise`` path, brief §7), the PoC is
    **regenerated from the amended outline** with those instructions as extra steering — a fresh
    build, not a patch (brief §4 "regenerate rather than patch"). The instructions are
    user-derived and wrapped as untrusted content too (§9.2): they steer the build but never
    license dropping the banner or reaching the network."""
    prompt = load_prompt("poc_gen")
    parts = [wrap_untrusted(outline_md, label="## The project outline to prototype")]
    if revision_instructions and revision_instructions.strip():
        parts.append(
            wrap_untrusted(
                revision_instructions,
                label="## Changes the user has asked for in this revision",
            )
        )
        parts.append(
            "## Your task\n\nRebuild the single self-contained HTML document from the outline "
            "above, applying the requested changes. Regenerate it whole — do not try to patch a "
            "previous version. Begin with `<!doctype html>`, with the limitations banner first in "
            "reading order. No prose, no code fences."
        )
    else:
        parts.append(
            "## Your task\n\nReturn only the single self-contained HTML document your "
            "instructions describe — beginning with `<!doctype html>`, with the limitations "
            "banner first in reading order. No prose, no code fences."
        )
    resp = client.complete_text(prompt.model_role, prompt.system, "\n\n".join(parts))
    html = strip_code_fence(resp.text)
    _validate(html)
    return PocResult(html=html, model=resp.model, prompt_version=prompt.version)


def _validate(html: str) -> None:
    if not html.strip():
        raise PocError("PoC generation returned empty output.")
    low = html.lower()
    if "<!doctype html" not in low and "<html" not in low:
        raise PocError("PoC output is not an HTML document (no '<!doctype html>' or '<html>').")
    if LIMITATIONS_MARKER not in html:
        raise PocError(
            f"PoC output has no limitations banner (expected class={LIMITATIONS_MARKER!r}). "
            "The banner is a first-class requirement authored into the file (design §6.3, §12.4)."
        )
