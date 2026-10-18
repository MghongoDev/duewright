"""Tests for the task rules."""

from datetime import date

import pytest

from duewright.manager import (
    TaskManager,
    TaskNotFoundError,
    is_due_today,
    is_overdue,
)
from duewright.models import Task

TODAY = date(2026, 10, 18)


def make_manager():
    """A manager holding one of each case the ordering has to handle.

    Ids run from 1 in the order the tasks are added, so the last one is 5.
    """
    manager = TaskManager()
    manager.add("Undated low", priority="low")
    manager.add("Dated soon", priority="low", due_date=date(2026, 10, 20))
    manager.add("Dated later", priority="high", due_date=date(2026, 11, 1))
    manager.add("Dated soon and high", priority="high", due_date=date(2026, 10, 20))
    manager.add("Finished", due_date=date(2026, 10, 1))
    manager.toggle_done(5)
    return manager


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


def test_a_task_carries_its_priority_and_due_date():
    manager = TaskManager()
    manager.add("Pay the rent", priority="high", due_date=date(2026, 10, 5))
    task = manager.get(1)
    assert (task.priority, task.due_date) == ("high", date(2026, 10, 5))


def test_the_priority_defaults_to_medium():
    manager = TaskManager()
    manager.add("Buy milk")
    assert manager.get(1).priority == "medium"


def test_the_list_orders_pending_first_then_dated_then_priority():
    manager = make_manager()
    assert [task.title for task in manager.list_tasks()] == [
        "Dated soon and high",
        "Dated soon",
        "Dated later",
        "Undated low",
        "Finished",
    ]


def test_an_undated_task_sorts_below_a_dated_one():
    manager = TaskManager()
    manager.add("Undated", priority="high")
    manager.add("Dated", priority="low", due_date=date(2026, 12, 1))
    assert [task.title for task in manager.list_tasks()] == ["Dated", "Undated"]


def test_the_id_breaks_a_tie_on_due_date_and_priority():
    manager = TaskManager()
    manager.add("First", priority="high", due_date=date(2026, 10, 20))
    manager.add("Second", priority="high", due_date=date(2026, 10, 20))
    assert [task.title for task in manager.list_tasks()] == ["First", "Second"]


def test_overdue_means_pending_and_due_before_today():
    task = Task(title="Pay the rent", id=1, due_date=date(2026, 10, 5))
    assert is_overdue(task, TODAY) is True
    assert is_overdue(task, date(2026, 10, 5)) is False


def test_a_task_due_today_is_not_overdue():
    task = Task(title="Water the plants", id=1, due_date=TODAY)
    assert is_overdue(task, TODAY) is False
    assert is_due_today(task, TODAY) is True


def test_a_done_task_is_never_overdue():
    task = Task(title="Paid", id=1, done=True, due_date=date(2026, 10, 1))
    assert is_overdue(task, TODAY) is False
    assert is_due_today(task, TODAY) is False


def test_an_undated_task_is_never_overdue():
    task = Task(title="Someday", id=1)
    assert is_overdue(task, TODAY) is False
    assert is_due_today(task, TODAY) is False


def test_the_filter_narrows_by_state():
    manager = make_manager()
    assert len(manager.list_tasks(done=False)) == 4
    assert [task.title for task in manager.list_tasks(done=True)] == ["Finished"]


def test_the_search_ignores_case_and_matches_accents():
    manager = TaskManager()
    manager.add("Buy café ☕")
    manager.add("Call Sam")
    assert [task.title for task in manager.list_tasks(query="CAFÉ")] == ["Buy café ☕"]
    assert [task.title for task in manager.list_tasks(query="call")] == ["Call Sam"]
    assert manager.list_tasks(query="nothing at all") == []


def test_the_search_matches_the_title_only():
    manager = TaskManager()
    manager.add("Call Sam", priority="high")
    assert manager.list_tasks(query="high") == []


def test_the_summary_counts_pending_overdue_and_done():
    manager = TaskManager()
    manager.add("Pay the rent", due_date=date(2026, 10, 5))
    manager.add("Water the plants", due_date=TODAY)
    manager.add("Book tickets")
    manager.toggle_done(3)
    assert manager.summary(TODAY) == "2 pending, 1 overdue, 1 done"
