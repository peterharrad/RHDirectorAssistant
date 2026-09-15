"""Tests for parse.docx_reader: Word's automatic numbering is put back into the text.

They check numbers and headings only, not the wording, so they pass on the redacted copy
of the lease in the public repo as well as on the real one.
"""
import re
from pathlib import Path

import pytest

from parse.docx_reader import docx_lines

LEASE = Path(__file__).resolve().parent.parent / "sources" / "RiversideHouse-IndividualLease.docx"
SCHEDULE = re.compile(r"^THE [A-Z]+ SCHEDULE$")


@pytest.fixture(scope="module")
def lines():
    if not LEASE.exists():
        pytest.skip("individual lease not present")
    return [line.text for line in docx_lines(LEASE, {})]


def starts(lines, prefix):
    return any(text.startswith(prefix) for text in lines)


def schedule(lines, heading):
    """The lines of one schedule, from its heading up to the next schedule's."""
    start = lines.index(heading)
    end = next((i for i in range(start + 1, len(lines)) if SCHEDULE.match(lines[i])), len(lines))
    return lines[start:end]


def test_clause_numbers_come_from_the_heading_styles(lines):
    # an empty Heading 1 paragraph at the top takes number 1, so the first clause is 2
    assert starts(lines, "2 INTERPRETATIONS")
    assert starts(lines, "7 AGREEMENTS AND DECLARATIONS")
    assert starts(lines, "7.11 ") and starts(lines, "7.12 ")


def test_a_schedule_list_restarts_and_its_sub_paragraphs_follow_it(lines):
    numbered = [t.split()[0] for t in schedule(lines, "THE SECOND SCHEDULE") if re.match(r"^\d", t)]
    assert numbered[:2] == ["1", "1.1"]


def test_unnumbered_paragraphs_have_no_label(lines):
    sixth = schedule(lines, "THE SIXTH SCHEDULE")
    assert not re.match(r"^\d", sixth[1])  # the schedule's title
    parts = [i for i, t in enumerate(sixth) if t.startswith("PART")]
    assert len(parts) > 1
    assert not re.match(r"^\d", sixth[parts[1] + 1])  # Part B's title
    assert not re.match(r"^\d", sixth[parts[1] + 2])  # its single unnumbered paragraph
