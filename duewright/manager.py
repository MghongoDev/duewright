"""The rules that operate on tasks.

This module never reads input, prints, or touches the disk, so every rule
here can be tested on its own.
"""

from typing import Optional

from duewright.models import Task


class TaskNotFoundError(Exception):
    """Raised when no task carries the id that was asked for."""


class TaskManager:
    """Holds the tasks in memory and applies changes to them."""

    def __init__(self, tasks: Optional[list[Task]] = None, next_id: int = 1) -> None:
        self.tasks: list[Task] = list(tasks) if tasks else []
        self.next_id = next_id

    def add(self, title: str) -> Task:
        """Create a task, give it the next id, and return it."""
        task = Task(title=title, id=self.next_id)
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
        """Return a copy of the task list, in the order the tasks were added."""
        return list(self.tasks)
