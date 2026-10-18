"""Tests for moving the tasks from a JSON file into the database."""

import json
from datetime import date

import pytest

from duewright.errors import CorruptStorageError, MigrationError
from duewright.models import Task
from duewright.repositories.migrate import migrate_json
from duewright.repositories.sqlite_repo import SqliteTaskRepository

CREATED = "2026-10-18T17:52:04+00:00"


def write_version_1(path):
    """A file as the first release wrote it: no priority and no due date."""
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "next_id": 3,
                "tasks": [
                    {"id": 1, "title": "Buy milk", "done": False, "created_at": CREATED},
                    {"id": 2, "title": "Call Sam", "done": True, "created_at": CREATED},
                ],
            }
        ),
        encoding="utf-8",
    )


def write_version_2(path):
    """A file with a priority and a due date."""
    path.write_text(
        json.dumps(
            {
                "version": 2,
                "next_id": 2,
                "tasks": [
                    {
                        "id": 1,
                        "title": "Pay the rent",
                        "done": False,
                        "created_at": CREATED,
                        "priority": "high",
                        "due_date": "2026-10-05",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_a_version_1_file_moves_over(tmp_path):
    source = tmp_path / "tasks.json"
    write_version_1(source)
    report = migrate_json(source, tmp_path / "tasks.db")
    assert report.source_count == 2
    assert report.written is True
    moved = SqliteTaskRepository(tmp_path / "tasks.db").list_tasks()
    assert [task.id for task in moved] == [1, 2]
    assert [task.title for task in moved] == ["Buy milk", "Call Sam"]
    assert moved[1].done is True
    assert moved[0].created_at == CREATED


def test_a_version_2_file_keeps_every_field(tmp_path):
    source = tmp_path / "tasks.json"
    write_version_2(source)
    migrate_json(source, tmp_path / "tasks.db")
    moved = SqliteTaskRepository(tmp_path / "tasks.db").list_tasks()[0]
    assert moved.priority == "high"
    assert moved.due_date == date(2026, 10, 5)
    assert moved.created_at == CREATED


def test_the_source_file_is_left_alone(tmp_path):
    source = tmp_path / "tasks.json"
    write_version_2(source)
    before = source.read_text(encoding="utf-8")
    migrate_json(source, tmp_path / "tasks.db")
    assert source.read_text(encoding="utf-8") == before


def test_a_dry_run_writes_nothing(tmp_path):
    source = tmp_path / "tasks.json"
    write_version_2(source)
    database = tmp_path / "tasks.db"
    report = migrate_json(source, database, dry_run=True)
    assert report.source_count == 1
    assert report.written is False
    assert not database.exists()


def test_a_database_that_already_holds_tasks_is_refused(tmp_path):
    source = tmp_path / "tasks.json"
    write_version_2(source)
    database = tmp_path / "tasks.db"
    migrate_json(source, database)
    with pytest.raises(MigrationError):
        migrate_json(source, database)


def test_a_damaged_source_leaves_the_destination_empty(tmp_path):
    source = tmp_path / "tasks.json"
    source.write_text('{"version": 2, "tasks": [', encoding="utf-8")
    database = tmp_path / "tasks.db"
    with pytest.raises(CorruptStorageError):
        migrate_json(source, database)
    assert SqliteTaskRepository(database).list_tasks() == []


def test_the_tasks_keep_their_ids_even_out_of_order(tmp_path):
    """The check compares by id, so a file listed in another order still moves."""
    source = tmp_path / "tasks.json"
    source.write_text(
        json.dumps(
            {
                "version": 2,
                "next_id": 10,
                "tasks": [
                    {"id": 7, "title": "Later id", "done": False, "created_at": CREATED},
                    {"id": 3, "title": "Earlier id", "done": False, "created_at": CREATED},
                ],
            }
        ),
        encoding="utf-8",
    )
    report = migrate_json(source, tmp_path / "tasks.db")
    assert report.written is True
    moved = SqliteTaskRepository(tmp_path / "tasks.db").list_tasks()
    assert sorted(task.id for task in moved) == [3, 7]


def test_a_task_added_after_the_move_does_not_reuse_an_id(tmp_path):
    source = tmp_path / "tasks.json"
    write_version_1(source)
    database = tmp_path / "tasks.db"
    migrate_json(source, database)
    assert SqliteTaskRepository(database).add(Task(title="After the move")).id == 3
