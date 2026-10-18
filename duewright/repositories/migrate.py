"""Moving the tasks from a JSON file into the database, without losing any.

The file is read with the same loader the rest of the program uses, so every
older version of it is understood. Nothing here writes to the file.
"""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from duewright.errors import MigrationError
from duewright.models import Task
from duewright.repositories.json_repo import JsonTaskRepository
from duewright.repositories.sqlite_repo import SqliteTaskRepository, migrate

COMPARED_FIELDS = ("id", "title", "done", "priority", "due_date", "created_at")


@dataclass
class MigrationReport:
    """What the migration found and what it did."""

    source_count: int
    written: bool


def migrate_json(source: Path, database: Path, dry_run: bool = False) -> MigrationReport:
    """Copy the tasks from a JSON file into a database, and check the result.

    A database that already holds tasks is refused, because merging two lists
    is not what this is for. A dry run reads the file and stops, so nothing is
    written at all.
    """
    tasks, _ = JsonTaskRepository(source).list_tasks()
    _refuse_a_target_that_is_not_empty(database)
    if dry_run:
        return MigrationReport(source_count=len(tasks), written=False)
    _insert_in_one_transaction(database, tasks)
    stored, _ = SqliteTaskRepository(database).list_tasks()
    if not _same_tasks(tasks, stored):
        raise MigrationError(
            "the database does not hold the same tasks as the file, so the move "
            "is not reported as done"
        )
    return MigrationReport(source_count=len(tasks), written=True)


def _refuse_a_target_that_is_not_empty(database: Path) -> None:
    """Raise when the database already holds tasks."""
    if not database.exists():
        return
    existing, _ = SqliteTaskRepository(database).list_tasks()
    if existing:
        raise MigrationError(
            f"the database already holds {len(existing)} tasks, so nothing was moved"
        )


def _insert_in_one_transaction(database: Path, tasks: list[Task]) -> None:
    """Write every task in a single transaction, keeping the ids they carry."""
    conn = sqlite3.connect(database)
    try:
        migrate(conn)
        conn.executemany(
            "INSERT INTO tasks (id, title, done, priority, due_date, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    task.id,
                    task.title,
                    int(task.done),
                    task.priority,
                    task.due_date.isoformat() if task.due_date else None,
                    task.created_at,
                )
                for task in tasks
            ],
        )
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def _same_tasks(source: list[Task], stored: list[Task]) -> bool:
    """Return True when both sides hold the same tasks, field by field.

    The comparison is by id rather than by position, because the file and the
    database need not list the tasks in the same order.
    """
    if len(source) != len(stored):
        return False
    by_id = {task.id: task for task in stored}
    for task in source:
        other = by_id.get(task.id)
        if other is None:
            return False
        if any(getattr(task, field) != getattr(other, field) for field in COMPARED_FIELDS):
            return False
    return True
