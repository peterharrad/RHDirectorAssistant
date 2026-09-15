"""Frontmatter generation.

Each concept file inherits provenance from its source document's entry in
config/manifest.yml, mapped onto OKF fields (type, resource, sources, generated),
plus its own position in the document (part, section, article_number,
source_pages). All frontmatter fields are snake_case, following OKF; keys in the
repo's config files are kebab-case. See docs/okf-conventions.md.
"""
from __future__ import annotations

import tomllib
from functools import cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

# Replaced with a timestamp when the bundle is written; kept unchanged if the concept is.
AT_PLACEHOLDER = "__GENERATED_AT__"


@cache
def tool_id() -> str:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    return f"{project['name']} {project['version']}"


def generated() -> dict:
    return {"by": tool_id(), "at": AT_PLACEHOLDER}


def source_entry(doc: dict) -> dict:
    entry = {
        "id": doc["id"],
        "title": doc.get("description"),
        "author": doc.get("author"),
        "last_modified": str(doc["last-modified"]) if doc.get("last-modified") else None,
        "resource": doc.get("resource"),
    }
    return {k: v for k, v in entry.items() if v is not None}


def concept_frontmatter(
    doc: dict,
    *,
    title: str,
    description: str | None = None,
    type_: str | None = None,
    position: dict | None = None,
    status: str = "draft",
) -> dict:
    fm: dict = {"type": type_ or doc["concept-type"], "title": title}
    if description:
        fm["description"] = description.strip()
    if doc.get("resource"):
        fm["resource"] = doc["resource"]
    for key, value in (position or {}).items():
        if value not in (None, "", []):
            fm[key] = value
    fm["sources"] = [source_entry(doc)]
    fm["generated"] = generated()
    fm["status"] = status
    return fm


def render(fm: dict | None, body: str) -> str:
    head = ""
    if fm:
        head = "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=10_000) + "---\n\n"
    return head + body.strip() + "\n"
