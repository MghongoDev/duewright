"""Tests for the input validators."""

import pytest

from duewright.validators import clean_title, parse_task_id, parse_yes_no


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Buy milk", "Buy milk"),
        ("  Buy milk  ", "Buy milk"),
        ("Buy café ☕", "Buy café ☕"),
        ("x" * 100, "x" * 100),
    ],
)
def test_clean_title_accepts(text, expected):
    assert clean_title(text) == expected


@pytest.mark.parametrize("text", ["", "   ", "\t\n", "x" * 101, "x" * 500])
def test_clean_title_rejects(text):
    with pytest.raises(ValueError):
        clean_title(text)


@pytest.mark.parametrize(
    ("text", "expected"),
    [("1", 1), ("42", 42), (" 42 ", 42), ("99999999999999999999", 99999999999999999999)],
)
def test_parse_task_id_accepts(text, expected):
    assert parse_task_id(text) == expected


@pytest.mark.parametrize("text", ["", "abc", "1.5", "-1", "0", "1 2", "0x10"])
def test_parse_task_id_rejects(text):
    with pytest.raises(ValueError):
        parse_task_id(text)


@pytest.mark.parametrize("text", ["y", "Y", "yes", "YES", " yes "])
def test_parse_yes_no_accepts_yes(text):
    assert parse_yes_no(text) is True


@pytest.mark.parametrize("text", ["n", "N", "no", "NO", " no "])
def test_parse_yes_no_accepts_no(text):
    assert parse_yes_no(text) is False


@pytest.mark.parametrize("text", ["", "maybe", "yep", "1", "0", "no thanks"])
def test_parse_yes_no_rejects(text):
    with pytest.raises(ValueError):
        parse_yes_no(text)
