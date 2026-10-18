"""The shapes a request has to have and a response always has.

These models check the shape of what arrives. The rules that decide what a
value means live in the service, so the API and the menu enforce the same
ones.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from duewright.models import PRIORITIES


class TaskIn(BaseModel):
    """What a request carries to create a task."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=100)
    priority: str = "medium"
    due_date: Optional[date] = None

    @field_validator("priority")
    @classmethod
    def priority_is_one_of_three(cls, value: str) -> str:
        if value not in PRIORITIES:
            raise ValueError("Priority is low, medium or high.")
        return value


class TaskUpdate(BaseModel):
    """A partial update.

    A field that is left out keeps the value it has. A field that is sent as
    null clears it, which is how a due date is removed. A null title or
    priority is refused by the service, because neither means anything.
    """

    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[date] = None
    done: Optional[bool] = None


class TaskOut(BaseModel):
    """A task as a response carries it."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    done: bool
    priority: str
    due_date: Optional[date]
    created_at: str


class TaskPage(BaseModel):
    """One page of tasks, and enough to ask for the next one."""

    items: list[TaskOut]
    total: int
    limit: int
    offset: int
