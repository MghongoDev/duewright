"""Tests for the rules the service holds."""

import re
from datetime import date, timedelta

import pytest

from duewright.errors import InvalidTaskError, TaskNotFoundError
from duewright.models import Task
from duewright.repositories.memory import InMemoryTaskRepository
from duewright.service import TaskService, is_due_soon, is_due_today, is_overdue

TODAY = date(2026, 10, 18)


@pytest.fixture
def service():
    return TaskService(InMemoryTaskRepository())


def make_service_with_every_case():
    """A service holding one of each case the ordering has to handle.

    Ids run from 1 in the order the tasks are added, so the last one is 5.
    """
    service = TaskService(InMemoryTaskRepository())
    service.add("Undated low", priority="low")
    service.add("Dated soon", priority="low", due_date=date(2026, 10, 20))
    service.add("Dated later", priority="high", due_date=date(2026, 11, 1))
    service.add("Dated soon and high", priority="high", due_date=date(2026, 10, 20))
    service.add("Finished", due_date=date(2026, 10, 1))
    service.toggle_done(5)
    return service


def test_add_gives_increasing_ids(service):
    assert service.add("Buy milk").id == 1
    assert service.add("Call Sam").id == 2


def test_ids_are_never_reused(service):
    """Deleting a task does not free its id (see docs/adr/0002)."""
    assert service.add("Buy milk").id == 1
    service.delete(1)
    assert service.add("Call Sam").id == 2


def test_deleting_a_middle_task_leaves_the_other_ids_alone(service):
    for number in range(3):
        service.add(f"task {number}")
    service.delete(2)
    page, _ = service.list_tasks()
    assert [task.id for task in page] == [1, 3]


def test_changing_one_task_leaves_the_others_alone(service):
    """The general path changes one task and touches nothing else."""
    service.add("Buy milk")
    service.add("Call Sam")
    service.change(1, {"title": "Buy oat milk"})
    assert service.get(1).title == "Buy oat milk"
    page, _ = service.list_tasks()
    assert [task.title for task in page] == ["Buy oat milk", "Call Sam"]


@pytest.mark.parametrize(
    ("changes", "refusal"),
    [
        ({"title": None}, "title cannot be null"),
        ({"title": "   "}, "A title is required."),
        ({"priority": "urgent"}, "Priority is low, medium or high."),
        ({"urgent": True}, "urgent is not a field of a task."),
    ],
    ids=["null title", "blank title", "unknown priority", "unknown field"],
)
def test_the_general_path_refuses_what_it_cannot_apply(service, changes, refusal):
    """A change it cannot apply is refused, and the task keeps what it had."""
    service.add("Buy milk")
    with pytest.raises(InvalidTaskError, match=re.escape(refusal)):
        service.change(1, changes)
    assert service.get(1).title == "Buy milk"


def test_toggle_done_flips_the_flag_both_ways(service):
    service.add("Buy milk")
    service.toggle_done(1)
    assert service.get(1).done is True
    service.toggle_done(1)
    assert service.get(1).done is False


@pytest.mark.parametrize(
    "action",
    [
        lambda service: service.get(99),
        lambda service: service.change(99, {"title": "nothing"}),
        lambda service: service.toggle_done(99),
        lambda service: service.delete(99),
    ],
    ids=["get", "change", "toggle_done", "delete"],
)
def test_unknown_id_raises(service, action):
    service.add("Buy milk")
    with pytest.raises(TaskNotFoundError):
        action(service)


def test_a_task_carries_its_priority_and_due_date(service):
    service.add("Pay the rent", priority="high", due_date=date(2026, 10, 5))
    task = service.get(1)
    assert (task.priority, task.due_date) == ("high", date(2026, 10, 5))


def test_the_priority_defaults_to_medium(service):
    service.add("Buy milk")
    assert service.get(1).priority == "medium"


def test_the_service_sorts_what_the_store_hands_back(service):
    """The store keeps the order tasks were added; the display does not."""
    service.add("Undated", priority="high")
    service.add("Dated", priority="low", due_date=date(2026, 12, 1))
    assert [task.title for task in service.repository.list_tasks()] == [
        "Undated",
        "Dated",
    ]
    page, _ = service.list_tasks()
    assert [task.title for task in page] == ["Dated", "Undated"]


def test_the_list_orders_pending_first_then_dated_then_priority():
    service = make_service_with_every_case()
    page, _ = service.list_tasks()
    assert [task.title for task in page] == [
        "Dated soon and high",
        "Dated soon",
        "Dated later",
        "Undated low",
        "Finished",
    ]


def test_an_undated_task_sorts_below_a_dated_one(service):
    service.add("Undated", priority="high")
    service.add("Dated", priority="low", due_date=date(2026, 12, 1))
    page, _ = service.list_tasks()
    assert [task.title for task in page] == ["Dated", "Undated"]


def test_the_id_breaks_a_tie_on_due_date_and_priority(service):
    service.add("First", priority="high", due_date=date(2026, 10, 20))
    service.add("Second", priority="high", due_date=date(2026, 10, 20))
    page, _ = service.list_tasks()
    assert [task.title for task in page] == ["First", "Second"]


def test_overdue_means_pending_and_due_before_today(service):
    task = service.add("Pay the rent", due_date=date(2026, 10, 5))
    assert is_overdue(task, TODAY) is True
    assert is_overdue(task, date(2026, 10, 5)) is False


def test_a_task_due_today_is_not_overdue(service):
    task = service.add("Water the plants", due_date=TODAY)
    assert is_overdue(task, TODAY) is False
    assert is_due_today(task, TODAY) is True


def test_a_done_task_is_never_overdue(service):
    task = service.add("Paid", due_date=date(2026, 10, 1))
    service.toggle_done(task.id)
    assert is_overdue(service.get(task.id), TODAY) is False
    assert is_due_today(service.get(task.id), TODAY) is False


def test_an_undated_task_is_never_overdue(service):
    task = service.add("Someday")
    assert is_overdue(task, TODAY) is False
    assert is_due_today(task, TODAY) is False


def test_the_filter_narrows_by_state():
    service = make_service_with_every_case()
    pending, _ = service.list_tasks(done=False)
    assert len(pending) == 4
    done, _ = service.list_tasks(done=True)
    assert [task.title for task in done] == ["Finished"]


def test_the_search_ignores_case_and_matches_accents(service):
    service.add("Buy café ☕")
    service.add("Call Sam")
    page, _ = service.list_tasks(query="CAFÉ")
    assert [task.title for task in page] == ["Buy café ☕"]
    page, _ = service.list_tasks(query="call")
    assert [task.title for task in page] == ["Call Sam"]
    assert service.list_tasks(query="nothing at all")[0] == []


def test_the_search_matches_the_title_only(service):
    service.add("Call Sam", priority="high")
    assert service.list_tasks(query="high")[0] == []


def test_the_summary_counts_pending_overdue_and_done(service):
    service.add("Pay the rent", due_date=date(2026, 10, 5))
    service.add("Water the plants", due_date=TODAY)
    service.add("Book tickets")
    service.toggle_done(3)
    assert service.summary(TODAY) == "2 pending, 1 overdue, 1 done"


def test_a_page_carries_the_total_that_matched(service):
    for number in range(25):
        service.add(f"task {number}")
    page, total = service.list_tasks(limit=10, offset=20)
    assert len(page) == 5
    assert total == 25


def test_a_page_past_the_end_is_empty(service):
    service.add("Buy milk")
    page, total = service.list_tasks(limit=10, offset=10)
    assert page == []
    assert total == 1


@pytest.mark.parametrize(
    ("days_away", "expected"),
    [(-1, False), (0, False), (1, True), (3, True), (4, False)],
)
def test_a_task_is_due_soon_inside_the_horizon(days_away, expected):
    """Three days is the horizon, and the day itself belongs to due today."""
    task = Task(title="Buy milk", due_date=TODAY + timedelta(days=days_away))
    assert is_due_soon(task, TODAY) is expected


def test_a_done_task_is_never_due_soon():
    task = Task(title="Buy milk", done=True, due_date=TODAY + timedelta(days=1))
    assert is_due_soon(task, TODAY) is False


def test_a_task_with_no_due_date_is_never_due_soon():
    assert is_due_soon(Task(title="Buy milk"), TODAY) is False
