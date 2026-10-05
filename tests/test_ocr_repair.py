"""Tests for the OpenCodeReview-derived comment args repair engine."""

from __future__ import annotations

import pytest

from devlensx.review.repair import (
    has_odd_quotes,
    has_suspect_truncation,
    parse_and_repair_comments,
    repair_serialized_comments,
    repair_trailing_commas_and_brackets,
    repaired_comments_acceptable,
)


def test_repair_clean_json():
    clean = '[{"content": "Looks good", "path": "main.py", "category": "logic"}]'
    comments, meta = parse_and_repair_comments(clean)
    assert len(comments) == 1
    assert comments[0]["content"] == "Looks good"
    assert comments[0]["path"] == "main.py"
    assert meta["repaired"] is False


def test_repair_unescaped_prose_quotes():
    # LLM forgot to escape internal quotes: "content": "You should use "sys.exit(1)" instead."
    raw = '[{"content": "You should use "sys.exit(1)" instead.", "path": "cli.py"}]'
    comments, meta = parse_and_repair_comments(raw)
    assert len(comments) == 1
    assert 'sys.exit(1)' in comments[0]["content"]
    assert meta["repaired"] is True
    assert meta["escaped_chars"] >= 2


def test_repair_illegal_backslashes():
    # Illegal backslash \d and windows path C:\Users
    raw = '[{"content": "Regex pattern \\d+ failed in C:\\Users\\app\\test.py", "path": "test.py"}]'
    comments, meta = parse_and_repair_comments(raw)
    assert len(comments) == 1
    assert "test.py" in comments[0]["path"]
    assert meta["repaired"] is True


def test_repair_trailing_commas_and_unclosed_brackets():
    raw = '{"comments": [{"content": "Fix null check", "path": "foo.go",},],}'
    comments, meta = parse_and_repair_comments(raw)
    assert len(comments) == 1
    assert comments[0]["content"] == "Fix null check"
    assert meta["repaired"] is True


def test_repair_markdown_code_fence():
    raw = """Here are the review findings:
```json
[
  {
    "content": "Potential goroutine leak: ticker is never stopped.",
    "path": "server.go",
    "category": "concurrency"
  }
]
```
Please let me know if you need anything else!"""
    comments, meta = parse_and_repair_comments(raw)
    assert len(comments) == 1
    assert "Potential goroutine leak" in comments[0]["content"]


def test_has_odd_quotes():
    assert has_odd_quotes('This is "quoted"') is False
    assert has_odd_quotes('This is "cut short') is True
    assert has_odd_quotes('Escaped \\"quote\\" is fine') is False


def test_has_suspect_truncation():
    # Odd quotes indicates truncation
    valid_batch = [{"content": 'Check "foo" and "bar"'}]
    truncated_batch = [{"content": 'Check "foo and'}]
    assert has_suspect_truncation(valid_batch) is False
    assert has_suspect_truncation(truncated_batch) is True


def test_repaired_comments_acceptable():
    entries = [{"content": "Good finding", "path": "a.py"}]
    assert repaired_comments_acceptable(entries, '"content": "Good finding"') is True
    # Unknown field must fail
    bad_field_entries = [{"content": "Good finding", "unknown_bogus_field": 123}]
    assert repaired_comments_acceptable(bad_field_entries, '"content": "..."') is False
