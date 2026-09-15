"""Tests for assemble: concepts carry no file format, and each writer resolves references."""
from build_okf import resolve_references, concept_file
from assemble import Concept


def test_references_name_a_concept_not_a_file():
    concept = Concept(name="clause-07-12", title="Clause 7.12", body=["pursuant to [Clause 7.10](ref:clause-07-10)"])
    assert "ref:clause-07-10" in concept.body[0]
    assert "/" not in concept.body[0].split("ref:")[1]


def test_the_okf_writer_turns_references_into_bundle_paths():
    text = "see [Clause 7.10](ref:clause-07-10) and [Clause 7.11](ref:clause-07-11)"
    assert resolve_references(text, "leases/sample-lease") == (
        "see [Clause 7.10](/leases/sample-lease/clause-07-10.md) and [Clause 7.11](/leases/sample-lease/clause-07-11.md)"
    )


def test_the_okf_writer_puts_the_title_above_the_body():
    doc = {"id": "d", "concept-type": "lease clause", "description": "D", "author": "A", "last-modified": "2026-01-01"}
    out = concept_file(Concept(name="clause-03", title="Clause 3 – Demise", body=["IN consideration"]), doc, "leases/d")
    assert out.path == "leases/d/clause-03.md"
    assert out.content.split("---\n\n", 1)[1] == "# Clause 3 – Demise\n\nIN consideration\n"
