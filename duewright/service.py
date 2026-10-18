"""The rules that operate on tasks.

The service asks a repository to store things. It never touches a file, so
every rule here can be tested on its own.
"""

from datetime import date
from typing import Optional

from duewright.models import Task
from duewright.repositories.base import TaskRepository

# The order the display puts priorities in, best first.
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def sort_key(task: Task) -> tuple:
    """Return the key that orders the list.

    Pending tasks first, then tasks that carry a due date, earliest due date
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


def is_overdue(task: Task, today: date) -> bool:
    """Return True when a pending task's due date is before today.

    A task due today is not overdue, and a done task is never overdue.
    """
    return not task.done and task.due_date is not None and task.due_date < today


def is_due_today(task: Task, today: date) -> bool:
    """Return True when a pending task is due today."""
    return not task.done and task.due_date == today


class TaskService:
    """Holds the rules and asks a repository to keep the results."""

    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    def add(
        self,
        title: str,
        priority: str = "medium",
        due_date: Optional[date] = None,
    ) -> Task:
        """Create a task, let the repository give it an id, and return it."""
        return self.repository.add(Task(title=title, priority=priority, due_date=due_date))

    def get(self, task_id: int) -> Task:
        """Return the task with this id, or raise TaskNotFoundError."""
        return self.repository.get(task_id)

    def update_title(self, task_id: int, title: str) -> Task:
        """Replace a task's title and return the task."""
        task = self.repository.get(task_id)
        task.title = title
        return self.repository.update(task)

    def toggle_done(self, task_id: int) -> Task:
        """Flip a task's done flag and return the task."""
        task = self.repository.get(task_id)
        task.done = not task.done
        return self.repository.update(task)

    def delete(self, task_id: int) -> None:
        """Remove a task. The id is not handed out again."""
        self.repository.delete(task_id)

    def list_tasks(
        self,
        done: Optional[bool] = None,
        query: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> tuple[list[Task], int]:
        """Return one page of the tasks in display order, and how many matched.

        The repository hands back the filtered tasks in the order they were
        added, and the ordering and the paging happen here, in Python. That is
        fine at this scale, and a store holding hundreds of thousands of tasks
        would do both in the store instead.
        """
        matched = self.repository.list_tasks(done=done, query=query)
        ordered = sorted(matched, key=sort_key)
        total = len(ordered)
        if limit is None:
            return ordered[offset:], total
        return ordered[offset : offset + limit], total

    def summary(self, today: Optional[date] = None) -> str:
        """Return a line describing the whole list, not a filtered view."""
        today = today or date.today()
        tasks = self.repository.list_tasks()
        pending = sum(1 for task in tasks if not task.done)
        done = sum(1 for task in tasks if task.done)
        overdue = sum(1 for task in tasks if is_overdue(task, today))
        return f"{pending} pending, {overdue} overdue, {done} done"
