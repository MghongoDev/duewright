"""Tests for the REST API, run in process against an in-memory store."""

import inspect

import pytest
from fastapi.testclient import TestClient

from duewright.api.app import create_app
from duewright.api.deps import get_service
from duewright.repositories.memory import InMemoryTaskRepository
from duewright.repositories.sqlite_repo import SqliteTaskRepository
from duewright.service import TaskService

TEST_KEY = "test-key-1234567890"
HEADER = "X-API-Key"


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


class BrokenRepository:
    """A store that fails the way a bug would, to see what the client is told."""

    def list_tasks(self, done=None, query=None):
        raise RuntimeError("something went wrong inside")

    def get(self, task_id):
        raise RuntimeError("something went wrong inside")

    def add(self, task):
        raise RuntimeError("something went wrong inside")

    def update(self, task):
        raise RuntimeError("something went wrong inside")

    def delete(self, task_id):
        raise RuntimeError("something went wrong inside")


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    """Every test runs with a key set, unless it clears it on purpose."""
    monkeypatch.setenv("DUEWRIGHT_API_KEY", TEST_KEY)
    return TEST_KEY


@pytest.fixture
def service():
    """A service over a store that keeps nothing."""
    return TaskService(InMemoryTaskRepository())


@pytest.fixture
def app(service):
    """The application, with the store swapped for the in-memory one."""
    application = create_app()
    application.dependency_overrides[get_service] = lambda: service
    return application


@pytest.fixture
def client(app):
    """A client that carries the key."""
    return TestClient(app, headers={HEADER: TEST_KEY})


@pytest.fixture
def client_without_key(app):
    """A client that carries nothing."""
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


SKIPPED_METHODS = {"HEAD", "OPTIONS"}


def routes_of(app):
    """Every route the application answers, included routers and all.

    A router keeps its own routes rather than copying them into the
    application, so the walk steps into it. Walking the real routes rather than
    the documented ones means a route hidden from the docs is still checked.
    """
    for route in app.routes:
        inner = getattr(route, "routes", None)
        if inner is None:
            inner = getattr(getattr(route, "original_router", None), "routes", None)
        if inner:
            yield from inner
        else:
            yield route


def test_the_routes_that_touch_the_store_are_not_async(app):
    """A blocking store call inside an async route would freeze the whole server."""
    touching = [
        route for route in routes_of(app) if getattr(route, "path", "").startswith("/api/v1")
    ]
    assert len(touching) >= 5
    for route in touching:
        assert not inspect.iscoroutinefunction(route.endpoint), route.path


def test_a_request_with_no_key_is_401(client_without_key):
    response = client_without_key.get("/api/v1/tasks")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_a_wrong_key_is_401(app):
    response = TestClient(app, headers={HEADER: "wrong-key-1234567890"}).get("/api/v1/tasks")
    assert response.status_code == 401


def test_the_right_key_is_200(client):
    assert client.get("/api/v1/tasks").status_code == 200


def test_health_works_without_a_key(client_without_key):
    response = client_without_key.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_a_server_with_no_key_configured_rejects_everything(app, monkeypatch):
    """Fail closed: no key set means no request is allowed, not every request."""
    monkeypatch.delenv("DUEWRIGHT_API_KEY")
    response = TestClient(app, headers={HEADER: TEST_KEY}).get("/api/v1/tasks")
    assert response.status_code == 401


def test_a_server_with_an_empty_key_configured_rejects_everything(app, monkeypatch):
    monkeypatch.setenv("DUEWRIGHT_API_KEY", "")
    response = TestClient(app, headers={HEADER: TEST_KEY}).get("/api/v1/tasks")
    assert response.status_code == 401


def test_the_key_never_appears_in_a_response_body(client):
    created = create(client, title="Buy milk")
    assert TEST_KEY not in created.text
    assert TEST_KEY not in client.get("/api/v1/tasks").text


def test_every_route_under_the_versioned_path_requires_a_key(app, client_without_key):
    """A route added later cannot be left open by accident."""
    checked = 0
    for route in routes_of(app):
        path = getattr(route, "path", "")
        if not path.startswith("/api/v1"):
            continue
        for method in route.methods - SKIPPED_METHODS:
            response = client_without_key.request(method, path.replace("{task_id}", "1"))
            assert response.status_code == 401, f"{method} {path} is not protected"
            checked += 1
    assert checked >= 5


def test_the_documented_routes_say_the_key_is_required(app):
    """So the interactive docs offer a way to send one."""
    schema = app.openapi()
    assert "X-API-Key" in str(schema["components"]["securitySchemes"])
    for path, operations in schema["paths"].items():
        if not path.startswith("/api/v1"):
            continue
        for method, operation in operations.items():
            if method.upper() not in SKIPPED_METHODS:
                assert operation.get("security"), f"{method} {path} declares no key"


def test_an_unexpected_error_is_a_plain_500(app):
    """No traceback and no file paths reach the client."""
    app.dependency_overrides[get_service] = lambda: TaskService(BrokenRepository())
    client = TestClient(app, headers={HEADER: TEST_KEY}, raise_server_exceptions=False)
    response = client.get("/api/v1/tasks")
    assert response.status_code == 500
    body = response.text
    assert "Traceback" not in body
    assert "RuntimeError" not in body
    assert "something went wrong inside" not in body
    assert "duewright" not in body


def test_the_real_store_works_through_the_api(tmp_path, monkeypatch):
    """No overrides at all, so a wiring mistake cannot hide behind a fake."""
    monkeypatch.setenv("DUEWRIGHT_DATA_DIR", str(tmp_path))
    client = TestClient(create_app(), headers={HEADER: TEST_KEY})
    created = client.post("/api/v1/tasks", json={"title": "Buy milk", "priority": "high"})
    assert created.status_code == 201
    listed = client.get("/api/v1/tasks").json()
    assert [task["title"] for task in listed["items"]] == ["Buy milk"]
    stored = SqliteTaskRepository(tmp_path / "tasks.db").list_tasks()
    assert [task.title for task in stored] == ["Buy milk"]
