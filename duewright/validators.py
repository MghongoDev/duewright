"""Pure functions that check and clean what the user typed.

Each function either returns a clean value or raises a ValueError carrying a
message the menu can show. The two that decide what a task means raise
InvalidTaskError, which is a ValueError as well, so the menu still catches one
kind of error while the API can map that one onto a 422.
"""

from datetime import date
from typing import Any, Optional

from duewright.errors import InvalidTaskError
from duewright.models import PRIORITIES

MAX_TITLE_LENGTH = 100

YES_ANSWERS = {"y", "yes"}
NO_ANSWERS = {"n", "no"}

STATES = ("all", "pending", "done")

CLEAR_ANSWERS = {"none", "clear"}

# What an answer of none means while a due date is being changed:
# clear it.
CLEAR = object()


def clean_title(text: str) -> str:
    """Return a trimmed title, or raise InvalidTaskError when it cannot be used."""
    title = text.strip()
    if not title:
        raise InvalidTaskError("A title is required.")
    if len(title) > MAX_TITLE_LENGTH:
        raise InvalidTaskError(f"A title can be at most {MAX_TITLE_LENGTH} characters.")
    return title


def parse_task_id(text: str) -> int:
    """Return a task id, or raise ValueError when it is not a whole number of 1 or more."""
    try:
        task_id = int(text.strip())
    except ValueError:
        raise ValueError("A task id is a whole number.") from None
    if task_id < 1:
        raise ValueError("A task id is 1 or more.")
    return task_id


def parse_yes_no(text: str) -> bool:
    """Return True for yes and False for no, or raise ValueError for anything else."""
    answer = text.strip().lower()
    if answer in YES_ANSWERS:
        return True
    if answer in NO_ANSWERS:
        return False
    raise ValueError("Please answer y or n.")


def parse_priority(text: str) -> str:
    """Return low, medium or high, or raise InvalidTaskError for anything else."""
    priority = text.strip().lower()
    if priority not in PRIORITIES:
        raise InvalidTaskError("Priority is low, medium or high.")
    return priority


def parse_due_date(text: str) -> Optional[date]:
    """Return a due date, None for a blank answer, or raise ValueError."""
    answer = text.strip()
    if not answer:
        return None
    try:
        return date.fromisoformat(answer)
    except ValueError:
        raise ValueError("Use YYYY-MM-DD, for example 2026-10-05.") from None


def parse_due_date_edit(text: str) -> Any:
    """Return the date an edit asks for, CLEAR to remove it, or raise ValueError.

    A blank answer never reaches this function. The menu reads a blank
    answer as keeping what is there, which is the rule the API applies to a
    field left out of a request, so only a word can ask for the date to go.
    """
    answer = text.strip()
    if not answer:
        raise ValueError("A blank answer keeps the due date. Answer none to clear it.")
    if answer.lower() in CLEAR_ANSWERS:
        return CLEAR
    return parse_due_date(answer)


def parse_state(text: str) -> str:
    """Return all, pending or done, or raise ValueError for anything else."""
    state = text.strip().lower()
    if state not in STATES:
        raise ValueError("Show all, pending or done.")
    return state
