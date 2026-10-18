"""The interface a task repository has to satisfy.

The rules that decide the display order and the search live here, beside
the interface, so the stores that filter in Python share one of each. A
store that orders and filters in its own query has to produce the same
results, which the contract suite checks against every implementation.
"""

from datetime import date
from typing import Optional, Protocol

from duewright.models import Task

# The order the display puts priorities in, best first.
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def sort_key(task: Task) -> tuple:
    """Return the key that orders the list.

    Pending Tasks first, then Tasks that carry a due date, earliest due date
    first, then higher priority, then lower id. Python compares the tuple
    element by element, so the order of this tuple is the order of the list.
    """
    return (
        task.done,
        task.due_date is None,
        task.due_date or date.max,
        PRIORITY_ORDER.get(task.priority, PRIORITY_ORDER["medium"]),
        task.id or 0,
    )


def matches(task: Task, done: Optional[bool], query: Optional[str]) -> bool:
    """Return True when a Task passes the filter and the search.

    The search folds case with casefold, so text outside ASCII matches the
    way a reader expects. A store that filters in its own query has to fold
    the same way.
    """
    if done is not None and task.done is not done:
        return False
    return not query or query.casefold() in task.title.casefold()


def page_of(tasks: list[Task], limit: Optional[int], offset: int) -> tuple[list[Task], int]:
    """Return the page asked for, and how many Tasks matched in total."""
    total = len(tasks)
    if limit is None:
        return tasks[offset:], total
    return tasks[offset : offset + limit], total


class TaskRepository(Protocol):
    """What the service needs from whatever holds the tasks.

    An implementation does not inherit from this. It only has to provide these
    methods with these signatures, and the type checker will accept it as
    satisfying the interface.
    """

    def list_tasks(
        self,
        done: Optional[bool] = None,
        query: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> tuple[list[Task], int]:
        """Return one page of the Tasks that match, in display order, and the total.

        A done of None means every Task, False means pending only and True
        means done only. The query matches the title, ignoring case. The page
        starts at the offset and holds at most limit Tasks, and a limit of None
        means every Task from the offset on. The count is of every Task that
        matched rather than of the page.
        """
        ...

    def get(self, task_id: int) -> Task:
        """Return one task, or raise TaskNotFoundError."""
        ...

    def add(self, task: Task) -> Task:
        """Store a new task, give it an id, and return it."""
        ...

    def update(self, task: Task) -> Task:
        """Store a changed task, or raise TaskNotFoundError."""
        ...

    def delete(self, task_id: int) -> None:
        """Remove a task, or raise TaskNotFoundError."""
        ...
