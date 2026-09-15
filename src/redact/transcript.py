"""Redact a scanned document: its transcript, and a stand-in PDF for the source.

The build reads a scanned document from its transcript, and checks the transcript's
source-sha256 against the source file. The public repo gets the transcript redacted line
by line (page marks and whole-line bold headings kept) and, as the source, a plain PDF
of the redacted text, whose fingerprint goes into the transcript.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from parse.extract import PAGE_MARK, WHOLE_LINE_BOLD, sha256, split_frontmatter
from redact.text import Redactor


def _stand_in(target: Path, name: str, lines: list[str]) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import simpleSplit
    from reportlab.pdfgen.canvas import Canvas

    target.parent.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(str(target), pagesize=A4, invariant=1)
    canvas.setTitle(f"Redacted stand-in: {name}")
    width, height = A4
    y = height - 60

    def write(text: str, font: str = "Helvetica", size: float = 10) -> None:
        nonlocal y
        for part in simpleSplit(text, font, size, width - 120) or [""]:
            if y < 60:
                canvas.showPage()
                y = height - 60
            canvas.setFont(font, size)
            canvas.drawString(60, y, part.encode("cp1252", "replace").decode("cp1252"))
            y -= size * 1.4

    write(f"Redacted stand-in for {name}", "Helvetica-Bold", 14)
    write("The real document is not published. This file holds the redacted transcript's "
          "text so that the build can check the transcript against it.")
    y -= 10
    for line in lines:
        if PAGE_MARK.match(line):
            write(line, "Helvetica-Oblique", 8)
        elif m := WHOLE_LINE_BOLD.match(line):
            write(m.group(1), "Helvetica-Bold")
        else:
            write(line)
    canvas.save()


def redact_transcript(transcript: Path, target_transcript: Path, target_source: Path, redactor: Redactor) -> None:
    fm, body = split_frontmatter(transcript.read_text(encoding="utf-8").replace("\r\n", "\n"))
    lines = []
    for line in body.split("\n"):
        if not line.strip() or PAGE_MARK.match(line.strip()) or WHOLE_LINE_BOLD.match(line.strip()):
            lines.append(line)
        else:
            lines.append(redactor.line(line))
    _stand_in(target_source, Path(fm["source"]).name, lines)

    public = {
        "source": fm["source"],
        "source-sha256": sha256(target_source),
        "transcribed-by": fm.get("transcribed-by"),
        "transcribed-at": fm.get("transcribed-at"),
        "checked-by": fm.get("checked-by"),
        "covers": fm.get("covers"),
        "redacted": (
            "Body text replaced with lorem ipsum; headings, numbering, defined terms and "
            "cross-references kept. The source file is a stand-in PDF of this text, not the "
            "real document."
        ),
    }
    head = yaml.safe_dump({k: v for k, v in public.items() if v is not None}, sort_keys=False, allow_unicode=True, width=88)
    target_transcript.parent.mkdir(parents=True, exist_ok=True)
    target_transcript.write_bytes(f"---\n{head}---\n{chr(10).join(lines)}".encode("utf-8"))
