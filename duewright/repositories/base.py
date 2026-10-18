"""The interface a task repository has to satisfy."""

from typing import Optional, Protocol

from duewright.models import Task


class TaskRepository(Protocol):
    """What the service needs from whatever holds the tasks.

    An implementation does not inherit from this. It only has to provide these
    methods with these signatures, and the type checker will accept it as
    satisfying the interface.
    """

    def list_tasks(self, done: Optional[bool] = None, query: Optional[str] = None) -> list[Task]:
        """Return the tasks that match, in the order they were added.

        A done of None means every task, False means pending only and True
        means done only. The query matches the title, ignoring case.
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
