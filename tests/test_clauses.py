"""Tests for parse.clauses: unit boundaries, keys, heading context, front matter."""
from pathlib import Path

import yaml

from parse.clauses import parse_units
from parse.extract import Line, read_transcript

ROOT = Path(__file__).resolve().parent.parent
RULES = yaml.safe_load((ROOT / "config" / "parse-rules" / "articles.yml").read_text(encoding="utf-8"))


def parsed():
    _, lines = read_transcript(ROOT / "tests" / "fixtures" / "articles-snippet.md")
    return parse_units(lines, RULES)


def units():
    return {u.key: u for u in parsed().units}


def test_front_matter_ends_at_first_part():
    doc = parsed()
    assert [l.text for l in doc.front_matter] == ["Articles of Association", "Example Company Limited"]


def test_units_are_keyed_by_their_number():
    assert list(units()) == [("1",), ("2",), ("3",), ("4",)]


def test_units_record_the_headings_in_force():
    by_key = units()
    assert by_key[("1",)].headings == {
        "part": "Part 1 – Interpretation and objects of the RTM company",
        "section": None,
        "article-heading": "Defined terms",
    }
    assert by_key[("2",)].headings["section"] == "Name and objects"
    assert by_key[("2",)].headings["article-heading"] is None
    assert by_key[("3",)].headings["article-heading"] == "Chairing"
    assert by_key[("4",)].headings == {
        "part": "Part 6 – Directors’ indemnity",
        "section": None,
        "article-heading": "Indemnity",
    }


def test_unit_text_excludes_number_and_headings():
    by_key = units()
    assert by_key[("1",)].text_lines[0] == "(1) In the articles, unless the context requires otherwise:"
    assert by_key[("3",)].text_lines == [
        "(1) The directors may appoint a director to chair their meetings.",
        "(2) The person so appointed is known as the chairman.",
    ]
    assert by_key[("3",)].pages == [2]


def test_unit_number_and_filename_come_from_its_pattern():
    unit = units()[("4",)]
    assert unit.number == "4"
    assert unit.pattern.filename.format_map({"number": "04"}) == "article-04"
    assert unit.index == 3


def test_no_warnings_for_clean_input():
    assert parsed().warnings == []


SIZED_RULES = {
    "headings": [
        {
            "level": "chapter",
            "size": 32,
            "patterns": [
                {"match": r"^(?P<number>\d+)\s+(?P<title>.+)$", "display": "{number} {title}"},
                {"match": r"^(?P<title>Appendix [A-Z].*)$", "display": "{title}"},
            ],
        }
    ],
    "units": {
        "size": 16,
        "key": ["chapter", "section"],
        "patterns": [
            {"match": r"^(?P<chapter>\d+)\.(?P<section>\d+)\s+(?P<title>.+)$",
             "filename": "section-{chapter}-{section}", "title": "{chapter}.{section} {title}",
             "number": "{chapter}.{section}"},
            {"match": r"^(?P<chapter>B)(?P<section>\d+)\s+(?P<title>.+)$",
             "filename": "appendix-b-{section}", "title": "B{section} {title}", "number": "B{section}"},
        ],
        "heading-fallback": [
            {"level": "chapter", "match": "^Appendix", "filename": "{slug}", "title": "{chapter}", "number": ""},
        ],
    },
}

SIZED_LINES = [
    Line("5 Service charges", size=32, page=1),
    Line("5.1 Introduction", size=16, page=1),
    Line("Service charges are payable under the lease.", size=11, page=1),
    Line("5.2 Demands", size=16, page=2),
    Line("A demand must be in writing.", size=11, page=2),
    Line("Appendix B: Statutory rights", size=32, page=3),
    Line("B2 Names and addresses", size=16, page=3),
    Line("The landlord must notify the leaseholder.", size=11, page=3),
]


def test_units_found_by_font_size_and_several_patterns():
    doc = parse_units(SIZED_LINES, SIZED_RULES)
    keys = [u.key for u in doc.units]
    assert keys == [("5", "1"), ("5", "2"), ("b", "2")]  # keys are lower-case
    assert [u.number for u in doc.units] == ["5.1", "5.2", "B2"]
    assert doc.units[0].headings["chapter"] == "5 Service charges"
    assert doc.units[2].headings["chapter"] == "Appendix B: Statutory rights"
    assert doc.warnings == []


def test_text_under_a_heading_with_no_units_becomes_its_own_unit():
    lines = [
        Line("Appendix A: Lease variations", size=32, page=1),
        Line("A lease can be varied by agreement.", size=11, page=1),
    ]
    doc = parse_units(lines, SIZED_RULES)
    assert [u.key for u in doc.units] == [("appendix-a-lease-variations",)]
    assert doc.units[0].fields["chapter"] == "Appendix A: Lease variations"
    assert doc.warnings == []


AGREEMENT_RULES = {
    "headings": [
        {
            "level": "appendix",
            "size": 16,
            "match": r"^APPENDIX\s+(?P<number>\d+)$",
            "title-from-next-line": {"size": 13},
            "display": "Appendix {number} – {title}",
        },
        {
            "level": "clause",
            "size": 13,
            "match": r"^(?P<number>\d+)\.\s+(?P<title>.+)$",
            "display": "{number}. {title}",
        },
    ],
    "units": {
        "size": 10,
        "key": ["clause", "sub"],
        "patterns": [
            {"match": r"^(?P<clause>\d+)\.(?P<sub>\d+)\s+",
             "filename": "clause-{clause}-{sub}", "title": "Clause {clause}.{sub} – {clause_title}",
             "number": "{clause}.{sub}"},
        ],
        "heading-fallback": [
            {"level": "clause", "filename": "clause-{clause_number}",
             "title": "Clause {clause_number} – {clause_title}", "key": "{clause_number}"},
            {"level": "appendix", "filename": "appendix-{appendix_number}",
             "title": "Appendix {appendix_number} – {appendix_title}", "key": "appendix.{appendix_number}"},
        ],
    },
}

AGREEMENT_LINES = [
    Line("3. Services to be provided", size=13, page=1),
    Line("3.1 The Manager will perform the Services.", size=10, page=1),
    Line("16. Waiver", size=13, page=2),
    Line("No indulgence shown by either party.", size=10, page=2),
    Line("APPENDIX 1", size=16, page=3),
    Line("FEES", size=13, page=3),
    Line("The Management Fee is payable quarterly.", size=10, page=3),
]


def test_a_unit_can_use_the_parts_of_the_heading_above_it():
    doc = parse_units(AGREEMENT_LINES, AGREEMENT_RULES)
    sub_clause = doc.units[0]
    assert sub_clause.key == ("3", "1")
    assert sub_clause.fields["clause_title"] == "Services to be provided"
    assert sub_clause.pattern.title.format_map(sub_clause.fields) == "Clause 3.1 – Services to be provided"


def test_fallbacks_pick_the_deepest_heading_and_can_set_their_own_key():
    doc = parse_units(AGREEMENT_LINES, AGREEMENT_RULES)
    assert [u.key for u in doc.units] == [("3", "1"), ("16",), ("appendix", "1")]
    appendix = doc.units[2]
    assert appendix.fields["appendix_title"] == "FEES"  # display-case is not set here
    assert doc.warnings == []


def test_a_pattern_can_require_a_heading_level():
    rules = {
        "headings": [{"level": "schedule", "bold": True, "match": r"^The (?P<ordinal>\w+) Schedule$",
                      "display": "The {ordinal} Schedule"}],
        "units": {
            "key": ["para"],
            "patterns": [{"match": r"^(?P<para>\d+)\.\s+", "requires-heading": "schedule",
                          "filename": "schedule-{schedule_ordinal_lower}-{para}", "title": "{para}",
                          "key": "schedule.{schedule_ordinal}.{para}"}],
        },
    }
    lines = [
        Line("1. Before any schedule, not a paragraph.", page=1),
        Line("The First Schedule", bold=True, page=1),
        Line("1. Of support and shelter.", page=1),
    ]
    doc = parse_units(lines, rules)
    assert [u.key for u in doc.units] == [("schedule", "first", "1")]
    assert doc.warnings == ["page 1: text outside any unit: '1. Before any schedule, not a paragraph.'"]
