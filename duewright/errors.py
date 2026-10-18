"""The errors the package raises.

They live here rather than beside the code that raises them, so that a
repository and the service can both refer to them without importing each
other.
"""

from pathlib import Path
from typing import Optional


class TaskNotFoundError(Exception):
    """Raised when no task carries the id that was asked for."""


class StorageVersionError(Exception):
    """The store was written by a newer version of Duewright than this one."""


class UnknownBackendError(ValueError):
    """The settings name a place to keep tasks that this program does not have."""


class CorruptStorageError(Exception):
    """The store could not be read at all.

    A file that cannot be parsed is moved aside, and its new name travels with
    the error so the menu can say where it went. A database has nowhere to
    move itself to, so that name stays empty.
    """

    def __init__(self, reason: str, spoiled_path: Optional[Path] = None) -> None:
        super().__init__(reason)
        self.spoiled_path = spoiled_path
