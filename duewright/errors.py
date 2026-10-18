"""The errors the package raises.

They live here rather than beside the code that raises them, so that a
repository and the service can both refer to them without importing each
other.
"""


class TaskNotFoundError(Exception):
    """Raised when no task carries the id that was asked for."""


class StorageVersionError(Exception):
    """The store was written by a newer version of Duewright than this one."""
