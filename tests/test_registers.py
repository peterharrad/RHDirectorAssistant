"""Tests for parse.registers: entry fields and the schedule of notices of leases."""
from parse.registers import ENTRY_START, Entry


def test_an_entry_number_may_have_no_date():
    assert ENTRY_START.match("6").group("date") is None
    assert ENTRY_START.match("7 2001-07-17").group("date") == "2001-07-17"
    assert ENTRY_START.match("3.1 Not for 21 years") is None  # quoted deed clauses are not entries


def test_a_schedule_row_is_all_fields_with_an_optional_note():
    row = Entry(72, None, [
        "Registration Date : 01.01.2000",
        "Property Description : 99 Example House",
        "NOTE: See entry in the Charges Register",
    ])
    assert row.fields == {
        "Registration Date": "01.01.2000",
        "Property Description": "99 Example House",
        "Note": "NOTE: See entry in the Charges Register",
    }


def test_an_ordinary_entry_is_not_a_schedule_row():
    entry = Entry(2, "2006-01-05", ["Short particulars of the lease(s):", "Term : 999 years from 1 October 2001"])
    assert entry.fields is None
