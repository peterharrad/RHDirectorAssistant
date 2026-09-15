"""Heading-level state machine.

Tracks the current value at each heading level while walking a document. When a
heading is seen at level n, level n is replaced and every level below it is cleared.
Which lines count as headings at which level is supplied by the document's parse
rules — by font size, bold, capitalisation, length and pattern — not decided here.

A heading also keeps the parts it was built from (its number, its title), so a unit
underneath it can use them in its own title: "Clause 3.1 – Services to be provided".
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

from .extract import Line


class HeadingState:
    """Current value at each heading level, highest level first."""

    def __init__(self, levels: list[str], next_unit_only: list[str] = ()):
        self.levels = list(levels)
        self.values: dict[str, str | None] = dict.fromkeys(self.levels)
        self.fields: dict[str, dict[str, str]] = {level: {} for level in self.levels}
        self.next_unit_only = set(next_unit_only)

    def set(self, level: str, value: str, fields: dict[str, str] | None = None) -> None:
        self.values[level] = value
        self.fields[level] = dict(fields or {})
        for lower in self.levels[self.levels.index(level) + 1:]:
            self.values[lower] = None
            self.fields[lower] = {}

    def take(self) -> tuple[dict[str, str | None], dict[str, str]]:
        """Snapshot for a unit starting now: (value per level, flattened heading fields).

        Clears levels that apply to one unit only. Heading fields are flattened to
        "<level>_<name>", e.g. clause_title.
        """
        values = dict(self.values)
        flat = {}
        for level, fields in self.fields.items():
            for name, value in fields.items():
                flat[f"{level}_{name}"] = value
                if isinstance(value, str):
                    flat[f"{level}_{name}_lower"] = value.lower()
        for level in self.next_unit_only:
            self.values[level] = None
            self.fields[level] = {}
        return values, flat


@dataclass
class Heading:
    level: str
    value: str
    fields: dict[str, str] = field(default_factory=dict)
    consumed: int = 0  # following lines used as part of this heading


@dataclass
class HeadingRule:
    level: str
    patterns: list[tuple[re.Pattern, str | None]] = field(default_factory=list)
    bold: bool | None = None
    size: int | None = None
    style: str | None = None  # paragraph style, for Word documents
    case: str | None = None  # "upper" or "mixed"
    max_words: int | None = None  # the heading has fewer words than this
    title_from_next_line: bool | dict = False  # True, or the style the next line must have
    scope: str = "until-replaced"  # or "next-unit"

    @classmethod
    def from_config(cls, cfg: dict) -> "HeadingRule":
        raw = cfg.get("patterns") or (
            [{"match": cfg["match"], "display": cfg.get("display")}] if cfg.get("match") else []
        )
        return cls(
            level=cfg["level"],
            patterns=[(re.compile(p["match"]), p.get("display")) for p in raw],
            bold=cfg.get("bold"),
            size=cfg.get("size"),
            style=cfg.get("style"),
            case=cfg.get("case"),
            max_words=cfg.get("max-words"),
            title_from_next_line=cfg.get("title-from-next-line", False),
            scope=cfg.get("scope", "until-replaced"),
        )

    def fits_style(self, line: Line) -> bool:
        if self.bold is not None and line.bold != self.bold:
            return False
        if self.size is not None and line.size != self.size:
            return False
        if self.style is not None and line.style != self.style:
            return False
        if self.max_words and len(line.text.split()) >= self.max_words:
            return False
        if self.case and (self.case == "upper") != is_upper(line.text):
            return False
        return True


def matches_style(line: Line, spec: bool | dict) -> bool:
    """Does this line have the style a rule asks for? True means bold."""
    if spec is True:
        return line.bold
    return all(getattr(line, key.replace("-", "_"), None) == value for key, value in spec.items())


def is_upper(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters)


def sentence_case(text: str, acronyms: list[str] = ()) -> str:
    out = text.lower()
    out = out[:1].upper() + out[1:]
    for word in acronyms:
        out = re.sub(rf"\b{re.escape(word)}\b", word, out, flags=re.IGNORECASE)
    return out


def classify(
    line: Line,
    next_line: Line | None,
    rules: list[HeadingRule],
    acronyms: list[str] = (),
    display_case: str | None = None,
) -> Heading | None:
    """Return the heading this line starts, or None if it isn't a heading."""

    def show(text: str) -> str:
        return sentence_case(text, acronyms) if display_case == "sentence" and is_upper(text) else text

    for rule in rules:
        if not rule.fits_style(line):
            continue
        if not rule.patterns:
            return Heading(rule.level, show(line.text))
        for pattern, display in rule.patterns:
            m = pattern.match(line.text)
            if not m:
                continue
            fields = {k: (v or "").strip() for k, v in m.groupdict().items()}
            consumed = 0
            if (
                rule.title_from_next_line
                and not fields.get("title")
                and next_line is not None
                and matches_style(next_line, rule.title_from_next_line)
            ):
                fields["title"] = next_line.text
                consumed = 1
            if fields.get("title"):
                fields["title"] = show(fields["title"])
            for name, value in list(fields.items()):
                fields[name + "_lower"] = value.lower()  # for filenames
                fields[name + "_title"] = value.title()  # "FIRST" -> "First"
            # A pattern need not capture every part the display template mentions.
            shown = display.format_map(defaultdict(str, fields)) if display else None
            value = shown.strip().rstrip(" –-").strip() if shown else show(line.text)
            return Heading(rule.level, value, fields, consumed)
    return None
