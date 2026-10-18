"""The contract that every task repository has to satisfy.

Every test here runs against every implementation, so a second backend can
arrive without the rules being touched or restated.
"""

from datetime import date

import pytest

from duewright.errors import TaskNotFoundError
from duewright.models import Task
from duewright.repositories.json_repo import JsonTaskRepository
from duewright.repositories.memory import InMemoryTaskRepository
from duewright.repositories.sqlite_repo import SqliteTaskRepository


@pytest.fixture(params=["json", "sqlite", "memory"])
def make_repo(request, tmp_path):
    """Build a repository. Calling it twice means the same store, restarted."""
    shared = InMemoryTaskRepository()

    def factory():
        if request.param == "json":
            return JsonTaskRepository(tmp_path / "tasks.json")
        if request.param == "sqlite":
            return SqliteTaskRepository(tmp_path / "tasks.db")
        return shared

    return factory


def titles(repo, **filters):
    """The titles a store returned, in the order it returned them."""
    page, _ = repo.list_tasks(**filters)
    return [task.title for task in page]


def test_a_missing_store_starts_empty(make_repo):
    page, total = make_repo().list_tasks()
    assert page == []
    assert total == 0


def test_ids_are_never_reused(make_repo):
    """A deleted id is not handed to a different task (see docs/adr/0002)."""
    repo = make_repo()
    first = repo.add(Task(title="Buy milk"))
    repo.delete(first.id)
    second = repo.add(Task(title="Call Sam"))
    assert second.id > first.id


def test_a_restart_keeps_the_tasks(make_repo):
    make_repo().add(Task(title="Buy milk"))
    assert titles(make_repo()) == ["Buy milk"]


def test_the_tasks_come_back_in_display_order(make_repo):
    """Pending first, then the earliest due date, then the higher priority, then the lower id.

    Every term of the order gets something to decide here, so a store that
    orders its own way has to agree with the others about all of them.
    """
    repo = make_repo()
    finished = repo.add(Task(title="done, undated"))
    repo.add(Task(title="pending, undated, low", priority="low"))
    repo.add(Task(title="pending, undated, high, added first", priority="high"))
    repo.add(Task(title="pending, undated, high, added later", priority="high"))
    repo.add(Task(title="pending, due later", due_date=date(2026, 11, 1)))
    repo.add(Task(title="pending, due sooner", due_date=date(2026, 10, 5)))
    finished.done = True
    repo.update(finished)

    assert titles(repo) == [
        "pending, due sooner",
        "pending, due later",
        "pending, undated, high, added first",
        "pending, undated, high, added later",
        "pending, undated, low",
        "done, undated",
    ]


def test_a_round_trip_keeps_every_field(make_repo):
    repo = make_repo()
    repo.add(Task(title="Pay the rent", priority="high", due_date=date(2026, 10, 5)))
    task = make_repo().list_tasks()[0][0]
    assert task.title == "Pay the rent"
    assert task.priority == "high"
    assert task.due_date == date(2026, 10, 5)
    assert task.done is False
    assert task.created_at is not None


def test_an_update_survives_a_restart(make_repo):
    repo = make_repo()
    task = repo.add(Task(title="Buy milk"))
    task.title = "Buy oat milk"
    repo.update(task)
    assert make_repo().get(task.id).title == "Buy oat milk"


def test_toggling_survives_a_restart(make_repo):
    repo = make_repo()
    task = repo.add(Task(title="Buy milk"))
    task.done = True
    repo.update(task)
    assert make_repo().get(task.id).done is True


def test_deleting_removes_the_task(make_repo):
    repo = make_repo()
    task = repo.add(Task(title="Buy milk"))
    repo.delete(task.id)
    assert titles(repo) == []


def test_deleting_a_middle_task_leaves_the_others_alone(make_repo):
    repo = make_repo()
    for title in ["first", "second", "third"]:
        repo.add(Task(title=title))
    repo.delete(2)
    assert titles(repo) == ["first", "third"]


@pytest.mark.parametrize(
    "action",
    [
        lambda repo: repo.get(99),
        lambda repo: repo.update(Task(title="nothing", id=99)),
        lambda repo: repo.delete(99),
    ],
    ids=["get", "update", "delete"],
)
def test_a_missing_id_raises(make_repo, action):
    repo = make_repo()
    repo.add(Task(title="Buy milk"))
    with pytest.raises(TaskNotFoundError):
        action(repo)


def test_the_done_filter(make_repo):
    repo = make_repo()
    repo.add(Task(title="pending"))
    done = repo.add(Task(title="done"))
    done.done = True
    repo.update(done)
    assert titles(repo, done=False) == ["pending"]
    assert titles(repo, done=True) == ["done"]
    assert titles(repo) == ["pending", "done"]


def test_the_search_ignores_case_and_matches_accents(make_repo):
    """The search folds case the same way in every store, including outside ASCII."""
    repo = make_repo()
    repo.add(Task(title="Buy café ☕"))
    repo.add(Task(title="Call Sam"))
    assert titles(repo, query="CAFÉ") == ["Buy café ☕"]
    assert titles(repo, query="call") == ["Call Sam"]
    assert titles(repo, query="nothing at all") == []


def test_the_filter_and_the_search_combine(make_repo):
    repo = make_repo()
    first = repo.add(Task(title="Buy milk"))
    repo.add(Task(title="Buy bread"))
    first.done = True
    repo.update(first)
    assert titles(repo, done=False, query="buy") == ["Buy bread"]


def test_a_page_starts_and_stops_where_it_is_told(make_repo):
    repo = make_repo()
    for title in ["one", "two", "three", "four"]:
        repo.add(Task(title=title))
    page, total = repo.list_tasks(limit=2, offset=1)
    assert [task.title for task in page] == ["two", "three"]
    assert total == 4


def test_the_total_counts_every_match_rather_than_the_page(make_repo):
    repo = make_repo()
    for title in ["one", "two", "three"]:
        repo.add(Task(title=title))
    page, total = repo.list_tasks(limit=1)
    assert len(page) == 1
    assert total == 3


def test_a_page_past_the_end_is_empty_and_still_counts(make_repo):
    repo = make_repo()
    repo.add(Task(title="one"))
    page, total = repo.list_tasks(limit=10, offset=10)
    assert page == []
    assert total == 1


def test_a_page_is_of_the_tasks_that_matched(make_repo):
    """The page is taken from the matches, not from the whole store."""
    repo = make_repo()
    repo.add(Task(title="Buy milk"))
    repo.add(Task(title="Buy bread"))
    repo.add(Task(title="Call Sam"))
    page, total = repo.list_tasks(query="buy", limit=1, offset=1)
    assert [task.title for task in page] == ["Buy bread"]
    assert total == 2


def test_a_search_treats_a_wildcard_as_a_character(make_repo):
    """A title holding a percent sign is found by searching for that sign."""
    repo = make_repo()
    repo.add(Task(title="Save 50% today"))
    repo.add(Task(title="Call Sam"))
    assert titles(repo, query="50%") == ["Save 50% today"]
    assert titles(repo, query="%") == ["Save 50% today"]
    assert titles(repo, query="_") == []
