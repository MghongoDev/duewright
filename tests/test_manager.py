"""Tests for the task rules."""

import pytest

from duewright.manager import TaskManager, TaskNotFoundError


def test_add_gives_increasing_ids():
    manager = TaskManager()
    assert manager.add("Buy milk").id == 1
    assert manager.add("Call Sam").id == 2


def test_ids_are_never_reused():
    """Deleting a task does not free its id (see docs/adr/0002)."""
    manager = TaskManager()
    assert manager.add("Buy milk").id == 1
    manager.delete(1)
    assert manager.add("Call Sam").id == 2


def test_deleting_a_middle_task_leaves_the_other_ids_alone():
    manager = TaskManager()
    for number in range(3):
        manager.add(f"task {number}")
    manager.delete(2)
    assert [task.id for task in manager.all()] == [1, 3]


def test_update_title_leaves_the_other_tasks_alone():
    manager = TaskManager()
    manager.add("Buy milk")
    manager.add("Call Sam")
    manager.update_title(1, "Buy oat milk")
    assert manager.get(1).title == "Buy oat milk"
    assert [task.title for task in manager.all()] == ["Buy oat milk", "Call Sam"]


def test_toggle_done_flips_the_flag_both_ways():
    manager = TaskManager()
    manager.add("Buy milk")
    manager.toggle_done(1)
    assert manager.get(1).done is True
    manager.toggle_done(1)
    assert manager.get(1).done is False


def test_all_returns_a_copy():
    manager = TaskManager()
    manager.add("Buy milk")
    manager.all().clear()
    assert len(manager.all()) == 1


@pytest.mark.parametrize(
    "action",
    [
        lambda manager: manager.get(99),
        lambda manager: manager.update_title(99, "nothing"),
        lambda manager: manager.toggle_done(99),
        lambda manager: manager.delete(99),
    ],
    ids=["get", "update_title", "toggle_done", "delete"],
)
def test_unknown_id_raises(action):
    manager = TaskManager()
    manager.add("Buy milk")
    with pytest.raises(TaskNotFoundError):
        action(manager)


def test_a_loaded_manager_continues_from_its_counter():
    manager = TaskManager([], next_id=7)
    assert manager.add("Buy milk").id == 7
