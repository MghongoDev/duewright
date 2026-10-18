"""Reading and writing the task file.

This is the only module that knows about JSON and the filesystem.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from duewright.models import Task

FILE_VERSION = 2


class CorruptStorageError(Exception):
    """The task file could not be read, and has been kept under another name."""

    def __init__(self, reason: str, spoiled_path: Path) -> None:
        super().__init__(reason)
        self.spoiled_path = spoiled_path


class StorageVersionError(Exception):
    """The task file was written by a newer version of Duewright than this one."""


def save_tasks(path: Path, tasks: list[Task], next_id: int) -> None:
    """Write the tasks in one step, so a crash cannot leave the file half written."""
    tmp_path = path.with_name(path.name + ".tmp")
    payload = {
        "version": FILE_VERSION,
        "next_id": next_id,
        "tasks": [task.to_dict() for task in tasks],
    }
    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
    except OSError:
        # A write that fails must not leave a stray temporary file behind.
        tmp_path.unlink(missing_ok=True)
        raise


def load_tasks(path: Path) -> tuple[list[Task], int]:
    """Read the tasks and the next id from the file.

    A missing file gives an empty list. A file that cannot be parsed is moved
    aside and reported, because it may hold the only copy of the user's tasks.
    A file written by a newer version is refused, so that saving over it
    cannot throw away fields this program does not know about.
    """
    if not path.exists():
        return [], 1
    try:
        with open(path, encoding="utf-8") as handle:
            data: Any = json.load(handle)
        raw_tasks = data["tasks"]
        if not isinstance(raw_tasks, list) or not all(isinstance(item, dict) for item in raw_tasks):
            raise ValueError("the file does not hold a list of tasks")
        tasks = [Task.from_dict(item) for item in raw_tasks]
    except json.JSONDecodeError as error:
        raise CorruptStorageError(f"it is not valid JSON ({error})", _set_aside(path)) from error
    except (KeyError, TypeError, ValueError) as error:
        raise CorruptStorageError(
            f"it is not shaped like a task file ({error})", _set_aside(path)
        ) from error

    version = data.get("version")
    if isinstance(version, int) and version > FILE_VERSION:
        raise StorageVersionError(
            f"{path.name} is version {version}, and this program understands "
            f"version {FILE_VERSION}. Update Duewright before opening it."
        )

    next_id = data.get("next_id")
    if not isinstance(next_id, int) or next_id < 1:
        # A hand-written file may carry no counter. The highest id it holds is
        # the best guess available.
        next_id = max((task.id or 0 for task in tasks), default=0) + 1
    return tasks, next_id


def _set_aside(path: Path) -> Path:
    """Move an unreadable file aside and return where it went."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    spoiled = path.with_name(f"{path.name}.corrupt-{stamp}")
    path.replace(spoiled)
    return spoiled
