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


@pytest.fixture(params=["json", "memory"])
def make_repo(request, tmp_path):
    """Build a repository. Calling it twice means the same store, restarted."""
    shared = InMemoryTaskRepository()

    def factory():
        if request.param == "json":
            return JsonTaskRepository(tmp_path / "tasks.json")
        return shared

    return factory


def test_a_missing_store_starts_empty(make_repo):
    assert make_repo().list_tasks() == []


def test_ids_are_never_reused(make_repo):
    """A deleted id is not handed to a different task (see docs/adr/0002)."""
    repo = make_repo()
    first = repo.add(Task(title="Buy milk"))
    repo.delete(first.id)
    second = repo.add(Task(title="Call Sam"))
    assert second.id > first.id


def test_a_restart_keeps_the_tasks(make_repo):
    make_repo().add(Task(title="Buy milk"))
    assert [task.title for task in make_repo().list_tasks()] == ["Buy milk"]


def test_the_tasks_come_back_in_the_order_they_were_added(make_repo):
    repo = make_repo()
    for title in ["first", "second", "third"]:
        repo.add(Task(title=title))
    assert [task.title for task in repo.list_tasks()] == ["first", "second", "third"]


def test_a_round_trip_keeps_every_field(make_repo):
    repo = make_repo()
    repo.add(Task(title="Pay the rent", priority="high", due_date=date(2026, 10, 5)))
    task = make_repo().list_tasks()[0]
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
    assert repo.list_tasks() == []


def test_deleting_a_middle_task_leaves_the_others_alone(make_repo):
    repo = make_repo()
    for title in ["first", "second", "third"]:
        repo.add(Task(title=title))
    repo.delete(2)
    assert [task.title for task in repo.list_tasks()] == ["first", "third"]


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
    assert [task.title for task in repo.list_tasks(done=False)] == ["pending"]
    assert [task.title for task in repo.list_tasks(done=True)] == ["done"]
    assert len(repo.list_tasks()) == 2


def test_the_search_ignores_case_and_matches_accents(make_repo):
    repo = make_repo()
    repo.add(Task(title="Buy café ☕"))
    repo.add(Task(title="Call Sam"))
    assert [task.title for task in repo.list_tasks(query="CAFÉ")] == ["Buy café ☕"]
    assert [task.title for task in repo.list_tasks(query="call")] == ["Call Sam"]
    assert repo.list_tasks(query="nothing at all") == []


def test_the_filter_and_the_search_combine(make_repo):
    repo = make_repo()
    first = repo.add(Task(title="Buy milk"))
    repo.add(Task(title="Buy bread"))
    first.done = True
    repo.update(first)
    assert [task.title for task in repo.list_tasks(done=False, query="buy")] == ["Buy bread"]
