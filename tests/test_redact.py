"""Tests for redact.text: what is kept and what becomes lorem ipsum."""
from redact.main import rule_patterns
from redact.text import LOREM, Redactor

LOREM_WORDS = set(LOREM)


def words(text: str) -> list[str]:
    return [w.strip(".,;:()'’").lower() for w in text.split()]


def test_numbering_and_punctuation_are_kept_and_words_are_not():
    out = Redactor().line("2.1 Words importing one gender shall include any other gender.")
    assert out.startswith("2.1 ")
    assert out.endswith(".")
    assert all(w in LOREM_WORDS for w in words(out)[1:])


def test_defined_terms_and_cross_references_are_kept():
    r = Redactor(keep=[r"(?i)\bclause\s+\d+(?:\.\d+)?"], terms=["Maintained Property", "Lessee"])
    out = r.line("the Lessee's covenants in clause 7.10 about the Maintained Property.")
    assert "Lessee's" in out
    assert "clause 7.10" in out
    assert "Maintained Property." in out
    assert "covenants" not in out


def test_digits_become_zeros_and_years_are_not_numbering():
    out = Redactor().line("2015 Lease dated 15.04.2011 for £1,250")
    assert out.startswith("0000 ")
    assert "00.00.0000" in out and "£0,000" in out


def test_a_kept_label_does_not_keep_what_runs_on_from_it():
    r = Redactor(keep=[r"^(?P<term>[A-Z][^:]{1,60}):\s"])
    out = r.line("Signature: .J.o.h.n.(Jul 11, 2025)")
    assert out.startswith("Signature: ")
    assert "J.o.h.n" not in out and "Jul" not in out


def test_capitals_are_kept():
    out = Redactor().line("NOTE: Copy filed")
    assert out.split()[0].isupper() and out.split()[1][0].isupper()


def test_parse_rules_supply_what_must_be_kept():
    rules = {
        "extract": {"drop": ["^Footer"], "skip-pages": [{"page": 10, "expect": "Signed (1)"}]},
        "back-matter": {"starts-at": "^IN WITNESS"},
        "definitions": [{"after-text": "In this Deed", "skip-terms": ["PARTICULARS"]}],
        "cross-references": ["(?i)clause (\\d+)", {"match": "(?i)paragraph (\\d+)"}],
    }
    patterns = rule_patterns(rules)
    assert "^Footer" in patterns and "^IN WITNESS" in patterns
    assert r"Signed\ \(1\)" in patterns and "In\\ this\\ Deed" in patterns
    assert "(?i)paragraph (\\d+)" in patterns
