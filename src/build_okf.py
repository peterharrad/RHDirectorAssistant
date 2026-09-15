"""Build the OKF bundle.

Takes the concepts from assemble.py and writes each one as an OKF concept file under
okf-bundle/<bundle-path>/, with frontmatter. Then adds the legislation references and
authored/, generates the index.md files, validates links and fields, and appends to
okf-bundle/log.md. Everything OKF-specific lives here, in frontmatter.py and in validate/;
deciding what the concepts are does not. okf-bundle/ is fully generated and may be rebuilt
from scratch.

    rh-build            build okf-bundle/
    rh-build --check    report what a build would change, without writing anything
"""
from __future__ import annotations

import argparse
import datetime as dt
import posixpath
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from assemble import REFERENCE, Concept, assemble_all
from frontmatter import AT_PLACEHOLDER, concept_frontmatter, generated, render
from parse.extract import split_frontmatter
from validate import links, schema

ROOT = Path(__file__).resolve().parent.parent
RESERVED = {"index.md", "log.md"}
OKF_VERSION = "0.2"
GROUP_FIELDS = ("part", "chapter", "section")  # frontmatter fields that group an index
AT_LINE = re.compile(r"^(\s+at: )(.*)$", re.M)


@dataclass
class Output:
    path: str  # bundle-relative, e.g. "articles/article-17.md"
    content: str | bytes
    order: int | None = None  # position in the source document, for index listings


@dataclass
class BuildResult:
    outputs: list[Output] = field(default_factory=list)
    built: dict[str, int] = field(default_factory=dict)  # document id -> concepts
    skipped: dict[str, str] = field(default_factory=dict)  # document id -> reason
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- concepts as OKF files


def resolve_references(text: str, base: str) -> str:
    """ref: links name a concept in the same document; in the bundle that's a file path."""
    return REFERENCE.sub(lambda m: f"](/{base}/{m.group(1)}.md)", text)


def concept_file(concept: Concept, doc: dict, base: str) -> Output:
    fm = concept_frontmatter(
        doc,
        title=concept.title,
        description=concept.description,
        type_=concept.type,
        position=concept.position,
        status=concept.status,
    )
    body = "\n\n".join([f"# {concept.title}", *concept.body])
    return Output(f"{base}/{concept.name}.md", render(fm, resolve_references(body, base)), order=concept.order)


def legislation_file(concept: Concept) -> Output:
    fm = {"type": concept.type, "title": concept.title}
    for key, value in (("description", concept.description), ("resource", concept.resource), ("tags", concept.tags)):
        if value:
            fm[key] = value
    fm["generated"] = generated()
    fm["status"] = concept.status
    body = "\n\n".join([f"# {concept.title}", *concept.body])
    return Output(f"legislation/{concept.name}.md", render(fm, body))


def collect_authored(root: Path) -> list[Output]:
    base = root / "authored"
    outputs = []
    for p in sorted(base.rglob("*")) if base.exists() else []:
        if p.is_dir() or p == base / "README.md":
            continue
        rel = p.relative_to(base).as_posix()
        content = p.read_text(encoding="utf-8").replace("\r\n", "\n") if p.suffix == ".md" else p.read_bytes()
        outputs.append(Output(rel, content))
    return outputs


def build_indexes(outputs: list[Output], manifest: dict) -> list[Output]:
    concepts = {
        o.path: (split_frontmatter(o.content)[0] or {}, o.order)
        for o in outputs
        if o.path.endswith(".md") and posixpath.basename(o.path) not in RESERVED
    }
    dirs = {""}
    for path in concepts:
        parts = path.split("/")[:-1]
        dirs.update("/".join(parts[: i + 1]) for i in range(len(parts)))

    bundle = manifest.get("bundle") or {}
    titles = dict(bundle.get("groups") or {})
    for doc in manifest.get("documents", []):
        if doc.get("bundle-path"):
            titles.setdefault(doc["bundle-path"].strip("/"), doc.get("description"))

    indexes = []
    for d in sorted(dirs):
        title = bundle.get("title", "Bundle") if d == "" else titles.get(d) or d.rsplit("/", 1)[-1]
        lines = [f"# {title}", ""]
        subdirs = sorted(s for s in dirs if s and posixpath.dirname(s) == d)
        for s in subdirs:
            lines.append(f"- [{titles.get(s) or s.rsplit('/', 1)[-1]}](/{s}/index.md)")
        if subdirs:
            lines.append("")
        # Document order where known (articles by number), otherwise by path.
        files = sorted(
            ((p, fm, order) for p, (fm, order) in concepts.items() if posixpath.dirname(p) == d),
            key=lambda f: (f[2] if f[2] is not None else 10**9, f[0]),
        )
        def add_heading(text: str) -> None:
            if lines[-1] != "":
                lines.append("")
            lines.extend([text, ""])

        previous: list[str] = []
        for path, fm, _ in files:
            levels = [fm[f] for f in GROUP_FIELDS if fm.get(f)][:2]
            for depth, value in enumerate(levels):
                if previous[depth:depth + 1] != [value]:
                    add_heading(f"{'#' * (depth + 2)} {value}")
                    previous = levels[: depth + 1]
            previous = levels
            entry = f"- [{fm.get('title') or posixpath.basename(path)}](/{path})"
            if fm.get("description"):
                entry += f": {fm['description']}"
            lines.append(entry)
            if files and path == files[-1][0]:
                lines.append("")
        lines.append("<!-- Generated by build_okf.py. Do not edit by hand. -->")
        fm = None
        if d == "":
            fm = {"okf_version": OKF_VERSION, "title": title}
            if bundle.get("description"):
                fm["description"] = bundle["description"]
        indexes.append(Output(f"{d}/index.md" if d else "index.md", render(fm, "\n".join(lines))))
    return indexes


# ---------------------------------------------------------------- build and write


def build(root: Path = ROOT) -> BuildResult:
    assembly = assemble_all(root)
    result = BuildResult(skipped=dict(assembly.skipped), errors=list(assembly.errors))
    for assembled in assembly.documents:
        doc = assembled.doc
        if not doc.get("bundle-path"):
            result.skipped[doc["id"]] = "no bundle-path in the manifest"
            continue
        base = doc["bundle-path"].strip("/")
        outputs = [concept_file(c, doc, base) for c in assembled.concepts]
        result.outputs += outputs
        result.built[doc["id"]] = len(outputs)
        result.warnings += [f"{doc['id']}: {w}" for w in assembled.warnings]
    result.outputs += [legislation_file(c) for c in assembly.legislation]
    result.outputs += collect_authored(root)

    seen: set[str] = set()
    for o in result.outputs:
        if o.path in seen:
            result.errors.append(f"two concepts would be written to {o.path}")
        seen.add(o.path)

    result.outputs += build_indexes(result.outputs, assembly.manifest)
    texts = {o.path: o.content for o in result.outputs if isinstance(o.content, str)}
    existing = {o.path for o in result.outputs}
    result.errors += links.dangling_links(texts, existing)
    result.errors += schema.check(texts, existing)
    return result


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def finalise(outputs: list[Output], previous: Path | None, now: str) -> dict[str, str | bytes]:
    """Fill in generated.at: keep the previous timestamp for concepts whose content is unchanged."""
    files: dict[str, str | bytes] = {}
    for o in outputs:
        content = o.content
        if isinstance(content, str) and AT_PLACEHOLDER in content:
            at = f"'{now}'"
            old_path = previous / o.path if previous else None
            if old_path and old_path.exists():
                old = old_path.read_text(encoding="utf-8").replace("\r\n", "\n")
                m = AT_LINE.search(old)
                if m and AT_LINE.sub(r"\1X", old) == AT_LINE.sub(r"\1X", content):
                    at = m.group(2)
            content = content.replace(AT_PLACEHOLDER, at)
        files[o.path] = content
    return files


def _bytes(content: str | bytes) -> bytes:
    return content.encode("utf-8") if isinstance(content, str) else content


def read_tree(folder: Path) -> dict[str, bytes]:
    if not folder.exists():
        return {}
    tree = {}
    for p in folder.rglob("*"):
        if p.is_file():
            data = p.read_bytes()
            tree[p.relative_to(folder).as_posix()] = data.replace(b"\r\n", b"\n") if p.suffix == ".md" else data
    return tree


def compare(files: dict[str, str | bytes], folder: Path) -> list[str]:
    """Differences between a finished build and what's on disk, ignoring log.md."""
    old = read_tree(folder)
    old.pop("log.md", None)
    new = {p: _bytes(c) for p, c in files.items()}
    return (
        [f"added    {p}" for p in sorted(set(new) - set(old))]
        + [f"removed  {p}" for p in sorted(set(old) - set(new))]
        + [f"changed  {p}" for p in sorted(set(new) & set(old)) if new[p] != old[p]]
    )


def write_bundle(folder: Path, files: dict[str, str | bytes], now: str) -> list[str]:
    changes = compare(files, folder)
    log_path = folder / "log.md"
    log = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    if "## " not in log:
        log = "# Build log\n"
    if folder.exists():
        shutil.rmtree(folder)
    for path, content in files.items():
        target = folder / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_bytes(content))
    if changes:
        counts = {kind: sum(c.startswith(kind) for c in changes) for kind in ("added", "changed", "removed")}
        log = log.rstrip() + f"\n\n## {now}\n\n" + ", ".join(f"{v} {k}" for k, v in counts.items()) + "\n"
    log_path.write_text(log.rstrip() + "\n", encoding="utf-8", newline="\n")
    return changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the OKF bundle from sources/.")
    parser.add_argument("--check", action="store_true", help="report what a build would change, without writing")
    args = parser.parse_args(argv)

    bundle = ROOT / "okf-bundle"
    result = build(ROOT)
    for doc_id, count in result.built.items():
        print(f"built    {doc_id}: {count} concepts")
    for doc_id, reason in result.skipped.items():
        print(f"skipped  {doc_id}: {reason}")
    for w in result.warnings:
        print(f"warning  {w}")
    for e in result.errors:
        print(f"ERROR    {e}")

    now = now_iso()
    files = finalise(result.outputs, bundle, now)
    if args.check:
        changes = compare(files, bundle)
        print("\n".join(changes) if changes else "okf-bundle/ is up to date")
        return 1 if changes or result.errors else 0
    changes = write_bundle(bundle, files, now)
    print(f"wrote okf-bundle/: {len(files)} files, {len(changes)} changed")
    return 1 if result.errors else 0


if __name__ == "__main__":
    sys.exit(main())
