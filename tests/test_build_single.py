"""Single files: section layout, and a golden test against the committed single-files/."""
import pytest

from assemble import Concept
from build_single import OUTPUT, ROOT, Section, build, compare, concept_section, render_section


def test_section_has_heading_then_fields_then_body():
    concept = Concept(
        name="article-17",
        title="Article 17 – Chairing",
        body=["See [article 26](ref:article-26)."],
        description="Directors may appoint a chairman.",
        position={"part": "Part 2", "article_number": 17, "source_pages": [5]},
    )
    assert render_section(concept_section(concept)) == (
        '<a id="article-17"></a>\n\n'
        "# Article 17 – Chairing\n\n"
        "- title: Article 17 – Chairing\n"
        "- description: Directors may appoint a chairman.\n"
        "- article_number: 17\n\n"
        "See [article 26](#article-26)."
    )


def test_reference_lists_and_empty_values():
    section = Section("clause-04", "Clause 4", [], reference={"clause_numbers": [4, "4.1"]})
    assert "- clause_numbers: 4, 4.1" in render_section(section)
    concept = Concept(name="schedule-second", title="Second Schedule", body=[], position={"clause_number": ""})
    assert concept_section(concept).reference == {}


def test_build_has_no_errors():
    assert build(ROOT).errors == []


def test_single_files_match_committed():
    folder = ROOT / OUTPUT
    if not folder.exists():
        pytest.skip("single-files/ has not been built yet")
    assert compare(build(ROOT).files, folder) == [], "run rh-build-single and review the changes in single-files/"


def test_authored_section_describing_an_image_is_left_out(tmp_path):
    from build_single import authored_sections

    folder = tmp_path / "authored" / "building"
    folder.mkdir(parents=True)
    (folder / "plan.md").write_text(
        "---\ntitle: Plan\n---\n# Plan\n\nFacts.\n\n## Diagram\n\n![plan](plan.png)\n\nLegend.\n\n"
        "## More\n\nSee [notes](/building/notes.md).\n",
        encoding="utf-8",
    )
    sections, _, warnings = authored_sections(folder)
    assert sections[0].body == ["Facts.\n\n## More\n\nSee [notes](#notes)."]
    assert warnings == ["authored/building/plan.md: left out ## Diagram"]
