"""The REST API.

Every route that reaches the store is a plain function rather than an async
one, because the store it reaches blocks. FastAPI runs a plain function in a
worker thread, so a slow store delays that one request instead of the whole
server.
"""

from importlib.metadata import PackageNotFoundError, version
from typing import Annotated, Optional, TypeAlias

from fastapi import Depends, FastAPI, Query, Request, status
from fastapi.responses import JSONResponse

from duewright.api.deps import get_service
from duewright.api.schemas import TaskIn, TaskOut, TaskPage, TaskUpdate
from duewright.errors import InvalidTaskError, TaskNotFoundError
from duewright.service import TaskService

API_PREFIX = "/api/v1"
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# The service a route works through. A test swaps it for one over an in-memory
# store by overriding get_service.
ServiceDep: TypeAlias = Annotated[TaskService, Depends(get_service)]


def app_version() -> str:
    """Return the version of the installed package."""
    try:
        return version("duewright")
    except PackageNotFoundError:
        return "unknown"


def create_app() -> FastAPI:
    """Build the application."""
    app = FastAPI(
        title="Duewright",
        summary="The task list over HTTP.",
        version=app_version(),
    )
    register_error_handlers(app)
    register_routes(app)
    return app


def register_error_handlers(app: FastAPI) -> None:
    """Map the service's errors onto status codes, in one place."""

    @app.exception_handler(TaskNotFoundError)
    def task_not_found(request: Request, error: Exception) -> JSONResponse:
        """Answer 404, with a body that names the task that was not there."""
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(error)},
        )

    @app.exception_handler(InvalidTaskError)
    def invalid_task(request: Request, error: Exception) -> JSONResponse:
        """Answer 422, with the rule that was broken."""
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": str(error)},
        )


def register_routes(app: FastAPI) -> None:
    """Add the routes."""

    @app.get("/health", tags=["health"], summary="Report that the server is up")
    def health() -> dict[str, str]:
        """Answer without touching the store."""
        return {"status": "ok"}

    @app.get(
        f"{API_PREFIX}/tasks",
        response_model=TaskPage,
        tags=["tasks"],
        summary="List tasks",
    )
    def list_tasks(
        service: ServiceDep,
        done: Optional[bool] = Query(None, description="true for done, false for pending"),
        q: Optional[str] = Query(None, description="a word the title contains"),
        limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
        offset: int = Query(0, ge=0),
    ) -> TaskPage:
        """Return one page of tasks in display order, and how many matched."""
        items, total = service.list_tasks(done=done, query=q, limit=limit, offset=offset)
        return TaskPage(
            items=[TaskOut.model_validate(task) for task in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    @app.post(
        f"{API_PREFIX}/tasks",
        response_model=TaskOut,
        status_code=status.HTTP_201_CREATED,
        tags=["tasks"],
        summary="Create a task",
    )
    def create_task(body: TaskIn, service: ServiceDep) -> TaskOut:
        """Create a pending task and return it."""
        task = service.add(body.title, priority=body.priority, due_date=body.due_date)
        return TaskOut.model_validate(task)

    @app.get(
        f"{API_PREFIX}/tasks/{{task_id}}",
        response_model=TaskOut,
        tags=["tasks"],
        summary="Read one task",
    )
    def read_task(task_id: int, service: ServiceDep) -> TaskOut:
        """Return one task, or 404 when no task carries that id."""
        return TaskOut.model_validate(service.get(task_id))

    @app.patch(
        f"{API_PREFIX}/tasks/{{task_id}}",
        response_model=TaskOut,
        tags=["tasks"],
        summary="Change the parts of a task the body names",
    )
    def update_task(task_id: int, body: TaskUpdate, service: ServiceDep) -> TaskOut:
        """Change a task. A field the body leaves out keeps the value it has."""
        changes = body.model_dump(exclude_unset=True)
        return TaskOut.model_validate(service.change(task_id, changes))

    @app.delete(
        f"{API_PREFIX}/tasks/{{task_id}}",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["tasks"],
        summary="Delete a task",
    )
    def delete_task(task_id: int, service: ServiceDep) -> None:
        """Delete a task. The id is not handed out again."""
        service.delete(task_id)
