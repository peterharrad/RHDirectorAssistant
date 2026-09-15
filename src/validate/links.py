"""Link checks: links between concept files that point at nothing.

Bundle-relative links (/articles/article-17.md) and relative links (layout.png)
are both resolved. External links are not checked.
"""
from __future__ import annotations

import posixpath
import re

LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)\)")
EXTERNAL = re.compile(r"^[a-z][a-z0-9+.-]*:", re.I)


def resolve(target: str, from_path: str) -> str | None:
    """Bundle-relative path a link points at, or None for external / in-page links."""
    if EXTERNAL.match(target) or target.startswith("#"):
        return None
    target = target.split("#", 1)[0]
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(posixpath.dirname(from_path), target))


def dangling_links(texts: dict[str, str], existing: set[str]) -> list[str]:
    problems = []
    for path, text in sorted(texts.items()):
        for m in LINK.finditer(text):
            target = resolve(m.group(1), path)
            if target is not None and target not in existing:
                problems.append(f"{path}: broken link to {m.group(1)}")
    return problems
