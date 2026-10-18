"""Where the tasks are kept."""

import os
from pathlib import Path

FOLDER_NAME = ".duewright"


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
