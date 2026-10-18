"""The menu and the operational commands.

This is the only module that reads input or prints, which is what keeps the
rest of the package testable and reusable.
"""

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Any, Callable, Optional

from duewright import config
from duewright.errors import (
    CorruptStorageError,
    MigrationError,
    StorageVersionError,
    TaskNotFoundError,
    UnknownBackendError,
)
from duewright.models import Task
from duewright.repositories.migrate import migrate_json
from duewright.service import TaskService, is_due_today, is_overdue
from duewright.validators import (
    clean_title,
    parse_due_date,
    parse_priority,
    parse_state,
    parse_task_id,
    parse_yes_no,
)

MENU = """
1) Add a task
2) List tasks
3) Edit a task title
4) Mark a task done / undone
5) Delete a task
6) Filter the list
7) Search titles
0) Quit
"""

TITLE_COLUMN = 24

# The address the server binds to unless it is told otherwise. It is the
# loopback address rather than every address, so starting the server does not
# put the task list on the network.
LOOPBACK = "127.0.0.1"


def show_menu() -> None:
    """Print the menu."""
    print(MENU)


def format_task(task: Task, today: date) -> str:
    """Return one line of the list for a task."""
    mark = "x" if task.done else " "
    line = f"[{mark}]  {task.id:>3}  {task.title:<{TITLE_COLUMN}}  {task.priority:<6}"
    if task.due_date is not None:
        line += f"  due {task.due_date.isoformat()}"
    if is_overdue(task, today):
        line += "  OVERDUE"
    elif is_due_today(task, today):
        line += "  DUE TODAY"
    return line.rstrip()


def print_tasks(
    service: TaskService,
    done: Optional[bool] = None,
    query: Optional[str] = None,
) -> None:
    """Print the list, or the view asked for, with a summary underneath."""
    today = date.today()
    page, total = service.list_tasks(done=done, query=query)
    if total == 0:
        filtered = done is not None or query is not None
        print("No tasks match." if filtered else "No tasks yet.")
        return
    for task in page:
        print(format_task(task, today))
    print(service.summary(today))


def prompt(question: str, parser: Callable[[str], Any], blank: Any = None) -> Any:
    """Ask until the parser accepts an answer.

    A blank answer cancels the operation and returns None, unless blank is
    given, in which case a blank answer returns that value instead. The
    priority and the due date use that, because a blank answer there means
    medium and none.
    """
    while True:
        answer = input(question)
        if not answer.strip():
            return blank
        try:
            return parser(answer)
        except ValueError as error:
            print(error)


def ask_confirm(question: str) -> bool:
    """Ask a yes or no question. A blank answer means no."""
    while True:
        answer = input(question).strip()
        if not answer:
            return False
        try:
            return parse_yes_no(answer)
        except ValueError as error:
            print(error)


def report_unreadable(error: CorruptStorageError) -> None:
    """Say what happened to a store that could not be read."""
    print(f"The store could not be read: {error}.")
    if error.spoiled_path is not None:
        print(f"It is kept as {error.spoiled_path.name}, and the list starts empty.")


def handle_add(service: TaskService) -> None:
    """Ask for a title, a priority and a due date, then show the list."""
    title = prompt("Title: ", clean_title)
    if title is None:
        print("Cancelled.")
        return
    priority = prompt(
        "Priority (low/medium/high, blank for medium): ", parse_priority, blank="medium"
    )
    if priority is None:
        print("Cancelled.")
        return
    due_date = prompt("Due date (YYYY-MM-DD, blank for none): ", parse_due_date, blank=None)
    service.add(title, priority=priority, due_date=due_date)
    print_tasks(service)


def handle_update(service: TaskService) -> None:
    """Ask for an id and a new title, then show the list."""
    task_id = prompt("Task id to edit: ", parse_task_id)
    if task_id is None:
        print("Cancelled.")
        return
    try:
        service.get(task_id)
    except TaskNotFoundError:
        print(f"No task with id {task_id}.")
        return
    title = prompt("New title: ", clean_title)
    if title is None:
        print("Cancelled.")
        return
    service.update_title(task_id, title)
    print_tasks(service)


def handle_toggle(service: TaskService) -> None:
    """Ask for an id, flip its done flag, then show the list."""
    task_id = prompt("Task id to mark: ", parse_task_id)
    if task_id is None:
        print("Cancelled.")
        return
    try:
        service.toggle_done(task_id)
    except TaskNotFoundError:
        print(f"No task with id {task_id}.")
        return
    print_tasks(service)


def handle_delete(service: TaskService) -> None:
    """Ask for an id, confirm, delete that task, then show the list."""
    task_id = prompt("Task id to delete: ", parse_task_id)
    if task_id is None:
        print("Cancelled.")
        return
    try:
        task = service.get(task_id)
    except TaskNotFoundError:
        print(f"No task with id {task_id}.")
        return
    if not ask_confirm(f"Delete task {task_id} ({task.title})? (y/N) "):
        print("Nothing was deleted.")
        return
    service.delete(task_id)
    print_tasks(service)


def handle_filter(service: TaskService) -> None:
    """Ask which tasks to show, then show that view."""
    state = prompt("Show (all/pending/done): ", parse_state, blank="all")
    if state is None:
        print("Cancelled.")
        return
    done = {"all": None, "pending": False, "done": True}[state]
    print_tasks(service, done=done)


def handle_search(service: TaskService) -> None:
    """Ask for a keyword, then show the tasks whose title contains it."""
    query = input("Search titles: ").strip()
    if not query:
        print("Cancelled.")
        return
    print_tasks(service, query=query)


def load_service() -> TaskService:
    """Build the service over whatever the settings say.

    The first read happens here, so a store that cannot be read is reported
    before the menu appears rather than when the first option is chosen.
    """
    service = TaskService(config.make_repository())
    try:
        service.list_tasks()
    except CorruptStorageError as error:
        report_unreadable(error)
    return service


def run_menu() -> None:
    """Run the menu loop until the user quits."""
    try:
        service = load_service()
    except (StorageVersionError, UnknownBackendError) as error:
        print(f"Cannot start: {error}")
        return
    print("Duewright")
    try:
        while True:
            show_menu()
            choice = input("Choose an option: ").strip()

            if choice == "0":
                print("Goodbye.")
                break
            try:
                if choice == "1":
                    handle_add(service)
                elif choice == "2":
                    print_tasks(service)
                elif choice == "3":
                    handle_update(service)
                elif choice == "4":
                    handle_toggle(service)
                elif choice == "5":
                    handle_delete(service)
                elif choice == "6":
                    handle_filter(service)
                elif choice == "7":
                    handle_search(service)
                else:
                    print(f"{choice!r} is not an option.")
            except CorruptStorageError as error:
                # Every operation reads the store, so one that breaks while the
                # menu is open surfaces here rather than at the next restart.
                report_unreadable(error)
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye.")


def run_server(arguments: list[str]) -> int:
    """Serve the task list over HTTP, and return the exit code."""
    parser = argparse.ArgumentParser(
        prog="duewright serve",
        description="Serve the task list over HTTP.",
    )
    parser.add_argument(
        "--host",
        default=LOOPBACK,
        help=f"the address to bind to (default: {LOOPBACK})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="the port to listen on (default: 8000)",
    )
    parsed = parser.parse_args(arguments)
    # Imported here rather than at the top, so the menu works without the api
    # extra installed.
    import uvicorn

    uvicorn.run(
        "duewright.api.app:create_app",
        factory=True,
        host=parsed.host,
        port=parsed.port,
    )
    return 0


def run_migration(arguments: list[str]) -> int:
    """Move a task file into the database, and return the exit code."""
    parser = argparse.ArgumentParser(
        prog="duewright migrate-json",
        description="Move the tasks from a JSON file into the database.",
    )
    parser.add_argument("path", type=Path, help="the JSON file to read")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="read the file and check it without writing anything",
    )
    parsed = parser.parse_args(arguments)
    database = config.data_dir() / config.DATABASE_FILE_NAME
    try:
        report = migrate_json(parsed.path, database, dry_run=parsed.dry_run)
    except (MigrationError, CorruptStorageError, StorageVersionError) as error:
        print(f"Nothing was moved: {error}.")
        return 1
    if not report.written:
        print(f"The file holds {report.source_count} tasks, and nothing was written.")
        print("This was a dry run.")
        return 0
    print(f"Moved {report.source_count} tasks into {database}.")
    print("They were read back and compared, and every field matched.")
    return 0


# The operational commands, by the word that starts them. A bare duewright is
# the menu.
COMMANDS = {"migrate-json": run_migration, "serve": run_server}


def main() -> None:
    """Run the menu, or one of the operational commands."""
    arguments = sys.argv[1:]
    if not arguments:
        run_menu()
        return
    command = COMMANDS.get(arguments[0])
    if command is None:
        print(f"{arguments[0]!r} is not a command. The commands are {', '.join(COMMANDS)}.")
        print("Run duewright with no arguments for the menu.")
        raise SystemExit(2)
    raise SystemExit(command(arguments[1:]))
