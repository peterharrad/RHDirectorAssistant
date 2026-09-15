"""Redact a born-digital PDF by drawing it again.

Each page is redrawn at its own size with the same ruled lines and boxes (so tables are
still found). Each line of text starts where it did, at the same height, size, weight and
colour, with its words replaced (see text.py) and set in a standard font: Helvetica, or
Times for a serif original. The words flow at their natural spacing. Where a line is
broken into columns or table cells, each part starts at its own position. A part is only
squeezed, evenly, if it would otherwise run into the next part or off the page. Images (logos, signatures) are left out, and so is the original's metadata.
"""
from __future__ import annotations

from pathlib import Path

from redact.text import Redactor

DESCENT = 0.207  # Helvetica's descent as a fraction of the font size, as pdfminer reads it
GAP = 0.12  # a gap wider than this, times the font size, is a space (space glyphs aren't listed)
COLUMN = 0.8  # a gap wider than this, times the font size, starts a new column or table cell
MARGIN = 18  # points kept clear at the right edge of the page


def _colour(canvas, value, stroke: bool, space=None) -> None:
    """Set a colour as pdfplumber reads it. A spot ink (Separation) is a tint: 1 is full ink."""
    set_gray, set_rgb, set_cmyk = (
        (canvas.setStrokeGray, canvas.setStrokeColorRGB, canvas.setStrokeColorCMYK)
        if stroke
        else (canvas.setFillGray, canvas.setFillColorRGB, canvas.setFillColorCMYK)
    )
    try:
        values = [float(v) for v in (value if isinstance(value, (list, tuple)) else [value])]
    except (TypeError, ValueError):
        values = []
    if len(values) == 1 and any(s in str(space) for s in ("Separation", "DeviceN")):
        set_gray(1 - values[0])
    elif len(values) == 1:
        set_gray(values[0])
    elif len(values) == 3:
        set_rgb(*values)
    elif len(values) == 4:
        set_cmyk(*values)
    else:
        set_gray(0)


def _graphics(canvas, page, height: float) -> None:
    for rect in page.rects:
        canvas.setLineWidth(rect.get("linewidth") or 0.5)
        stroke, fill = bool(rect.get("stroke")), bool(rect.get("fill"))
        _colour(canvas, rect.get("stroking_color"), True, rect.get("scs"))
        _colour(canvas, rect.get("non_stroking_color"), False, rect.get("ncs"))
        if not (stroke or fill):
            stroke = True  # an invisible box still marks table edges: keep it, in white
            canvas.setStrokeGray(1)
        canvas.rect(rect["x0"], height - rect["bottom"], rect["width"], rect["height"], stroke=int(stroke), fill=int(fill))
    for shape in [*page.lines, *page.curves]:
        points = shape.get("pts") or []
        if len(points) < 2:
            continue
        canvas.setLineWidth(shape.get("linewidth") or 0.5)
        _colour(canvas, shape.get("stroking_color"), True, shape.get("scs"))
        _colour(canvas, shape.get("non_stroking_color"), False, shape.get("ncs"))
        path = canvas.beginPath()
        path.moveTo(points[0][0], height - points[0][1])
        for x, top in points[1:]:
            path.lineTo(x, height - top)
        fill = shape["object_type"] == "curve" and bool(shape.get("fill"))
        canvas.drawPath(path, stroke=1, fill=int(fill))


def _pieces(chars: list[dict]) -> list[tuple[list[dict], bool]]:
    """Characters grouped into words, also split where the font or size changes.

    Each piece comes with whether a space separates it from the piece before.
    """
    pieces: list[tuple[list[dict], bool]] = []
    spaced = False
    for char in sorted(chars, key=lambda c: c["x0"]):
        if char["text"].isspace():
            spaced = True
            continue
        previous = pieces[-1][0][-1] if pieces else None
        if previous and (previous["text"], round(previous["x0"], 1)) == (char["text"], round(char["x0"], 1)):
            continue  # drawn twice in the same place (some ligatures are): text extraction reads it once
        gap = previous is not None and char["x0"] - previous["x1"] > max(1.0, GAP * char["size"])
        if (
            previous is None
            or spaced
            or gap
            or char["fontname"] != previous["fontname"]
            or round(char["size"], 1) != round(previous["size"], 1)
        ):
            pieces.append(([char], bool(pieces) and (spaced or gap)))
        else:
            pieces[-1][0].append(char)
        spaced = False
    return pieces


def _font(chars: list[dict]) -> str:
    names = [c["fontname"].lower() for c in chars]
    half = len(names) / 2
    bold = sum("bold" in n or "black" in n or "heavy" in n for n in names) > half
    italic = sum("italic" in n or "oblique" in n for n in names) > half
    if sum(any(s in n for s in ("times", "serif", "georgia", "cambria", "garamond")) and "sans" not in n for n in names) > half:
        return {(False, False): "Times-Roman", (True, False): "Times-Bold", (False, True): "Times-Italic", (True, True): "Times-BoldItalic"}[bold, italic]
    return {(False, False): "Helvetica", (True, False): "Helvetica-Bold", (False, True): "Helvetica-Oblique", (True, True): "Helvetica-BoldOblique"}[bold, italic]


def _segments(pieces: list[tuple[list[dict], bool]]) -> list[list[int]]:
    """Piece indexes grouped into the parts of a line: a wide gap starts a new column or cell."""
    segments: list[list[int]] = []
    for index, (piece, _) in enumerate(pieces):
        if segments:
            previous = pieces[segments[-1][-1]][0][-1]
            if piece[0]["x0"] - previous["x1"] <= COLUMN * piece[0]["size"]:
                segments[-1].append(index)
                continue
        segments.append([index])
    return segments


def _draw(canvas, pieces: list[tuple[list[dict], bool]], texts: list[str], height: float, limit: float) -> None:
    """Draw one part of a line from where it started, its words at natural spacing."""
    from reportlab.pdfbase.pdfmetrics import stringWidth

    first_chars = pieces[0][0]
    first = first_chars[0]
    size = first["size"]
    runs = []
    for i, ((chars, spaced), text) in enumerate(zip(pieces, texts)):
        text = text.encode("cp1252", "replace").decode("cp1252")
        runs.append((chars, (" " if spaced and i else "") + text, _font(chars)))
    natural = sum(stringWidth(text, font, chars[0]["size"]) for chars, text, font in runs)
    room = limit - first["x0"]
    obj = canvas.beginText()
    obj.setTextOrigin(first["x0"], height - first["top"] - size + DESCENT * size)
    if natural > room > 0:
        obj.setHorizScale(100.0 * room / natural)
    for chars, text, font in runs:
        _colour(obj, chars[0].get("non_stroking_color"), False, chars[0].get("ncs"))
        obj.setFont(font, chars[0]["size"])
        obj.textOut(text)
    canvas.drawText(obj)


def redact_pdf(source: Path, target: Path, redactor: Redactor, keep_sizes: list[int] = ()) -> int:
    """Write a redacted copy of source to target. Returns the number of pages."""
    import pdfplumber
    from reportlab.pdfgen.canvas import Canvas

    target.parent.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(str(target), invariant=1)
    canvas.setAuthor("")
    canvas.setTitle(f"Redacted: {source.stem}")
    with pdfplumber.open(source) as pdf:
        for page in pdf.pages:
            width, height = page.width, page.height
            canvas.setPageSize((width, height))
            _graphics(canvas, page, height)
            for line in page.extract_text_lines(return_chars=True):
                pieces = _pieces(line["chars"])
                if not pieces:
                    continue
                keep_line = round(max(c["size"] for c in line["chars"])) in keep_sizes
                # The line as the parser reads it: pieces joined by a space where there is a gap.
                text, offsets = "", []
                for piece, spaced in pieces:
                    if spaced:
                        text += " "
                    start = len(text)
                    text += "".join(c["text"] for c in piece)
                    offsets.append((start, len(text)))
                tokens = [] if keep_line else redactor.spans(text)
                mask = redactor.kept(text)
                texts = []
                for start, end in offsets:
                    original = new = text[start:end]
                    for s, e, replacement in tokens:
                        if s <= start and end <= e:
                            if (s, e) == (start, end):
                                new = replacement
                            else:  # part of a word, where the font changes mid-word
                                new = redactor.partial(original, mask[start:end])
                            break
                    texts.append(new)
                segments = _segments(pieces)
                for number, segment in enumerate(segments):
                    if number + 1 < len(segments):
                        following = pieces[segments[number + 1][0]][0][0]
                        limit = following["x0"] - 0.3 * following["size"]
                    else:
                        limit = width - MARGIN
                    _draw(canvas, [pieces[i] for i in segment], [texts[i] for i in segment], height, limit)
            canvas.showPage()
        pages = len(pdf.pages)
    canvas.save()
    return pages
