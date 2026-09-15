"""Clause and sub-clause splitting.

Splits a line stream into numbered units (articles, sections, sub-clauses, appendix
entries) using the start patterns in the document's parse rules. A unit runs until
the next unit start or the next heading; headings are never part of its text.

Each unit records the heading values in force when it started, the parts of those
headings (clause_title and so on), and a key built from its own numbers: ("17",),
("1", "2"), ("appendix", "3"). Keys are lower-case, and are what cross-reference
links resolve against.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

from .extract import Line
from .headings import HeadingRule, HeadingState, classify


@dataclass
class UnitPattern:
    """One way a unit can start, with the names its concept file gets."""

    match: re.Pattern | None  # None for a heading fallback, which has no start line
    filename: str
    title: str
    title_without_heading: str | None = None
    number: str | None = None  # template for the unit's number, e.g. "{chapter}.{section}"
    key: str | None = None  # template for the unit's key, e.g. "appendix.{clause_number}"
    title_if_split: str | None = None  # title to use when units of its own follow
    group_heading: str | None = None  # sub-heading when merged into a group concept
    number_field: str | None = None  # frontmatter field for this pattern's number
    continues_with: list[str] | None = None  # paragraph styles that continue the unit

    @classmethod
    def from_config(cls, cfg: dict) -> "UnitPattern":
        return cls(
            match=re.compile(cfg["match"]) if cfg.get("match") else None,
            filename=cfg["filename"],
            title=cfg["title"],
            title_without_heading=cfg.get("title-without-heading"),
            number=cfg.get("number"),
            key=cfg.get("key"),
            title_if_split=cfg.get("title-if-split"),
            group_heading=cfg.get("group-heading"),
            number_field=cfg.get("number-field"),
            continues_with=cfg.get("continues-with-style"),
        )


@dataclass
class Unit:
    key: tuple[str, ...]
    fields: dict[str, object]  # its own numbers, plus the parts of the headings above it
    pattern: UnitPattern
    headings: dict[str, str | None]
    index: int  # position in the document, for ordering
    lines: list[Line] = field(default_factory=list)
    positions: list[int] = field(default_factory=list)  # where each line sits in the document

    @property
    def pages(self) -> list[int]:
        return sorted({l.page for l in self.lines if l.page is not None})

    @property
    def text_lines(self) -> list[str]:
        return [l.text for l in self.lines]

    @property
    def number(self) -> str:
        if self.pattern.number is not None:
            return self.pattern.number.format_map(defaultdict(str, self.fields))
        return ".".join(self.key)


@dataclass
class ParsedDocument:
    front_matter: list[Line]
    units: list[Unit]
    warnings: list[str]


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def make_key(template: str | None, fields: dict, default: str) -> tuple[str, ...]:
    text = template.format_map(defaultdict(str, fields)) if template else default
    return tuple(part.lower() for part in text.split("."))


def _fields(m: re.Match) -> dict[str, object]:
    out: dict[str, object] = {}
    for name, value in m.groupdict().items():
        value = (value or "").strip()
        out[name] = int(value) if value.isdigit() else value
        if isinstance(out[name], str):
            out[name + "_lower"] = out[name].lower()  # for filenames, e.g. appendix-b-03
    return out


def parse_units(lines: list[Line], rules: dict) -> ParsedDocument:
    heading_rules = [HeadingRule.from_config(c) for c in rules.get("headings", [])]
    state = HeadingState(
        [r.level for r in heading_rules],
        [r.level for r in heading_rules if r.scope == "next-unit"],
    )
    units_cfg = rules["units"]
    # a pattern can be limited to text under a given heading level, e.g. schedule paragraphs
    patterns = [
        (UnitPattern.from_config(c), c.get("requires-heading"), c.get("unless-heading"))
        for c in units_cfg["patterns"]
    ]
    key_fields = units_cfg["key"]
    unit_size = units_cfg.get("size")
    # Text under a heading that has no units of its own: an appendix, or a clause's
    # opening words. Entries are tried in order, deepest heading level first.
    fallbacks = [
        (v["level"], re.compile(v["match"]) if v.get("match") else None, UnitPattern.from_config(v))
        for v in units_cfg.get("heading-fallback", [])
    ]
    acronyms = rules.get("acronyms", [])
    display_case = rules.get("display-case")
    front_ends_at = (rules.get("front-matter") or {}).get("ends-at")
    back_starts_at = (rules.get("back-matter") or {}).get("starts-at")
    back_matter = re.compile(back_starts_at) if back_starts_at else None

    doc = ParsedDocument([], [], [])
    in_front = front_ends_at is not None
    current: Unit | None = None
    seen: set[tuple[str, ...]] = set()

    def start_unit(pattern: UnitPattern, fields: dict, key: tuple[str, ...],
                   values: dict, first: Line | None) -> None:
        nonlocal current
        if key in seen:
            doc.warnings.append(f"two units share the key {'.'.join(key)}")
        seen.add(key)
        current = Unit(key, fields, pattern, values, len(doc.units), [first] if first else [], [i] if first else [])
        doc.units.append(current)

    i = 0
    while i < len(lines):
        line = lines[i]
        if back_matter is not None and back_matter.match(line.text):
            break  # execution formalities and anything after them
        next_line = lines[i + 1] if i + 1 < len(lines) else None
        heading = classify(line, next_line, heading_rules, acronyms, display_case)
        if in_front:
            if heading is None or heading.level != front_ends_at:
                doc.front_matter.append(line)
                i += 1
                continue
            in_front = False
        if heading is not None:
            state.set(heading.level, heading.value, heading.fields)
            current = None
            i += 1 + heading.consumed
            continue

        started = False
        if unit_size is None or line.size == unit_size:
            for pattern, requires, unless in patterns:
                if requires and not state.values.get(requires):
                    continue
                if unless and state.values.get(unless):
                    continue
                m = pattern.match.match(line.text)
                if not m:
                    continue
                own = _fields(m)
                values, from_headings = state.take()
                fields = {**from_headings, **own}
                default = ".".join(str(own.get(f, "")) for f in key_fields)
                rest = line.text[m.end():].strip()
                first = Line(rest, line.bold, line.page, line.size, line.x0) if rest else None
                start_unit(pattern, fields, make_key(pattern.key, fields, default), values, first)
                started = True
                break
        if started:
            i += 1
            continue

        if (
            current is not None
            and current.pattern.continues_with is not None
            and line.style not in current.pattern.continues_with
        ):
            current = None  # back at the level above, e.g. a clause's closing words after its sub-clauses
        if current is not None:
            current.lines.append(line)
            current.positions.append(i)
        elif any(state.values.get(level) for level, _, _ in fallbacks):
            choice = next(
                (
                    (level, state.values[level], pattern)
                    for level, rx, pattern in fallbacks
                    if state.values.get(level) and (rx is None or rx.match(state.values[level]))
                ),
                None,
            )
            if choice is None:
                doc.warnings.append(f"page {line.page}: no fallback matches the current headings")
            else:
                level, heading_value, pattern = choice
                values, from_headings = state.take()
                fields = {**from_headings, level: heading_value, "slug": slug(heading_value)}
                key = make_key(pattern.key, fields, slug(heading_value))
                existing = next((unit for unit in doc.units if unit.key == key), None)
                if existing is not None:
                    existing.lines.append(line)  # more text for a concept already started
                    existing.positions.append(i)
                    current = existing
                else:
                    start_unit(pattern, fields, key, values, line)
        else:
            doc.warnings.append(f"page {line.page}: text outside any unit: {line.text[:60]!r}")
        i += 1

    if in_front:
        doc.warnings.append(f"no '{front_ends_at}' heading found; everything was treated as front matter")
    return doc
