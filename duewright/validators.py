"""Pure functions that check and clean what the user typed.

Each function either returns a clean value or raises ValueError with a message
the menu can show. Nothing here reads input or prints, which is what makes
these rules easy to test.
"""

MAX_TITLE_LENGTH = 100

YES_ANSWERS = {"y", "yes"}
NO_ANSWERS = {"n", "no"}


def clean_title(text: str) -> str:
    """Return a trimmed title, or raise ValueError when it cannot be used."""
    title = text.strip()
    if not title:
        raise ValueError("A title is required.")
    if len(title) > MAX_TITLE_LENGTH:
        raise ValueError(f"A title can be at most {MAX_TITLE_LENGTH} characters.")
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
