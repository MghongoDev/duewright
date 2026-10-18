"""A repository that keeps the tasks in memory.

The tests use it, and it keeps the interface honest: if a behaviour cannot be
expressed here, it does not belong in the interface.
"""

from typing import Optional

from duewright.errors import TaskNotFoundError
from duewright.models import Task
from duewright.repositories.base import matches, page_of, sort_key


class InMemoryTaskRepository:
    """Holds the tasks in a dictionary, with a counter for the next id."""

    def __init__(self) -> None:
        self._tasks: dict[int, Task] = {}
        self._next_id = 1

    def list_tasks(
        self,
        done: Optional[bool] = None,
        query: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> tuple[list[Task], int]:
        """Return one page of the tasks that match, in display order, and the total."""
        matched = [task for task in self._tasks.values() if matches(task, done, query)]
        return page_of(sorted(matched, key=sort_key), limit, offset)

    def get(self, task_id: int) -> Task:
        """Return one task, or raise TaskNotFoundError."""
        task = self._tasks.get(task_id)
        if task is None:
            raise TaskNotFoundError(f"no task with id {task_id}")
        return task

    def add(self, task: Task) -> Task:
        """Store a new task, give it the next id, and return it."""
        task.id = self._next_id
        self._next_id += 1
        self._tasks[task.id] = task
        return task

    def update(self, task: Task) -> Task:
        """Store a changed task, or raise TaskNotFoundError."""
        if task.id not in self._tasks:
            raise TaskNotFoundError(f"no task with id {task.id}")
        self._tasks[task.id] = task
        return task

    def delete(self, task_id: int) -> None:
        """Remove a task, or raise TaskNotFoundError."""
        if task_id not in self._tasks:
            raise TaskNotFoundError(f"no task with id {task_id}")
        del self._tasks[task_id]
