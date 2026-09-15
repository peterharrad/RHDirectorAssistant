"""Write redacted copies of the source documents into the public repo, and check them.

    rh-redact                   redact every document into the output folder
    rh-redact --only rics-code  just one document
    rh-redact --check           rebuild the redacted copies' concepts and compare them
                                with the real documents' (names, titles, positions)

The output folder is config/redaction.yml's output, relative to this repo, unless --out
is given. Its config/ must match this repo's, because the check builds with it.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path


from assemble import Skip, assemble_document, load_yaml
from parse.extract import StaleTranscript
from redact.pdf import redact_pdf
from redact.text import Redactor
from redact.transcript import redact_transcript
from redact.word import redact_docx

ROOT = Path(__file__).resolve().parent.parent.parent
TERM_HEADING = re.compile(r"^## (.+)$", re.M)


def rule_patterns(rules: dict) -> list[str]:
    """What the parse rules look for in the text, which redaction must keep."""
    found: list[str] = []
    extract = rules.get("extract") or {}
    found += extract.get("drop") or []
    found += [re.escape(i["expect"]) for i in extract.get("skip-pages") or [] if isinstance(i, dict) and i.get("expect")]
    found += [p for p in [(rules.get("back-matter") or {}).get("starts-at")] if p]
    definitions = rules.get("definitions") or []
    for d in definitions if isinstance(definitions, list) else [definitions]:
        for key in ("after-text", "first-cell", "from-heading", "to-heading", "term"):
            if d.get(key):
                found.append(d[key] if key in ("from-heading", "to-heading", "term") else re.escape(d[key]))
        found += [rf"(?<!\w){re.escape(t)}(?!\w)" for t in d.get("skip-terms") or []]
    for ref in rules.get("cross-references") or []:
        found.append(ref["match"] if isinstance(ref, dict) else ref)
    return found


def defined_terms(concepts) -> list[str]:
    terms = []
    for concept in concepts:
        if concept.type in ("definitions", "particulars"):
            terms += TERM_HEADING.findall("\n\n".join(concept.body))
    return terms


def redact_document(doc: dict, settings: dict, out: Path) -> None:
    method = settings.get("method")
    source = ROOT / doc["source"]
    target = out / doc["source"]
    if method == "copy":
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        transcript = ROOT / "transcripts" / f"{doc['id']}.md"
        if transcript.exists():
            shutil.copyfile(transcript, out / "transcripts" / transcript.name)
        return
    rules = load_yaml(ROOT / "config" / doc["parse-rules"])
    concepts, _ = assemble_document(doc, ROOT)
    redactor = Redactor(rule_patterns(rules) + (settings.get("keep") or []), defined_terms(concepts))
    if method == "pdf":
        redact_pdf(source, target, redactor, settings.get("keep-sizes") or [])
    elif method == "docx":
        redact_docx(source, target, redactor, settings.get("titles-after") or [])
    elif method == "transcript":
        redact_transcript(ROOT / "transcripts" / f"{doc['id']}.md", out / "transcripts" / f"{doc['id']}.md", target, redactor)
    else:
        raise ValueError(f"{doc['id']}: unknown redaction method {method!r}")


def _shape(concepts) -> list[tuple]:
    return [(c.name, c.title, tuple(sorted((k, str(v)) for k, v in c.position.items()))) for c in concepts]


def check_document(doc: dict, out: Path) -> list[str]:
    try:
        real, _ = assemble_document(doc, ROOT)
        redacted, warnings = assemble_document(doc, out)
    except (Skip, StaleTranscript, ValueError) as e:
        return [f"{doc['id']}: {e}"]
    problems = []
    real_shape, redacted_shape = _shape(real), _shape(redacted)
    if len(real) != len(redacted):
        problems.append(f"{doc['id']}: {len(real)} concepts, but {len(redacted)} from the redacted copy")
    real_by_name = {s[0]: s for s in real_shape}
    redacted_by_name = {s[0]: s for s in redacted_shape}
    for name in real_by_name.keys() - redacted_by_name.keys():
        problems.append(f"{doc['id']}: missing {name}")
    for name in redacted_by_name.keys() - real_by_name.keys():
        problems.append(f"{doc['id']}: extra {name}")
    for name in real_by_name.keys() & redacted_by_name.keys():
        a, b = real_by_name[name], redacted_by_name[name]
        if a[1] != b[1]:
            problems.append(f"{doc['id']}: {name} title {a[1]!r} became {b[1]!r}")
        if a[2] != b[2]:
            changed = sorted(set(a[2]) ^ set(b[2]))
            problems.append(f"{doc['id']}: {name} position differs: {changed}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Redact the source documents for the public repo.")
    parser.add_argument("--out", type=Path, help="the public repo (default: output in config/redaction.yml)")
    parser.add_argument("--only", action="append", help="a document id; may be repeated")
    parser.add_argument("--check", action="store_true", help="compare the redacted copies' concepts with the real ones")
    args = parser.parse_args(argv)

    settings = load_yaml(ROOT / "config" / "redaction.yml")
    out = (args.out or (ROOT / settings.get("output", "../RHDirectorAssistant"))).resolve()
    manifest = load_yaml(ROOT / "config" / "manifest.yml")
    problems = 0
    for doc in manifest.get("documents", []):
        if args.only and doc["id"] not in args.only:
            continue
        doc_settings = (settings.get("documents") or {}).get(doc["id"])
        if not doc_settings:
            print(f"skipped  {doc['id']}: no redaction settings")
            continue
        if args.check:
            found = check_document(doc, out)
            problems += len(found)
            print("\n".join(found) if found else f"matches  {doc['id']}")
        else:
            redact_document(doc, doc_settings, out)
            print(f"wrote    {doc['id']}: {doc['source']} ({doc_settings['method']})")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
