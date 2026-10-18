"""The behaviours that belong to the database, not to every repository."""

import sqlite3
from datetime import date

import pytest

from duewright.errors import CorruptStorageError, StorageVersionError
from duewright.models import Task
from duewright.repositories.sqlite_repo import SqliteTaskRepository

INSERT = "INSERT INTO tasks (title, done, priority, due_date, created_at) VALUES (?, ?, ?, ?, ?)"


def test_the_schema_version_is_recorded(tmp_path):
    path = tmp_path / "tasks.db"
    SqliteTaskRepository(path).add(Task(title="Buy milk"))
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1


def test_a_database_from_a_newer_version_is_refused(tmp_path):
    path = tmp_path / "tasks.db"
    SqliteTaskRepository(path).list_tasks()
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA user_version = 99")
        conn.commit()
    with pytest.raises(StorageVersionError):
        SqliteTaskRepository(path).list_tasks()


def test_a_file_that_is_not_a_database_is_reported(tmp_path):
    """Pointing the setting at the wrong file says so, rather than crashing."""
    path = tmp_path / "tasks.db"
    path.write_text("this is not a database", encoding="utf-8")
    with pytest.raises(CorruptStorageError):
        SqliteTaskRepository(path).list_tasks()


def test_a_title_that_looks_like_sql_is_stored_as_typed(tmp_path):
    """Every value goes in as a parameter, so a title is only ever a title."""
    path = tmp_path / "tasks.db"
    hostile = "'); DROP TABLE tasks;--"
    repo = SqliteTaskRepository(path)
    repo.add(Task(title=hostile))
    page, _ = repo.list_tasks()
    assert page[0].title == hostile
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT count(*) FROM tasks").fetchone()[0] == 1


def test_the_schema_refuses_an_invalid_priority(tmp_path):
    """The table refuses bad data even when the code above it has a bug."""
    path = tmp_path / "tasks.db"
    SqliteTaskRepository(path).list_tasks()
    with sqlite3.connect(path) as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(INSERT, ("Buy milk", 0, "urgent", None, "2026-10-18T17:52:04+00:00"))


def test_the_schema_refuses_an_empty_title(tmp_path):
    path = tmp_path / "tasks.db"
    SqliteTaskRepository(path).list_tasks()
    with sqlite3.connect(path) as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(INSERT, ("", 0, "medium", None, "2026-10-18T17:52:04+00:00"))


def test_the_schema_refuses_a_title_that_is_too_long(tmp_path):
    path = tmp_path / "tasks.db"
    SqliteTaskRepository(path).list_tasks()
    with sqlite3.connect(path) as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(INSERT, ("x" * 101, 0, "medium", None, "2026-10-18T17:52:04+00:00"))


def test_the_schema_refuses_a_done_flag_that_is_not_a_flag(tmp_path):
    path = tmp_path / "tasks.db"
    SqliteTaskRepository(path).list_tasks()
    with sqlite3.connect(path) as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(INSERT, ("Buy milk", 7, "medium", None, "2026-10-18T17:52:04+00:00"))


def test_a_due_date_is_stored_as_an_iso_string(tmp_path):
    path = tmp_path / "tasks.db"
    SqliteTaskRepository(path).add(Task(title="Pay the rent", due_date=date(2026, 10, 5)))
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT due_date FROM tasks").fetchone()[0] == "2026-10-05"


def test_a_task_without_a_due_date_stores_nothing_there(tmp_path):
    path = tmp_path / "tasks.db"
    SqliteTaskRepository(path).add(Task(title="Buy milk"))
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT due_date FROM tasks").fetchone()[0] is None
