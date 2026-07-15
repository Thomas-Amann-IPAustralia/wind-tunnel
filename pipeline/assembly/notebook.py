"""Notebook assembly — the DTA 12-section report as an nbformat notebook (TECH_SPEC
§12.1, design §8).

The final artefact is a Jupyter notebook in **assembly-and-provenance format,
non-executable** (no code cells; nothing runs), built programmatically from the
committed run artefacts. The cell plan mirrors the instrument exactly: a title block,
sections 1–4 (threshold) with the computed rating table, sections 5–12 (full) in tool
order with inline citations, the residual 12.3/12.4 summary, the appendices
(implementation plan, recommended next steps, unresolved disagreements, provenance),
and the deduplicated reference list.

Structured blocks (title, residual table, unresolved panel, provenance) are emitted as
HTML embedded in markdown cells so the stylesheet (§12.5) can style them by class; prose
is plain markdown. This module is pure — it takes a gathered data bundle (the stage does
the I/O) and returns a ``NotebookNode``.
"""

from __future__ import annotations

import html

import nbformat
from nbformat.v4 import new_markdown_cell, new_notebook

DRAFT_MARK = "DRAFT — for SME review"
STANDING_DISCLAIMER = "Draft for SME review — not an approval, not legal advice."

_RISK_SECTIONS = ("3.1", "3.2", "3.3", "3.4", "3.5", "3.6", "3.7", "3.8")


def build_notebook(data: dict) -> nbformat.NotebookNode:
    """Assemble the report notebook from a gathered data bundle (see the stage's
    ``gather_inputs``). No code cells — the notebook is a document, not a program."""
    cells = [
        _title_block(data),
        _md(_threshold_section(data)),
        _md(_full_section(data)),
        _md(_residual_section(data)),
        _md(_implementation_plan(data)),
        _md(_next_steps(data)),
    ]
    unresolved = _unresolved_section(data)
    if unresolved:
        cells.append(_md(unresolved))
    poc = _poc_section(data)
    if poc:
        cells.append(_md(poc))
    cells.append(_md(_provenance_section(data)))
    cells.append(_md(_references_section(data)))

    nb = new_notebook(cells=cells)
    nb.metadata["windtunnel"] = {"run_id": data.get("run_id", ""), "artefact": "assessment"}
    return nb


def _md(text: str) -> nbformat.NotebookNode:
    return new_markdown_cell(text)


# -- cells ---------------------------------------------------------------------


def _title_block(data: dict) -> nbformat.NotebookNode:
    title = html.escape(data.get("title") or "AI impact assessment")
    run_id = html.escape(data.get("run_id", ""))
    generated = html.escape(data.get("generated_at", ""))
    revision = data.get("revision_label", "")
    rev_html = f'<p class="rev">{html.escape(revision)}</p>' if revision else ""
    return _md(
        f'<div class="title-block">\n'
        f'  <p class="draft-mark">{html.escape(DRAFT_MARK)}</p>\n'
        f"  <h1>{title}</h1>\n"
        f"  {rev_html}\n"
        f'  <p class="meta">Run <code>{run_id}</code> · Generated {generated}</p>\n'
        f'  <p class="disclaimer">{html.escape(STANDING_DISCLAIMER)}</p>\n'
        f"</div>"
    )


def _threshold_section(data: dict) -> str:
    body = (data.get("threshold_md") or "").strip()
    return "# Threshold assessment — sections 1–4\n\n" + (body or "_Not available._")


def _full_section(data: dict) -> str:
    lines = ["# Full assessment — sections 5–12", ""]
    blocks = data.get("full_sections") or []
    if not blocks:
        lines.append("_No full-assessment sections were drafted._")
        return "\n".join(lines)
    for block in blocks:
        sid = block["section_id"]
        title = block.get("title", "")
        friendly = block.get("friendly", "")
        lines.append(f"## {sid} · {title}")
        if friendly:
            lines.append(f'<p class="attribution">Assessed by: {html.escape(friendly)}</p>')
        lines.append("")
        if block.get("gap"):
            lines.append(f'<p class="gap-note">Gap — {html.escape(block["gap"])}</p>')
        else:
            lines.append(block.get("body", "").strip())
            cites = block.get("citations") or []
            if cites:
                rendered = "; ".join(f"[{c['short_name']}, {c['locator']}]" for c in cites)
                lines.append(f'<p class="citations">Sources: {html.escape(rendered)}</p>')
        lines.append("")
    return "\n".join(lines)


def _residual_section(data: dict) -> str:
    residual = data.get("residual") or {}
    sections = residual.get("sections") or {}
    lines = ["# Residual risk — 12.3 and 12.4", "", "## 12.3 Residual risk summary", ""]
    lines += ['<table class="risk-table">']
    lines.append(
        "<thead><tr><th>Area</th><th>Consequence</th><th>Likelihood</th>"
        "<th>Residual rating</th></tr></thead><tbody>"
    )
    for sid in _RISK_SECTIONS:
        r = sections.get(sid) or {}
        rating = r.get("rating", "")
        lines.append(
            f"<tr><td>{sid}</td><td>{html.escape(r.get('consequence', ''))}</td>"
            f"<td>{html.escape(r.get('likelihood', ''))}</td>"
            f'<td class="chip chip-{_slug(rating)}">{html.escape(rating)}</td></tr>'
        )
    lines += ["</tbody></table>", ""]
    overall = residual.get("overall_residual", "")
    lines += [
        f'<p class="overall">12.4 Overall residual risk rating '
        f'(highest-wins): <span class="chip chip-{_slug(overall)}">{html.escape(overall)}</span></p>',
        "",
    ]
    if data.get("high_risk_governance_review_required"):
        lines.append(
            '<p class="human-action">12.5 — Overall residual risk is High: refer to an '
            "internal governance body for review. No agent can perform this review; it is a "
            "flagged human action.</p>"
        )
    else:
        lines.append(
            '<p class="human-action">12.5 — Internal governance body review is a human '
            "action where the agency's governance policy requires it.</p>"
        )
    return "\n".join(lines)


def _implementation_plan(data: dict) -> str:
    body = (data.get("architect_md") or "").strip()
    body = _strip_leading_h1(body)
    return "# Appendix — Implementation Plan\n\n" + (body or "_Not available._")


def _next_steps(data: dict) -> str:
    lines = ["# Appendix — Recommended next steps", ""]
    gaps = data.get("gaps") or []
    skipped = data.get("skipped_questions") or []
    if not gaps and not skipped:
        lines.append("No gaps or unanswered questions were recorded.")
        return "\n".join(lines)
    lines.append(
        "Where the assessment could not be completed from the available evidence, the "
        "point is recorded here as a concrete next step for the project team — not a "
        "failure of the assessment."
    )
    lines.append("")
    for gap in gaps:
        friendly = gap.get("friendly", "")
        who = f" _({html.escape(friendly)})_" if friendly else ""
        lines.append(f"- **§{gap['section']}**{who}: {gap['reason']}")
    for q in skipped:
        lines.append(
            f"- **Unanswered checkpoint question** ({q.get('question_id', '')}): {q.get('text', '')}"
        )
    return "\n".join(lines)


def _unresolved_section(data: dict) -> str:
    unresolved = data.get("unresolved") or []
    if not unresolved:
        return ""
    lines = [
        "# Appendix — Points of unresolved disagreement",
        "",
        '<div class="unresolved-intro">For a governance assessment, honest disagreement is '
        "more credible than manufactured agreement. These points are flagged for human "
        "judgement.</div>",
        "",
    ]
    for u in unresolved:
        pa, pb = u.get("position_a") or {}, u.get("position_b") or {}
        lines.append('<div class="unresolved-panel">')
        lines.append(f"<h3>{html.escape(u.get('topic', ''))}</h3>")
        lines.append(_position_html(pa))
        lines.append(_position_html(pb))
        lines.append(
            f'<p class="why">Why unresolved: {html.escape(u.get("why_unresolved", ""))}</p>'
        )
        lines.append("</div>")
    return "\n".join(lines)


def _position_html(pos: dict) -> str:
    who = html.escape(str(pos.get("specialist", "")))
    claim = html.escape(str(pos.get("claim", "")))
    support = pos.get("support") or []
    sup = (
        f' <span class="citations">{html.escape("; ".join(str(s) for s in support))}</span>'
        if support
        else ""
    )
    return f'<p class="position"><strong>{who}:</strong> {claim}{sup}</p>'


def _poc_section(data: dict) -> str:
    poc_html = data.get("poc_html")
    if not poc_html:
        return ""
    srcdoc = html.escape(poc_html, quote=True)
    return (
        "# Appendix — Proof of concept\n\n"
        '<iframe class="poc-frame" sandbox="" title="Proof of concept" '
        f'srcdoc="{srcdoc}"></iframe>\n\n'
        "_The proof of concept uses no real data, no real integrations, and simulated "
        "logic. Its limitations banner travels inside the file itself._"
    )


def _provenance_section(data: dict) -> str:
    prov = data.get("provenance") or {}
    lines = ["# Appendix — Provenance", "", '<div class="provenance">']
    lines.append(f"<p>Run id: <code>{html.escape(data.get('run_id', ''))}</code></p>")
    lines.append(f"<p>Created: <code>{html.escape(data.get('created_at', ''))}</code></p>")
    lines.append(f"<p>Generated: <code>{html.escape(data.get('generated_at', ''))}</code></p>")

    roles = prov.get("roles") or {}
    if roles:
        lines.append("<p>Models and prompts per role:</p><ul>")
        for role, info in sorted(roles.items()):
            model = html.escape(str(info.get("model", "")))
            pv = html.escape(str(info.get("prompt_version", "")))
            lines.append(f"<li><code>{html.escape(role)}</code>: {model} (prompt {pv})</li>")
        lines.append("</ul>")

    manifests = prov.get("corpus_manifests") or []
    if manifests:
        lines.append("<p>Corpus manifest versions:</p><ul>")
        for m in manifests:
            lines.append(
                f"<li><code>{html.escape(str(m.get('specialist', '')))}</code>: "
                f"{html.escape(str(m.get('generated_at', '')))} "
                f"({m.get('document_count', 0)} documents)</li>"
            )
        lines.append("</ul>")

    attested = data.get("attested")
    ceiling = html.escape(str(data.get("sensitivity_ceiling", "OFFICIAL")))
    verb = "were attested" if attested else "were NOT attested"
    lines.append(
        f'<p class="attestation">Inputs {verb} by the submitting officer as at or below '
        f"{ceiling}.</p>"
    )
    lines.append("</div>")
    return "\n".join(lines)


def _references_section(data: dict) -> str:
    refs = data.get("references") or []
    lines = ["# References", ""]
    if not refs:
        lines.append("_No corpus documents were cited._")
        return "\n".join(lines)
    lines.append('<div class="references">')
    for ref in refs:
        parts = [f"<strong>{html.escape(ref['short_name'])}</strong>"]
        if ref.get("title") and ref["title"] != ref["short_name"]:
            parts.append(html.escape(ref["title"]))
        for key in ("publisher", "version"):
            if ref.get(key):
                parts.append(html.escape(ref[key]))
        line = " — ".join(parts)
        url = ref.get("source_url")
        if url:
            line += f' <a href="{html.escape(url, quote=True)}">{html.escape(url)}</a>'
        if not ref.get("resolved", True):
            line += ' <span class="unresolved-ref">(source not found in corpus manifest)</span>'
        lines.append(f'<p class="reference">{line}</p>')
    lines.append("</div>")
    return "\n".join(lines)


# -- helpers -------------------------------------------------------------------


def _strip_leading_h1(md: str) -> str:
    """Drop a leading ``# heading`` so an embedded artefact's own title does not clash
    with the report's heading hierarchy."""
    lines = md.splitlines()
    if lines and lines[0].startswith("# "):
        return "\n".join(lines[1:]).strip()
    return md


def _slug(rating: str) -> str:
    return (rating or "none").strip().lower().replace(" ", "-")
