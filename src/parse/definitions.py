"""Definitions extraction.

Splits a definitions clause into its introduction, one entry per defined term, and
any closing notes. A term starts a line (e.g. “articles” means …); lines that don't
start a new term belong to the previous one. Definitions tables (leases, the RICS
glossary) are not handled yet.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Definition:
    term: str
    lines: list[str] = field(default_factory=list)


@dataclass
class DefinitionList:
    intro: list[str]
    definitions: list[Definition]
    notes: list[str]


def parse_definitions(lines: list[str], term_pattern: str, ends_at: str | None = None) -> DefinitionList:
    term_re = re.compile(term_pattern)
    end_re = re.compile(ends_at) if ends_at else None
    result = DefinitionList([], [], [])
    for text in lines:
        if result.notes or (result.definitions and end_re and end_re.match(text)):
            result.notes.append(text)
            continue
        m = term_re.match(text)
        if m:
            result.definitions.append(Definition(m.group("term").strip(), [text]))
        elif result.definitions:
            result.definitions[-1].lines.append(text)
        else:
            result.intro.append(text)
    return result


def definitions_from_rows(
    rows: list[list[str]], skip_terms: list[str] = (), term_pattern: str | None = None
) -> DefinitionList:
    """Turn the rows of a two-column definitions table into definitions.

    A row whose term cell is empty continues the definition above it. Line breaks
    inside a cell come from the page layout, so they are joined back up.
    """
    skip = {t.strip().lower() for t in skip_terms}
    result = DefinitionList([], [], [])
    for row in rows:
        term = " ".join((row[0] or "").split())
        text = " ".join((row[1] or "").split()) if len(row) > 1 else ""
        if term and term_pattern and (m := re.match(term_pattern, term)):
            term = m.group("term").strip()  # e.g. strip the quotes round a term
        if term.lower() in skip or not (term or text):
            continue
        if term:
            result.definitions.append(Definition(term, [text] if text else []))
        elif result.definitions:
            result.definitions[-1].lines.append(text)
    return result
