"""Source document -> line stream.

Produces the lines the parse rules work on, each with the layout attributes they
need (font size, bold, indent, page). Two engines:

- transcript: a scanned PDF is read from its committed transcript in transcripts/,
  because its OCR text layer carries no font information and has errors.
- pdf-layout: a born-digital PDF is read with pdfplumber. Lines wrapped by the page
  width are joined back into one logical line, so a paragraph or a heading is one
  Line however it was laid out.

- docx: a Word document, with its automatic numbering put back into the text
  (see docx_reader.py).
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", re.S)
PAGE_MARK = re.compile(r"^<!--\s*page\s+(\d+)\s*-->$")
WHOLE_LINE_BOLD = re.compile(r"^\*\*(.+)\*\*$")


@dataclass
class Line:
    text: str
    bold: bool = False
    page: int | None = None
    size: int | None = None  # font size in points, for size-based heading rules
    x0: float | None = None  # left edge, for indented text
    style: str | None = None  # paragraph style, for Word documents


class StaleTranscript(Exception):
    """The source file has changed since its transcript was made."""


def split_frontmatter(text: str) -> tuple[dict | None, str]:
    """Split a markdown file into (frontmatter dict, body). No frontmatter -> (None, text)."""
    m = FRONTMATTER.match(text)
    if not m:
        return None, text
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- transcripts


def parse_transcript_lines(body: str) -> list[Line]:
    lines: list[Line] = []
    page = None
    for raw in body.splitlines():
        text = raw.strip()
        if not text:
            continue
        m = PAGE_MARK.match(text)
        if m:
            page = int(m.group(1))
            continue
        if text.startswith("<!--"):
            continue
        b = WHOLE_LINE_BOLD.match(text)
        if b and "**" not in b.group(1):
            lines.append(Line(b.group(1).strip(), True, page))
        else:
            lines.append(Line(text, False, page))
    return lines


def read_transcript(path: Path) -> tuple[dict, list[Line]]:
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    return meta or {}, parse_transcript_lines(body)


# ---------------------------------------------------------------- born-digital PDFs


def _is_bold(chars) -> bool:
    letters = [c for c in chars if not c["text"].isspace()]
    if not letters:
        return False
    bold = sum("bold" in c["fontname"].lower() for c in letters)
    return bold / len(letters) > 0.8


def markdown_table(rows: list[list[str]]) -> str:
    """A table's rows as a markdown table, header row first."""
    cleaned = [[" ".join((c or "").split()).replace("|", "\\|") for c in row] for row in rows if any(row)]
    if not cleaned:
        return ""
    width = max(len(r) for r in cleaned)
    cleaned = [r + [""] * (width - len(r)) for r in cleaned]
    head, *body = cleaned
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * width]
    lines += ["| " + " | ".join(r) + " |" for r in body]
    return "\n".join(lines)


def pdf_lines(source: Path, cfg: dict) -> list[Line]:
    """Read a born-digital PDF, joining wrapped lines back into logical lines."""
    import pdfplumber

    top_margin = cfg.get("top-margin", 0)
    bottom_margin = cfg.get("bottom-margin", 10_000)
    join_ratio = cfg.get("join-ratio", 1.6)
    breaks = tuple(cfg.get("break-prefixes", []))
    drop = [re.compile(p) for p in cfg.get("drop", [])]

    as_markdown = cfg.get("tables") == "markdown"
    skip = {}
    for item in cfg.get("skip-pages", []):
        if isinstance(item, int):
            skip[item] = None
        else:
            skip[item["page"]] = item.get("expect")
    lines: list[Line] = []
    with pdfplumber.open(source) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            if number in skip:
                expected = skip[number]
                if expected and expected not in (page.extract_text() or ""):
                    raise ValueError(
                        f"{source.name} page {number} was to be skipped but does not contain "
                        f"{expected!r}; the document may have changed"
                    )
                continue
            previous_top = None
            tables = []
            if as_markdown:
                for table in page.find_tables():
                    rows = [r for r in table.extract() if any(r)]
                    # A single-cell box is a highlighted note, not a table: leave it as text.
                    if len(rows) < 2 or max(len(r) for r in rows) < 2:
                        continue
                    text = markdown_table(rows)
                    if text:
                        tables.append([table.bbox, text, False])
            for raw in page.extract_text_lines(extra_attrs=["fontname", "size"]):
                if not top_margin <= raw["top"] <= bottom_margin:
                    continue
                inside = False
                for box in tables:
                    (x0, top, x1, bottom), text, done = box
                    if top <= raw["top"] <= bottom:
                        inside = True
                        if not done:
                            box[2] = True
                            lines.append(Line(text, False, number, None, round(x0, 1)))
                            previous_top = None
                if inside:
                    continue
                text = raw["text"].strip()
                if not text or any(d.search(text) for d in drop):
                    previous_top = None
                    continue
                size = round(max(c["size"] for c in raw["chars"]))
                gap = None if previous_top is None else raw["top"] - previous_top
                previous_top = raw["top"]
                wrapped = (
                    lines
                    and lines[-1].page == number
                    and lines[-1].size == size
                    and gap is not None
                    and gap <= join_ratio * size
                    and not text.startswith(breaks)
                )
                if wrapped:
                    lines[-1].text += " " + text
                else:
                    lines.append(Line(text, _is_bold(raw["chars"]), number, size, round(raw["x0"], 1)))
    return lines


def pdf_tables(
    source: Path,
    *,
    from_heading: str,
    to_heading: str | None = None,
    heading_size: int | None = None,
) -> list[list[list[str]]]:
    """Rows of every table on the pages from one heading up to and including another."""
    import pdfplumber

    start = end = None
    from_re = re.compile(from_heading)
    to_re = re.compile(to_heading) if to_heading else None
    rows: list[list[list[str]]] = []
    with pdfplumber.open(source) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            headings = []
            for raw in page.extract_text_lines(extra_attrs=["size"]):
                size = round(max(c["size"] for c in raw["chars"]))
                if heading_size is None or size == heading_size:
                    headings.append(raw["text"].strip())
            if start is None and any(from_re.match(t) for t in headings):
                start = number
            if start is not None:
                rows += page.extract_tables()
                if to_re is not None and number > start and any(to_re.match(t) for t in headings):
                    end = number
                elif to_re is not None and number == start:
                    pass
            if end is not None:
                break
    if start is None:
        raise ValueError(f"heading {from_heading!r} not found in {source.name}")
    return rows


# ---------------------------------------------------------------- entry point


def extract(source: Path, transcript: Path | None = None, cfg: dict | None = None) -> list[Line]:
    cfg = cfg or {}
    if transcript is not None and transcript.exists():
        meta, lines = read_transcript(transcript)
        recorded = meta.get("source-sha256")
        if source.exists() and recorded != sha256(source):
            raise StaleTranscript(
                f"{transcript.name} does not match {source.name} (source-sha256 differs); "
                "re-check the transcript against the source, then update source-sha256"
            )
        return lines
    if not source.exists():
        raise FileNotFoundError(f"source not found: {source.name}")
    if cfg.get("engine") == "pdf-layout" and source.suffix.lower() == ".pdf":
        return pdf_lines(source, cfg)
    if cfg.get("engine") == "docx" and source.suffix.lower() == ".docx":
        from .docx_reader import docx_lines

        return docx_lines(source, cfg)
    raise NotImplementedError(
        f"no transcript for {source.name}, and direct {source.suffix} extraction is not written yet"
    )
