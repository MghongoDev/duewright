"""The menu.

This is the only module that reads input or prints, which is what keeps the
rest of the package testable and reusable.
"""

from datetime import date
from pathlib import Path
from typing import Any, Callable, Optional

from duewright import config
from duewright.manager import TaskManager, TaskNotFoundError, is_due_today, is_overdue
from duewright.models import Task
from duewright.storage import (
    CorruptStorageError,
    StorageVersionError,
    load_tasks,
    save_tasks,
)
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

TASKS_FILE_NAME = "tasks.json"

TITLE_COLUMN = 24


def tasks_file() -> Path:
    """Return the task file inside the per-user data folder.

    The folder comes from the configuration, so the file no longer depends on
    where the code is installed or on the folder the menu was started from.
    """
    return config.data_dir() / TASKS_FILE_NAME


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


def print_tasks(manager: TaskManager, tasks: Optional[list[Task]] = None) -> None:
    """Print the given tasks, or the whole list, with a summary underneath."""
    today = date.today()
    if not manager.all():
        print("No tasks yet.")
        return
    shown = manager.list_tasks() if tasks is None else tasks
    if not shown:
        print("No tasks match.")
    else:
        for task in shown:
            print(format_task(task, today))
    print(manager.summary(today))


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


def commit(manager: TaskManager) -> None:
    """Write the current tasks to disk, reporting a write that fails."""
    try:
        save_tasks(tasks_file(), manager.all(), manager.next_id)
    except OSError as error:
        print(f"Your change was not saved: {error}")
        print("It will be lost when you quit.")


def handle_add(manager: TaskManager) -> None:
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
    due_date = prompt(
        "Due date (YYYY-MM-DD, blank for none): ", parse_due_date, blank=None
    )
    manager.add(title, priority=priority, due_date=due_date)
    commit(manager)
    print_tasks(manager)


def handle_update(manager: TaskManager) -> None:
    """Ask for an id and a new title, then show the list."""
    task_id = prompt("Task id to edit: ", parse_task_id)
    if task_id is None:
        print("Cancelled.")
        return
    try:
        manager.get(task_id)
    except TaskNotFoundError:
        print(f"No task with id {task_id}.")
        return
    title = prompt("New title: ", clean_title)
    if title is None:
        print("Cancelled.")
        return
    manager.update_title(task_id, title)
    commit(manager)
    print_tasks(manager)


def handle_toggle(manager: TaskManager) -> None:
    """Ask for an id, flip its done flag, then show the list."""
    task_id = prompt("Task id to mark: ", parse_task_id)
    if task_id is None:
        print("Cancelled.")
        return
    try:
        manager.toggle_done(task_id)
    except TaskNotFoundError:
        print(f"No task with id {task_id}.")
        return
    commit(manager)
    print_tasks(manager)


def handle_delete(manager: TaskManager) -> None:
    """Ask for an id, confirm, delete that task, then show the list."""
    task_id = prompt("Task id to delete: ", parse_task_id)
    if task_id is None:
        print("Cancelled.")
        return
    try:
        task = manager.get(task_id)
    except TaskNotFoundError:
        print(f"No task with id {task_id}.")
        return
    if not ask_confirm(f"Delete task {task_id} ({task.title})? (y/N) "):
        print("Nothing was deleted.")
        return
    manager.delete(task_id)
    commit(manager)
    print_tasks(manager)


def handle_filter(manager: TaskManager) -> None:
    """Ask which tasks to show, then show that view."""
    state = prompt("Show (all/pending/done): ", parse_state, blank="all")
    if state is None:
        print("Cancelled.")
        return
    done = {"all": None, "pending": False, "done": True}[state]
    print_tasks(manager, manager.list_tasks(done=done))


def handle_search(manager: TaskManager) -> None:
    """Ask for a keyword, then show the tasks whose title contains it."""
    query = input("Search titles: ").strip()
    if not query:
        print("Cancelled.")
        return
    print_tasks(manager, manager.list_tasks(query=query))


def load_manager() -> TaskManager:
    """Build a manager from the task file, reporting a file it cannot read."""
    path = tasks_file()
    try:
        tasks, next_id = load_tasks(path)
    except CorruptStorageError as error:
        print(f"{path.name} could not be read: {error}.")
        print(f"It is kept as {error.spoiled_path.name}, and Duewright is starting empty.")
        tasks, next_id = [], 1
    except OSError as error:
        print(f"Could not read {path.name}: {error}")
        print("Duewright is starting with an empty list.")
        tasks, next_id = [], 1
    return TaskManager(tasks, next_id)


def main() -> None:
    """Load the tasks, then run the menu loop until the user quits."""
    try:
        manager = load_manager()
    except StorageVersionError as error:
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
            elif choice == "1":
                handle_add(manager)
            elif choice == "2":
                print_tasks(manager)
            elif choice == "3":
                handle_update(manager)
            elif choice == "4":
                handle_toggle(manager)
            elif choice == "5":
                handle_delete(manager)
            elif choice == "6":
                handle_filter(manager)
            elif choice == "7":
                handle_search(manager)
            else:
                print(f"{choice!r} is not an option.")
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye.")
