"""The repository that keeps the tasks in a JSON file.

This is the only module that knows about JSON and about the shape of the file.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from duewright.errors import CorruptStorageError, StorageVersionError, TaskNotFoundError
from duewright.models import Task
from duewright.repositories.base import matches, page_of, sort_key

FILE_VERSION = 2


class JsonTaskRepository:
    """Reads the file, changes it, and swaps a complete file back in.

    Every method does that rather than holding the tasks in memory, so a
    second copy of the program cannot be working from a stale picture of the
    file for longer than one operation.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    def list_tasks(
        self,
        done: Optional[bool] = None,
        query: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> tuple[list[Task], int]:
        """Return one page of the tasks that match, in display order, and the total."""
        tasks, _ = self._read()
        matched = [task for task in tasks if matches(task, done, query)]
        return page_of(sorted(matched, key=sort_key), limit, offset)

    def get(self, task_id: int) -> Task:
        """Return one task, or raise TaskNotFoundError."""
        tasks, _ = self._read()
        for task in tasks:
            if task.id == task_id:
                return task
        raise TaskNotFoundError(f"no task with id {task_id}")

    def add(self, task: Task) -> Task:
        """Store a new task, give it the next id, and return it."""
        tasks, next_id = self._read()
        task.id = next_id
        tasks.append(task)
        self._write(tasks, next_id + 1)
        return task

    def update(self, task: Task) -> Task:
        """Store a changed task, or raise TaskNotFoundError."""
        tasks, next_id = self._read()
        for index, stored in enumerate(tasks):
            if stored.id == task.id:
                tasks[index] = task
                self._write(tasks, next_id)
                return task
        raise TaskNotFoundError(f"no task with id {task.id}")

    def delete(self, task_id: int) -> None:
        """Remove a task, or raise TaskNotFoundError."""
        tasks, next_id = self._read()
        remaining = [task for task in tasks if task.id != task_id]
        if len(remaining) == len(tasks):
            raise TaskNotFoundError(f"no task with id {task_id}")
        self._write(remaining, next_id)

    def _read(self) -> tuple[list[Task], int]:
        """Read the file and return the tasks and the next id.

        A missing file gives an empty list. A file that cannot be parsed is
        moved aside and reported, because it may hold the only copy of the
        user's tasks. A file from a newer version is refused, so that saving
        over it cannot throw away fields this program does not know about.
        """
        if not self.path.exists():
            return [], 1
        try:
            with open(self.path, encoding="utf-8") as handle:
                data: Any = json.load(handle)
            raw_tasks = data["tasks"]
            if not isinstance(raw_tasks, list) or not all(
                isinstance(item, dict) for item in raw_tasks
            ):
                raise ValueError("the file does not hold a list of tasks")
            tasks = [Task.from_dict(item) for item in raw_tasks]
        except json.JSONDecodeError as error:
            raise CorruptStorageError(
                f"it is not valid JSON ({error})", self._set_aside()
            ) from error
        except (KeyError, TypeError, ValueError) as error:
            raise CorruptStorageError(
                f"it is not shaped like a task file ({error})", self._set_aside()
            ) from error

        version = data.get("version")
        if isinstance(version, int) and version > FILE_VERSION:
            raise StorageVersionError(
                f"{self.path.name} is version {version}, and this program "
                f"understands version {FILE_VERSION}. Update Duewright before "
                f"opening it."
            )

        next_id = data.get("next_id")
        if not isinstance(next_id, int) or next_id < 1:
            # A hand-written file may carry no counter. The highest id it holds
            # is the best guess available.
            next_id = max((task.id or 0 for task in tasks), default=0) + 1
        return tasks, next_id

    def _write(self, tasks: list[Task], next_id: int) -> None:
        """Write the tasks in one step, so a crash cannot leave the file half written."""
        tmp_path = self.path.with_name(self.path.name + ".tmp")
        payload = {
            "version": FILE_VERSION,
            "next_id": next_id,
            "tasks": [task.to_dict() for task in tasks],
        }
        try:
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.path)
        except OSError:
            # A write that fails must not leave a stray temporary file behind.
            tmp_path.unlink(missing_ok=True)
            raise

    def _set_aside(self) -> Path:
        """Move an unreadable file aside and return where it went."""
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        spoiled = self.path.with_name(f"{self.path.name}.corrupt-{stamp}")
        self.path.replace(spoiled)
        return spoiled
