"""Tests for parse.extract and the description fallback."""
from assemble import first_sentence
from parse.extract import markdown_table, parse_transcript_lines


def test_transcript_lines_carry_bold_and_page():
    lines = parse_transcript_lines("<!-- page 3 -->\n**PART 2**\n8. Subject to the articles.\n")
    assert [(l.text, l.bold, l.page) for l in lines] == [
        ("PART 2", True, 3),
        ("8. Subject to the articles.", False, 3),
    ]


def test_markdown_table_uses_the_first_row_as_the_header():
    table = markdown_table([["Item", "From whom"], ["Information sheet", "Estate\nagent"], [None, None]])
    assert table.splitlines() == [
        "| Item | From whom |",
        "|---|---|",
        "| Information sheet | Estate agent |",
    ]


def test_first_sentence_skips_bullets_and_tables():
    lines = ["| a | b |", "• a bullet point that is quite long but still only a bullet",
             "The landlord must notify the leaseholder of an address in England. Failure to do this matters."]
    assert first_sentence(lines) == "The landlord must notify the leaseholder of an address in England."


def test_first_sentence_ignores_an_early_full_stop():
    text = ["You must comply with the Data Protection Act 2018 s. 4 and the UK GDPR when handling personal data."]
    assert first_sentence(text) == text[0]
