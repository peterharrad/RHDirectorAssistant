"""Tests for parse.definitions: quoted-term definition clauses."""
from parse.definitions import parse_definitions

TERM = r'^[“"](?P<term>[^”"]+)[”"]'
ENDS = r"^\(\d+\)\s"

LINES = [
    "(1) In the articles, unless the context requires otherwise:",
    "“articles” means the company’s articles of association;",
    "“immediate landlord” in relation to a unit, means the person who:",
    "(a) if the unit is subject to a lease, is the landlord under the lease;",
    "“chairman” has the meaning given in article 3;",
    "(2) Other words bear the same meaning as in the Companies Act 2006.",
]


def test_terms_intro_and_notes():
    result = parse_definitions(LINES, TERM, ENDS)
    assert [d.term for d in result.definitions] == ["articles", "immediate landlord", "chairman"]
    assert result.intro == [LINES[0]]
    assert result.notes == [LINES[5]]


def test_continuation_lines_stay_with_their_term():
    result = parse_definitions(LINES, TERM, ENDS)
    assert result.definitions[1].lines == LINES[2:4]
