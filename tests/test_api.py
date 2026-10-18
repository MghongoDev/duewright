"""Tests for the REST API, run in process against an in-memory store."""

import inspect

import pytest
from fastapi.testclient import TestClient

from duewright.api.app import create_app
from duewright.api.deps import get_service
from duewright.repositories.memory import InMemoryTaskRepository
from duewright.service import TaskService


class UntouchableRepository:
    """A store that fails if anything reaches it, which proves a route does not."""

    def list_tasks(self, done=None, query=None):
        raise AssertionError("the store was read")

    def get(self, task_id):
        raise AssertionError("the store was read")

    def add(self, task):
        raise AssertionError("the store was written")

    def update(self, task):
        raise AssertionError("the store was written")

    def delete(self, task_id):
        raise AssertionError("the store was written")


@pytest.fixture
def service():
    """A service over a store that keeps nothing."""
    return TaskService(InMemoryTaskRepository())


@pytest.fixture
def client(service):
    """A client for the app, with the store swapped for the in-memory one."""
    app = create_app()
    app.dependency_overrides[get_service] = lambda: service
    return TestClient(app)


def create(client, **body):
    """Create a task and return the response."""
    return client.post("/api/v1/tasks", json=body)


def test_creating_a_task_returns_201_and_the_task(client):
    response = create(client, title="Buy milk", priority="high")
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["title"] == "Buy milk"
    assert body["priority"] == "high"
    assert body["done"] is False
    assert body["due_date"] is None
    assert body["created_at"]


def test_listing_returns_an_envelope(client):
    create(client, title="Buy milk")
    response = client.get("/api/v1/tasks")
    assert response.status_code == 200
    body = response.json()
    assert [task["title"] for task in body["items"]] == ["Buy milk"]
    assert body["total"] == 1
    assert body["limit"] == 20
    assert body["offset"] == 0


def test_the_list_can_be_paged(client):
    for title in ("One", "Two", "Three"):
        create(client, title=title)
    body = client.get("/api/v1/tasks?limit=2&offset=1").json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["limit"] == 2
    assert body["offset"] == 1


def test_the_list_can_be_filtered_and_searched(client):
    create(client, title="Buy milk")
    create(client, title="Call Sam")
    marked = create(client, title="Book tickets").json()
    client.patch(f"/api/v1/tasks/{marked['id']}", json={"done": True})

    pending = client.get("/api/v1/tasks?done=false").json()
    assert [task["title"] for task in pending["items"]] == ["Buy milk", "Call Sam"]
    assert pending["total"] == 2

    searched = client.get("/api/v1/tasks?q=milk").json()
    assert [task["title"] for task in searched["items"]] == ["Buy milk"]
    assert searched["total"] == 1


def test_reading_one_task(client):
    created = create(client, title="Buy milk").json()
    response = client.get(f"/api/v1/tasks/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_a_missing_task_is_404_and_the_body_names_it(client):
    response = client.get("/api/v1/tasks/7")
    assert response.status_code == 404
    assert "7" in response.json()["detail"]


def test_a_partial_update_changes_only_what_it_names(client):
    created = create(client, title="Buy milk", priority="low").json()
    response = client.patch(f"/api/v1/tasks/{created['id']}", json={"title": "Buy oat milk"})
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Buy oat milk"
    assert body["priority"] == "low"
    assert body["due_date"] is None


def test_a_partial_update_can_mark_a_task_done(client):
    created = create(client, title="Buy milk").json()
    body = client.patch(f"/api/v1/tasks/{created['id']}", json={"done": True}).json()
    assert body["done"] is True


def test_an_explicit_null_clears_the_due_date(client):
    created = create(client, title="Buy milk", due_date="2026-10-05").json()
    assert created["due_date"] == "2026-10-05"
    response = client.patch(f"/api/v1/tasks/{created['id']}", json={"due_date": None})
    assert response.status_code == 200
    assert response.json()["due_date"] is None


def test_a_title_cannot_be_nulled(client):
    created = create(client, title="Buy milk").json()
    response = client.patch(f"/api/v1/tasks/{created['id']}", json={"title": None})
    assert response.status_code == 422
    assert "title" in response.json()["detail"]


def test_a_priority_cannot_be_nulled(client):
    created = create(client, title="Buy milk").json()
    response = client.patch(f"/api/v1/tasks/{created['id']}", json={"priority": None})
    assert response.status_code == 422
    assert "priority" in response.json()["detail"]


def test_updating_a_missing_task_is_404(client):
    assert client.patch("/api/v1/tasks/7", json={"title": "Buy milk"}).status_code == 404


def test_deleting_returns_204_with_no_body(client):
    created = create(client, title="Buy milk").json()
    response = client.delete(f"/api/v1/tasks/{created['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/api/v1/tasks/{created['id']}").status_code == 404


def test_deleting_a_missing_task_is_404(client):
    assert client.delete("/api/v1/tasks/7").status_code == 404


def test_health_answers_without_touching_the_store():
    """A route that never reaches the store, proved with a store that would shout."""
    app = create_app()
    app.dependency_overrides[get_service] = lambda: TaskService(UntouchableRepository())
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_a_misspelled_field_is_rejected(client):
    response = client.post("/api/v1/tasks", json={"title": "Buy milk", "prioirty": "high"})
    assert response.status_code == 422
    assert "prioirty" in str(response.json())


@pytest.mark.parametrize(
    "body",
    [
        {"title": ""},
        {"title": "   "},
        {"title": "Buy milk", "priority": "urgent"},
        {"title": "x" * 101},
        {"title": "Buy milk", "due_date": "the fifth"},
    ],
)
def test_a_body_that_makes_no_sense_is_422(client, body):
    assert client.post("/api/v1/tasks", json=body).status_code == 422


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "done=maybe"])
def test_a_bad_query_is_422(client, query):
    assert client.get(f"/api/v1/tasks?{query}").status_code == 422


@pytest.mark.parametrize("path", ["/api/v1/tasks/abc", "/api/v1/tasks/1.5"])
def test_a_non_integer_id_is_422(client, path):
    assert client.get(path).status_code == 422


def test_the_unversioned_path_is_not_there(client):
    assert client.get("/tasks").status_code == 404


def test_the_routes_that_touch_the_store_are_not_async():
    """A blocking store call inside an async route would freeze the whole server."""
    app = create_app()
    touching = [route for route in app.routes if getattr(route, "path", "").startswith("/api/v1")]
    assert touching
    for route in touching:
        assert not inspect.iscoroutinefunction(route.endpoint), route.path
