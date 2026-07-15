"""pipeline.assembly — the notebook + HTML report builder (TECH_SPEC §12).

Public surface:
    build_notebook(data)      -> nbformat NotebookNode (the DTA 12-section report)
    render_html(nb, title=)   -> str (the self-contained nbconvert HTML render)
    resolve_references(...)   -> list[Reference]
    build_document_index(...) -> dict[short_name, doc]
"""

from assembly.notebook import build_notebook
from assembly.references import Reference, build_document_index, resolve_references
from assembly.render import render_html

__all__ = [
    "build_notebook",
    "render_html",
    "Reference",
    "build_document_index",
    "resolve_references",
]
