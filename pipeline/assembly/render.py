"""HTML render of the report notebook (TECH_SPEC §12.5, design §8).

nbconvert's ``basic`` HTML template renders the notebook's markdown cells to HTML
with none of the Jupyter chrome; this module wraps that body in a self-contained
document carrying the custom stylesheet (§12.5) that delivers the Report register
(design §8): serif body, exact DTA numbering, mono citations, the calm
unresolved-disagreement panel, a mono provenance record, a running-footer standing
disclaimer, and a print stylesheet that keeps risk tables whole and chips legible in
greyscale (colour is never the only cue). The stylesheet is inlined so the render is a
single portable file — no external fonts, scripts, or styles are fetched.
"""

from __future__ import annotations

import html
from pathlib import Path

import nbformat
from nbconvert import HTMLExporter

from assembly.notebook import STANDING_DISCLAIMER

_CSS_PATH = Path(__file__).resolve().parent / "templates" / "report.css"


def render_html(nb: nbformat.NotebookNode, *, title: str = "AI impact assessment") -> str:
    """Render ``nb`` to a self-contained HTML report string. Non-executing — the
    notebook has only markdown cells, so nbconvert never runs a kernel."""
    exporter = HTMLExporter(template_name="basic")
    body, _ = exporter.from_notebook_node(nb)
    css = _CSS_PATH.read_text(encoding="utf-8")
    return _document(title, css, body)


def _document(title: str, css: str, body: str) -> str:
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>{html.escape(title)}</title>",
            f"<style>\n{css}\n</style>",
            "</head>",
            "<body>",
            '<main class="report">',
            body,
            "</main>",
            f'<div class="running-footer" role="contentinfo">{html.escape(STANDING_DISCLAIMER)}</div>',
            "</body>",
            "</html>",
            "",
        ]
    )
