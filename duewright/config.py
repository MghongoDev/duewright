"""Where the tasks are kept, and which repository keeps them."""

import os
from pathlib import Path

from duewright.errors import UnknownBackendError
from duewright.repositories.base import TaskRepository
from duewright.repositories.json_repo import JsonTaskRepository
from duewright.repositories.sqlite_repo import SqliteTaskRepository

FOLDER_NAME = ".duewright"
JSON_FILE_NAME = "tasks.json"
DATABASE_FILE_NAME = "tasks.db"
BACKENDS = ("json", "sqlite")
DEFAULT_BACKEND = "sqlite"


def data_dir() -> Path:
    """Return the folder that holds the task file, creating it if it is not there.

    The environment variable wins, so tests and anyone who wants a different
    location can point it somewhere else. Otherwise the folder sits in the
    user's home folder, which survives reinstalling the package.
    """
    override = os.environ.get("DUEWRIGHT_DATA_DIR")
    folder = Path(override) if override else Path.home() / FOLDER_NAME
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def make_repository() -> TaskRepository:
    """Return the repository the settings ask for.

    The database is the default because two copies of the program can use it
    at once, which a single JSON file cannot manage.
    """
    backend = os.environ.get("DUEWRIGHT_BACKEND", DEFAULT_BACKEND).strip().lower()
    folder = data_dir()
    if backend == "json":
        return JsonTaskRepository(folder / JSON_FILE_NAME)
    if backend == "sqlite":
        return SqliteTaskRepository(folder / DATABASE_FILE_NAME)
    raise UnknownBackendError(
        f"DUEWRIGHT_BACKEND is {backend!r}, and the choices are {', '.join(BACKENDS)}."
    )
