"""Tests for reading and writing the task file."""

import json
from datetime import date

import pytest

from duewright.manager import TaskManager
from duewright.models import Task
from duewright.storage import (
    CorruptStorageError,
    StorageVersionError,
    load_tasks,
    save_tasks,
)


def test_round_trip(tmp_path):
    path = tmp_path / "tasks.json"
    save_tasks(path, [Task(title="Buy milk", id=1)], next_id=2)
    tasks, next_id = load_tasks(path)
    assert [task.title for task in tasks] == ["Buy milk"]
    assert tasks[0].id == 1
    assert tasks[0].done is False
    assert next_id == 2


def test_missing_file_gives_an_empty_list(tmp_path):
    assert load_tasks(tmp_path / "tasks.json") == ([], 1)


def test_corrupt_file_is_kept_and_reported(tmp_path):
    path = tmp_path / "tasks.json"
    path.write_text('{"version": 1, "tasks": [', encoding="utf-8")
    with pytest.raises(CorruptStorageError) as raised:
        load_tasks(path)
    assert not path.exists()
    assert raised.value.spoiled_path.exists()
    assert "corrupt" in raised.value.spoiled_path.name


def test_a_file_of_the_wrong_shape_counts_as_corrupt(tmp_path):
    path = tmp_path / "tasks.json"
    path.write_text('{"version": 1, "tasks": "not a list"}', encoding="utf-8")
    with pytest.raises(CorruptStorageError):
        load_tasks(path)


def test_a_bad_due_date_counts_as_corrupt(tmp_path):
    path = tmp_path / "tasks.json"
    path.write_text(
        json.dumps(
            {
                "version": 2,
                "next_id": 2,
                "tasks": [{"id": 1, "title": "Buy milk", "due_date": "soon"}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(CorruptStorageError):
        load_tasks(path)


def test_saving_leaves_no_temp_file_behind(tmp_path):
    path = tmp_path / "tasks.json"
    save_tasks(path, [], next_id=1)
    assert [entry.name for entry in tmp_path.iterdir()] == ["tasks.json"]


def test_a_write_that_fails_leaves_no_temp_file_behind(tmp_path):
    path = tmp_path / "not-a-folder" / "tasks.json"
    with pytest.raises(OSError):
        save_tasks(path, [Task(title="Buy milk", id=1)], next_id=2)
    assert list(tmp_path.iterdir()) == []


def test_non_ascii_title_survives_a_round_trip(tmp_path):
    path = tmp_path / "tasks.json"
    save_tasks(path, [Task(title="Buy café ☕", id=1)], next_id=2)
    tasks, _ = load_tasks(path)
    assert tasks[0].title == "Buy café ☕"
    assert "café ☕" in path.read_text(encoding="utf-8")


def test_done_and_created_at_survive_a_round_trip(tmp_path):
    path = tmp_path / "tasks.json"
    task = Task(title="Buy milk", id=1, done=True, created_at="2026-10-18T17:52:04+00:00")
    save_tasks(path, [task], next_id=2)
    loaded, _ = load_tasks(path)
    assert loaded[0].done is True
    assert loaded[0].created_at == "2026-10-18T17:52:04+00:00"


def test_priority_and_due_date_survive_a_round_trip(tmp_path):
    path = tmp_path / "tasks.json"
    task = Task(title="Pay the rent", id=1, priority="high", due_date=date(2026, 10, 5))
    save_tasks(path, [task], next_id=2)
    loaded, _ = load_tasks(path)
    assert loaded[0].priority == "high"
    assert loaded[0].due_date == date(2026, 10, 5)


def test_saving_writes_the_current_version(tmp_path):
    path = tmp_path / "tasks.json"
    save_tasks(path, [], next_id=1)
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == 2


def test_a_version_1_file_still_loads(tmp_path):
    path = tmp_path / "tasks.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "next_id": 2,
                "tasks": [
                    {
                        "id": 1,
                        "title": "Buy milk",
                        "done": False,
                        "created_at": "2026-10-18T17:52:04+00:00",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    tasks, next_id = load_tasks(path)
    assert tasks[0].title == "Buy milk"
    assert tasks[0].priority == "medium"
    assert tasks[0].due_date is None
    assert next_id == 2


def test_an_unknown_priority_falls_back_to_medium(tmp_path):
    path = tmp_path / "tasks.json"
    path.write_text(
        json.dumps(
            {
                "version": 2,
                "next_id": 2,
                "tasks": [{"id": 1, "title": "Buy milk", "priority": "urgent"}],
            }
        ),
        encoding="utf-8",
    )
    tasks, _ = load_tasks(path)
    assert tasks[0].priority == "medium"


def test_a_newer_file_is_refused_rather_than_overwritten(tmp_path):
    path = tmp_path / "tasks.json"
    path.write_text(
        json.dumps({"version": 99, "next_id": 2, "tasks": []}), encoding="utf-8"
    )
    with pytest.raises(StorageVersionError):
        load_tasks(path)
    assert path.exists()


def test_a_file_without_a_counter_falls_back_to_the_highest_id(tmp_path):
    path = tmp_path / "tasks.json"
    path.write_text(
        json.dumps({"version": 1, "tasks": [{"id": 4, "title": "Buy milk"}]}),
        encoding="utf-8",
    )
    _, next_id = load_tasks(path)
    assert next_id == 5


def test_a_loaded_counter_still_keeps_ids_unique(tmp_path):
    path = tmp_path / "tasks.json"
    save_tasks(path, [Task(title="Buy milk", id=7)], next_id=8)
    tasks, next_id = load_tasks(path)
    manager = TaskManager(tasks, next_id)
    assert manager.add("Call Sam").id == 8
