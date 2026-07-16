"""Shared helpers for the brainstorm *synthesis* agents (PoC and flow map).

Unlike the interviewer and sufficiency judge (which emit strict JSON), the PoC and flow-map
agents emit a whole artefact as free text — an HTML document, or Mermaid source. Models often
wrap such output in a Markdown code fence even when told not to; ``strip_code_fence`` trims a
single leading/trailing fence defensively (the artefact-specific validation still runs on what
is inside, and fails loudly if it is not what we asked for).
"""

from __future__ import annotations


def strip_code_fence(text: str) -> str:
    """Trim one surrounding ```lang … ``` (or bare ```) fence, if present.

    Mirrors ``llm._strip_code_fence`` (which is private to that module and JSON-specific): drops
    the opening fence line — ``` or ```html / ```mermaid — and a matching closing fence. Purely
    defensive; if there was no fence the text is returned stripped of surrounding whitespace."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[-1] if "\n" in stripped else ""
        if stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()[:-3]
    return stripped.strip()
