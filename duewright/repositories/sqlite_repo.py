"""The repository that keeps the tasks in a SQLite database.

The schema refuses bad data on its own, so a bug in the code above cannot
write a task the rules would not allow. The database records which version of
the schema it holds, so a later change can be applied in order rather than
guessed at.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Optional

from duewright.errors import CorruptStorageError, StorageVersionError, TaskNotFoundError
from duewright.models import Task

SCHEMA_V1 = """
CREATE TABLE tasks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT    NOT NULL CHECK (length(title) BETWEEN 1 AND 100),
    done       INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
    priority   TEXT    NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    due_date   TEXT,
    created_at TEXT    NOT NULL
);
"""

MIGRATIONS = {1: SCHEMA_V1}

LOCK_TIMEOUT_SECONDS = 5


def migrate(conn: sqlite3.Connection) -> None:
    """Apply any migration the database is missing.

    A database newer than this code is refused, because opening it and saving
    over it would throw away whatever the newer version added.
    """
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    latest = max(MIGRATIONS)
    if current > latest:
        raise StorageVersionError(
            f"the database is schema version {current}, and this program "
            f"understands version {latest}. Update Duewright before opening it."
        )
    for version in range(current + 1, latest + 1):
        conn.executescript(MIGRATIONS[version])
        # PRAGMA does not take a parameter, and the version comes from this
        # module's own table rather than from anyone's input.
        conn.execute(f"PRAGMA user_version = {version}")


class SqliteTaskRepository:
    """Keeps the tasks in a database, opening one short-lived connection per operation.

    A connection held open would block another copy of the program, and a
    connection cannot be shared across threads, so every method opens its own
    and closes it again.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    def list_tasks(self, done: Optional[bool] = None, query: Optional[str] = None) -> list[Task]:
        """Return the tasks that match, in the order they were added."""
        statement = "SELECT * FROM tasks"
        parameters: tuple[object, ...] = ()
        if done is not None:
            statement += " WHERE done = ?"
            parameters = (int(done),)
        statement += " ORDER BY id"
        with self._connection() as conn:
            rows = conn.execute(statement, parameters).fetchall()
        tasks = [self._to_task(row) for row in rows]
        if query:
            # SQLite compares text without case for ASCII only, so the search
            # happens here, where every backend behaves the same way.
            needle = query.casefold()
            tasks = [task for task in tasks if needle in task.title.casefold()]
        return tasks

    def get(self, task_id: int) -> Task:
        """Return one task, or raise TaskNotFoundError."""
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise TaskNotFoundError(f"no task with id {task_id}")
        return self._to_task(row)

    def add(self, task: Task) -> Task:
        """Store a new task, give it the next id, and return it."""
        with self._connection() as conn:
            cursor = conn.execute(
                "INSERT INTO tasks (title, done, priority, due_date, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    task.title,
                    int(task.done),
                    task.priority,
                    task.due_date.isoformat() if task.due_date else None,
                    task.created_at,
                ),
            )
            task.id = cursor.lastrowid
        return task

    def update(self, task: Task) -> Task:
        """Store a changed task, or raise TaskNotFoundError."""
        with self._connection() as conn:
            cursor = conn.execute(
                "UPDATE tasks SET title = ?, done = ?, priority = ?, due_date = ? WHERE id = ?",
                (
                    task.title,
                    int(task.done),
                    task.priority,
                    task.due_date.isoformat() if task.due_date else None,
                    task.id,
                ),
            )
            if cursor.rowcount == 0:
                raise TaskNotFoundError(f"no task with id {task.id}")
        return task

    def delete(self, task_id: int) -> None:
        """Remove a task, or raise TaskNotFoundError."""
        with self._connection() as conn:
            cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            if cursor.rowcount == 0:
                raise TaskNotFoundError(f"no task with id {task_id}")

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Open the database, bring the schema up to date, and close it again.

        The timeout is how long to wait for a lock another process holds,
        rather than failing the moment the database is busy.
        """
        conn = sqlite3.connect(self.path, timeout=LOCK_TIMEOUT_SECONDS)
        conn.row_factory = sqlite3.Row
        try:
            try:
                migrate(conn)
                yield conn
                conn.commit()
            except sqlite3.DatabaseError as error:
                raise CorruptStorageError(f"it is not a database ({error})") from error
            except BaseException:
                conn.rollback()
                raise
        finally:
            conn.close()

    @staticmethod
    def _to_task(row: sqlite3.Row) -> Task:
        """Turn a row back into a task, converting the dates."""
        due_date = row["due_date"]
        return Task(
            title=row["title"],
            id=row["id"],
            done=bool(row["done"]),
            created_at=row["created_at"],
            priority=row["priority"],
            due_date=date.fromisoformat(due_date) if due_date else None,
        )
