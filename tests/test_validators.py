"""Tests for the input validators."""

from datetime import date

import pytest

from duewright.validators import (
    CLEAR,
    clean_title,
    parse_due_date,
    parse_due_date_edit,
    parse_priority,
    parse_state,
    parse_task_id,
    parse_yes_no,
)


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


@pytest.mark.parametrize(
    ("text", "expected"),
    [("low", "low"), ("HIGH", "high"), (" Medium ", "medium")],
)
def test_parse_priority_accepts(text, expected):
    assert parse_priority(text) == expected


@pytest.mark.parametrize("text", ["", "urgent", "1", "med", "high priority"])
def test_parse_priority_rejects(text):
    with pytest.raises(ValueError):
        parse_priority(text)


@pytest.mark.parametrize(
    ("text", "expected"),
    [("2026-10-05", date(2026, 10, 5)), (" 2026-10-05 ", date(2026, 10, 5))],
)
def test_parse_due_date_accepts(text, expected):
    assert parse_due_date(text) == expected


@pytest.mark.parametrize("text", ["", "   "])
def test_parse_due_date_treats_a_blank_answer_as_none(text):
    assert parse_due_date(text) is None


@pytest.mark.parametrize("text", ["05/10/2026", "2026-13-45", "tomorrow", "2026-10"])
def test_parse_due_date_rejects(text):
    with pytest.raises(ValueError):
        parse_due_date(text)


@pytest.mark.parametrize(
    ("text", "expected"),
    [("all", "all"), ("Pending", "pending"), (" done ", "done")],
)
def test_parse_state_accepts(text, expected):
    assert parse_state(text) == expected


@pytest.mark.parametrize("text", ["", "open", "finished", "everything"])
def test_parse_state_rejects(text):
    with pytest.raises(ValueError):
        parse_state(text)


def test_an_edit_asks_for_a_date_the_same_way_adding_does():
    assert parse_due_date_edit("2026-11-01") == date(2026, 11, 1)


def test_none_clears_a_due_date_on_an_edit():
    assert parse_due_date_edit("none") is CLEAR
    assert parse_due_date_edit("NONE") is CLEAR


def test_an_edit_still_refuses_a_date_it_cannot_read():
    with pytest.raises(ValueError):
        parse_due_date_edit("the fifth")


def test_an_edit_does_not_read_a_blank_as_clearing():
    """A blank answer means keep, so the function refuses it rather than clearing."""
    with pytest.raises(ValueError):
        parse_due_date_edit("   ")
