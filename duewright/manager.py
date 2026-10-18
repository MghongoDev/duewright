"""The rules that operate on tasks.

This module never reads input, prints, or touches the disk, so every rule
here can be tested on its own.
"""

from datetime import date
from typing import Optional

from duewright.models import Task


class TaskNotFoundError(Exception):
    """Raised when no task carries the id that was asked for."""


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


class TaskManager:
    """Holds the tasks in memory and applies changes to them."""

    def __init__(self, tasks: Optional[list[Task]] = None, next_id: int = 1) -> None:
        self.tasks: list[Task] = list(tasks) if tasks else []
        self.next_id = next_id

    def add(
        self,
        title: str,
        priority: str = "medium",
        due_date: Optional[date] = None,
    ) -> Task:
        """Create a task, give it the next id, and return it."""
        task = Task(title=title, id=self.next_id, priority=priority, due_date=due_date)
        self.next_id += 1
        self.tasks.append(task)
        return task

    def get(self, task_id: int) -> Task:
        """Return the task with this id, or raise TaskNotFoundError."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        raise TaskNotFoundError(f"no task with id {task_id}")

    def update_title(self, task_id: int, title: str) -> Task:
        """Replace a task's title and return the task."""
        task = self.get(task_id)
        task.title = title
        return task

    def toggle_done(self, task_id: int) -> Task:
        """Flip a task's done flag and return the task."""
        task = self.get(task_id)
        task.done = not task.done
        return task

    def delete(self, task_id: int) -> None:
        """Remove a task. The id is not handed out again."""
        self.tasks.remove(self.get(task_id))

    def all(self) -> list[Task]:
        """Return a copy of the tasks in the order they were added.

        This is the order the file stores, which is not the order the list
        shows.
        """
        return list(self.tasks)

    def list_tasks(
        self,
        done: Optional[bool] = None,
        query: Optional[str] = None,
    ) -> list[Task]:
        """Return the tasks in display order, filtered by state and keyword.

        A done of None means every task, False means pending only and True
        means done only. The query matches the title, ignoring case.
        """
        tasks = [task for task in self.tasks if done is None or task.done is done]
        if query:
            needle = query.casefold()
            tasks = [task for task in tasks if needle in task.title.casefold()]
        return sorted(tasks, key=sort_key)

    def summary(self, today: Optional[date] = None) -> str:
        """Return a line describing the whole list, not a filtered view."""
        today = today or date.today()
        pending = sum(1 for task in self.tasks if not task.done)
        done = sum(1 for task in self.tasks if task.done)
        overdue = sum(1 for task in self.tasks if is_overdue(task, today))
        return f"{pending} pending, {overdue} overdue, {done} done"
