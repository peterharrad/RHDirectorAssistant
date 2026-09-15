"""Build the single files: one markdown file per source document.

Takes the same concepts from assemble.py as the OKF bundle, so a single file holds
exactly what that document's concept files hold, in document order. Each concept becomes
a heading 1, followed by its title, description and reference (article number, clause
number…). Cross-references become links within the file. The building notes in
authored/ and the legislation references each become a file too. single-files/ is fully
generated and may be rebuilt from scratch. See docs/single-file-conventions.md.

    rh-build-single            build single-files/
    rh-build-single --check    report what a build would change, without writing anything
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from assemble import REFERENCE, Concept, assemble_all
from frontmatter import render, source_entry, tool_id
from parse.extract import split_frontmatter

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = "single-files"

# Position fields that say where a concept sits in its document, as its reference.
REFERENCE_FIELDS = (
    "article_number",
    "article_numbers",
    "clause_number",
    "clause_numbers",
    "paragraph_number",
    "section_number",
    "register",
)
IMAGE = re.compile(r"^!\[[^\]]*\]\([^)]*\)$")
BUNDLE_LINK = re.compile(r"\]\(/[^)\s]*?/([^/)\s]+)\.md\)")


@dataclass
class Section:
    anchor: str
    title: str
    body: list[str]
    description: str | None = None
    reference: dict = field(default_factory=dict)


@dataclass
class BuildResult:
    files: dict[str, str] = field(default_factory=dict)  # file name -> content
    built: dict[str, int] = field(default_factory=dict)  # file name -> sections
    skipped: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _value(value) -> str:
    return ", ".join(str(v) for v in value) if isinstance(value, list) else str(value)


def render_section(section: Section) -> str:
    fields = [f"- title: {section.title}"]
    if section.description:
        fields.append(f"- description: {section.description.strip()}")
    fields += [f"- {k}: {_value(v)}" for k, v in section.reference.items()]
    body = REFERENCE.sub(lambda m: f"](#{m.group(1)})", "\n\n".join(section.body))
    return "\n\n".join(filter(None, [f'<a id="{section.anchor}"></a>', f"# {section.title}", "\n".join(fields), body]))


def render_file(fm: dict, sections: list[Section]) -> str:
    return render(fm, "\n\n".join(render_section(s) for s in sections))


def concept_section(concept: Concept) -> Section:
    reference = {
        k: concept.position[k]
        for k in REFERENCE_FIELDS
        if concept.position.get(k) not in (None, "", [])
    }
    return Section(concept.name, concept.title, concept.body, concept.description, reference)


def file_frontmatter(title: str, sources: list[dict], description: str | None = None) -> dict:
    fm: dict = {"title": title}
    if description:
        fm["description"] = description
    fm["sources"] = sources
    fm["generated_by"] = tool_id()
    return fm


def authored_sections(folder: Path) -> tuple[list[Section], list[dict], list[str]]:
    """Hand-written concepts in one authored/ folder, without the images they embed.

    A heading 2 section that embeds an image describes the image, so it goes too.
    """
    sections, sources, warnings = [], [], []
    for path in sorted(folder.glob("*.md")):
        fm, body = split_frontmatter(path.read_text(encoding="utf-8").replace("\r\n", "\n"))
        fm = fm or {}
        lines = body.strip().split("\n")
        if lines and lines[0].startswith("# "):
            lines = lines[1:]  # the title becomes the section heading
        chunks: list[list[str]] = [[]]
        for line in lines:
            if line.startswith("## "):
                chunks.append([])
            chunks[-1].append(line)
        kept = []
        for i, chunk in enumerate(chunks):
            if any(IMAGE.match(line.strip()) for line in chunk):
                where = chunk[0] if i else "image"
                warnings.append(f"{path.relative_to(folder.parent.parent).as_posix()}: left out {where}")
                if i:
                    continue
                chunk = [line for line in chunk if not IMAGE.match(line.strip())]
            kept += chunk
        text = BUNDLE_LINK.sub(lambda m: f"](#{m.group(1)})", "\n".join(kept)).strip()
        text = re.sub(r"\n{3,}", "\n\n", text)
        sections.append(Section(path.stem, fm.get("title") or path.stem, [text], fm.get("description")))
        sources += fm.get("sources") or []
    return sections, sources, warnings


def build(root: Path = ROOT) -> BuildResult:
    assembly = assemble_all(root)
    result = BuildResult(skipped=dict(assembly.skipped), errors=list(assembly.errors))
    for assembled in assembly.documents:
        doc = assembled.doc
        sections = [concept_section(c) for c in assembled.concepts]
        fm = file_frontmatter(doc.get("description") or doc["id"], [source_entry(doc)])
        name = f"{doc['id']}.md"
        result.files[name] = render_file(fm, sections)
        result.built[name] = len(sections)
        result.warnings += [f"{doc['id']}: {w}" for w in assembled.warnings]

    groups = (assembly.manifest.get("bundle") or {}).get("groups") or {}
    if assembly.legislation:
        sections = [
            Section(c.name, c.title, [b for b in c.body if b != c.description], c.description)
            for c in assembly.legislation
        ]
        fm = file_frontmatter(groups.get("legislation", "Legislation"), [], "Acts referred to by the governing documents.")
        del fm["sources"]
        result.files["legislation.md"] = render_file(fm, sections)
        result.built["legislation.md"] = len(sections)

    authored = root / "authored"
    for folder in sorted(p for p in authored.iterdir() if p.is_dir()) if authored.exists() else []:
        sections, sources, warnings = authored_sections(folder)
        if not sections:
            continue
        name = f"{folder.name}.md"
        result.files[name] = render_file(file_frontmatter(groups.get(folder.name, folder.name), sources), sections)
        result.built[name] = len(sections)
        result.warnings += warnings

    for name, content in result.files.items():
        anchors = set(re.findall(r'<a id="([^"]+)"></a>', content))
        for target in sorted(set(re.findall(r"\]\(#([^)\s]+)\)", content)) - anchors):
            result.errors.append(f"{name}: link to #{target}, which is not in the file")
    return result


def read_tree(folder: Path) -> dict[str, bytes]:
    if not folder.exists():
        return {}
    return {p.name: p.read_bytes().replace(b"\r\n", b"\n") for p in folder.glob("*.md")}


def compare(files: dict[str, str], folder: Path) -> list[str]:
    old = read_tree(folder)
    new = {p: c.encode("utf-8") for p, c in files.items()}
    return (
        [f"added    {p}" for p in sorted(set(new) - set(old))]
        + [f"removed  {p}" for p in sorted(set(old) - set(new))]
        + [f"changed  {p}" for p in sorted(set(new) & set(old)) if new[p] != old[p]]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build one markdown file per source document.")
    parser.add_argument("--check", action="store_true", help="report what a build would change, without writing")
    args = parser.parse_args(argv)

    folder = ROOT / OUTPUT
    result = build(ROOT)
    for name, count in result.built.items():
        print(f"built    {name}: {count} sections")
    for doc_id, reason in result.skipped.items():
        print(f"skipped  {doc_id}: {reason}")
    for w in result.warnings:
        print(f"warning  {w}")
    for e in result.errors:
        print(f"ERROR    {e}")

    changes = compare(result.files, folder)
    if args.check:
        print("\n".join(changes) if changes else f"{OUTPUT}/ is up to date")
        return 1 if changes or result.errors else 0
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir()
    for name, content in result.files.items():
        (folder / name).write_bytes(content.encode("utf-8"))
    print(f"wrote {OUTPUT}/: {len(result.files)} files, {len(changes)} changed")
    return 1 if result.errors else 0


if __name__ == "__main__":
    sys.exit(main())
