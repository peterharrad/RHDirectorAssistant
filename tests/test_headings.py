"""Tests for parse.headings: level replacement and clearing of lower levels."""
from parse.extract import Line
from parse.headings import HeadingRule, HeadingState, classify, sentence_case


def test_new_heading_clears_lower_levels():
    state = HeadingState(["part", "section", "heading"])
    state.set("part", "Part 1")
    state.set("section", "Objects")
    state.set("heading", "Defined terms")
    state.set("part", "Part 2")
    assert state.values == {"part": "Part 2", "section": None, "heading": None}


def test_next_unit_only_level_is_used_once():
    state = HeadingState(["section", "heading"], next_unit_only=["heading"])
    state.set("section", "Voting")
    state.set("heading", "Poll votes")
    assert state.take()[0] == {"section": "Voting", "heading": "Poll votes"}
    assert state.take()[0] == {"section": "Voting", "heading": None}


def test_heading_parts_are_available_to_the_units_below():
    state = HeadingState(["clause"])
    state.set("clause", "3. Services", {"number": "3", "title": "Services"})
    values, fields = state.take()
    assert values == {"clause": "3. Services"}
    assert fields == {
        "clause_number": "3",
        "clause_number_lower": "3",
        "clause_title": "Services",
        "clause_title_lower": "services",  # lower-case forms are for filenames
    }


def test_sentence_case_keeps_acronyms():
    assert sentence_case("NAME AND OBJECTS OF RTM COMPANY", ["RTM"]) == "Name and objects of RTM company"
    assert sentence_case("DIRECTORS’ POWERS AND RESPONSIBILITIES") == "Directors’ powers and responsibilities"


RULES = [
    HeadingRule.from_config({"level": "part", "match": r"^PART\s+(?P<number>\d+)\b\s*(?P<title>.*)$",
                             "bold": True, "title-from-next-line": True, "display": "Part {number} – {title}"}),
    HeadingRule.from_config({"level": "section", "bold": True, "case": "upper", "max-words": 15}),
    HeadingRule.from_config({"level": "heading", "bold": True, "case": "mixed", "max-words": 15}),
]


def test_part_title_on_next_line():
    h = classify(Line("PART 2", True), Line("DIRECTORS", True), RULES, display_case="sentence")
    assert (h.level, h.value, h.consumed) == ("part", "Part 2 – Directors", 1)


def test_part_title_on_same_line():
    h = classify(Line("PART 6 DIRECTORS’ INDEMNITY", True), Line("Indemnity", True), RULES, display_case="sentence")
    assert (h.level, h.value, h.consumed) == ("part", "Part 6 – Directors’ indemnity", 0)


def test_style_decides_section_or_heading():
    assert classify(Line("VOTING AT GENERAL MEETINGS", True), None, RULES).level == "section"
    assert classify(Line("Poll votes", True), None, RULES).level == "heading"
    assert classify(Line("Poll votes", False), None, RULES) is None
