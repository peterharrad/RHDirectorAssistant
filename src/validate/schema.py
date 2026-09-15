"""Schema checks: every concept has frontmatter with a type and title, every field
name is snake_case (as OKF's are), and a bundle-relative resource points at a file
that exists."""
from __future__ import annotations

import posixpath
import re

from parse.extract import split_frontmatter

RESERVED = {"index.md", "log.md"}
SNAKE_CASE = re.compile(r"^[a-z][a-z0-9_]*$")


def field_names(value, prefix: str = ""):
    """Every key in a frontmatter structure, with its dotted path."""
    if isinstance(value, dict):
        for key, inner in value.items():
            yield f"{prefix}{key}", str(key)
            yield from field_names(inner, f"{prefix}{key}.")
    elif isinstance(value, list):
        for item in value:
            yield from field_names(item, prefix)


def check(texts: dict[str, str], existing: set[str]) -> list[str]:
    problems = []
    for path, text in sorted(texts.items()):
        if not path.endswith(".md") or posixpath.basename(path) in RESERVED:
            continue
        fm, _ = split_frontmatter(text)
        if fm is None:
            problems.append(f"{path}: no frontmatter")
            continue
        for key in ("type", "title"):
            if not fm.get(key):
                problems.append(f"{path}: missing {key}")
        for dotted, name in field_names(fm):
            if not SNAKE_CASE.match(name):
                problems.append(f"{path}: field {dotted} is not snake_case")
        resource = fm.get("resource")
        if isinstance(resource, str) and resource.startswith("/") and resource.lstrip("/") not in existing:
            problems.append(f"{path}: resource {resource} not found in the bundle")
    return problems
