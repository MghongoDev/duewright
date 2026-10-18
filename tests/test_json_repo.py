"""The behaviours that belong to the JSON file, not to every repository."""

import json

import pytest

from duewright.errors import CorruptStorageError, StorageVersionError
from duewright.models import Task
from duewright.repositories.json_repo import JsonTaskRepository


def test_a_damaged_file_is_kept_and_reported(tmp_path):
    path = tmp_path / "tasks.json"
    path.write_text('{"version": 2, "tasks": [', encoding="utf-8")
    with pytest.raises(CorruptStorageError) as raised:
        JsonTaskRepository(path).list_tasks()
    assert not path.exists()
    assert raised.value.spoiled_path is not None
    assert raised.value.spoiled_path.exists()
    assert "corrupt" in raised.value.spoiled_path.name


def test_a_file_of_the_wrong_shape_counts_as_damaged(tmp_path):
    path = tmp_path / "tasks.json"
    path.write_text('{"version": 2, "tasks": "not a list"}', encoding="utf-8")
    with pytest.raises(CorruptStorageError):
        JsonTaskRepository(path).list_tasks()


def test_a_bad_due_date_counts_as_damaged(tmp_path):
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
        JsonTaskRepository(path).list_tasks()


def test_a_newer_file_is_refused_rather_than_overwritten(tmp_path):
    path = tmp_path / "tasks.json"
    newer = {"version": 99, "next_id": 1, "tasks": []}
    path.write_text(json.dumps(newer), encoding="utf-8")
    with pytest.raises(StorageVersionError):
        JsonTaskRepository(path).list_tasks()
    assert json.loads(path.read_text(encoding="utf-8")) == newer


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
    task = JsonTaskRepository(path).get(1)
    assert task.title == "Buy milk"
    assert task.priority == "medium"
    assert task.due_date is None


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
    assert JsonTaskRepository(path).get(1).priority == "medium"


def test_a_file_without_a_counter_falls_back_to_the_highest_id(tmp_path):
    path = tmp_path / "tasks.json"
    path.write_text(
        json.dumps({"version": 1, "tasks": [{"id": 4, "title": "Buy milk"}]}),
        encoding="utf-8",
    )
    assert JsonTaskRepository(path).add(Task(title="Call Sam")).id == 5


def test_writing_records_the_current_version(tmp_path):
    path = tmp_path / "tasks.json"
    JsonTaskRepository(path).add(Task(title="Buy milk"))
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == 2


def test_writing_leaves_no_temp_file_behind(tmp_path):
    path = tmp_path / "tasks.json"
    JsonTaskRepository(path).add(Task(title="Buy milk"))
    assert [entry.name for entry in tmp_path.iterdir()] == ["tasks.json"]


def test_a_write_that_fails_leaves_no_temp_file_behind(tmp_path):
    repo = JsonTaskRepository(tmp_path / "not-a-folder" / "tasks.json")
    with pytest.raises(OSError):
        repo.add(Task(title="Buy milk"))
    assert list(tmp_path.iterdir()) == []


def test_a_non_ascii_title_survives(tmp_path):
    path = tmp_path / "tasks.json"
    JsonTaskRepository(path).add(Task(title="Buy café ☕"))
    assert JsonTaskRepository(path).list_tasks()[0].title == "Buy café ☕"
    assert "café ☕" in path.read_text(encoding="utf-8")
