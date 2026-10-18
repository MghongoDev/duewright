"""The Task model.

A Task carries its title first and its id second, because a task exists
before the store gives it an id (see docs/adr/0002).
"""

from datetime import date, datetime, timezone
from typing import Any, Optional

PRIORITIES = ("low", "medium", "high")


class Task:
    """One thing the user has decided to do."""

    def __init__(
        self,
        title: str,
        id: Optional[int] = None,
        done: bool = False,
        created_at: Optional[str] = None,
        priority: str = "medium",
        due_date: Optional[date] = None,
    ) -> None:
        self.id = id
        self.title = title
        self.done = done
        self.created_at = (
            created_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
        )
        self.priority = priority if priority in PRIORITIES else "medium"
        self.due_date = due_date

    def to_dict(self) -> dict[str, Any]:
        """Return the task as plain data, ready to be written as JSON."""
        return {
            "id": self.id,
            "title": self.title,
            "done": self.done,
            "created_at": self.created_at,
            "priority": self.priority,
            "due_date": self.due_date.isoformat() if self.due_date else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        """Build a task from stored data, tolerating keys that are not there."""
        due_date = data.get("due_date")
        return cls(
            title=data.get("title", ""),
            id=data.get("id"),
            done=data.get("done", False),
            created_at=data.get("created_at"),
            priority=data.get("priority", "medium"),
            due_date=date.fromisoformat(due_date) if due_date else None,
        )

    def __repr__(self) -> str:
        return f"Task(id={self.id!r}, title={self.title!r}, done={self.done!r})"
