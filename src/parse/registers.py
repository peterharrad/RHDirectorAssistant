"""HM Land Registry title register sectioning.

Reads a title register printed from the "Search for land and property information"
service and splits it into its registers (A: Property, B: Proprietorship, C: Charges)
and their numbered entries.

The page is laid out in columns: entry number and entry date on the left, the entry's
text on the right. An entry is therefore found by where its number sits, not by a line
starting with a number, because entries quote deeds that have numbered clauses of their
own ("3.1 Not for 21 years..."). Within an entry, a wider vertical gap starts a new
paragraph, as do "NOTE:" lines and "Key : value" lines such as "Term : 999 years".

Entries in the freehold's schedule of notices of leases have no entry date and are a
list of "Key : value" fields; they are kept apart as schedule entries.
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path

REGISTER_HEADING = re.compile(r"^(?P<letter>[A-Z]):\s+(?P<name>.+ Register)$")
ENTRY_START = re.compile(r"^(?P<number>\d+)(?:\s+(?P<date>\d{4}-\d{2}-\d{2}))?$")
FIELD_LINE = re.compile(r"^(?P<key>[A-Z][A-Za-z' ]{1,30}?)\s:\s*(?P<value>.*)$")
NOTE_LINE = re.compile(r"^NOTE:")
ACCESSED = re.compile(r"Accessed on (?P<date>\d{1,2} \w+ \d{4}) at (?P<time>\d{2}:\d{2}:\d{2})")
TITLE_FOR = re.compile(r"\((?P<tenure>Freehold|Leasehold)\)\s*$")
TITLE_NUMBER = re.compile(r"^[A-Z]{2,3}\d+$")


@dataclass
class Entry:
    number: int
    date: str | None
    paragraphs: list[str] = field(default_factory=list)
    pages: set[int] = field(default_factory=set)

    @property
    def fields(self) -> dict[str, str] | None:
        """The entry's "Key : value" fields, if that is all it is (a schedule of leases row)."""
        found: dict[str, str] = {}
        notes: list[str] = []
        for paragraph in self.paragraphs:
            if NOTE_LINE.match(paragraph) and found:
                notes.append(paragraph)  # a note after the fields belongs to the row
                continue
            m = FIELD_LINE.match(paragraph)
            if not m or notes:
                return None
            found[m.group("key").strip()] = m.group("value").strip()
        if notes:
            found["Note"] = " ".join(notes)
        return found or None


@dataclass
class Register:
    letter: str
    name: str
    intro: list[str] = field(default_factory=list)
    class_of_title: str | None = None
    entries: list[Entry] = field(default_factory=list)

    @property
    def heading(self) -> str:
        return f"{self.letter}: {self.name}"

    @property
    def pages(self) -> list[int]:
        return sorted({p for e in self.entries for p in e.pages})


@dataclass
class TitleRegister:
    title_number: str | None = None
    tenure: str | None = None
    accessed: str | None = None  # ISO 8601, when the register was viewed
    registers: list[Register] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _rows(page, tolerance: float = 3.0) -> list[list[dict]]:
    """Words grouped into visual rows, top to bottom, each row left to right."""
    words = page.extract_words(extra_attrs=["fontname", "size"], keep_blank_chars=False)
    rows: list[list[dict]] = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if rows and abs(rows[-1][0]["top"] - word["top"]) <= tolerance:
            rows[-1].append(word)
        else:
            rows.append([word])
    return [sorted(r, key=lambda w: w["x0"]) for r in rows]


def _text(words: list[dict]) -> str:
    return " ".join(w["text"] for w in words).replace("¬", "").strip()


def parse_register(source: Path, cfg: dict) -> TitleRegister:
    import pdfplumber

    split_x = cfg.get("description-column", 200)  # words left of this are number / date
    paragraph_gap = cfg.get("paragraph-gap", 27)  # a wider gap between rows starts a paragraph
    heading_size = cfg.get("heading-size", 16)

    result = TitleRegister()
    current: Register | None = None
    entry: Entry | None = None
    state = "header"
    last_top = last_page = None

    with pdfplumber.open(source) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            for row in _rows(page):
                text = _text(row)
                if not text:
                    continue
                size = round(max(w["size"] for w in row))
                heading = REGISTER_HEADING.match(text)

                if state == "header":
                    if m := ACCESSED.search(text):
                        when = dt.datetime.strptime(f"{m.group('date')} {m.group('time')}", "%d %B %Y %H:%M:%S")
                        result.accessed = when.isoformat()
                    elif m := TITLE_FOR.search(text):
                        result.tenure = m.group("tenure")
                    elif TITLE_NUMBER.match(text) and result.title_number is None:
                        result.title_number = text

                if heading and size == heading_size:
                    current = Register(heading.group("letter"), heading.group("name"))
                    result.registers.append(current)
                    entry, state = None, "intro"
                    continue
                if state == "header":
                    continue
                if state == "intro":
                    if text.startswith("Entry number"):
                        state = "entries"
                    elif text.startswith("Class of Title:"):
                        current.class_of_title = text.split(":", 1)[1].strip()
                    else:
                        current.intro.append(text)
                    continue

                # state == "entries": split the row into its columns
                left = _text([w for w in row if w["x0"] < split_x])
                right = _text([w for w in row if w["x0"] >= split_x])
                if left:
                    m = ENTRY_START.match(left)
                    if not m:
                        result.warnings.append(f"page {page_number}: unexpected text in the entry column: {left!r}")
                    else:
                        entry = Entry(int(m.group("number")), m.group("date"))
                        current.entries.append(entry)
                        last_top = last_page = None
                if not right:
                    continue
                if entry is None:
                    result.warnings.append(f"page {page_number}: text before the first entry: {right[:50]!r}")
                    continue
                entry.pages.add(page_number)
                same_page = last_page == page_number
                new_paragraph = (
                    not entry.paragraphs
                    or (same_page and row[0]["top"] - last_top > paragraph_gap)
                    or NOTE_LINE.match(right)
                    or FIELD_LINE.match(right)
                )
                if new_paragraph:
                    entry.paragraphs.append(right)
                elif re.search(r"[A-Za-z]-$", entry.paragraphs[-1]):
                    entry.paragraphs[-1] += right  # a word hyphenated across lines: "under-" "lease(s)"
                else:
                    entry.paragraphs[-1] += " " + right
                last_top, last_page = row[0]["top"], page_number

    for register in result.registers:
        numbers = [e.number for e in register.entries]
        for a, b in zip(numbers, numbers[1:]):
            if b != a + 1:
                result.warnings.append(f"{register.heading}: entry numbers jump from {a} to {b}")
    if not result.registers:
        result.warnings.append(f"no registers found in {source.name}")
    return result
