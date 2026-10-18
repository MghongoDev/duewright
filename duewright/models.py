"""The Task model.

A Task carries its title first and its id second, because a task exists
before the store gives it an id (see docs/adr/0002).
"""

from datetime import datetime, timezone
from typing import Any, Optional


class Task:
    """One thing the user has decided to do."""

    def __init__(
        self,
        title: str,
        id: Optional[int] = None,
        done: bool = False,
        created_at: Optional[str] = None,
    ) -> None:
        self.id = id
        self.title = title
        self.done = done
        self.created_at = (
            created_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the task as plain data, ready to be written as JSON."""
        return {
            "id": self.id,
            "title": self.title,
            "done": self.done,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        """Build a task from stored data, tolerating keys that are not there."""
        return cls(
            title=data.get("title", ""),
            id=data.get("id"),
            done=data.get("done", False),
            created_at=data.get("created_at"),
        )

    def __repr__(self) -> str:
        return f"Task(id={self.id!r}, title={self.title!r}, done={self.done!r})"
