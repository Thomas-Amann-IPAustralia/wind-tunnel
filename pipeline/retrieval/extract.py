"""Structure-aware extraction (TECH_SPEC §8.6 step 2, §8.7).

Each extractor turns a source document into a list of `Segment`s carrying a typed,
human-checkable locator (§8.2). Extractors emit fine-grained leaf units; the
chunker (chunk.py) packs/splits them. Dispatch is by format; unsupported formats
raise loudly rather than degrade silently.

Locator discipline (§8.2): PDFs anchor to the TRUE source page (the citation-
integrity guarantee, PROJECT_BRIEF §10); docx/md prose anchor to the heading path;
spreadsheets to sheet + row range or record key; txt/rtf to paragraph ranges.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from retrieval.model import Segment

SUPPORTED_FORMATS = ("pdf", "docx", "xlsx", "md", "txt", "rtf")


def format_of(path: Path) -> str:
    """Map a file to its extractor format, tolerating doubled extensions
    (e.g. 'foo.pdf.pdf') by taking the final real suffix."""
    suffix = path.suffix.lower().lstrip(".")
    if suffix == "markdown":
        return "md"
    return suffix


def extract(path: Path, fmt: str) -> list[Segment]:
    if fmt == "md":
        return extract_md(path)
    if fmt == "pdf":
        return extract_pdf(path)
    if fmt == "docx":
        return extract_docx(path)
    if fmt == "xlsx":
        return extract_xlsx(path)
    if fmt in ("txt", "rtf"):
        return extract_text(path, fmt)
    raise ValueError(
        f"Unsupported format {fmt!r} for {path.name}; expected one of {SUPPORTED_FORMATS}."
    )


# --- helpers -----------------------------------------------------------------

_WS = re.compile(r"[ \t]+")
_MULTINL = re.compile(r"\n{2,}")


def _clean(text: str) -> str:
    return _WS.sub(" ", text).strip()


def _section_path(stack: list[str]) -> str:
    return " > ".join(s for s in stack if s)


def _heading_locator(stack: list[str]) -> str:
    """Locator for heading-anchored prose: the deepest heading, prefixed §."""
    deepest = next((s for s in reversed(stack) if s), None)
    return f"§{deepest}" if deepest else "§(document start)"


# --- Markdown ----------------------------------------------------------------

_MD_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


def extract_md(path: Path) -> list[Segment]:
    text = path.read_text(encoding="utf-8", errors="replace")
    segments: list[Segment] = []
    # heading stack indexed by markdown level (1..6)
    stack: list[str] = []  # positional: stack[i] is the level-(i+1) heading
    buffer: list[str] = []

    def flush() -> None:
        if not buffer:
            return
        para = _clean("\n".join(buffer))
        buffer.clear()
        if para:
            segments.append(
                Segment(
                    text=para,
                    kind="prose",
                    section_path=_section_path(stack),
                    locator=_heading_locator(stack),
                )
            )

    for raw in text.splitlines():
        m = _MD_HEADING.match(raw)
        if m:
            flush()
            level = len(m.group(1))
            title = _clean(m.group(2))
            # trim the stack to the parent level, then set this level
            del stack[level - 1 :]
            while len(stack) < level - 1:
                stack.append("")
            stack.append(title)
            continue
        if raw.strip() == "":
            flush()
        else:
            buffer.append(raw)
    flush()
    return segments


# --- PDF (PyMuPDF) -----------------------------------------------------------


def _pdf_body_size(doc) -> float:
    sizes: Counter = Counter()
    for page in doc:
        d = page.get_text("dict")
        for block in d.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if span.get("text", "").strip():
                        sizes[round(span["size"], 1)] += len(span["text"])
    return sizes.most_common(1)[0][0] if sizes else 10.0


# Numbered-control registries printed inline in PDFs (the ISM prints
# "Control: ISM-2002; Revision: 1; …" ahead of each control statement). Detecting
# these makes each control individually fetchable by key — fetch("ISM-1612")
# returns exactly that control (TECH_SPEC §8.1, §8.6 step 3). The true page stays
# the locator (citation integrity); record_key is the fetch handle.
_CONTROL_MARKER = re.compile(r"Control:\s*(ISM-\d{3,4})\b")


def _split_control_records(segments: list[Segment]) -> list[Segment]:
    out: list[Segment] = []
    for seg in segments:
        if seg.kind != "prose":
            out.append(seg)
            continue
        matches = list(_CONTROL_MARKER.finditer(seg.text))
        if not matches:
            out.append(seg)
            continue
        bounds = [m.start() for m in matches] + [len(seg.text)]
        pre = seg.text[: bounds[0]].strip()
        if pre:
            out.append(
                Segment(
                    text=pre,
                    kind="prose",
                    section_path=seg.section_path,
                    locator=seg.locator,
                    page=seg.page,
                )
            )
        for i, m in enumerate(matches):
            body = seg.text[m.start() : bounds[i + 1]].strip()
            if body:
                out.append(
                    Segment(
                        text=body,
                        kind="record",
                        section_path=seg.section_path,
                        locator=seg.locator,
                        record_key=m.group(1),
                        page=seg.page,
                    )
                )
    return out


def extract_pdf(path: Path) -> list[Segment]:
    import fitz  # PyMuPDF

    segments: list[Segment] = []
    with fitz.open(path) as doc:
        body_size = _pdf_body_size(doc)
        heading: str = ""  # nearest heading above current text, for section_path
        for pageno, page in enumerate(doc, start=1):
            d = page.get_text("dict")
            for block in d.get("blocks", []):
                lines = block.get("lines", [])
                if not lines:
                    continue
                block_text_parts: list[str] = []
                max_size = 0.0
                for line in lines:
                    spans = line.get("spans", [])
                    line_text = "".join(s.get("text", "") for s in spans)
                    if line_text.strip():
                        block_text_parts.append(line_text)
                        for s in spans:
                            max_size = max(max_size, s.get("size", 0.0))
                text = _clean("\n".join(block_text_parts))
                if not text:
                    continue
                is_heading = max_size >= body_size + 1.5 and len(text) <= 120
                if is_heading:
                    heading = text
                    continue
                segments.append(
                    Segment(
                        text=text,
                        kind="prose",
                        section_path=heading,
                        locator=f"p.{pageno}",
                        page=pageno,
                    )
                )
    return _split_control_records(segments)


# --- DOCX (python-docx) ------------------------------------------------------

# Heading styles that define document/provision structure. In legislation
# compilations the section/part/division headings carry the outline level in the
# style name (ActHead 2 = Part, 3 = Division, 5 = Section); SubsectionHead is a
# named sub-heading. The provision BODY styles (paragraph, subsection, Definition,
# …) are NOT headings — they are the text that hangs under a heading. Table-of-
# contents and running-header styles are navigation and are skipped.
_HEADING_STYLE = re.compile(r"^Heading\s*(\d+)", re.IGNORECASE)
_ACTHEAD_STYLE = re.compile(r"^ActHead\s*(\d+)", re.IGNORECASE)
_SKIP_STYLE = re.compile(r"^(toc|header|footer|ENotes)", re.IGNORECASE)
# A legislative SECTION heading begins with an arabic number (optionally a letter
# suffix), e.g. "6  Interpretation", "22A  Cabinet notebooks". Parts/Divisions
# begin with "Part"/"Division" and do not match, so they don't become provisions.
_SECTION_NUMBER = re.compile(r"^(\d+[A-Za-z]*)\b")


def _provision_locator(section_heading: str) -> str | None:
    m = _SECTION_NUMBER.match(section_heading)
    return f"s {m.group(1)}" if m else None


def _docx_table_markdown(table) -> str:
    rows = []
    for row in table.rows:
        cells = [_clean(c.text) for c in row.cells]
        rows.append("| " + " | ".join(cells) + " |")
    if not rows:
        return ""
    header = rows[0]
    sep = "| " + " | ".join(["---"] * (header.count("|") - 1)) + " |"
    return "\n".join([header, sep, *rows[1:]])


def extract_docx(path: Path) -> list[Segment]:
    import docx  # python-docx
    from docx.document import Document as _Doc
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = docx.Document(str(path))
    segments: list[Segment] = []
    stack: list[str] = []  # heading stack by heading level
    provision: str | None = None  # current legislative section locator ("s 6")

    def iter_block_items(parent):
        parent_elm = parent.element.body if isinstance(parent, _Doc) else parent._tc
        for child in parent_elm.iterchildren():
            if isinstance(child, CT_P):
                yield Paragraph(child, parent)
            elif isinstance(child, CT_Tbl):
                yield Table(child, parent)

    def body_locator() -> str:
        # legislation: cite the provision (s N); everything else: the heading path
        return provision if provision else _heading_locator(stack)

    for item in iter_block_items(document):
        if isinstance(item, Table):
            md = _docx_table_markdown(item)
            if md:
                segments.append(
                    Segment(
                        text=md,
                        kind="table",
                        section_path=_section_path(stack),
                        locator=body_locator(),
                    )
                )
            continue
        para = item
        text = _clean(para.text)
        if not text:
            continue
        style = (para.style.name if para.style else "") or ""
        if _SKIP_STYLE.match(style):  # table-of-contents / running headers
            continue

        heading_level = None
        m = _HEADING_STYLE.match(style)
        if m:
            heading_level = int(m.group(1))
        elif a := _ACTHEAD_STYLE.match(style):
            heading_level = int(a.group(1))
        elif style.lower() == "subsectionhead":
            heading_level = 6  # a named sub-heading beneath the section

        if heading_level is not None:
            del stack[heading_level - 1 :]
            while len(stack) < heading_level - 1:
                stack.append("")
            stack.append(text)
            # a legislative section heading updates the provision anchor
            prov = _provision_locator(text)
            if prov is not None:
                provision = prov
            continue

        segments.append(
            Segment(
                text=text,
                kind="prose",
                section_path=_section_path(stack),
                locator=body_locator(),
            )
        )
    return segments


# --- XLSX (openpyxl) ---------------------------------------------------------


def _sheet_rows(ws) -> list[list[str]]:
    rows = []
    for row in ws.iter_rows(values_only=True):
        cells = ["" if v is None else str(v).strip() for v in row]
        if any(cells):
            rows.append(cells)
    return rows


def extract_xlsx(path: Path) -> list[Segment]:
    """Normalize + serialize each sheet by shape (TECH_SPEC §8.7).

    First-pass classification: a sheet with a plausible key column (first column
    mostly non-empty, short, unique-ish) is treated as a REGISTRY and emitted as
    per-row record segments carrying a record_key; otherwise it is emitted as
    prose row segments. Header depth of one row is assumed and repeated into each
    record for context (grouped two-row headers are flattened best-effort).
    """
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    segments: list[Segment] = []
    for ws in wb.worksheets:
        rows = _sheet_rows(ws)
        if not rows:
            continue
        header = rows[0]
        body = rows[1:]
        sheet = ws.title
        # decide registry vs prose: is the first column a stable-looking key?
        first_col = [r[0] for r in body if r and r[0]]
        looks_keyed = (
            len(first_col) >= 3
            and len(first_col) == len(set(first_col))
            and all(len(v) <= 40 for v in first_col)
        )
        for i, row in enumerate(body, start=2):  # row 1 is the header
            pairs = [
                f"{_clean(h)}: {_clean(v)}" for h, v in zip(header, row) if _clean(v) and _clean(h)
            ]
            if not pairs:
                continue
            text = "; ".join(pairs)
            if looks_keyed and row and row[0].strip():
                key = row[0].strip()
                segments.append(
                    Segment(
                        text=text,
                        kind="record",
                        section_path=sheet,
                        locator=key,
                        record_key=key,
                    )
                )
            else:
                segments.append(
                    Segment(
                        text=text,
                        kind="table",
                        section_path=sheet,
                        locator=f"{sheet}!r{i}",
                    )
                )
    wb.close()
    return segments


# --- TXT / RTF ---------------------------------------------------------------

_RTF_CONTROL = re.compile(r"\\[a-z]+-?\d*\s?|[{}]")


def extract_text(path: Path, fmt: str) -> list[Segment]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if fmt == "rtf":
        raw = _RTF_CONTROL.sub("", raw)
    paragraphs = [p for p in _MULTINL.split(raw) if _clean(p)]
    segments: list[Segment] = []
    for i, para in enumerate(paragraphs, start=1):
        segments.append(
            Segment(
                text=_clean(para.replace("\n", " ")),
                kind="prose",
                section_path="",
                locator=f"¶{i}",
            )
        )
    return segments
