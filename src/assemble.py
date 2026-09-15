"""Assemble concepts from source documents, independent of any output format.

For each manifest document, parse it and apply its overrides to decide what the
concepts are: their names, titles, descriptions, status, position in the document and
body text. Nothing here knows about files, folders or frontmatter. An output writer
(build_okf.py for the OKF bundle) turns the concepts into its own format.

Cross-references in body text are written as markdown links to a concept name within
the same document, "[clause 7.10](ref:clause-07-10)". Each writer resolves them in its
own way: a file path for OKF, a jump within the file for a single-file output.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from parse.clauses import ParsedDocument, Unit, make_key, parse_units, slug
from parse.definitions import definitions_from_rows, parse_definitions
from parse.extract import StaleTranscript, extract, markdown_table, pdf_tables, split_frontmatter
from parse.registers import parse_register

PAGES_FIELD = "source_pages"
REFERENCE = re.compile(r"\]\(ref:([^)\s]+)\)")


@dataclass
class Concept:
    name: str  # identity within its document, e.g. "article-17"
    title: str
    body: list[str]  # markdown blocks after the title; cross-references as ref: links
    description: str | None = None
    status: str = "draft"
    type: str | None = None  # None: the document's concept-type
    position: dict = field(default_factory=dict)  # where it sits: part, section, number, pages
    order: int | None = None  # position in the source document
    resource: str | None = None  # legislation references only
    tags: list[str] | None = None  # legislation references only


@dataclass
class AssembledDocument:
    doc: dict  # the manifest entry
    concepts: list[Concept]
    warnings: list[str]


@dataclass
class Assembly:
    manifest: dict
    documents: list[AssembledDocument] = field(default_factory=list)
    legislation: list[Concept] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)  # document id -> reason
    errors: list[str] = field(default_factory=list)


class Skip(Exception):
    """A document that can't be assembled yet: missing source, rules or transcript."""


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def first_sentence(lines: list[str], limit: int = 240) -> str | None:
    """First real sentence of a unit, used as a description when none is written."""
    short = None
    for text in lines:
        text = text.strip()
        if not text or text.startswith(("•", "#", "|")):
            continue
        if len(text) < 40:
            short = short or text
            continue
        for m in re.finditer(r"(?<=[.!?])\s", text):
            if m.start() >= 60:
                return text[: m.start()]
        return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…"
    return short


# ---------------------------------------------------------------- documents


class DocumentAssembler:
    """Turns one parsed document into concepts, applying its overrides."""

    def __init__(self, doc: dict, rules: dict, overrides: dict, parsed: ParsedDocument, source: Path):
        self.doc = doc
        self.rules = rules
        self.parsed = parsed
        self.source = source
        self.units_cfg = rules["units"]
        self.key_fields = self.units_cfg["key"]
        self.number_field = self.units_cfg.get("number-field", "number")
        self.numbers_field = self.units_cfg.get("numbers-field", self.number_field + "s")
        self.describe_from = self.units_cfg.get("description")
        defs = rules.get("definitions") or []
        self.defs_cfgs = defs if isinstance(defs, list) else [defs]  # definitions tables, particulars
        self.defs_over = overrides.get("definitions") or {}
        self.groups = overrides.get("groups") or []
        self.descriptions = {str(k): v for k, v in (overrides.get("descriptions") or {}).items()}
        # draft until reviewed: set per document in the manifest, or per concept here
        self.doc_status = doc.get("status", "draft")
        self.statuses = {str(k): v for k, v in (overrides.get("status") or {}).items()}
        self.headings = {str(k): v for k, v in (overrides.get("headings") or {}).items()}
        # a cross-reference is a pattern whose named groups give the key, or {match, key} with a key template
        self.xrefs = [
            (re.compile(x), None) if isinstance(x, str) else (re.compile(x["match"]), x["key"])
            for x in rules.get("cross-references", [])
        ]
        self.body_headings = [
            (re.compile(b["match"]) if b.get("match") else None, b.get("size"), b["markdown"])
            for b in rules.get("body-headings", [])
        ]
        self.warnings = list(parsed.warnings)
        self.undescribed: list[str] = []
        self.units = {u.key: u for u in parsed.units}
        self.targets = self._targets()

    # ---- naming and keys

    @staticmethod
    def to_key(value) -> tuple[str, ...]:
        return tuple(part.lower() for part in str(value).split("."))

    @staticmethod
    def padded(fields: dict) -> dict:
        """Names pad numbers to two digits so they sort in document order."""
        def pad(value):
            if isinstance(value, int):
                return f"{value:02d}"
            return f"{int(value):02d}" if isinstance(value, str) and value.isdigit() else value

        return {k: pad(v) for k, v in fields.items()}

    def name(self, unit: Unit) -> str:
        return unit.pattern.filename.format_map(defaultdict(str, self.padded(unit.fields)))

    def _targets(self) -> dict[tuple[str, ...], str]:
        """Which concept each unit ends up in, for cross-references."""
        targets = {key: self.name(u) for key, u in self.units.items()}
        for cfg in self.defs_cfgs:
            if cfg.get("unit") is not None:
                targets[self.to_key(cfg["unit"])] = cfg["file"]
        for group in self.groups:
            for value in group["units"]:
                targets[self.to_key(value)] = group["file"]
        return targets

    # ---- text

    def link(self, text: str, current: str) -> str:
        def repl(m: re.Match) -> str:
            groups = {k: (v or "").strip() for k, v in m.groupdict().items()}
            if template:
                key = make_key(template, groups, "")
            else:
                key = tuple(groups.get(f, "").lower() for f in self.key_fields)
            while key and not key[-1]:
                key = key[:-1]
            target = self.targets.get(key)
            if target is None or target == current:
                return m.group(0)
            return f"[{m.group(0)}](ref:{target})"

        for rx, template in self.xrefs:
            text = rx.sub(repl, text)
        return text

    def render_line(self, line) -> str:
        if isinstance(line, str):
            return line
        for pattern, size, markdown in self.body_headings:
            if (size is None or line.size == size) and (pattern is None or pattern.match(line.text)):
                return f"{markdown} {line.text}"
        return f"**{line.text}**" if line.bold else line.text

    def paragraphs(self, lines: list, current: str) -> str:
        return "\n\n".join(self.link(self.render_line(l), current) for l in lines)

    def position(self, unit: Unit) -> dict:
        return {f: unit.headings.get(f) for f in self.units_cfg.get("fields", [])}

    def number_value(self, unit: Unit):
        number = unit.number
        return int(number) if number.isdigit() else number

    def status(self, key: str) -> str:
        return self.statuses.get(key, self.doc_status)

    def description(self, key: str, unit: Unit | None = None) -> str | None:
        text = self.descriptions.get(key)
        if text:
            return text
        if unit is not None and self.describe_from == "first-sentence":
            return first_sentence(unit.text_lines)
        self.undescribed.append(key)
        return None

    # ---- concepts

    def assemble(self) -> tuple[list[Concept], list[str]]:
        concepts, used = [], set()
        for cfg in self.defs_cfgs:
            concepts.append(self.definitions(cfg))
            if cfg.get("unit") is not None:
                used.add(self.to_key(cfg["unit"]))
        for group in self.groups:
            concepts.append(self.group(group))
            used.update(self.to_key(v) for v in group["units"])
        for key, unit in self.units.items():
            if key not in used:
                concepts.append(self.unit(unit))
        for key in sorted(set(self.headings) - {".".join(k) for k in self.units}):
            self.warnings.append(f"heading override for unit {key}, which doesn't exist")
        if self.undescribed:
            self.warnings.append(
                f"{len(self.undescribed)} concepts have no description (first: {', '.join(self.undescribed[:5])})"
            )
        return concepts, self.warnings

    def unit(self, unit: Unit) -> Concept:
        key = ".".join(unit.key)
        heading = self.headings.get(key) or unit.headings.get(self.units_cfg.get("heading-level"))
        template = unit.pattern.title if heading else (unit.pattern.title_without_heading or unit.pattern.title)
        if unit.pattern.title_if_split and any(
            len(k) > len(unit.key) and k[: len(unit.key)] == unit.key for k in self.units
        ):
            template = unit.pattern.title_if_split  # units of its own follow: this is the lead-in
        if not heading and unit.pattern.title_without_heading is None and "{heading}" in unit.pattern.title:
            self.warnings.append(f"unit {key} has no heading")
        title = template.format_map(defaultdict(str, {**unit.fields, "heading": heading or ""})).strip(" –-")
        name = self.targets[unit.key]
        return Concept(
            name=name,
            title=title,
            body=[self.paragraphs(unit.lines, name)],
            description=self.description(key, unit),
            status=self.status(key),
            position={
                **self.position(unit),
                unit.pattern.number_field or self.number_field: self.number_value(unit),
                PAGES_FIELD: unit.pages,
            },
            order=unit.index,
        )

    def group(self, group: dict) -> Concept:
        name, title = group["file"], group["title"]
        parts, pages, members = [], set(), []
        if group.get("include-front-matter"):
            parts.append(self.paragraphs(self.parsed.front_matter, name))
            pages.update(l.page for l in self.parsed.front_matter if l.page is not None)
        for value in group["units"]:
            unit = self.units.get(self.to_key(value))
            if unit is None:
                self.warnings.append(f"group {group['file']}: unit {value} not found")
                continue
            members.append(unit)
            pages.update(unit.pages)
        # Text in document order, so words that follow a sub-clause stay after it; each
        # member's sub-heading goes before its first line.
        pieces = sorted(
            ((position, n, line) for n, unit in enumerate(members) for position, line in zip(unit.positions, unit.lines)),
            key=lambda piece: piece[0],
        )
        headed, block, block_member = set(), [], None
        for _, n, line in pieces:
            if n != block_member:
                if block:
                    parts.append(self.paragraphs(block, name))
                block, block_member = [], n
                if n not in headed:
                    headed.add(n)
                    unit = members[n]
                    heading = unit.pattern.group_heading
                    if heading is None:
                        heading = unit.pattern.title_without_heading or unit.pattern.title
                    if heading:  # an empty group-heading means "run this unit straight in"
                        fields = defaultdict(str, {**unit.fields, "heading": ""})
                        parts.append("## " + heading.format_map(fields).strip(" –-"))
            block.append(line)
        if block:
            parts.append(self.paragraphs(block, name))
        return Concept(
            name=name,
            title=title,
            body=parts,
            description=self.description(group["file"]),
            status=self.status(group["file"]),
            type=group.get("type"),
            position={
                **(self.position(members[0]) if members else {}),
                self.numbers_field: [self.number_value(u) for u in members],
                PAGES_FIELD: sorted(pages),
            },
            order=min((u.index for u in members), default=0),
        )

    def definitions(self, cfg: dict) -> Concept:
        name = cfg["file"]
        title = cfg.get("title", "Definitions")
        unit = self.units.get(self.to_key(cfg["unit"])) if cfg.get("unit") is not None else None
        position: dict = {}
        if cfg.get("form") == "table" and self.source.suffix.lower() == ".docx":
            from parse.docx_reader import docx_tables

            matches = [
                rows
                for before, rows in docx_tables(self.source)
                if (cfg.get("after-text") and cfg["after-text"] in before)
                or (cfg.get("first-cell") and rows and rows[0] and cfg["first-cell"] in rows[0][0])
            ]
            if not matches:
                self.warnings.append(f"{cfg['file']}: no table found")
            parsed = definitions_from_rows(matches[0] if matches else [], cfg.get("skip-terms", []), cfg.get("term-cell"))
        elif cfg.get("form") == "table":
            rows = [
                row
                for table in pdf_tables(
                    self.source,
                    from_heading=cfg["from-heading"],
                    to_heading=cfg.get("to-heading"),
                    heading_size=cfg.get("heading-size"),
                )
                for row in table
            ]
            parsed = definitions_from_rows(rows, cfg.get("skip-terms", []), cfg.get("term-cell"))
        elif unit is None:
            self.warnings.append(f"definitions unit {cfg.get('unit')} not found")
            parsed = definitions_from_rows([])
        else:
            parsed = parse_definitions(unit.text_lines, cfg["term"], cfg.get("ends-at"))
            position = {
                **self.position(unit),
                self.number_field: self.number_value(unit),
                PAGES_FIELD: unit.pages,
            }
        parts = []
        if parsed.intro:
            parts.append(self.paragraphs(parsed.intro, name))
        for d in parsed.definitions:
            parts += [f"## {d.term}", self.paragraphs(d.lines, name)]
        if parsed.notes:
            if self.defs_over.get("notes-heading"):
                parts.append(f"## {self.defs_over['notes-heading']}")
            parts.append(self.paragraphs(parsed.notes, name))
        known = {d.term.lower() for d in parsed.definitions}
        for extra in self.defs_over.get("defined-elsewhere") or []:
            term, key = extra["term"], self.to_key(extra["unit"])
            target = self.targets.get(key)
            if target is None:
                self.warnings.append(f"defined-elsewhere: unit {extra['unit']} for {term!r} not found")
                continue
            if term.lower() in known:
                self.warnings.append(f"defined-elsewhere: {term!r} is already in the definitions clause")
            if term.lower() not in " ".join(self.units[key].text_lines).lower():
                self.warnings.append(f"defined-elsewhere: {term!r} does not appear in unit {extra['unit']}")
            parts += [f"## {term}", f"Defined in [{extra.get('ref', extra['unit'])}](ref:{target})."]
        return Concept(
            name=name,
            title=title,
            body=parts,
            description=self.description(cfg["file"]),
            status=self.status(cfg["file"]),
            type=cfg.get("type"),
            position=position,
            order=-1,
        )


def assemble_title_register(doc: dict, rules: dict, root: Path) -> tuple[list[Concept], list[str]]:
    """One concept per register (A, B, C), its entries as a markdown table."""
    source = root / doc["source"]
    if not source.exists():
        raise Skip(f"source not found: {source.name}")
    parsed = parse_register(source, rules.get("extract") or {})
    tenure = parsed.tenure or ""
    concepts = []
    for index, register in enumerate(parsed.registers):
        parts = {"heading": register.heading, "title_number": parsed.title_number or "", "tenure": tenure}
        title = rules["title"].format_map(defaultdict(str, parts)).strip()
        intro = " ".join(register.intro)
        body = [intro]
        if register.class_of_title:
            body.append(f"Class of Title: {register.class_of_title}")
        cell = lambda paragraphs: "<br>".join(paragraphs)
        entries = [e for e in register.entries if not e.fields]
        if entries:
            rows = [["Entry", "Date", "Description"]]
            rows += [[str(e.number), e.date or "", cell(e.paragraphs)] for e in entries]
            body.append(markdown_table(rows))
        schedule = [e for e in register.entries if e.fields]
        if schedule:
            columns: list[str] = []
            for e in schedule:
                columns += [k for k in e.fields if k not in columns]
            columns.sort(key=lambda k: k == "Note")  # notes last
            rows = [["Entry", *columns]] + [[str(e.number), *(e.fields.get(k, "") for k in columns)] for e in schedule]
            body += [rules.get("schedule-heading", "## Schedule of notices of leases"), markdown_table(rows)]
        concepts.append(
            Concept(
                name=slug(register.heading),
                title=title,
                body=body,
                description=f"The {register.name.lower()} of {tenure.lower()} title {parsed.title_number}. {intro}".replace("  ", " "),
                status=doc.get("status", "draft"),
                position={
                    "title_number": parsed.title_number,
                    "tenure": tenure,
                    "register": register.heading,
                    "entry_count": len(register.entries),
                    "accessed": parsed.accessed,
                    PAGES_FIELD: register.pages,
                },
                order=index,
            )
        )
    return concepts, parsed.warnings


def assemble_document(doc: dict, root: Path) -> tuple[list[Concept], list[str]]:
    for key in ("source", "parse-rules"):
        if not doc.get(key):
            raise Skip(f"no {key} in the manifest")
    rules_path = root / "config" / doc["parse-rules"]
    if not rules_path.exists():
        raise Skip(f"config/{doc['parse-rules']} does not exist yet")
    overrides: dict = {}
    if doc.get("overrides"):
        over_path = root / "config" / doc["overrides"]
        if not over_path.exists():
            raise Skip(f"config/{doc['overrides']} does not exist yet")
        overrides = split_frontmatter(over_path.read_text(encoding="utf-8"))[0] or {}
    rules = load_yaml(rules_path)
    if rules.get("kind") == "title-register":
        return assemble_title_register(doc, rules, root)
    if "units" not in rules:
        raise Skip(f"config/{doc['parse-rules']} has no 'units' section yet")
    source = root / doc["source"]
    try:
        lines = extract(source, root / "transcripts" / f"{doc['id']}.md", rules.get("extract"))
    except (FileNotFoundError, NotImplementedError) as e:
        raise Skip(str(e)) from None
    return DocumentAssembler(doc, rules, overrides, parse_units(lines, rules), source).assemble()


def assemble_legislation(manifest: dict) -> list[Concept]:
    concepts = []
    for item in manifest.get("legislation") or []:
        name = re.sub(r"[^a-z0-9]+", "-", item["reference"].lower()).strip("-")
        body = []
        if item.get("description"):
            body.append(item["description"])
        if item.get("resource"):
            body.append(f"Full text: [legislation.gov.uk]({item['resource']})")
        concepts.append(
            Concept(
                name=name,
                title=item["reference"],
                body=body,
                description=item.get("description"),
                status=item.get("status", "draft"),
                type="legislation",
                resource=item.get("resource"),
                tags=item.get("tags"),
            )
        )
    return concepts


def assemble_all(root: Path) -> Assembly:
    """Every manifest document's concepts, and the legislation references."""
    manifest = load_yaml(root / "config" / "manifest.yml")
    assembly = Assembly(manifest)
    for doc in manifest.get("documents", []):
        try:
            concepts, warnings = assemble_document(doc, root)
        except Skip as e:
            assembly.skipped[doc["id"]] = str(e)
            continue
        except StaleTranscript as e:
            assembly.errors.append(f"{doc['id']}: {e}")
            continue
        assembly.documents.append(AssembledDocument(doc, concepts, warnings))
    assembly.legislation = assemble_legislation(manifest)
    return assembly
