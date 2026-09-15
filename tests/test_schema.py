"""Tests for validate.schema: required fields and snake_case field names."""
from validate.schema import check

GOOD = """---
type: articles clause
title: Article 17
article_number: 17
sources:
- id: articles
  last_modified: '2026-05-28'
---
Body
"""


def test_valid_concept_passes():
    assert check({"articles/article-17.md": GOOD}, set()) == []


def test_non_snake_case_fields_are_reported_at_any_depth():
    bad = GOOD.replace("article_number", "article-number").replace("last_modified", "last-modified")
    assert check({"a.md": bad}, set()) == [
        "a.md: field article-number is not snake_case",
        "a.md: field sources.last-modified is not snake_case",
    ]


def test_missing_type_and_title_are_reported():
    assert check({"a.md": "---\narticle_number: 1\n---\n"}, set()) == ["a.md: missing type", "a.md: missing title"]


def test_index_and_log_are_not_concepts():
    assert check({"index.md": "# Index\n", "articles/log.md": "# Log\n"}, set()) == []
